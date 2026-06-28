"""
FastAPI server — exposes the AWS Agent via REST API.
"""
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os
import time
import json

from backend.app.agents.aws_agent import CustomAgentExecuter
from backend.app.rag.retriever import get_or_create_retriever, rebuild_knowledge_base
from backend.app.tools import ALL_TOOLS
from backend.app.tools.tools import execute_aws_cloud_control


app = FastAPI(
    title="Agentic AWS Resource Manager",
    description="AI Agent that manages AWS resources through natural language.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def build_rag_index_on_startup():
    """Build or load the RAG FAISS index when the application starts."""
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        return

    try:
        get_or_create_retriever(openai_api_key)
    except Exception:
        # If RAG fails, continue starting the app without breaking the API.
        pass


class ChatRequest(BaseModel):
    message: str = Field(..., description="Natural language message for the AWS agent")
    chat_history: list[dict] = Field(
        default=[],
        description="Previous conversation messages for context"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "List all my S3 buckets",
                    "chat_history": []
                },
                {
                    "message": "Show me details of the first one",
                    "chat_history": [
                        {"role": "user", "content": "List all my S3 buckets"},
                        {"role": "assistant", "content": "You have 2 buckets: my-app-bucket, my-logs-bucket"}
                    ]
                }
            ]
        }
    }


class ToolStep(BaseModel):
    tool: str
    tool_input: Any
    observation: str


class ChatResponse(BaseModel):
    message: str
    response: str
    steps: list[ToolStep]
    duration_ms: int
    approval_required: bool = False
    approval_id: Optional[str] = None
    approval_message: Optional[str] = None


class ApprovalRequest(BaseModel):
    approval_id: str
    tool: str
    tool_input: Any
    status: str
    created_at: str
    message: str


class AdminRebuildRequest(BaseModel):
    s3_bucket: Optional[str] = None
    s3_prefix: str = Field(
        default="company-documents/",
        description="S3 prefix where company PDF documents are stored.",
    )


ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "admin-secret")


def verify_admin_api_key(x_admin_api_key: str = Header(..., alias="x-admin-api-key")):
    if x_admin_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized admin API key.")
    return x_admin_api_key


def format_observation(obs_str: str) -> str:
    """
    Format tool observation JSON into clean markdown.
    
    Args:
        obs_str: JSON string observation from tool
        
    Returns:
        Formatted markdown string
    """
    try:
        obs = json.loads(obs_str)
    except:
        return obs_str
    
    if isinstance(obs, dict) and "resources" in obs:
        lines = []
        count = obs.get('count', 0)
        resource_type = obs.get('resource_type', 'Resources')
        resource_display = resource_type.replace('AWS::', '').replace('::', ' - ')
        
        lines.append(f"### {count} {resource_display}")
        lines.append("")
        
        for i, resource in enumerate(obs["resources"], 1):
            identifier = resource.get("identifier", "N/A")
            props = resource.get("properties", {})
            
            lines.append(f"{i}. **{identifier}**")
            
            if isinstance(props, dict):
                for key, val in sorted(props.items()):
                    if val and val != "":
                        key_display = key.replace('_', ' ').replace(key[0], key[0].upper(), 1)
                        val_str = str(val)
                        if len(val_str) > 100:
                            val_str = val_str[:97] + "..."
                        
                        lines.append(f"   • **{key_display}:** {val_str}")
            else:
                lines.append(f"   • {props}")
            
            lines.append("")  # Add spacing between items
        
        return "\n".join(lines)
    
    if isinstance(obs, dict) and obs.get('status') == 'error':
        error_msg = obs.get('message', 'Unknown error')
        error_code = obs.get('error_code', '')
        if error_code:
            return f"❌ **Error ({error_code}):** {error_msg}"
        return f"❌ **Error:** {error_msg}"
    
    if isinstance(obs, dict):
        lines = []
        status = obs.get('status')
        
        if status == 'success':
            for key, val in sorted(obs.items()):
                if key not in ['status', 'resources'] and val:
                    key_display = key.replace('_', ' ').title()
                    lines.append(f"✓ **{key_display}:** {val}")
        else:
            for key, val in sorted(obs.items()):
                if val and key != 'status':
                    key_display = key.replace('_', ' ').title()
                    lines.append(f"**{key_display}:** {val}")
        
        return "\n".join(lines) if lines else str(obs)
    
    return str(obs)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": "Agentic AWS Resource Manager"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}


@app.post(
    "/admin/rebuild-knowledge-base",
    tags=["Admin"],
    dependencies=[Depends(verify_admin_api_key)],
)
def admin_rebuild_knowledge_base_endpoint(request: AdminRebuildRequest):
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured.")

    bucket = request.s3_bucket or os.getenv("COMPANY_DOCS_BUCKET")
    prefix = request.s3_prefix or os.getenv("COMPANY_DOCS_PREFIX", "company-documents/")
    if not bucket:
        raise HTTPException(
            status_code=400,
            detail="S3 bucket is required. Provide s3_bucket in the request or set COMPANY_DOCS_BUCKET.",
        )

    try:
        _, document_count = rebuild_knowledge_base(openai_api_key, bucket, prefix)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Knowledge base rebuild failed: {exc}")

    return {
        "status": "success",
        "message": "Knowledge base rebuilt from S3 and FAISS index updated.",
        "bucket": bucket,
        "prefix": prefix,
        "documents_loaded": document_count,
    }


