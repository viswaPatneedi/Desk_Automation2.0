#!/usr/bin/env python3
"""Harden PostgreSQL table access for the dashboard.

Goal:
- Make tables private at DB layer.
- Remove access from PUBLIC role.
- Grant access only to the application DB role.

Note:
- This script typically requires a privileged database user (table owner/superuser)
  because current tables are owned by postgres.
"""

import os
import sys

import psycopg2

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config.flask_database import DatabaseConfig


def run_hardening():
    cfg = DatabaseConfig()
    app_role = cfg.user

    statements = [
        "REVOKE ALL ON SCHEMA public FROM PUBLIC;",
        "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;",
        "REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC;",
        f"GRANT USAGE ON SCHEMA public TO {app_role};",
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {app_role};",
        f"GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {app_role};",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC;",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM PUBLIC;",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {app_role};",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {app_role};",
    ]

    conn = psycopg2.connect(
        host=cfg.host,
        port=cfg.port,
        database=cfg.database,
        user=cfg.user,
        password=cfg.password,
    )

    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
        conn.commit()
        print("OK: Database privacy hardening applied.")
        print(f"App role with access: {app_role}")
        return 0
    except Exception as exc:
        conn.rollback()
        print("ERROR: Unable to apply hardening with current DB role.")
        print(str(exc))
        print("Hint: Run this with table owner/superuser or grant ownership/privileges first.")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(run_hardening())
