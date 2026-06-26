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


def get_rds_client(region: str = "us-east-1"):
    return boto3.client("rds", region_name=region)


def format_error(e: ClientError, action: str) -> str:
    return json.dumps({
        "status": "error",
        "service": "RDS",
        "operation": action,
        "error_code": e.response["Error"]["Code"],
        "message": e.response["Error"]["Message"],
    })


def create_rds_instance(
    db_instance_identifier: str,
    engine: str,
    db_instance_class: str,
    allocated_storage: int,
    master_username: str,
    master_user_password: str,
    publicly_accessible: bool = False,
    db_subnet_group_name: str = "",
    vpc_security_group_ids: list[str] | None = None,
    tags: dict | list[dict] | None = None,
    region: str = "us-east-1",
) -> str:
    try:
        client = get_rds_client(region)
        params = {
            "DBInstanceIdentifier": db_instance_identifier,
            "Engine": engine,
            "DBInstanceClass": db_instance_class,
            "AllocatedStorage": allocated_storage,
            "MasterUsername": master_username,
            "MasterUserPassword": master_user_password,
            "PubliclyAccessible": publicly_accessible,
        }
        if db_subnet_group_name:
            params["DBSubnetGroupName"] = db_subnet_group_name
        if vpc_security_group_ids:
            params["VpcSecurityGroupIds"] = vpc_security_group_ids
        if tags:
            if isinstance(tags, dict):
                params["Tags"] = [{"Key": k, "Value": str(v)} for k, v in tags.items()]
            else:
                params["Tags"] = tags

        client.create_db_instance(**params)
        waiter = client.get_waiter("db_instance_available")
        waiter.wait(DBInstanceIdentifier=db_instance_identifier)

        return json.dumps({
            "status": "success",
            "service": "RDS",
            "operation": "create_db",
            "region": region,
            "db_identifier": db_instance_identifier,
            "state": "available",
        })
    except ClientError as e:
        return format_error(e, "create_db")
    except Exception as e:
        return json.dumps({"status": "error", "service": "RDS", "operation": "create_db", "message": str(e)})


def describe_db_instances(
    db_instance_identifier: str = "",
    region: str = "us-east-1",
) -> str:
    try:
        client = get_rds_client(region)
        kwargs = {}
        if db_instance_identifier:
            kwargs["DBInstanceIdentifier"] = db_instance_identifier

        response = client.describe_db_instances(**kwargs)
        db_instances = []
        for inst in response.get("DBInstances", []):
            db_instances.append({
                "db_identifier": inst.get("DBInstanceIdentifier"),
                "engine": inst.get("Engine"),
                "instance_class": inst.get("DBInstanceClass"),
                "allocated_storage": inst.get("AllocatedStorage"),
                "status": inst.get("DBInstanceStatus"),
                "endpoint": inst.get("Endpoint", {}).get("Address"),
                "port": inst.get("Endpoint", {}).get("Port"),
                "publicly_accessible": inst.get("PubliclyAccessible"),
                "availability_zone": inst.get("AvailabilityZone"),
                "vpc_security_group_ids": [g.get("VpcSecurityGroupId") for g in inst.get("VpcSecurityGroups", [])],
                "db_subnet_group": inst.get("DBSubnetGroup"),
                "storage_type": inst.get("StorageType"),
                "multi_az": inst.get("MultiAZ"),
            })

        return json.dumps({
            "status": "success",
            "service": "RDS",
            "operation": "describe_db_instances",
            "region": region,
            "count": len(db_instances),
            "db_instances": db_instances,
        })
    except ClientError as e:
        return format_error(e, "describe_db_instances")
    except Exception as e:
        return json.dumps({"status": "error", "service": "RDS", "operation": "describe_db_instances", "message": str(e)})


def start_db_instance(db_instance_identifier: str, region: str = "us-east-1") -> str:
    try:
        client = get_rds_client(region)
        client.start_db_instance(DBInstanceIdentifier=db_instance_identifier)
        waiter = client.get_waiter("db_instance_available")
        waiter.wait(DBInstanceIdentifier=db_instance_identifier)

        return json.dumps({
            "status": "success",
            "service": "RDS",
            "operation": "start_db_instance",
            "region": region,
            "db_identifier": db_instance_identifier,
            "state": "available",
        })
    except ClientError as e:
        return format_error(e, "start_db_instance")
    except Exception as e:
        return json.dumps({"status": "error", "service": "RDS", "operation": "start_db_instance", "message": str(e)})


