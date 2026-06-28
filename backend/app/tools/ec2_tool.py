import json
import boto3
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field

try:
    from langchain.tools import StructuredTool
except Exception:
    from langchain.tools import BaseTool

    class _SimpleTool(BaseTool):
        def __init__(self, func, name, description, args_schema=None):
            super().__init__(name=name, description=description, args_schema=args_schema)
            self.func = func

        def _run(self, *args, **kwargs):
            return self.func(*args, **kwargs)

        async def _arun(self, *args, **kwargs):
            return self.func(*args, **kwargs)

    class StructuredTool:
        @staticmethod
        def from_function(func, name, description, args_schema=None):
            return _SimpleTool(func=func, name=name, description=description, args_schema=args_schema)


def get_ec2_client(region: str = "us-east-1"):
    return boto3.client("ec2", region_name=region)


def format_error(e: ClientError, action: str) -> str:
    return json.dumps({
        "status": "error",
        "service": "EC2",
        "operation": action,
        "error_code": e.response["Error"]["Code"],
        "message": e.response["Error"]["Message"],
    })


def create_ec2_instance(
    image_id: str,
    instance_type: str,
    key_name: str = "",
    security_group_ids: list[str] | None = None,
    subnet_id: str = "",
    tags: dict | list[dict] | None = None,
    min_count: int = 1,
    max_count: int = 1,
    region: str = "us-east-1",
) -> str:
    try:
        client = get_ec2_client(region)
        params = {
            "ImageId": image_id,
            "InstanceType": instance_type,
            "MinCount": min_count,
            "MaxCount": max_count,
        }
        if key_name:
            params["KeyName"] = key_name
        if security_group_ids:
            params["SecurityGroupIds"] = security_group_ids
        if subnet_id:
            params["SubnetId"] = subnet_id
        if tags:
            if isinstance(tags, dict):
                params["TagSpecifications"] = [{
                    "ResourceType": "instance",
                    "Tags": [{"Key": k, "Value": str(v)} for k, v in tags.items()],
                }]
            else:
                params["TagSpecifications"] = [{
                    "ResourceType": "instance",
                    "Tags": tags,
                }]

        response = client.run_instances(**params)
        instance_ids = [i["InstanceId"] for i in response["Instances"]]

        waiter = client.get_waiter("instance_running")
        waiter.wait(InstanceIds=instance_ids)

        return json.dumps({
            "status": "success",
            "service": "EC2",
            "operation": "create_instance",
            "region": region,
            "instance_ids": instance_ids,
            "instance_id": instance_ids[0] if len(instance_ids) == 1 else None,
            "state": "running",
        })
    except ClientError as e:
        return format_error(e, "create_instance")
    except Exception as e:
        return json.dumps({"status": "error", "service": "EC2", "operation": "create_instance", "message": str(e)})


def describe_instances(
    instance_ids: list[str] | None = None,
    region: str = "us-east-1",
) -> str:
    try:
        client = get_ec2_client(region)
        kwargs = {}
        if instance_ids:
            kwargs["InstanceIds"] = instance_ids

        response = client.describe_instances(**kwargs)
        instances = []
        for reservation in response.get("Reservations", []):
            for inst in reservation.get("Instances", []):
                instances.append({
                    "instance_id": inst.get("InstanceId"),
                    "image_id": inst.get("ImageId"),
                    "instance_type": inst.get("InstanceType"),
                    "state": inst.get("State", {}).get("Name"),
                    "subnet_id": inst.get("SubnetId"),
                    "vpc_id": inst.get("VpcId"),
                    "public_ip": inst.get("PublicIpAddress"),
                    "private_ip": inst.get("PrivateIpAddress"),
                    "availability_zone": inst.get("Placement", {}).get("AvailabilityZone"),
                    "security_group_ids": [g.get("GroupId") for g in inst.get("SecurityGroups", [])],
                    "tags": [{"Key": t.get("Key"), "Value": t.get("Value")} for t in inst.get("Tags", [])],
                })

        return json.dumps({
            "status": "success",
            "service": "EC2",
            "operation": "describe_instances",
            "region": region,
            "count": len(instances),
            "instances": instances,
        })
    except ClientError as e:
        return format_error(e, "describe_instances")
    except Exception as e:
        return json.dumps({"status": "error", "service": "EC2", "operation": "describe_instances", "message": str(e)})


