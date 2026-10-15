#!/usr/bin/env python3
"""Short-lived SSM-side PostgreSQL probe; credentials are resolved in AWS."""

import json
import re
import sys
from contextlib import closing

secret_arn, host, operation, table_name, marker = sys.argv[1:6]
if not re.fullmatch(r"dr_probe_[0-9]{14}", table_name):
    raise SystemExit("invalid probe table")

import boto3
import psycopg2
from psycopg2 import sql

if operation == "preflight":
    print(
        json.dumps(
            {
                "runtime": "ready",
                "python": sys.version.split()[0],
                "boto3": boto3.__version__,
                "psycopg2": psycopg2.__version__,
            },
            separators=(",", ":"),
        )
    )
    raise SystemExit(0)

BUSINESS_TABLES = (
    "companies",
    "portal_users",
    "audit_log",
    "orders",
    "outbox_events",
    "erp_partners",
    "erp_products",
    "erp_sales_orders",
    "erp_sales_order_lines",
    "erp_purchase_orders",
    "erp_purchase_order_lines",
    "erp_financial_documents",
    "internal_messages",
    "internal_mail_delivery",
)


def business_counts(cursor):
    cursor.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
    )
    available = {row[0] for row in cursor.fetchall()}
    counts = {}
    for name in BUSINESS_TABLES:
        if name in available:
            cursor.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier("public", name)))
            counts[name] = cursor.fetchone()[0]
    return counts

secret_region = secret_arn.split(":")[3]
secret = boto3.client("secretsmanager", region_name=secret_region).get_secret_value(
    SecretId=secret_arn
)
credentials = json.loads(secret["SecretString"])
with closing(
    psycopg2.connect(
        host=host,
        port=5432,
        dbname="tangamandapio",
        user=credentials["username"],
        password=credentials["password"],
        connect_timeout=8,
        sslmode="require",
    )
) as connection:
    connection.autocommit = False
    with connection.cursor() as cursor:
        table = sql.Identifier("public", table_name)
        if operation == "create":
            cursor.execute(
                sql.SQL("CREATE TABLE {} (marker text PRIMARY KEY, committed_at timestamptz NOT NULL DEFAULT clock_timestamp())").format(table)
            )
            cursor.execute(
                sql.SQL("INSERT INTO {} (marker) VALUES (%s) RETURNING committed_at").format(table),
                (marker,),
            )
            committed_at = cursor.fetchone()[0].isoformat()
            counts = business_counts(cursor)
            connection.commit()
            result = {"marker_present": True, "committed_at": committed_at, "business_counts": counts}
        elif operation == "verify":
            cursor.execute(
                sql.SQL("SELECT committed_at FROM {} WHERE marker = %s").format(table),
                (marker,),
            )
            row = cursor.fetchone()
            counts = business_counts(cursor)
            connection.commit()
            result = {
                "marker_present": row is not None,
                "committed_at": row[0].isoformat() if row else None,
                "business_counts": counts,
            }
        elif operation == "drop":
            cursor.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(table))
            connection.commit()
            result = {"marker_table_removed": True}
        else:
            raise SystemExit("invalid operation")

print(json.dumps(result, separators=(",", ":")))
