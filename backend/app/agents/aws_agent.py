"""
AWS Agent — LangChain ReAct agent with 2 powerful generic tools.
"""
import os
from pathlib import Path
from uuid import uuid4
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_aws import ChatBedrockConverse
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, ToolMessage, HumanMessage, AIMessage
from app.tools import ALL_TOOLS
from app.rag.retriever import retrieve_company_context
from langchain_core.runnables import RunnableSerializable
import json

env_path = None
for p in Path(__file__).resolve().parents:
    candidate = p / ".env"
    if candidate.exists():
        env_path = candidate
        break

if env_path is None:
    env_path = Path(__file__).parent.parent / ".env"

load_dotenv(dotenv_path=env_path)

SYSTEM_MESSAGE = """You are an expert AWS Resource Manager AI Assistant.

Your purpose is to help users manage, inspect, troubleshoot, and understand AWS resources.

You have access to tools that can interact with real AWS resources.

--------------------------------------------------
GENERAL BEHAVIOR
--------------------------------------------------

• Be friendly and conversational.
• Answer greetings naturally without using any tool.
• Answer general AWS knowledge questions from your own knowledge whenever possible.
• Never invent AWS resource information.
• Only use tools when real AWS data or an AWS action is required.
• Never assume the user's intent. If something is ambiguous, ask a clarifying question.

Examples:

User: Hi
Assistant: Hello! How can I help you with your AWS resources today?

User: What is an EC2 instance?
Assistant:
Explain normally.
Do NOT call any tool.

User:
How do I create an S3 bucket?

Assistant:
Explain the process.
Do NOT create a bucket unless the user explicitly asks.

--------------------------------------------------
WHEN TO USE TOOLS
--------------------------------------------------

Use tools ONLY when required.

Use aws_cloud_control when the user wants to:

• List AWS resources
• Read resource details
• Create resources
• Update resources
• Delete resources

Examples

✓ List my EC2 instances
✓ Create an S3 bucket
✓ Delete my RDS instance
✓ Show all VPCs
✓ Describe my Lambda function

Use cloudwatch_logs when the user asks about:

• CloudWatch logs
• Errors
• Debugging
• Log groups
• Recent application logs

Use final_answer ONLY after every required tool has completed successfully.

--------------------------------------------------
WHEN NOT TO USE TOOLS
--------------------------------------------------

Do NOT call tools for:

• Greetings
• Small talk
• Thanks
• Goodbye
• AWS theory
• Architecture explanations
• Interview questions
• General programming questions
• Python questions
• Cloud concepts

Examples:

Hi
Hello
Thank you
What is IAM?
Explain VPC.
What is Docker?
Difference between ECS and EKS?

These should NOT invoke any tool.

--------------------------------------------------
RESOURCE OPERATIONS
--------------------------------------------------

For CREATE operations:

If required information is missing,
ask the user for it.

Example:

Create an EC2 instance.

Assistant:

What AMI should I use?
What instance type?
Which VPC or subnet?

Do not guess missing values.

--------------------------------------------------
DELETE OPERATIONS
--------------------------------------------------

Deletion is destructive.

When the user asks to delete a resource:

1. Call the aws_cloud_control tool with operation="delete"
2. The tool will automatically handle approval workflow
3. Include the exact resource identifier the user specified
4. The system will ask for confirmation and only execute after approval

IMPORTANT: Always call the tool immediately when user asks to delete.
The tool handles the confirmation flow internally.

--------------------------------------------------
LIST OPERATIONS
--------------------------------------------------

When a tool returns resources:

• Include EVERY resource.
• Never summarize.
• Never truncate.
• Never say "...and more."

If there are 25 resources,
display all 25.

--------------------------------------------------
FORMATTING
--------------------------------------------------

When listing AWS resources, ALWAYS produce markdown using this exact format:

## EC2 Instances

**Total:** X

### Resource 1

| Property | Value |
|----------|-------|
| Name | ... |
| Instance ID | ... |
| State | ... |

Repeat for every resource.

Never output plain text.
Never output JSON.

--------------------------------------------------
ERROR HANDLING
--------------------------------------------------

If a tool returns an error:

• Explain the error clearly.
• Suggest likely causes.
• Suggest how to fix it.
• Never fabricate a successful result.

--------------------------------------------------
COMPANY CONTEXT
--------------------------------------------------

--------------------------------------------------
COMPANY CONTEXT (HIGHEST PRIORITY)
--------------------------------------------------

If company-specific context is provided through retrieved documents, treat it as the authoritative source for infrastructure configuration.

When generating tool calls:

• ALWAYS use values from the company context for:
  - AMI IDs
  - Instance types
  - VPC IDs
  - Subnet IDs
  - Security Group IDs
  - Key Pair names
  - IAM Roles
  - Availability Zones
  - Naming conventions
  - Organizational policies

• NEVER invent placeholder values such as:
  - ami-0abc123...
  - subnet-private-01
  - sg-web-dev

• NEVER replace a value that already exists in the company context unless the user explicitly overrides it.

• If the company context provides an AMI ID, that exact AMI ID MUST be passed to the tool.

• If required information is missing from both the user request and the company context, ask the user before calling any tool.

The company context has higher priority than the model's prior knowledge.
--------------------------------------------------
FINAL RULES
--------------------------------------------------

1. Never invent AWS resource information.
2. Use tools only when necessary.
3. Never call tools for greetings or theory questions.
4. Ask for clarification when required information is missing.
5. Require confirmation before destructive actions.
6. Always show complete resource lists.
7. Produce clean, professional markdown responses."""


