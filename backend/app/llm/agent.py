import operator
import os
import random
from typing import TypedDict, List, Annotated, Union

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
from backend.app.client.ntoss_client import NtossClient
from app.core.database import SessionLocal
from app.models.entities import IpReclaimCandidate
from app.models.enums import ReclaimStatus, DetailStatus

load_dotenv()

# 상태 정의: messages는 대화가 누적되도록 Annotated[..., operator.add] 유지
class AgentState(TypedDict):
    messages: Annotated[List[Union[dict, BaseMessage]], operator.add]
    intent: str
    max_per_team: int
    selected_ips: List[dict] # Candidate IPs for confirmation

class IPAMAgent:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            temperature=0,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        self.ntoss = NtossClient()
        self.graph = self._build_graph()

    def _convert_to_messages(self, messages: List[dict]) -> List[BaseMessage]:
        """프론트의 dict 형식을 LangChain 메시지 객체로 변환"""
        converted = []
        for m in messages:
            if isinstance(m, BaseMessage):
                converted.append(m)
                continue
            # Handle both role (frontend) and langchain roles
            role = m.get('role', '')
            content = m.get('content', '')
            if role == 'user':
                converted.append(HumanMessage(content=content))
            elif role == 'assistant':
                converted.append(AIMessage(content=content))
        return converted

    def intent_analyzer(self, state: AgentState):
        """전체 맥락을 보고 의도를 분석하는 노드"""
        history = self._convert_to_messages(state['messages'])
        
        prompt = f"""
        당신은 IP 관리 시스템의 오케스트레이터입니다. 
        대화 내용을 바탕으로 사용자의 의도를 분석하세요.
        
        [의도 분류 규칙]
        - START: IP 회수 대상 조회를 요청하거나 작업을 시작하려 함 (예: "회수작업 진행해줘", "목록 뽑아봐")
        - CONFIRM: 추출된 목록을 확인했고, 실제 회수 실행을 승인함 (예: "응", "진행해줘", "확정")
        - STATUS: 현재 작업 현황이나 상태를 물어봄 (예: "진행상황 알려줘", "어떻게 돼가?")
        - LIMIT: 팀당 회수 제한 개수(숫자) 변경을 요청함 (예: "팀당 5개로 늘려줘", "제한을 2개로 줄여")
        - CHAT: 일상적인 인사나 단순 질문
        - UNKNOWN: 위 범주에 해당하지 않음

        분석된 의도 코드 하나만 답변하세요.
        """
        response = self.llm.invoke(history + [HumanMessage(content=prompt)])
        intent = response.content.strip().upper()
        
        return {"intent": intent}

    def candidate_selector(self, state: AgentState):
        """IP 회수 후보군 추출 로직"""
        max_per_team = state.get("max_per_team", int(os.getenv("DEFAULT_MAX_PER_TEAM", 4)))
        daily_limit = int(os.getenv("DAILY_RECLAMATION_LIMIT", 20))
        
        db = SessionLocal()
        try:
            # Get all candidates in Ready status
            all_ready = db.query(IpReclaimCandidate).filter(IpReclaimCandidate.status == ReclaimStatus.READY).all()
            
            # Select randomly with team limit
            random.shuffle(all_ready)
            selected = []
            team_counts = {}
            
            for cand in all_ready:
                if len(selected) >= daily_limit:
                    break
                
                count = team_counts.get(cand.team, 0)
                if count < max_per_team:
                    selected.append({
                        "id": cand.id,
                        "nw_id": cand.nw_id,
                        "ip": cand.ip,
                        "team": cand.team,
                        "manager": cand.manager
                    })
                    team_counts[cand.team] = count + 1
            
            if not selected:
                return {"messages": [{"role": "assistant", "content": "현재 회수 가능한 후보 IP가 없습니다."}]}
            
            content = f"금일 회수 대상 {len(selected)}건을 추출했습니다.\n"
            content += f"(팀당 최대 {max_per_team}개 제한 적용)\n"
            for ip in selected:
                content += f"- {ip['team']}: {ip['ip']} ({ip['manager']})\n"
            content += "\n해당 목록으로 인프라 담당자에게 메일을 발송하고 NTOSS에 등록할까요?"
            
            return {
                "messages": [{"role": "assistant", "content": content}],
                "selected_ips": selected
            }
        finally:
            db.close()

    def task_executor(self, state: AgentState):
        """NTOSS 작업 실행 및 결과 보고"""
        selected_ips = state.get("selected_ips", [])
        if not selected_ips:
            return {"messages": [{"role": "assistant", "content": "먼저 목록을 추출해야 합니다. 'IP 회수 시작'을 말씀해 주세요."}]}
        
        db = SessionLocal()
        try:
            # 1. Create NTOSS Main Task
            main_res = self.ntoss.create_main_task("ADMIN_DONGHYUK")
            main_job_id = main_res.get("main_job_id")
            
            # 2. Create NTOSS Sub Task
            sub_res = self.ntoss.create_sub_task("ADMIN_DONGHYUK", main_job_id)
            sub_job_id = sub_res.get("sub_job_id")
            
            # 3. Register Targets in NTOSS
            targets = [{"nw_id": ip["nw_id"], "ip": ip["ip"]} for ip in selected_ips]
            self.ntoss.register_targets(sub_job_id, targets)
            
            # 4. Create DB Records
            main_task = IpReclaimMainTask(
                main_job_id=main_job_id,
                sub_job_id=sub_job_id,
                requester_id="ADMIN_DONGHYUK",
                status=ReclaimStatus.READY
            )
            db.add(main_task)
            db.flush() # Get id
            
            for ip in selected_ips:
                detail = IpReclaimDetail(
                    main_task_id=main_task.id,
                    nw_id=ip["nw_id"],
                    ip=ip["ip"],
                    status=DetailStatus.READY
                )
                db.add(detail)
                
                # Update candidate status
                cand = db.query(IpReclaimCandidate).get(ip["id"])
                if cand:
                    cand.status = ReclaimStatus.IN_PROGRESS
            
            db.commit()
            
            # 5. Mock Email sending to managers (Done at 9am conceptually, but we do it here for execution start)
            content = f"✅ 확정되었습니다. NTOSS 작업({main_job_id}) 등록을 완료했습니다.\n"
            content += f"인프라 담당자들에게 최종 확인 메일을 발송했습니다.\n"
            content += "오전 11시부터 DHCP 회수 작업이 순차적으로 진행됩니다."
            
            return {"messages": [{"role": "assistant", "content": content}]}
        except Exception as e:
            db.rollback()
            return {"messages": [{"role": "assistant", "content": f"오류가 발생했습니다: {str(e)}"}]}
        finally:
            db.close()

    def limit_handler(self, state: AgentState):
        """팀당 회수 제한 개수 변경"""
        history = self._convert_to_messages(state['messages'])
        prompt = "사용자가 팀당 최대 회수 가능 IP 개수를 몇 개로 변경하고 싶어하는지 숫자만 추출하세요. 숫자가 없으면 4를 반환하세요."
        response = self.llm.invoke(history + [HumanMessage(content=prompt)])
        
        try:
            new_limit = int(response.content.strip())
        except:
            new_limit = 4
            
        return {
            "max_per_team": new_limit,
            "messages": [{"role": "assistant", "content": f"팀당 최대 회수 가능 IP 개수를 {new_limit}개로 설정했습니다. '회수 시작'을 입력하시면 새 기준이 적용됩니다."}]
        }

    def fallback_node(self, state: AgentState):
        """의도를 파악하지 못했을 때 대답하는 노드"""
        content = "죄송합니다. 제가 이해할 수 있는 범위가 아니에요. 'IP 회수 시작'이나 '작업 현황 확인'과 같은 명령을 내려주세요."
        return {"messages": [{"role": "assistant", "content": content}]}

    def chat_node(self, state: AgentState):
        """일상적인 대화 처리 및 현황 조회"""
        intent = state.get("intent", "CHAT")
        history = self._convert_to_messages(state['messages'])
        
        if intent == "STATUS":
            db = SessionLocal()
            try:
                # Get latest main task
                latest_task = db.query(IpReclaimMainTask).order_by(IpReclaimMainTask.id.desc()).first()
                if not latest_task:
                    content = "현재 진행 중인 작업이 없습니다."
                else:
                    details = db.query(IpReclaimDetail).filter(IpReclaimDetail.main_task_id == latest_task.id).all()
                    content = f"현재 작업({latest_task.main_job_id}) 상태: {latest_task.status}\n"
                    content += f"총 {len(details)}건 중:\n"
                    # Simple summary
                    statuses = [d.status for d in details]
                    summary = {}
                    for s in statuses:
                        summary[s] = summary.get(s, 0) + 1
                    for s, count in summary.items():
                        content += f"- {s}: {count}건\n"
                
                return {"messages": [{"role": "assistant", "content": content}]}
            finally:
                db.close()
        
        response = self.llm.invoke(history) 
        return {"messages": [{"role": "assistant", "content": response.content}]}

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        workflow.add_node("analyzer", self.intent_analyzer)
        workflow.add_node("selector", self.candidate_selector)
        workflow.add_node("executor", self.task_executor)
        workflow.add_node("limit", self.limit_handler)
        workflow.add_node("fallback", self.fallback_node)
        workflow.add_node("chat", self.chat_node)

        workflow.set_entry_point("analyzer")
        
        # 조건부 라우팅 설정
        workflow.add_conditional_edges(
            "analyzer",
            lambda x: x["intent"],
            {
                "START": "selector",
                "CONFIRM": "executor",
                "STATUS": "chat",
                "CHAT": "chat",
                "LIMIT": "limit",
                "UNKNOWN": "fallback"
            }
        )
        
        workflow.add_edge("selector", END)
        workflow.add_edge("executor", END)
        workflow.add_edge("limit", END)
        workflow.add_edge("chat", END)
        workflow.add_edge("fallback", END)
        
        return workflow.compile()