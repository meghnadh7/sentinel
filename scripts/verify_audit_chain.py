from __future__ import annotations
#!/usr/bin/env python3
"""Verify the integrity of the hash-chained audit log."""

import asyncio
import sys

from rich.console import Console
from rich.table import Table

sys.path.insert(0, ".")

from sentinel.data.database import AsyncSessionLocal
from sentinel.data.audit_log import verify_audit_chain

console = Console()


async def main() -> None:
    console.print("[bold blue]Sentinel Audit Chain Verification[/bold blue]")
    console.print("=" * 50)

    async with AsyncSessionLocal() as session:
        is_valid, total, errors = await verify_audit_chain(session)

    if is_valid:
        console.print(f"[bold green]✓ chain intact: 100% valid[/bold green]")
        console.print(f"  Total entries verified: {total}")
    else:
        console.print(f"[bold red]✗ chain COMPROMISED — {len(errors)} error(s) found[/bold red]")
        console.print(f"  Total entries checked: {total}")
        console.print()

        table = Table(title="Chain Errors", show_header=True)
        table.add_column("Error", style="red")
        for err in errors:
            table.add_row(err)
        console.print(table)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