api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError(
        "OPENAI_API_KEY not found in environment. "
        "Please ensure .env file exists and contains OPENAI_API_KEY"
    )

import logging

logging.basicConfig(level=logging.DEBUG)

logging.getLogger("botocore").setLevel(logging.DEBUG)
logging.getLogger("boto3").setLevel(logging.DEBUG)
logging.getLogger("langchain").setLevel(logging.DEBUG)

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_MESSAGE),
    MessagesPlaceholder("chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])

name2tool = {tool.name: tool.func for tool in ALL_TOOLS}

APPROVAL_REQUIRED_ACTIONS = {

    "ec2_tool": [
        "create_instance",
        "terminate_instance",
        "stop_instance",
        "start_instance",
        "reboot_instance",
    ],

    "rds_tool": [
        "create_db_instance",
        "delete_db_instance",
        "modify_db_instance",
    ],

    "s3_tool": [
        "create_bucket",
        "delete_bucket",
    ],

    "lambda_tool": [
        "create_function",
        "delete_function",
        "update_function",
    ],

    "vpc_tool": [
        "create_vpc",
        "delete_vpc",
    ],

    "iam_tool": [
        "create_role",
        "delete_role",
        "attach_policy",
        "detach_policy",
    ],

    "cloudfront_tool": [
        "create_distribution",
        "delete_distribution",
    ],
}
REQUIRED_FIELDS = {
    "ec2": [
        "image_id",
        "instance_type",
        "key_name",
        "subnet_id",
        "security_group_ids",
    ],
    "rds": [
        "engine",
        "db_instance_class",
        "allocated_storage",
    ],
    "s3": [
        "bucket_name",
    ],
}

def get_missing_fields(resource, parameters):

    required = REQUIRED_FIELDS.get(resource, [])

    missing = []

    for field in required:
        if field not in parameters:
            missing.append(field)

    return missing

def build_query_with_company_context(query: str) -> str:
    """Retrieve relevant company documents and append them to the user query."""
    context_chunks = retrieve_company_context(query)
    if not context_chunks:
        return query

    joined_context = "\n\n".join(context_chunks)
    return (
        f"Company context:\n{joined_context}\n\n"
        f"User question:\n{query}"
    )


def _format_value(value):
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _title_label(key: str) -> str:
    return " ".join(
        word.capitalize() for word in str(key).replace("_", " ").split()
    )


def _extract_resource_name(properties: dict | None, identifier: str | None = None) -> str | None:
    if not isinstance(properties, dict):
        return identifier

    tags = properties.get("Tags") or properties.get("tags")
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, dict) and str(tag.get("Key", "")).lower() == "name":
                return str(tag.get("Value", ""))

    if properties.get("Name"):
        return str(properties.get("Name"))

    return identifier


def _format_resource_block(resource, index: int | None = None, resource_type: str | None = None):
    lines = []
    if index is not None:
        lines.append(f"Resource {index + 1}")

    identifier = resource.get("identifier")
    props = resource.get("properties") if isinstance(resource, dict) else None
    resource_name = _extract_resource_name(props if isinstance(props, dict) else resource, identifier)

    if resource_name:
        lines.append(f"Resource Name: {resource_name}")
    elif identifier:
        lines.append(f"Identifier: {identifier}")

    if resource_type:
        lines.append(f"Resource Type: {resource_type}")

    if isinstance(props, dict):
        for key in sorted(props.keys()):
            if key in {"Tags", "tags"}:
                continue
            lines.append(f"{_title_label(key)}: {_format_value(props[key])}")
    else:
        for key in sorted(resource.keys()):
            if key in {"identifier", "properties"}:
                continue
            lines.append(f"{_title_label(key)}: {_format_value(resource[key])}")

    return "\n".join(lines)


