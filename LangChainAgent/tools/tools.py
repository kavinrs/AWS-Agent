"""
AWS Tools for LangChain Agent - Consolidated Single File

Three powerful tools:
1. aws_cloud_control - Handle ANY AWS resource (S3, EC2, RDS, Lambda, DynamoDB, etc.)
2. cloudwatch_logs - Query CloudWatch Logs for debugging and monitoring
3. final_answer - Return final response to user
"""

import json
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field


def get_cc_client(region: str = "us-east-1"):
    """Create and return a CloudControl API client."""
    return boto3.client("cloudcontrol", region_name=region)


def wait_for_progress(client, request_token: str, timeout: int = 60) -> dict:
    """Poll until a mutating operation completes or times out."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get_resource_request_status(RequestToken=request_token)
        status = resp["ProgressEvent"]
        op_status = status["OperationStatus"]

        if op_status in ("SUCCESS", "FAILED", "CANCEL_COMPLETE"):
            return status

        time.sleep(3)

    return {"OperationStatus": "TIMEOUT", "StatusMessage": "Operation timed out after 60s"}


class CloudControlInput(BaseModel):
    """Input schema for AWS Cloud Control tool."""
    operation: str = Field(
        description='One of "create" | "read" | "update" | "delete" | "list"'
    )
    resource_type: str = Field(
        description='AWS CloudFormation resource type, e.g., "AWS::S3::Bucket", "AWS::EC2::Instance"'
    )
    identifier: str = Field(
        default="",
        description="Resource identifier for read/update/delete. Leave empty for list/create."
    )
    properties: Optional[dict] = Field(
        default=None,
        description="Dict of resource properties for create/update. Leave as None for read/delete/list."
    )
    region: str = Field(
        default="us-east-1",
        description="AWS region"
    )


def _aws_cloud_control_impl(
    operation: str,
    resource_type: str,
    identifier: str = "",
    properties: Optional[dict] = None,
    region: str = "us-east-1",
) -> str:
    """
    Execute ANY AWS resource operation using the Cloud Control API.

    Use this for ALL AWS resource management tasks:
    - S3 buckets, EC2 instances, RDS databases, Lambda functions,
      DynamoDB tables, VPCs, IAM roles, ECS clusters, SNS topics,
      SQS queues, and every other AWS resource type.

    Args:
        operation:     One of "create" | "read" | "update" | "delete" | "list"
        resource_type: AWS CloudFormation resource type string, e.g.:
                         "AWS::S3::Bucket"
                         "AWS::EC2::Instance"
                         "AWS::DynamoDB::Table"
                         "AWS::Lambda::Function"
                         "AWS::RDS::DBInstance"
                         "AWS::SQS::Queue"
                         "AWS::SNS::Topic"
        identifier:    Resource identifier for read / update / delete.
                       For S3 this is the bucket name.
                       For EC2 this is the instance ID. Leave empty for list/create.
        properties:    Dict of resource properties for create / update.
                       Leave as None for read / delete / list.
        region:        AWS region (default: "us-east-1")

    Returns:
        JSON string with operation result or error details.

    Examples:
        List S3 buckets:
            operation="list", resource_type="AWS::S3::Bucket"

        Create S3 bucket:
            operation="create", resource_type="AWS::S3::Bucket",
            properties={"BucketName": "my-bucket-2026"}

        Read S3 bucket:
            operation="read", resource_type="AWS::S3::Bucket",
            identifier="my-bucket-2026"

        Delete S3 bucket:
            operation="delete", resource_type="AWS::S3::Bucket",
            identifier="my-bucket-2026"

        List Lambda functions:
            operation="list", resource_type="AWS::Lambda::Function"

        List DynamoDB tables:
            operation="list", resource_type="AWS::DynamoDB::Table"
    """
    if properties is None:
        properties = {}

    try:
        client = get_cc_client(region)
        operation = operation.lower().strip()

        if operation == "list":
            paginator = client.get_paginator("list_resources")
            pages = paginator.paginate(TypeName=resource_type)

            resources = []
            for page in pages:
                for r in page.get("ResourceDescriptions", []):
                    entry = {"identifier": r["Identifier"]}
                    if r.get("Properties"):
                        try:
                            entry["properties"] = json.loads(r["Properties"])
                        except json.JSONDecodeError:
                            entry["properties"] = r["Properties"]
                    resources.append(entry)

            return json.dumps({
                "status": "success",
                "operation": "list",
                "resource_type": resource_type,
                "region": region,
                "count": len(resources),
                "resources": resources,
            })

        elif operation == "read":
            if not identifier:
                return json.dumps({"status": "error", "message": "identifier is required for read"})

            resp = client.get_resource(TypeName=resource_type, Identifier=identifier)
            desc = resp["ResourceDescription"]
            props = json.loads(desc.get("Properties", "{}"))

            return json.dumps({
                "status": "success",
                "operation": "read",
                "resource_type": resource_type,
                "identifier": identifier,
                "region": region,
                "properties": props,
            })

        elif operation == "create":
            resp = client.create_resource(
                TypeName=resource_type,
                DesiredState=json.dumps(properties),
            )
            progress = resp["ProgressEvent"]
            request_token = progress["RequestToken"]

            final = wait_for_progress(client, request_token)

            result = {
                "status": "success" if final["OperationStatus"] == "SUCCESS" else "failed",
                "operation": "create",
                "resource_type": resource_type,
                "region": region,
                "op_status": final["OperationStatus"],
            }
            if final.get("Identifier"):
                result["identifier"] = final["Identifier"]
            if final.get("StatusMessage"):
                result["message"] = final["StatusMessage"]
            if final["OperationStatus"] == "FAILED":
                result["error"] = final.get("StatusMessage", "Unknown error")

            return json.dumps(result)

        elif operation == "update":
            if not identifier:
                return json.dumps({"status": "error", "message": "identifier is required for update"})

            resp = client.update_resource(
                TypeName=resource_type,
                Identifier=identifier,
                PatchDocument=json.dumps([
                    {"op": "replace", "path": f"/{k}", "value": v}
                    for k, v in properties.items()
                ]),
            )
            progress = resp["ProgressEvent"]
            final = wait_for_progress(client, progress["RequestToken"])

            return json.dumps({
                "status": "success" if final["OperationStatus"] == "SUCCESS" else "failed",
                "operation": "update",
                "resource_type": resource_type,
                "identifier": identifier,
                "region": region,
                "op_status": final["OperationStatus"],
                "message": final.get("StatusMessage", ""),
            })

        elif operation == "delete":
            if not identifier:
                return json.dumps({"status": "error", "message": "identifier is required for delete"})

            resp = client.delete_resource(
                TypeName=resource_type,
                Identifier=identifier,
            )
            progress = resp["ProgressEvent"]
            final = wait_for_progress(client, progress["RequestToken"])

            return json.dumps({
                "status": "success" if final["OperationStatus"] == "SUCCESS" else "failed",
                "operation": "delete",
                "resource_type": resource_type,
                "identifier": identifier,
                "region": region,
                "op_status": final["OperationStatus"],
                "message": final.get("StatusMessage", ""),
            })

        else:
            return json.dumps({
                "status": "error",
                "message": f"Unknown operation '{operation}'. Use: create | read | update | delete | list",
            })

    except ClientError as e:
        return json.dumps({
            "status": "error",
            "operation": operation,
            "resource_type": resource_type,
            "error_code": e.response["Error"]["Code"],
            "message": e.response["Error"]["Message"],
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


aws_cloud_control = StructuredTool.from_function(
    func=_aws_cloud_control_impl,
    name="aws_cloud_control",
    description="""Execute ANY AWS resource operation using the Cloud Control API.

