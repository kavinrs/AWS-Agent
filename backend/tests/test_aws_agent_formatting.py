import json
import sys
import unittest
from pathlib import Path

# Ensure the backend package is importable when tests are run from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.aws_agent import _format_aws_cloud_control_markdown
from app.api.app import format_observation


class TestAWSAgentFormatting(unittest.TestCase):
    def test_format_aws_cloud_control_markdown_list(self):
        tool_input = {"resource_type": "AWS::EC2::Instance"}
        observation = json.dumps({
            "status": "success",
            "operation": "list",
            "resource_type": "AWS::EC2::Instance",
            "region": "us-east-1",
            "count": 2,
            "resources": [
                {
                    "identifier": "i-0123456789abcdef0",
                    "properties": {
                        "InstanceType": "t3.micro",
                        "State": "running",
                        "Tags": [{"Key": "Name", "Value": "web-server"}],
                    },
                },
                {
                    "identifier": "i-0abcdef1234567890",
                    "properties": {
                        "InstanceType": "t3.large",
                        "State": "stopped",
                        "Name": "db-server",
                    },
                },
            ],
        })

        formatted = _format_aws_cloud_control_markdown(observation, tool_input)

        self.assertIsInstance(formatted, str)
        self.assertIn("## EC2 Instance Resources Found", formatted)
        self.assertIn("Total: 2", formatted)
        self.assertIn("Resource Name: web-server", formatted)
        self.assertIn("Resource Name: db-server", formatted)
        self.assertIn("Resource Type: EC2 Instance", formatted)
        self.assertIn("Instance Type: t3.micro", formatted)
        self.assertIn("State: running", formatted)

    def test_format_observation_list(self):
        observation = {
            "status": "success",
            "operation": "list",
            "resource_type": "AWS::EC2::Instance",
            "region": "us-east-1",
            "count": 1,
            "resources": [
                {
                    "identifier": "i-0123456789abcdef0",
                    "properties": {
                        "InstanceType": "t3.micro",
                        "State": "running",
                        "Tags": [{"Key": "Name", "Value": "web-server"}],
                    },
                }
            ],
        }

        formatted = format_observation(json.dumps(observation))

        self.assertIn("## EC2 Instance Resources Found", formatted)
        self.assertIn("Total: 1", formatted)
        self.assertIn("Resource Name: web-server", formatted)
        self.assertIn("Resource Type: EC2 Instance", formatted)
        self.assertIn("Instance Type: t3.micro", formatted)

    def test_format_observation_read(self):
        observation = {
            "status": "success",
            "operation": "read",
            "resource_type": "AWS::S3::Bucket",
            "identifier": "my-bucket",
            "properties": {
                "Name": "my-bucket",
                "BucketName": "my-bucket",
                "Region": "us-east-1",
            },
        }

        formatted = format_observation(json.dumps(observation))

        self.assertIn("## S3 Bucket Resource Details", formatted)
        self.assertIn("Total: 1", formatted)
        self.assertIn("Resource Name: my-bucket", formatted)
        self.assertIn("Resource Type: S3 Bucket", formatted)
        self.assertIn("Bucket Name: my-bucket", formatted)
        self.assertIn("Region: us-east-1", formatted)

    def test_simplified_ec2_list_output(self):
        observation = {
            "status": "success",
            "operation": "list",
            "resource_type": "AWS::EC2::Instance",
            "region": "us-east-1",
            "count": 1,
            "resources": [
                {
                    "identifier": "i-0123456789abcdef0",
                    "properties": {
                        "Name": "petreunite-adoption-ec2",
                        "InstanceType": "c7i-flex.large",
                        "State": {"Name": "running"},
                        "PublicIpAddress": "107.20.210.48",
                        "PrivateIpAddress": "10.0.9.70",
                        "Placement": {"AvailabilityZone": "us-east-1a"},
                        "VpcId": "vpc-0c8ef0a4f4fd7b3a",
                        "SubnetId": "subnet-0a493b2b12ffb5475",
                        "SecurityGroups": [{"GroupId": "sg-01b6727c7d79f2b1c"}],
                    },
                },
            ],
        }

        formatted = format_observation(json.dumps(observation))

        self.assertIn("## EC2 Instance Resources Found", formatted)
        self.assertIn("Total: 1", formatted)
        self.assertIn("Resource Name: petreunite-adoption-ec2", formatted)
        self.assertIn("Instance Type: c7i-flex.large", formatted)
        self.assertIn("State: running", formatted)
        self.assertIn("Public IP: 107.20.210.48", formatted)
        self.assertIn("Private IP: 10.0.9.70", formatted)
        self.assertIn("Availability Zone: us-east-1a", formatted)
        self.assertIn("VPC: vpc-0c8ef0a4f4fd7b3a", formatted)
        self.assertIn("Subnet: subnet-0a493b2b12ffb5475", formatted)
        self.assertIn("Security Groups: sg-01b6727c7d79f2b1c", formatted)


if __name__ == "__main__":
    unittest.main()