def _format_aws_cloud_control_markdown(observation: str, tool_input: dict) -> str | None:
    try:
        data = json.loads(observation)
    except Exception:
        return None

    if data.get("status") != "success":
        return None

    operation = data.get("operation")
    resource_type = tool_input.get("resource_type", "AWS Resource")
    resource_name = resource_type.replace("AWS::", "").replace("::", " ").strip() or "AWS Resource"

    if operation == "list" and isinstance(data.get("resources"), list):
        resources = data["resources"]
        lines = [f"## {resource_name} Resources Found", f"Total: {len(resources)}", ""]
        for idx, resource in enumerate(resources):
            lines.append(_format_resource_block(resource, idx, resource_name))
            if idx < len(resources) - 1:
                lines.append("")
        return "\n".join(lines)

    if operation == "read" and isinstance(data.get("properties"), dict):
        resource_display = _extract_resource_name(data.get("properties"), data.get("identifier")) or resource_name
        lines = [f"## {resource_name} Resource Details", "Total: 1", ""]
        lines.append(f"Resource Name: {resource_display}")
        lines.append(f"Resource Type: {resource_name}")
        for key in sorted(data["properties"].keys()):
            if key in {"Tags", "tags"}:
                continue
            lines.append(f"{_title_label(key)}: {_format_value(data['properties'][key])}")
        return "\n".join(lines)

    return None


def _ensure_structured_response(final_answer: str, steps: list[dict]) -> str:
    if not isinstance(final_answer, str):
        return final_answer

    if "resource name" in final_answer.lower() or "total:" in final_answer.lower() or "aws resources found" in final_answer.lower():
        return final_answer

    for step in reversed(steps):
        if step.get("tool") == "aws_cloud_control":
            formatted = _format_aws_cloud_control_markdown(step.get("observation", ""), step.get("tool_input", {}))
            if formatted:
                return formatted

    return final_answer