Use for ALL AWS resource management: S3, EC2, RDS, Lambda, DynamoDB, VPCs, IAM, ECS, SNS, SQS, etc.

Operations: create | read | update | delete | list""",
    args_schema=CloudControlInput,
)


def get_logs_client(region: str = "us-east-1"):
    """Create and return a CloudWatch Logs client."""
    return boto3.client("logs", region_name=region)


class CloudWatchLogsInput(BaseModel):
    """Input schema for CloudWatch Logs tool."""
    action: str = Field(
        description='"list_groups" to show all log groups, or "get_logs" to fetch/filter events from a log group'
    )
    log_group_name: str = Field(
        default="",
        description='Full log group name, required for "get_logs". Examples: "/aws/lambda/<function-name>", "/aws/ecs/<cluster-name>"'
    )
    filter_pattern: str = Field(
        default="",
        description='Text/pattern to search for (default: "" = all logs). Examples: "ERROR", "Exception", "timeout"'
    )
    hours_back: int = Field(
        default=1,
        description="How many hours back to look (default: 1, max: 168 = 7 days)"
    )
    limit: int = Field(
        default=50,
        description="Max number of log events to return (default: 50, max: 200)"
    )
    region: str = Field(
        default="us-east-1",
        description="AWS region"
    )


def _cloudwatch_logs_impl(
    action: str,
    log_group_name: str = "",
    filter_pattern: str = "",
    hours_back: int = 1,
    limit: int = 50,
    region: str = "us-east-1",
) -> str:
    """
    Query AWS CloudWatch Logs for any log group.

    Use this to:
    - List all available log groups (Lambda, ECS, API Gateway, EC2, custom apps)
    - Search and filter log events within any log group
    - Debug errors, trace requests, monitor application behavior

    Args:
        action:           "list_groups" — show all log groups
                          "get_logs"    — fetch/filter events from a log group
        log_group_name:   Full log group name, required for "get_logs".
                          Common patterns:
                            "/aws/lambda/<function-name>"
                            "/aws/ecs/<cluster-name>"
                            "/aws/apigateway/<api-name>"
                            "/aws/rds/instance/<db-id>/error"
                            Any custom log group name
        filter_pattern:   Text/pattern to search for (default: "" = all logs).
                          Examples: "ERROR", "Exception", "timeout", "200"
        hours_back:       How many hours back to look (default: 1, max: 168 = 7 days)
        limit:            Max number of log events to return (default: 50, max: 200)
        region:           AWS region (default: "us-east-1")

    Returns:
        JSON string with log group list or matching log events.

    Examples:
        List all log groups:
            action="list_groups"

        Get recent Lambda errors:
            action="get_logs",
            log_group_name="/aws/lambda/my-function",
            filter_pattern="ERROR",
            hours_back=2

        Get all logs from a log group (last 30 mins):
            action="get_logs",
            log_group_name="/aws/lambda/my-function",
            hours_back=1

        Search for a specific request ID:
            action="get_logs",
            log_group_name="/aws/apigateway/my-api",
            filter_pattern="abc-123-request-id"
    """
    try:
        logs = get_logs_client(region)

        if action == "list_groups":
            paginator = logs.get_paginator("describe_log_groups")
            groups = []
            for page in paginator.paginate():
                for g in page.get("logGroups", []):
                    groups.append({
                        "name": g["logGroupName"],
                        "retention_days": g.get("retentionInDays", "Never expire"),
                        "stored_mb": round(g.get("storedBytes", 0) / 1_048_576, 2),
                    })

            return json.dumps({
                "status": "success",
                "action": "list_groups",
                "region": region,
                "count": len(groups),
                "log_groups": groups,
            })

        elif action == "get_logs":
            if not log_group_name:
                return json.dumps({
                    "status": "error",
                    "message": "log_group_name is required for action='get_logs'",
                })

            hours_back = max(1, min(hours_back, 168))   # clamp 1h – 7d
            limit = max(1, min(limit, 200))

            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=hours_back)

            kwargs = {
                "logGroupName": log_group_name,
                "startTime": int(start_time.timestamp() * 1000),
                "endTime": int(end_time.timestamp() * 1000),
                "limit": limit,
            }
            if filter_pattern:
                kwargs["filterPattern"] = filter_pattern

            resp = logs.filter_log_events(**kwargs)

            events = []
            for e in resp.get("events", []):
                events.append({
                    "timestamp": datetime.fromtimestamp(
                        e["timestamp"] / 1000, tz=timezone.utc
                    ).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "stream": e["logStreamName"],
                    "message": e["message"].strip(),
                })

            return json.dumps({
                "status": "success",
                "action": "get_logs",
                "log_group": log_group_name,
                "filter_pattern": filter_pattern or "(none)",
                "time_range": f"Last {hours_back} hour(s)",
                "region": region,
                "count": len(events),
                "events": events,
            })

        else:
            return json.dumps({
                "status": "error",
                "message": f"Unknown action '{action}'. Use: list_groups | get_logs",
            })

    except ClientError as e:
        return json.dumps({
            "status": "error",
            "action": action,
            "error_code": e.response["Error"]["Code"],
            "message": e.response["Error"]["Message"],
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


cloudwatch_logs = StructuredTool.from_function(
    func=_cloudwatch_logs_impl,
    name="cloudwatch_logs",
    description="""Query AWS CloudWatch Logs for any log group.

Use to list log groups or search and filter log events for debugging and monitoring.

Actions: list_groups | get_logs""",
    args_schema=CloudWatchLogsInput,
)


class FinalAnswerInput(BaseModel):
    """Input schema for Final Answer tool."""
    answer: str = Field(
        description="The final answer to provide to the user."
    )


def _final_answer_impl(answer: str) -> str:
    """
    Return the final answer from the agent.

    Called when the agent has completed its work and wants to provide the final response.

    Args:
        answer: The final answer string

    Returns:
        JSON string with the final answer
    """
    return json.dumps({
        "status": "success",
        "answer": answer,
    })


final_answer = StructuredTool.from_function(
    func=_final_answer_impl,
    name="final_answer",
    description="Provide the final answer to the user. Use when you have completed your task.",
    args_schema=FinalAnswerInput,
)


ALL_TOOLS = [
    aws_cloud_control,
    cloudwatch_logs,
    final_answer,
]
