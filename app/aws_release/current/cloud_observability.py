"""Read-only CloudWatch metrics used by the platform operations console."""

from datetime import datetime, timedelta, timezone


WINDOWS = {60, 360, 1440}


def _metric_query(metric_id, label, namespace, metric_name, dimensions, statistic, period):
    return {
        "Id": metric_id,
        "Label": label,
        "MetricStat": {
            "Metric": {
                "Namespace": namespace,
                "MetricName": metric_name,
                "Dimensions": [
                    {"Name": name, "Value": value}
                    for name, value in dimensions.items()
                ],
            },
            "Period": period,
            "Stat": statistic,
        },
        "ReturnData": True,
    }


def build_queries(config, period):
    """Build only queries for resources explicitly configured by deployment."""
    queries = []
    load_balancer = config.get("CLOUDWATCH_LOAD_BALANCER_FULL_NAME", "").strip()
    target_group = config.get("CLOUDWATCH_TARGET_GROUP_FULL_NAME", "").strip()
    if load_balancer and target_group:
        alb_dimensions = {"LoadBalancer": load_balancer}
        target_dimensions = {
            "LoadBalancer": load_balancer,
            "TargetGroup": target_group,
        }
        queries.extend(
            [
                _metric_query("alb_requests", "Solicitudes al ALB", "AWS/ApplicationELB", "RequestCount", alb_dimensions, "Sum", period),
                _metric_query("alb_p95", "Latencia p95", "AWS/ApplicationELB", "TargetResponseTime", target_dimensions, "p95", period),
                _metric_query("alb_5xx", "Errores 5xx", "AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", target_dimensions, "Sum", period),
                _metric_query("alb_healthy", "Destinos saludables", "AWS/ApplicationELB", "HealthyHostCount", target_dimensions, "Average", period),
                _metric_query("alb_unhealthy", "Destinos no saludables", "AWS/ApplicationELB", "UnHealthyHostCount", target_dimensions, "Maximum", period),
            ]
        )

    database_id = config.get("CLOUDWATCH_RDS_INSTANCE_ID", "").strip()
    if database_id:
        rds_dimensions = {"DBInstanceIdentifier": database_id}
        queries.extend(
            [
                _metric_query("rds_cpu", "CPU de RDS", "AWS/RDS", "CPUUtilization", rds_dimensions, "Average", period),
                _metric_query("rds_connections", "Conexiones RDS", "AWS/RDS", "DatabaseConnections", rds_dimensions, "Average", period),
            ]
        )

    asg_name = config.get("CLOUDWATCH_AUTO_SCALING_GROUP", "").strip()
    if asg_name:
        asg_dimensions = {"AutoScalingGroupName": asg_name}
        queries.extend(
            [
                _metric_query("asg_in_service", "Instancias en servicio", "AWS/AutoScaling", "GroupInServiceInstances", asg_dimensions, "Average", period),
                _metric_query("asg_desired", "Capacidad deseada", "AWS/AutoScaling", "GroupDesiredCapacity", asg_dimensions, "Average", period),
            ]
        )

    web_acl = config.get("CLOUDWATCH_WAF_WEB_ACL_NAME", "").strip()
    waf_region = config.get("CLOUDWATCH_WAF_REGION", "").strip()
    if web_acl and waf_region:
        waf_dimensions = {"WebACL": web_acl, "Rule": "ALL", "Region": waf_region}
        queries.extend(
            [
                _metric_query("waf_blocked", "Solicitudes bloqueadas por WAF", "AWS/WAFV2", "BlockedRequests", waf_dimensions, "Sum", period),
                _metric_query("waf_allowed", "Solicitudes permitidas por WAF", "AWS/WAFV2", "AllowedRequests", waf_dimensions, "Sum", period),
            ]
        )
    return queries


def collect_cloudwatch_metrics(config, window_minutes=60, now=None):
    """Return CloudWatch datapoints without leaking provider error details."""
    if window_minutes not in WINDOWS:
        raise ValueError("unsupported_metrics_window")
    period = 60 if window_minutes == 60 else 300 if window_minutes == 360 else 3600
    queries = build_queries(config, period)
    if not queries:
        return {
            "status": "not_configured",
            "window_minutes": window_minutes,
            "period_seconds": period,
            "metrics": {},
        }

    client = config.get("CLOUDWATCH_CLIENT")
    try:
        if client is None:
            import boto3

            region = config.get("CLOUDWATCH_REGION_NAME") or config.get("AWS_REGION_NAME") or None
            client = boto3.client("cloudwatch", region_name=region)
        end_time = now or datetime.now(timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        response = client.get_metric_data(
            MetricDataQueries=queries,
            StartTime=end_time - timedelta(minutes=window_minutes),
            EndTime=end_time,
            ScanBy="TimestampAscending",
        )
    except Exception as error:
        error_code = getattr(error, "response", {}).get("Error", {}).get("Code", "")
        status = "access_denied" if error_code in {"AccessDenied", "AccessDeniedException", "UnauthorizedOperation"} else "unavailable"
        return {
            "status": status,
            "window_minutes": window_minutes,
            "period_seconds": period,
            "metrics": {},
        }

    metrics = {}
    partial_data = False
    for result in response.get("MetricDataResults", []):
        partial_data = partial_data or result.get("StatusCode", "Complete") != "Complete"
        datapoints = sorted(
            zip(result.get("Timestamps", []), result.get("Values", [])),
            key=lambda item: item[0],
        )
        metrics[result.get("Id", "")] = {
            "label": result.get("Label", result.get("Id", "")),
            "status": result.get("StatusCode", "Complete"),
            "latest": datapoints[-1][1] if datapoints else None,
            "points": [
                {"timestamp": timestamp.astimezone(timezone.utc).isoformat(), "value": value}
                for timestamp, value in datapoints
            ],
        }
    has_datapoints = any(item["points"] for item in metrics.values())
    return {
        "status": "partial" if partial_data else "ok" if has_datapoints else "no_data",
        "window_minutes": window_minutes,
        "period_seconds": period,
        "metrics": metrics,
    }
