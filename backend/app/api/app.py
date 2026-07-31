"""
FastAPI server — exposes the AWS Agent via REST API.
"""
from datetime import datetime
import json
import os
import secrets
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import AuthToken, ChatSession, SessionLocal, User

env_path = None
for parent in Path(__file__).resolve().parents:
    candidate = parent / ".env"
    if candidate.exists():
        env_path = candidate
        break

if env_path is not None:
    load_dotenv(dotenv_path=env_path)

from app.agents.aws_agent import CustomAgentExecuter
from app.rag.retriever import get_or_create_retriever, rebuild_knowledge_base
from app.tools import ALL_TOOLS
from app.tools.tools import execute_aws_cloud_control


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
        pass


class ChatRequest(BaseModel):
    message: str = Field(..., description="Natural language message for the AWS agent")
    chat_history: list[dict] = Field(
        default=[],
        description="Previous conversation messages for context"
    )


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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_auth_token(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    auth_token = AuthToken(token=token, user_email=user.email)
    db.add(auth_token)
    db.commit()
    db.refresh(auth_token)
    return auth_token.token


def authenticate_user(email: str, password: str, db: Session) -> Optional[User]:
    user = db.get(User, email)
    if user and user.password == password:
        return user
    return None


def get_current_user(authorization: Optional[str] = Header(None, alias="Authorization"), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.strip().lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization token.")

    token = authorization.strip().split(" ", 1)[1]
    auth_token = db.get(AuthToken, token)
    if auth_token is None:
        raise HTTPException(status_code=401, detail="Invalid authorization token.")

    user = db.get(User, auth_token.user_email)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found for token.")

    return user


class AuthRequest(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")


class AuthResponse(BaseModel):
    email: str
    token: str
    sessions: list[dict]
    activeSessionId: Optional[str] = None


class SessionPayload(BaseModel):
    title: Optional[str] = None
    messages: list[dict] = Field(default_factory=list)


class SessionsResponse(BaseModel):
    sessions: list[dict]


class EmptyResponse(BaseModel):
    success: bool


def format_observation(obs_str: str) -> str:
    """
    Format tool observation JSON into clean markdown.
    """
    try:
        obs = json.loads(obs_str)
    except:
        return obs_str

    def _format_value(value: Any) -> str:
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    def _extract_resource_name(properties: Any, identifier: str | None = None) -> str | None:
        if isinstance(properties, dict):
            tags = properties.get('Tags') or properties.get('tags')
            if isinstance(tags, list):
                for tag in tags:
                    if isinstance(tag, dict) and str(tag.get('Key', '')).lower() == 'name':
                        return str(tag.get('Value', ''))
            if properties.get('Name'):
                return str(properties.get('Name'))
        return identifier

    if isinstance(obs, dict) and obs.get('status') == 'success' and isinstance(obs.get('resources'), list):
        count = obs.get('count', len(obs['resources']))
        resource_type = obs.get('resource_type', 'AWS Resource')
        resource_display = resource_type.replace('AWS::', '').replace('::', ' ').strip() or 'AWS Resource'

        lines = [f"## {resource_display} Resources Found", f"Total: {count}", ""]
        for idx, resource in enumerate(obs['resources']):
            identifier = resource.get('identifier', 'N/A')
            props = resource.get('properties', {})
            resource_name = _extract_resource_name(props, identifier)

            if resource_name:
                lines.append(f"Resource Name: {resource_name}")
            else:
                lines.append(f"Identifier: {identifier}")
            lines.append(f"Resource Type: {resource_display}")

            if isinstance(props, dict):
                for key in sorted(props.keys()):
                    if key in {'Tags', 'tags'}:
                        continue
                    lines.append(f"{key.replace('_', ' ').title()}: {_format_value(props[key])}")
            else:
                if props is not None:
                    lines.append(f"Properties: {_format_value(props)}")

            if idx < len(obs['resources']) - 1:
                lines.append("")

        return "\n".join(lines)

    if isinstance(obs, dict) and obs.get('status') == 'success' and isinstance(obs.get('properties'), dict):
        resource_type = obs.get('resource_type', 'AWS Resource')
        resource_display = resource_type.replace('AWS::', '').replace('::', ' ').strip() or 'AWS Resource'
        resource_name = _extract_resource_name(obs.get('properties'), obs.get('identifier')) or resource_display

        lines = [f"## {resource_display} Resource Details", "Total: 1", ""]
        lines.append(f"Resource Name: {resource_name}")
        lines.append(f"Resource Type: {resource_display}")
        for key in sorted(obs['properties'].keys()):
            if key in {'Tags', 'tags'}:
                continue
            lines.append(f"{key.replace('_', ' ').title()}: {_format_value(obs['properties'][key])}")
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


approval_requests: Dict[str, ApprovalRequest] = {}

conversational_pending: Optional[dict] = None


def _find_pending_approval(request_text: str) -> Optional[ApprovalRequest]:
    if not request_text:
        return None

    normalized = request_text.strip().lower()
    if normalized.startswith("/approve"):
        parts = normalized.split()
        if len(parts) >= 2:
            return approval_requests.get(parts[1])

    pending = [req for req in approval_requests.values() if req.status == "pending"]

    if "approve" in normalized:
        for req in pending:
            tool_input = req.tool_input
            if isinstance(tool_input, dict):
                identifier = str(tool_input.get("identifier", "")).lower()
                if identifier and identifier in normalized:
                    return req

    return None


@app.post("/auth/register", response_model=AuthResponse, tags=["Auth"])
def register(request: AuthRequest, db: Session = Depends(get_db)):
    email = request.email.strip().lower()
    if db.get(User, email) is not None:
        raise HTTPException(status_code=400, detail="Email is already registered.")

    user = User(email=email, password=request.password)
    db.add(user)
    db.commit()
    db.refresh(user)

    session = ChatSession(
        id=uuid.uuid4().hex,
        user_email=user.email,
        title="New conversation",
        messages=json.dumps([]),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    token = create_auth_token(db, user)

    return AuthResponse(
        email=user.email,
        token=token,
        sessions=[session.to_dict()],
        activeSessionId=session.id,
    )


@app.post("/auth/login", response_model=AuthResponse, tags=["Auth"])
def login(request: AuthRequest, db: Session = Depends(get_db)):
    email = request.email.strip().lower()
    user = authenticate_user(email, request.password, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    sessions = [session.to_dict() for session in sorted(user.sessions, key=lambda s: s.updated_at, reverse=True)]
    token = create_auth_token(db, user)

    return AuthResponse(
        email=user.email,
        token=token,
        sessions=sessions,
        activeSessionId=sessions[0]["id"] if sessions else None,
    )


@app.get("/sessions", response_model=SessionsResponse, tags=["Sessions"])
def list_sessions(user: User = Depends(get_current_user)):
    return {
        "sessions": [session.to_dict() for session in sorted(user.sessions, key=lambda s: s.updated_at, reverse=True)]
    }


@app.post("/sessions", response_model=dict, tags=["Sessions"])
def create_session(payload: SessionPayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = ChatSession(
        id=uuid.uuid4().hex,
        user_email=user.email,
        title=payload.title or "New conversation",
        messages=json.dumps(payload.messages or []),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session.to_dict()


@app.put("/sessions/{session_id}", response_model=dict, tags=["Sessions"])
def update_session(session_id: str, payload: SessionPayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.get(ChatSession, session_id)
    if session is None or session.user_email != user.email:
        raise HTTPException(status_code=404, detail="Session not found.")

    session.title = payload.title or session.title
    session.messages = json.dumps(payload.messages or [])
    session.updated_at = datetime.utcnow()
    db.add(session)
    db.commit()
    db.refresh(session)
    return session.to_dict()


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

    normalized_msg = request.message.strip().lower()
    confirmation_words = {"yes", "yes proceed", "proceed", "confirm", "go ahead", "continue", "okay", "ok"}
    cancel_words = {"cancel", "no", "stop", "abort"}

    def has_confirmation(msg):
        return any(word in msg for word in confirmation_words)
    
    def has_cancellation(msg):
        return any(word in msg for word in cancel_words)

    global conversational_pending

    if has_confirmation(normalized_msg) and conversational_pending is not None:
        pending = conversational_pending
        name2tool_local = {t.name: t.func for t in ALL_TOOLS}
        try:
            tool_result = name2tool_local[pending["tool_name"]](**pending["tool_args"])
        except Exception as e:
            conversational_pending = None
            raise HTTPException(status_code=500, detail=f"Execution failed: {e}")

        conversational_pending = None
        duration_ms = int((time.time() - start) * 1000)

        observation = tool_result if isinstance(tool_result, str) else json.dumps(tool_result)
        formatted_obs = format_observation(observation)

        return ChatResponse(
            message=request.message,
            response=formatted_obs,
            steps=[ToolStep(tool=pending["tool_name"], tool_input=pending["tool_args"], observation=formatted_obs)],
            duration_ms=duration_ms,
        )

    if has_cancellation(normalized_msg) and conversational_pending is not None:
        conversational_pending = None
        duration_ms = int((time.time() - start) * 1000)
        return ChatResponse(
            message=request.message,
            response="Operation cancelled.",
            steps=[],
            duration_ms=duration_ms,
        )

    pending_request = None
    if has_confirmation(normalized_msg):
        pending_list = [req for req in approval_requests.values() if req.status == "pending"]
        import re

        id_matches = re.findall(r"i-[0-9a-fA-F]{6,}", request.message)
        if id_matches:
            match_id = id_matches[0]
            for req in pending_list:
                try:
                    ti = req.tool_input
                    if isinstance(ti, dict) and str(ti.get("identifier", "")).lower() == match_id.lower():
                        pending_request = req
                        break
                except Exception:
                    continue

        if pending_request is None and request.chat_history:
            for hist in reversed(request.chat_history):
                if hist.get("role") != "assistant":
                    continue
                content = hist.get("content", "") or ""
                ids = re.findall(r"i-[0-9a-fA-F]{6,}", content)
                if ids:
                    match_id = ids[0]
                    for req in pending_list:
                        try:
                            ti = req.tool_input
                            if isinstance(ti, dict) and str(ti.get("identifier", "")).lower() == match_id.lower():
                                pending_request = req
                                break
                        except Exception:
                            continue
                    if pending_request:
                        break

                tool_calls = hist.get("tool_calls") or hist.get("steps") or []
                for tc in tool_calls:
                    try:
                        ti = tc.get("tool_input") or tc.get("args") or {}
                        tid = ti.get("identifier") if isinstance(ti, dict) else None
                        if tid:
                            for req in pending_list:
                                try:
                                    rti = req.tool_input
                                    if isinstance(rti, dict) and str(rti.get("identifier", "")).lower() == str(tid).lower():
                                        pending_request = req
                                        break
                                except Exception:
                                    continue
                        if pending_request:
                            break
                    except Exception:
                        continue
                if pending_request:
                    break

        if pending_request is None and pending_list:
            pending_request = pending_list[-1]
    if pending_request is None:
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
    except Exception:
        traceback.print_exc()
        raise

    duration_ms = int((time.time() - start) * 1000)

    formatted_steps = []
    for s in result.get("steps", []):
        step = ToolStep(**s)
        step.observation = format_observation(step.observation)
        formatted_steps.append(step)

    approval_required = False
    approval_id = None
    approval_message = None

    if result.get("pending_operation"):
        conversational_pending = result["pending_operation"]

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

        formatted_steps = [
            ToolStep(
                tool=pending["tool_name"],
                tool_input=pending["tool_input"],
                observation=format_observation(pending.get("message", "")),
            )
        ]

        result_output = approval_message

    response_text = result_output if result.get("pending_approval") else result.get("output", "")

    return ChatResponse(
        message=request.message,
        response=response_text,
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
