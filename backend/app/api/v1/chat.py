from typing import List, Optional
from app.llm import agent
from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.llm.agent import IPAMAgent
from pydantic import BaseModel


router = APIRouter()
agent = IPAMAgent()


class ChatRequest(BaseModel):
    history: List[dict]
    max_per_team: Optional[int] = 4
    selected_ips: Optional[List[dict]] = []

@router.post("/chat")
async def chat(req: ChatRequest):
    # LangGraph 실행
    initial_state = {
        "messages": req.history, 
        "intent": "", 
        "max_per_team": req.max_per_team,
        "selected_ips": req.selected_ips
    }
    result = agent.graph.invoke(initial_state)
    
    # Extract relevant state to return to front for context management
    return {
        "content": result["messages"][-1]["content"],
        "max_per_team": result.get("max_per_team", req.max_per_team),
        "selected_ips": result.get("selected_ips", req.selected_ips)
    }