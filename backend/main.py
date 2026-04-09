import os
from typing import List, Optional
from app.api.v1.chat import router as chat_router
from app.llm.agent import IPAMAgent
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from app.core.database import SessionLocal
from app.models.entities import IpReclaimCandidate
from app.models.enums import ReclaimStatus, DetailStatus
from backend.app.client.ntoss_client import NtossClient
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(title="IPAM AI Agent PoC")
agent = IPAMAgent()
ntoss = NtossClient()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])

class ChatRequest(BaseModel):
    history: List[dict]
    max_per_team: Optional[int] = 4
    selected_ips: Optional[List[dict]] = []

def send_gmail(subject: str, body: str, to_email: str):
    """Gmail 발송 유틸리티"""
    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")
    
    if not gmail_user or not gmail_password:
        print(f"[MAIL MOCK] To: {to_email}, Subject: {subject}")
        return

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = gmail_user
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(gmail_user, gmail_password)
            smtp.send_message(msg)
        print(f"[MAIL SENT] To: {to_email}")
    except Exception as e:
        print(f"[MAIL ERROR] {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)