-- Grant all privileges on sentinel_db to the sentinel user.
-- Table-level INSERT-only restriction on audit_log is enforced at app startup
-- after SQLAlchemy creates the tables (see sentinel/data/database.py).
GRANT ALL PRIVILEGES ON sentinel_db.* TO 'sentinel'@'%';
FLUSH PRIVILEGES;
