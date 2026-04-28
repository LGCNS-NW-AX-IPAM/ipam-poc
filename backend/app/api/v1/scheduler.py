import os
import logging
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.database import SessionLocal
from app.repositories.reclaim_job.job_repository import JobRepository
from app.client.ntoss_client import NtossClient
from app.utils.gmail_service import send_error_notification
from app.llm.reclaim_agent import reclaim_graph

router = APIRouter()
logger = logging.getLogger("SCHEDULER")
ntoss = NtossClient()


@router.post("/scheduler/dhcp")
def run_dhcp_reclaim():
    """
    [11:00 스케줄] DHCP 서버 IP 회수
    - IN-PROGRESS 상태 아이템 대상으로 NTOSS DHCP 회수 호출
    - 성공: DHCP_SUCCESS
    - 실패: DHCP_FAILED + 작업없음 처리 + 관리자 오류 메일
    """
    db = SessionLocal()
    try:
        repo = JobRepository(db)
        job = repo.get_active_job()
        if not job:
            return {"message": "진행 중인 활성 작업이 없습니다."}

        items = repo.get_items_by_job_and_status(job.ip_reclaim_job_id, ["IN-PROGRESS", "OWNER_CONFIRMED"])
        if not items:
            return {"message": "DHCP 회수 대상 아이템이 없습니다. (IN-PROGRESS, OWNER_CONFIRMED 상태 없음)"}

        results = []
        for idx, item in enumerate(items):
            if idx == 0:
                res = {"status": "ERROR", "error_msg": "DHCP Server Connection Timeout (강제 실패)"}
            else:
                res = {"status": "SUCCESS"}

            if res["status"] == "SUCCESS":
                repo.update_item_status_by_id(
                    item.ip_reclaim_job_item_id,
                    "DHCP_SUCCESS",
                    dhcp_result="SUCCESS"
                )
                results.append({"ip": item.ip_address, "status": "DHCP_SUCCESS"})
                logger.info(f"[DHCP] SUCCESS: {item.ip_address}")
            else:
                error_msg = res.get("error_msg", "Unknown error")
                repo.update_item_status_by_id(
                    item.ip_reclaim_job_item_id,
                    "DHCP_FAILED",
                    dhcp_result="FAILED",
                    ntoss_result_message=error_msg
                )
                # 담당자에게 오류 메일 발송 (조치 진행 여부 회신 요청)
                send_error_notification(
                    item.owner_email, "DHCP", item.ip_address, item.nw_id,
                    error_msg, sub_task_id=job.sub_task_id
                )
                results.append({"ip": item.ip_address, "status": "DHCP_FAILED", "error": error_msg})
                logger.warning(f"[DHCP] FAILED: {item.ip_address} | {error_msg}")

        return {"job_id": job.ip_reclaim_job_id, "processed": len(items), "results": results}
    finally:
        db.close()


@router.post("/scheduler/device")
def run_device_reclaim():
    """
    [17:00 스케줄] 장비 IP 회수
    - DHCP_SUCCESS 상태 아이템 대상으로 NTOSS 장비 회수 호출
    - 성공: DEVICE_SUCCESS → 전체 성공 시 서브/메인 작업 완료 처리
    - 실패: DEVICE_FAILED + 신규 서브작업 생성 + IP 재할당 + 서브작업 완료 + 작업없음 + 관리자 메일
    """
    db = SessionLocal()
    try:
        repo = JobRepository(db)
        job = repo.get_active_job()
        if not job:
            return {"message": "진행 중인 활성 작업이 없습니다."}

        items = repo.get_items_by_job_and_status(job.ip_reclaim_job_id, ["DHCP_SUCCESS"])
        if not items:
            return {"message": "장비 회수 대상 아이템이 없습니다. (DHCP_SUCCESS 상태 없음)"}

        results = []
        has_failure = False

        for idx, item in enumerate(items):
            device_id = item.device_id or "DEVICE-UNKNOWN"
            if idx == 0:
                res = {"status": "ERROR", "error_msg": "Device SNMP Response Error (강제 실패)"}
            else:
                res = {"status": "SUCCESS"}

            if res["status"] == "SUCCESS":
                repo.update_item_status_by_id(
                    item.ip_reclaim_job_item_id,
                    "DEVICE_SUCCESS",
                    device_result="SUCCESS"
                )
                results.append({"ip": item.ip_address, "status": "DEVICE_SUCCESS"})
                logger.info(f"[DEVICE] SUCCESS: {item.ip_address}")
            else:
                has_failure = True
                error_msg = res.get("error_msg", "Unknown error")

                repo.update_item_status_by_id(
                    item.ip_reclaim_job_item_id,
                    "DEVICE_FAILED",
                    device_result="FAILED",
                    ntoss_result_message=error_msg
                )
                # 담당자에게 오류 메일 발송 (조치 진행 여부 회신 요청)
                send_error_notification(
                    item.owner_email, "장비", item.ip_address, item.nw_id,
                    error_msg, sub_task_id=job.sub_task_id
                )
                results.append({"ip": item.ip_address, "status": "DEVICE_FAILED", "error": error_msg})
                logger.warning(f"[DEVICE] FAILED: {item.ip_address} | {error_msg}")

        # 실패 없을 때만 서브/메인 작업 완료 처리
        if not has_failure and items:
            ntoss.complete_sub_task(job.sub_task_id)
            ntoss.complete_main_task(job.main_task_id)
            repo.update_job_status(job.ip_reclaim_job_id, "DONE")
            logger.info(f"[DEVICE] 전체 완료 - job_id: {job.ip_reclaim_job_id}")

        return {"job_id": job.ip_reclaim_job_id, "processed": len(items), "results": results}
    finally:
        db.close()


class MailReplyRequest(BaseModel):
    content: str  # 담당자 메일 회신 본문


@router.post("/scheduler/mail-reply")
def handle_mail_reply(req: MailReplyRequest):
    """
    [Mock] 담당자 메일 회신 처리 — reclaim_agent 가 인텐트를 분석하여 처리
    - APPROVE / 부분 승인: IN-PROGRESS → OWNER_CONFIRMED (IP/팀 지정 가능)
    - REJECT: 지정 대상 REJECTED 처리
    - DHCP_RECOVERY: DHCP 실패 건 cancel_task_item 처리
    - DEVICE_RECOVERY: 장비 실패 건 신규 서브작업 생성 + IP 재할당 처리
    """
    state = {
        "messages": [{"role": "user", "content": req.content}],
        "intents": [],
        "current_intent": "",
        "query_plan": {},
        "selected_ips": [],
        "max_per_team": 4,
        "excluded_filters": [],
        "is_confirmed": True,
    }
    result = reclaim_graph.invoke(state)
    last_msg = result["messages"][-1]
    response_content = last_msg.content if hasattr(last_msg, "content") else last_msg.get("content")
    return {"message": response_content}
