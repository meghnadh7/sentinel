from __future__ import annotations
"""Slack webhooks + HITL approval workflow."""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from sentinel.config import get_settings

settings = get_settings()
UTC = timezone.utc


def _format_fairness_alert(model_id: str, alert_level: str, message: str) -> dict[str, Any]:
    emoji = ":rotating_light:" if alert_level == "action" else ":warning:"
    color = "#FF0000" if alert_level == "action" else "#FFA500"
    return {
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{emoji} Sentinel Alert — {alert_level.upper()}",
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Model:*
`{model_id}`"},
                            {"type": "mrkdwn", "text": f"*Alert Level:*
{alert_level.upper()}"},
                            {"type": "mrkdwn", "text": f"*Time:*
{datetime.now(UTC).isoformat()}"},
                            {"type": "mrkdwn", "text": f"*Message:*
{message}"},
                        ],
                    },
                ],
            }
        ]
    }


def _format_hitl_prompt(alert_id: str, model_id: str, message: str) -> dict[str, Any]:
    return {
        "attachments": [
            {
                "color": "#FF0000",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": ":stop_sign: HUMAN APPROVAL REQUIRED — MODEL FREEZE PENDING",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"*Model:* `{model_id}`
"
                                f"*Alert ID:* `{alert_id}`
"
                                f"*Issue:* {message}

"
                                "An 'action'-level fairness alert has been triggered. "
                                "Model freeze requires HITL approval within 24 hours.

"
                                f"To approve: `POST /api/alerts/{alert_id}/approve`
"
                                f"To reject: `POST /api/alerts/{alert_id}/reject`"
                            ),
                        },
                    },
                ],
            }
        ]
    }


async def _post_to_slack(payload: dict[str, Any]) -> bool:
    if not settings.slack_webhook_url:
        print(f"[Slack] WEBHOOK NOT CONFIGURED — would send: {payload.get('attachments', [{}])[0].get('blocks', [{}])[0]}")
        return True

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.slack_webhook_url,
                json=payload,
                timeout=10.0,
            )
            return response.status_code == 200
    except Exception as e:
        print(f"[Slack] Failed to send alert: {e}")
        return False


async def send_alert(
    model_id: str,
    alert_type: str,
    alert_level: str,
    message: str,
) -> str:
    """Send a Slack alert and create a DB alert record. Returns alert_id."""
    from sentinel.data.database import AsyncSessionLocal
    from sentinel.data.models import Alert

    alert_id = str(uuid.uuid4())
    hitl_required = alert_level == "action"

    async with AsyncSessionLocal() as session:
        alert = Alert(
            id=alert_id,
            model_id=model_id,
            alert_type=alert_type,
            alert_level=alert_level,
            message=message,
            hitl_required=hitl_required,
        )
        session.add(alert)
        await session.commit()

    payload = _format_fairness_alert(model_id, alert_level, message)
    await _post_to_slack(payload)

    if hitl_required:
        hitl_payload = _format_hitl_prompt(alert_id, model_id, message)
        await _post_to_slack(hitl_payload)

    return alert_id


async def wait_for_hitl_approval(
    alert_id: str,
    timeout_seconds: int | None = None,
) -> bool:
    """Block until HITL approval is received or timeout expires."""
    timeout = timeout_seconds or settings.hitl_approval_timeout_seconds
    from sentinel.data.feature_store import FeatureStore

    fs = FeatureStore()
    elapsed = 0
    poll_interval = 30

    while elapsed < timeout:
        approval = await fs.get_hitl_approval(alert_id)
        if approval == "approved":
            return True
        if approval == "rejected":
            return False
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    return False