approval_requests: Dict[str, ApprovalRequest] = {}


def _find_pending_approval(request_text: str) -> Optional[ApprovalRequest]:
    if not request_text:
        return None

    normalized = request_text.strip().lower()
    if normalized.startswith("/approve"):
        parts = normalized.split()
        if len(parts) >= 2:
            return approval_requests.get(parts[1])

    pending = [req for req in approval_requests.values() if req.status == "pending"]
    if len(pending) == 1:
        return pending[0]

    if "approve" in normalized:
        for req in pending:
            tool_input = req.tool_input
            if isinstance(tool_input, dict):
                identifier = str(tool_input.get("identifier", "")).lower()
                if identifier and identifier in normalized:
                    return req

    return None


@app.get("/tools", tags=["Agent"])
def list_tools():
    """Return all available agent tools and their descriptions."""
    return {
        "tools": [
            {"name": t.name, "description": t.description}
            for t in ALL_TOOLS
        ]
    }


@app.post("/chat", response_model=ChatResponse, tags=["Agent"])
def chat(request: ChatRequest):
    """
    Send a natural language message to the AWS Agent.
    The agent will reason, call the appropriate AWS tools, and return a response.
    Optionally include chat_history for context-aware conversations.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    start = time.time()
    pending_request = _find_pending_approval(request.message)
    if pending_request is not None:
        approved_tool_input = pending_request.tool_input
        if not isinstance(approved_tool_input, dict):
            try:
                approved_tool_input = json.loads(approved_tool_input)
            except Exception:
                approved_tool_input = {}

        approved_tool_input["approved"] = True

        try:
            tool_result = execute_aws_cloud_control(
                operation=approved_tool_input.get("operation", ""),
                resource_type=approved_tool_input.get("resource_type", ""),
                identifier=approved_tool_input.get("identifier", ""),
                properties=approved_tool_input.get("properties", None),
                region=approved_tool_input.get("region", "us-east-1"),
                approved=True,
            )
        except Exception as e:
            pending_request.status = "failed"
            raise HTTPException(status_code=500, detail=f"Approval execution failed: {str(e)}")

        pending_request.status = "approved"
        duration_ms = int((time.time() - start) * 1000)

        observation = tool_result if isinstance(tool_result, str) else json.dumps(tool_result)
        formatted_obs = format_observation(observation)

        return ChatResponse(
            message=request.message,
            response=f"Deletion approved and executed for {approved_tool_input.get('identifier', '')}.",
            steps=[ToolStep(
                tool=pending_request.tool,
                tool_input=approved_tool_input,
                observation=formatted_obs,
            )],
            duration_ms=duration_ms,
        )

    start = time.time()
    try:
        executor = CustomAgentExecuter(max_iterations=4)

        result = executor.invoke(request.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    duration_ms = int((time.time() - start) * 1000)

    # Format steps with nicely formatted observations
    formatted_steps = []
    for s in result["steps"]:
        step = ToolStep(**s)
        step.observation = format_observation(step.observation)
        formatted_steps.append(step)

    approval_required = False
    approval_id = None
    approval_message = None

    if result.get("pending_approval"):
        pending = result["pending_approval"]
        approval_id = pending["approval_id"]
        approval_required = True
        approval_message = pending.get("message", "Approval required")

        approval_requests[approval_id] = ApprovalRequest(
            approval_id=approval_id,
            tool=pending["tool_name"],
            tool_input=pending["tool_input"],
            status="pending",
            created_at=datetime.utcnow().isoformat() + "Z",
            message=approval_message,
        )

    return ChatResponse(
        message=request.message,
        response=result["output"],
        steps=formatted_steps,
        duration_ms=duration_ms,
        approval_required=approval_required,
        approval_id=approval_id,
        approval_message=approval_message,
    )


@app.post("/approve/{approval_id}", tags=["Approval"])
def approve(approval_id: str):
    request_record = approval_requests.get(approval_id)
    if request_record is None:
        raise HTTPException(status_code=404, detail="Approval request not found.")

    if request_record.status != "pending":
        raise HTTPException(status_code=400, detail=f"Approval request is already {request_record.status}.")

    approved_tool_input = request_record.tool_input
    if not isinstance(approved_tool_input, dict):
        try:
            approved_tool_input = json.loads(approved_tool_input)
        except Exception:
            approved_tool_input = {}

    approved_tool_input["approved"] = True

    try:
        tool_result = execute_aws_cloud_control(
            operation=approved_tool_input.get("operation", ""),
            resource_type=approved_tool_input.get("resource_type", ""),
            identifier=approved_tool_input.get("identifier", ""),
            properties=approved_tool_input.get("properties", None),
            region=approved_tool_input.get("region", "us-east-1"),
            approved=True,
        )
    except Exception as e:
        request_record.status = "failed"
        raise HTTPException(status_code=500, detail=f"Approval execution failed: {str(e)}")

    request_record.status = "approved"

    return {
        "approval_id": approval_id,
        "status": "approved",
        "result": json.loads(tool_result) if isinstance(tool_result, str) else tool_result,
    }