def stop_db_instance(db_instance_identifier: str, region: str = "us-east-1") -> str:
    try:
        client = get_rds_client(region)
        client.stop_db_instance(DBInstanceIdentifier=db_instance_identifier)
        waiter = client.get_waiter("db_instance_stopped")
        waiter.wait(DBInstanceIdentifier=db_instance_identifier)

        return json.dumps({
            "status": "success",
            "service": "RDS",
            "operation": "stop_db_instance",
            "region": region,
            "db_identifier": db_instance_identifier,
            "state": "stopped",
        })
    except ClientError as e:
        return format_error(e, "stop_db_instance")
    except Exception as e:
        return json.dumps({"status": "error", "service": "RDS", "operation": "stop_db_instance", "message": str(e)})


def delete_db_instance(db_instance_identifier: str, skip_final_snapshot: bool = True, region: str = "us-east-1") -> str:
    try:
        client = get_rds_client(region)
        client.delete_db_instance(
            DBInstanceIdentifier=db_instance_identifier,
            SkipFinalSnapshot=skip_final_snapshot,
        )
        waiter = client.get_waiter("db_instance_deleted")
        waiter.wait(DBInstanceIdentifier=db_instance_identifier)

        return json.dumps({
            "status": "success",
            "service": "RDS",
            "operation": "delete_db_instance",
            "region": region,
            "db_identifier": db_instance_identifier,
            "state": "deleted",
        })
    except ClientError as e:
        return format_error(e, "delete_db_instance")
    except Exception as e:
        return json.dumps({"status": "error", "service": "RDS", "operation": "delete_db_instance", "message": str(e)})


class RDSToolInput(BaseModel):
    action: str = Field(
        description='One of "create_db" | "describe_db_instances" | "start_db_instance" | "stop_db_instance" | "delete_db_instance"'
    )
    db_instance_identifier: str = Field(default="", description="RDS DB instance identifier")
    engine: str = Field(default="", description="Database engine, e.g. mysql, postgres")
    db_instance_class: str = Field(default="", description="RDS instance class")
    allocated_storage: int = Field(default=20, description="Allocated storage in GB")
    master_username: str = Field(default="", description="Master username")
    master_user_password: str = Field(default="", description="Master user password")
    publicly_accessible: bool = Field(default=False, description="Whether the DB is publicly accessible")
    db_subnet_group_name: str = Field(default="", description="DB subnet group name")
    vpc_security_group_ids: list[str] = Field(default_factory=list, description="VPC security group IDs")
    tags: dict | list[dict] = Field(default_factory=dict, description="Tags for the DB instance")
    skip_final_snapshot: bool = Field(default=True, description="Skip final snapshot when deleting")
    region: str = Field(default="us-east-1", description="AWS region")


def _rds_tool_impl(
    action: str,
    db_instance_identifier: str = "",
    engine: str = "",
    db_instance_class: str = "",
    allocated_storage: int = 20,
    master_username: str = "",
    master_user_password: str = "",
    publicly_accessible: bool = False,
    db_subnet_group_name: str = "",
    vpc_security_group_ids: list[str] | None = None,
    tags: dict | list[dict] | None = None,
    skip_final_snapshot: bool = True,
    region: str = "us-east-1",
) -> str:
    action = action.lower().strip()
    if action == "create_db":
        return create_rds_instance(
            db_instance_identifier=db_instance_identifier,
            engine=engine,
            db_instance_class=db_instance_class,
            allocated_storage=allocated_storage,
            master_username=master_username,
            master_user_password=master_user_password,
            publicly_accessible=publicly_accessible,
            db_subnet_group_name=db_subnet_group_name,
            vpc_security_group_ids=vpc_security_group_ids,
            tags=tags,
            region=region,
        )
    if action == "describe_db_instances":
        return describe_db_instances(db_instance_identifier=db_instance_identifier, region=region)
    if action == "start_db_instance":
        return start_db_instance(db_instance_identifier=db_instance_identifier, region=region)
    if action == "stop_db_instance":
        return stop_db_instance(db_instance_identifier=db_instance_identifier, region=region)
    if action == "delete_db_instance":
        return delete_db_instance(
            db_instance_identifier=db_instance_identifier,
            skip_final_snapshot=skip_final_snapshot,
            region=region,
        )

    return json.dumps({
        "status": "error",
        "service": "RDS",
        "operation": action,
        "message": "Unknown RDS action. Use create_db | describe_db_instances | start_db_instance | stop_db_instance | delete_db_instance",
    })


rds_tool = StructuredTool.from_function(
    func=_rds_tool_impl,
    name="rds_tool",
    description="Manage RDS instances using boto3. Actions: create_db, describe_db_instances, start_db_instance, stop_db_instance, delete_db_instance.",
    args_schema=RDSToolInput,
)
