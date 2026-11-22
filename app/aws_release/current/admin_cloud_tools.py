import hashlib
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode
from urllib.request import HTTPRedirectHandler, build_opener
from uuid import uuid4
from xml.etree import ElementTree

BACKUP_PREFIX = "dr/postgres/manual-outbox/"
AZURE_PREFIX = "postgres/"
MANUAL_NAME = re.compile(r"\d{8}T\d{6}Z-[a-f0-9]{12}\.json")
AZURE_NAME = re.compile(r"(?:\d{8}-(?:daily|manual-validation)|\d{8}T\d{6}Z-[a-f0-9]{12})\.json")
RESTORE_ACTION = "portal-capacity-test-restore"


class BackupTooLarge(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def technical_test_results():
    evidence = Path(__file__).with_name("technical-tests.json")
    return json.loads(evidence.read_text(encoding="utf-8"))


def aws_client(service, config):
    import boto3
    from botocore.config import Config

    return boto3.client(service, region_name=config.get("AWS_REGION_NAME") or None,
                        config=Config(connect_timeout=2, read_timeout=5, retries={"total_max_attempts": 2}))


def take_checkpoint(connection, postgres):
    connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY" if postgres else "BEGIN")
    now = datetime.now(timezone.utc)
    name = f"{now:%Y%m%dT%H%M%SZ}-{uuid4().hex[:12]}.json"
    contents = {"format": "tangamandapio-outbox-v1", "created_at": now.isoformat()}
    for table in ("orders", "outbox_events"):
        rows = connection.execute(f"SELECT * FROM {table} LIMIT 5001").fetchall()
        if len(rows) > 5000:
            raise BackupTooLarge
        contents[table] = [dict(row) for row in rows]
    data = json.dumps(contents, ensure_ascii=False, default=str, separators=(",", ":")).encode("utf-8")
    if len(data) > 16 * 1024 * 1024:
        raise BackupTooLarge
    return name, data, len(contents["outbox_events"])


def save_checkpoint(config, name, data):
    checksum = hashlib.sha256(data).hexdigest()
    aws_client("s3", config).put_object(
        Bucket=config["ADMIN_BACKUP_BUCKET"], Key=BACKUP_PREFIX + name, Body=data,
        ServerSideEncryption="AES256", ContentType="application/json", IfNoneMatch="*",
        Metadata={"sha256": checksum},
    )
    return checksum


def aws_backups(config):
    items = []
    client = aws_client("s3", config)
    pages = client.get_paginator("list_objects_v2").paginate(Bucket=config["ADMIN_BACKUP_BUCKET"], Prefix=BACKUP_PREFIX)
    for page in pages:
        for item in page.get("Contents", []):
            name = item["Key"].removeprefix(BACKUP_PREFIX)
            if MANUAL_NAME.fullmatch(name):
                items.append({"name": name, "bytes": item["Size"], "date": item["LastModified"].isoformat()})
    return sorted(items, key=lambda item: item["name"], reverse=True)[:50]


def azure_endpoint(config):
    account = config["ADMIN_AZURE_BACKUP_ACCOUNT"]
    container = config["ADMIN_AZURE_BACKUP_CONTAINER"]
    if not re.fullmatch(r"[a-z0-9]{3,24}", account) or not re.fullmatch(r"[a-z0-9-]{3,63}", container):
        raise ValueError("invalid_backup_container")
    sas = aws_client("ssm", config).get_parameter(
        Name=config["ADMIN_AZURE_BACKUP_PARAMETER"], WithDecryption=True,
    )["Parameter"]["Value"].lstrip("?")
    fields = parse_qs(sas)
    if fields.get("sp") != ["rl"] or fields.get("sr") != ["c"] or fields.get("spr") != ["https"]:
        raise ValueError("invalid_backup_authorization")
    return f"https://{account}.blob.core.windows.net/{container}", sas


def azure_backups(config):
    endpoint, sas = azure_endpoint(config)
    opener = build_opener(NoRedirect())
    items = []
    marker = ""
    for _ in range(10):
        query = urlencode({"restype": "container", "comp": "list", "prefix": AZURE_PREFIX,
                           "maxresults": 250, "marker": marker})
        with opener.open(f"{endpoint}?{query}&{sas}", timeout=4) as response:
            page = ElementTree.fromstring(response.read(512 * 1024))
        for blob in page.findall("./Blobs/Blob"):
            name = blob.findtext("Name", "").removeprefix(AZURE_PREFIX)
            if AZURE_NAME.fullmatch(name):
                modified = parsedate_to_datetime(blob.findtext("Properties/Last-Modified", ""))
                items.append({"name": name, "bytes": int(blob.findtext("Properties/Content-Length", "0")),
                              "date": modified.isoformat()})
        marker = page.findtext("NextMarker")
        if not marker:
            break
    else:
        raise ValueError("backup_listing_limit")
    return sorted(items, key=lambda item: item["date"], reverse=True)[:50]


def open_backup(config, source, name):
    if source == "aws" and MANUAL_NAME.fullmatch(name) and config["ADMIN_BACKUP_BUCKET"]:
        return aws_client("s3", config).get_object(Bucket=config["ADMIN_BACKUP_BUCKET"], Key=BACKUP_PREFIX + name)["Body"]
    if source == "azure" and AZURE_NAME.fullmatch(name) and config["ADMIN_AZURE_BACKUP_PARAMETER"] and config["ADMIN_AZURE_BACKUP_ACCOUNT"]:
        endpoint, sas = azure_endpoint(config)
        return build_opener(NoRedirect()).open(f"{endpoint}/{AZURE_PREFIX}{quote(name)}?{sas}", timeout=8)
    raise FileNotFoundError


def read_scaling_group(client, group_name):
    groups = client.describe_auto_scaling_groups(AutoScalingGroupNames=[group_name])["AutoScalingGroups"]
    if not groups:
        raise FileNotFoundError
    group = groups[0]
    actions = client.describe_scheduled_actions(AutoScalingGroupName=group_name,
                                                ScheduledActionNames=[RESTORE_ACTION])["ScheduledUpdateGroupActions"]
    policies = client.describe_policies(AutoScalingGroupName=group_name,
                                       PolicyTypes=["TargetTrackingScaling"])["ScalingPolicies"]
    tracking = (policy.get("TargetTrackingConfiguration", {}) for policy in policies
                if policy.get("Enabled", True))
    request_target = next((config["TargetValue"] for config in tracking if
                           config.get("PredefinedMetricSpecification", {}).get("PredefinedMetricType")
                           == "ALBRequestCountPerTarget"), None)
    active = sum(instance["LifecycleState"] == "InService" and instance["HealthStatus"] == "Healthy"
                 for instance in group["Instances"])
    return {"minimum": group["MinSize"], "maximum": group["MaxSize"], "desired": group["DesiredCapacity"],
            "healthy": active, "request_target_active": request_target is not None and not any(
                item["ProcessName"] in {"AlarmNotification", "Launch"} for item in group.get("SuspendedProcesses", [])
            ), "requests_per_target": request_target,
            "restore_at": actions[0]["StartTime"].isoformat() if actions else None}