class CustomAgentExecuter:
    chat_history:list[BaseMessage]

    def __init__(self,max_iterations:int=3):
        self.chat_history=[]
        self.max_iterations=max_iterations
        self.pending_operation = None
        self.operation_state = {
        "resource": None,
        "operation": None,
        "parameters": {},
        }
        self.agent: RunnableSerializable=({
            "input":lambda x:x["input"],
            "chat_history":lambda x:x["chat_history"],
            "agent_scratchpad":lambda x:x["agent_scratchpad"]
        }
        | prompt
        | llm.bind_tools(ALL_TOOLS)
        )
    
    def invoke(self, query: str) -> dict:
        confirmation_words = {
        "yes",
        "yes proceed",
        "proceed",
        "confirm",
        "go ahead",
        "continue",
        "okay",
        "ok",
        }

        cancel_words = {
            "cancel",
            "no",
            "stop",
            "abort",
        }

        if self.pending_operation:

            if query.lower().strip() in confirmation_words:

                tool_name = self.pending_operation["tool_name"]
                tool_args = self.pending_operation["tool_args"]
                
                tool_obs = name2tool[tool_name](**tool_args)

                self.pending_operation = None

                return {
                    "output": tool_obs,
                    "steps": [],
                }

            elif query.lower().strip() in cancel_words:

                self.pending_operation = None

                return {
                    "output": "Operation cancelled.",
                    "steps": [],
                }
        agent_scratchpad = []
        steps = []
        count = 0
        query_lower = query.lower()

        if "create" in query_lower and "ec2" in query_lower:

            self.operation_state["resource"] = "ec2"
            self.operation_state["operation"] = "create"

        elif "create" in query_lower and "rds" in query_lower:

            self.operation_state["resource"] = "rds"
            self.operation_state["operation"] = "create"

        elif "create" in query_lower and "s3" in query_lower:

            self.operation_state["resource"] = "s3"
            self.operation_state["operation"] = "create"
        
        parameters = self.operation_state["parameters"]

        if "t3.micro" in query:
            parameters["instance_type"] = "t3.micro"

        if "aws-agent" in query:
            parameters["key_name"] = "aws-agent"

        if query.strip().startswith("sg-"):
            parameters["security_group_ids"] = [query.strip()]

        if "no tags" in query.lower():
            parameters["tags"] = []

        state_text = f"""

        Current Operation State

        {json.dumps(self.operation_state, indent=2)}

        """

        augmented_query = (
            state_text
            + build_query_with_company_context(query)
        )

        while count < self.max_iterations:

            toolcall = self.agent.invoke({
                "input": augmented_query,
                "chat_history": self.chat_history,
                "agent_scratchpad": agent_scratchpad,
            })

            agent_scratchpad.append(toolcall)

            if not toolcall.tool_calls:

                final_answer = toolcall.content
                final_answer = _ensure_structured_response(final_answer, steps)

                self.chat_history.extend([
                    HumanMessage(content=query),
                    AIMessage(content=final_answer),
                ])

                return {
                    "output": final_answer,
                    "steps": steps,
                }

            for tool in toolcall.tool_calls:

                tool_name = tool["name"]
                tool_args = tool["args"]
                tool_call_id = tool["id"]
                if (
                    tool_name == "aws_cloud_control"
                    and isinstance(tool_args, dict)
                    and tool_args.get("operation", "").lower() == "delete"
                ):
                    print(f"[DEBUG-AGENT] *** DELETE OPERATION DETECTED! ***")
                    approval_id = str(uuid4())

                    pending_tool_input = dict(tool_args)
                    pending_tool_input.pop("approved", None)

                    identifier = pending_tool_input.get("identifier", "")

                    pending_obs = json.dumps({
                        "status": "pending_approval",
                        "operation": "delete",
                        "resource_type": pending_tool_input.get("resource_type", ""),
                        "identifier": identifier,
                        "region": pending_tool_input.get("region", "us-east-1"),
                        "approval_required": True,
                        "approval_id": approval_id,
                        "tool_name": tool_name,
                        "tool_input": pending_tool_input,
                    })

                    agent_scratchpad.append(
                        ToolMessage(
                            content=pending_obs,
                            tool_call_id=tool_call_id,
                        )
                    )

                    steps.append({
                        "tool": tool_name,
                        "tool_input": pending_tool_input,
                        "observation": pending_obs,
                    })

                    human_message = (
                        f"Deleting an AWS resource is a destructive action and will permanently remove it.\n\n"
                        f"**Resource Type:** {pending_tool_input.get('resource_type', 'Unknown')}\n"
                        f"**Identifier:** {identifier}\n"
                        f"**Region:** {pending_tool_input.get('region', 'us-east-1')}\n\n"
                        f"Please type **'yes'** to confirm the deletion or **'cancel'** to abort."
                    )

                    return {
                        "output": human_message,
                        "steps": steps,
                        "pending_approval": {
                            "approval_id": approval_id,
                            "tool_name": tool_name,
                            "tool_input": pending_tool_input,
                            "message": human_message,
                        },
                    }
                
                        

                if (
                    tool_name in APPROVAL_REQUIRED_ACTIONS
                    and isinstance(tool_args, dict)
                    and tool_args.get("action") in APPROVAL_REQUIRED_ACTIONS[tool_name]
                ):

                    pending_op = {
                        "tool_name": tool_name,
                        "tool_args": tool_args,
                    }

                    configuration = "\n".join(
                        f"• **{k.replace('_',' ').title()}**: {v}"
                        for k, v in tool_args.items()
                    )

                    return {
                        "output": (
                            "### Configuration Summary\n\n"
                            f"{configuration}\n\n"
                            "**Type 'Yes' to proceed or 'Cancel' to abort.**"
                        ),
                        "steps": steps,
                        "pending_operation": pending_op,
                    }
                tool_obs = name2tool[tool_name](**tool_args)

                steps.append({
                    "tool": tool_name,
                    "tool_input": tool_args,
                    "observation": tool_obs,
                })

                agent_scratchpad.append(
                    ToolMessage(
                        content=str(tool_obs),
                        tool_call_id=tool_call_id,
                    )
                )

                if tool_name == "final_answer":

                    try:
                        result = json.loads(tool_obs)
                        final_answer = result.get("answer", tool_obs)
                    except Exception:
                        final_answer = tool_obs

                    final_answer = _ensure_structured_response(final_answer, steps)

                    self.chat_history.extend([
                        HumanMessage(content=query),
                        AIMessage(content=final_answer),
                    ])

                    return {
                        "output": final_answer,
                        "steps": steps,
                    }

            count += 1

        self.chat_history.extend([
            HumanMessage(content=query),
            AIMessage(content="Task completed."),
        ])

        return {
            "output": "Task completed.",
            "steps": steps,
        }