def start_instance(instance_id: str, region: str = "us-east-1") -> str:
    try:
        client = get_ec2_client(region)
        client.start_instances(InstanceIds=[instance_id])
        waiter = client.get_waiter("instance_running")
        waiter.wait(InstanceIds=[instance_id])

        return json.dumps({
            "status": "success",
            "service": "EC2",
            "operation": "start_instance",
            "region": region,
            "instance_id": instance_id,
            "state": "running",
        })
    except ClientError as e:
        return format_error(e, "start_instance")
    except Exception as e:
        return json.dumps({"status": "error", "service": "EC2", "operation": "start_instance", "message": str(e)})


def stop_instance(instance_id: str, force: bool = False, region: str = "us-east-1") -> str:
    try:
        client = get_ec2_client(region)
        client.stop_instances(InstanceIds=[instance_id], Force=force)
        waiter = client.get_waiter("instance_stopped")
        waiter.wait(InstanceIds=[instance_id])

        return json.dumps({
            "status": "success",
            "service": "EC2",
            "operation": "stop_instance",
            "region": region,
            "instance_id": instance_id,
            "state": "stopped",
        })
    except ClientError as e:
        return format_error(e, "stop_instance")
    except Exception as e:
        return json.dumps({"status": "error", "service": "EC2", "operation": "stop_instance", "message": str(e)})


def terminate_instance(instance_id: str, region: str = "us-east-1") -> str:
    try:
        client = get_ec2_client(region)
        client.terminate_instances(InstanceIds=[instance_id])
        waiter = client.get_waiter("instance_terminated")
        waiter.wait(InstanceIds=[instance_id])

        return json.dumps({
            "status": "success",
            "service": "EC2",
            "operation": "terminate_instance",
            "region": region,
            "instance_id": instance_id,
            "state": "terminated",
        })
    except ClientError as e:
        return format_error(e, "terminate_instance")
    except Exception as e:
        return json.dumps({"status": "error", "service": "EC2", "operation": "terminate_instance", "message": str(e)})


class EC2ToolInput(BaseModel):
    action: str = Field(
        description='One of "create_instance" | "describe_instances" | "start_instance" | "stop_instance" | "terminate_instance"'
    )
    image_id: str = Field(default="", description="AMI ID for EC2 instance creation")
    instance_type: str = Field(default="", description="EC2 instance type")
    key_name: str = Field(default="", description="Key pair name")
    security_group_ids: list[str] = Field(default_factory=list, description="List of security group IDs")
    subnet_id: str = Field(default="", description="Subnet ID")
    tags: dict | list[dict] = Field(default_factory=dict, description="Tags for the new instance")
    min_count: int = Field(default=1, description="Minimum number of instances to launch")
    max_count: int = Field(default=1, description="Maximum number of instances to launch")
    instance_id: str = Field(default="", description="EC2 instance ID for start/stop/terminate")
    instance_ids: list[str] = Field(default_factory=list, description="List of EC2 instance IDs to describe")
    force: bool = Field(default=False, description="Force stop for EC2 instance")
    region: str = Field(default="us-east-1", description="AWS region")


def _ec2_tool_impl(
    action: str,
    image_id: str = "",
    instance_type: str = "",
    key_name: str = "",
    security_group_ids: list[str] | None = None,
    subnet_id: str = "",
    tags: dict | list[dict] | None = None,
    min_count: int = 1,
    max_count: int = 1,
    instance_id: str = "",
    instance_ids: list[str] | None = None,
    force: bool = False,
    region: str = "us-east-1",
) -> str:
    action = action.lower().strip()
    if action == "create_instance":
        return create_ec2_instance(
            image_id=image_id,
            instance_type=instance_type,
            key_name=key_name,
            security_group_ids=security_group_ids,
            subnet_id=subnet_id,
            tags=tags,
            min_count=min_count,
            max_count=max_count,
            region=region,
        )
    if action == "describe_instances":
        return describe_instances(instance_ids=instance_ids, region=region)
    if action == "start_instance":
        return start_instance(instance_id=instance_id, region=region)
    if action == "stop_instance":
        return stop_instance(instance_id=instance_id, force=force, region=region)
    if action == "terminate_instance":
        return terminate_instance(instance_id=instance_id, region=region)

    return json.dumps({
        "status": "error",
        "service": "EC2",
        "operation": action,
        "message": "Unknown EC2 action. Use create_instance | describe_instances | start_instance | stop_instance | terminate_instance",
    })


ec2_tool = StructuredTool.from_function(
    func=_ec2_tool_impl,
    name="ec2_tool",
    description="Manage EC2 instances using boto3. Actions: create_instance, describe_instances, start_instance, stop_instance, terminate_instance.",
    args_schema=EC2ToolInput,
)
