"""
FastAPI server — exposes the AWS Agent via REST API.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Any
import time
import json

from LangChainAgent.agent.aws_agent import CustomAgentExecuter
from langchain_core.messages import HumanMessage, AIMessage


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


@app.get("/tools", tags=["Agent"])
def list_tools():
    """Return all available agent tools and their descriptions."""
    from LangChainAgent.tools import ALL_TOOLS
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
    try:
        executor = CustomAgentExecuter(max_iterations=4)
        
        # # Add chat history to executor
        # if request.chat_history:
        #     for msg in request.chat_history:
        #         if msg["role"] == "user":
        #             executor.chat_history.append(HumanMessage(content=msg["content"]))
        #         elif msg["role"] == "assistant":
        #             executor.chat_history.append(AIMessage(content=msg["content"]))
        
        result = executor.invoke(request.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    duration_ms = int((time.time() - start) * 1000)
    
    # Format steps with nicely formatted observations
    formatted_steps = []
    for s in result["steps"]:
        step = ToolStep(**s)
        # Format the observation for better readability
        step.observation = format_observation(step.observation)
        formatted_steps.append(step)

    return ChatResponse(
        message=request.message,
        response=result["output"],
        steps=formatted_steps,
        duration_ms=duration_ms,
    )
