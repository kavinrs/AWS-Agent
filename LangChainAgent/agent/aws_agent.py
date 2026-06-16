"""
AWS Agent — LangChain ReAct agent with 2 powerful generic tools.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage,ToolMessage,HumanMessage,AIMessage
from LangChainAgent.tools import ALL_TOOLS
from langchain_core.runnables import RunnableSerializable
import json

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

SYSTEM_MESSAGE = """You are an expert AWS Resource Manager AI Agent.

CRITICAL - MUST INCLUDE ALL RESOURCES IN FINAL ANSWER 
When the tool returns a list of resources, you MUST include every single resource in your final answer.
If you receive 6 resources, your final answer must show all 6 resources.
If you receive 10 resources, your final answer must show all 10 resources.
NEVER abbreviate, truncate, or say "and X more". LIST THEM ALL.

RESPONSE FORMAT RULES (CRITICAL):
- Use proper markdown formatting for all responses
- Use **bold** for important terms and values (like resource names)
- Use ### for section headers
- Use numbered lists (1. 2. 3.) for items
- Use - for bullet points
- NEVER use asterisks *, #, or other symbols improperly
- Keep formatting clean and professional

When listing resources, format like this:
### AWS Resources Found

**Total: X Resources**

1. **Resource Name:** value - **Type:** value - **Status:** value
2. **Resource Name:** value - **Type:** value - **Status:** value
3. **Resource Name:** value - **Type:** value - **Status:** value

CRITICAL RULES FOR LISTING RESOURCES:
1. Include EVERY SINGLE resource returned by the tool - DO NOT truncate or summarize
2. If the tool returns 6 resources, your final answer MUST show all 6
3. If the tool returns 100 resources, your final answer MUST show all 100
4. Count the resources in the tool response and verify your answer includes exactly that count
5. Number each resource item (1., 2., 3., etc.) with no gaps
6. Include all relevant properties for each resource
7. DO NOT say "and X more..." - list every single resource explicitly

IMPORTANT FORMATTING RULES:
1. All bold text MUST use **text** format
2. All headers MUST use ### or ## or # format
3. Separate sections with blank lines
4. Use numbered lists for multiple items
5. Show complete data - never truncate lists

Tools available:
1. aws_cloud_control — manage AWS resources (list, create, read, update, delete)
2. cloudwatch_logs — query CloudWatch log groups
3. final_answer — provide your formatted final response with COMPLETE data (all resources)

ALWAYS:
- Call a tool to get real data (never invent)
- Format responses cleanly with proper markdown
- Include ALL resources in your final answer (MUST include every one, never truncate)
- Use the final_answer tool with well-formatted output containing EVERY resource returned
- For errors, explain them clearly
"""


api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError(
        "OPENAI_API_KEY not found in environment. "
        "Please ensure .env file exists and contains OPENAI_API_KEY"
    )

llm_openai = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=api_key,
)

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_MESSAGE),
    MessagesPlaceholder("chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])

name2tool = {tool.name: tool.func for tool in ALL_TOOLS}
class CustomAgentExecuter:
    chat_history:list[BaseMessage]

    def __init__(self,max_iterations:int=3):
        self.chat_history=[]
        self.max_iterations=max_iterations
        self.agent: RunnableSerializable=({
            "input":lambda x:x["input"],
            "chat_history":lambda x:x["chat_history"],
            "agent_scratchpad":lambda x:x["agent_scratchpad"]
        }
        | prompt
        | llm_openai.bind_tools(ALL_TOOLS,tool_choice="any")
        )
    
    def invoke(self,query:str)->dict:
        agent_scratchpad=[]
        count=0
        steps=[]
        final_answer_text = None
        
        while count<self.max_iterations:
            toolcall=self.agent.invoke({
                "input":query,
                "chat_history":self.chat_history,
                "agent_scratchpad":agent_scratchpad
            }
            )

            agent_scratchpad.append(toolcall)

            tool_name=toolcall.tool_calls[0]["name"]
            tool_args = toolcall.tool_calls[0]["args"]
            tool_call_id = toolcall.tool_calls[0]["id"]

            tool_obs=name2tool[tool_name](**tool_args)

            tool_exec=ToolMessage(
                content=f"{tool_obs}",
                tool_call_id=tool_call_id
            )

            agent_scratchpad.append(tool_exec)

            print(f"{count}: {tool_name}({tool_args})")
            
            steps.append({
                "tool": tool_name,
                "tool_input": tool_args,
                "observation": tool_obs,
            })

            if tool_name=="final_answer":
                try:
                    final_answer_dict = json.loads(tool_obs)
                    final_answer_text = final_answer_dict.get("answer", tool_obs)
                except:
                    final_answer_text = tool_obs
                break
            
            count += 1
        
        if final_answer_text is None:
            final_answer_text = "Task completed without final answer."
            
        self.chat_history.extend([
            HumanMessage(content=query),
            AIMessage(content=final_answer_text)
        ])

        return {"output": final_answer_text, "steps": steps}
