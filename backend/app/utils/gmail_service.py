import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("GMAIL_SERVICE")


def send_mail(to_email: str, subject: str, body: str) -> bool:
    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_user or not gmail_password:
        logger.info(f"[MAIL MOCK] To: {to_email} | Subject: {subject}\n{body}")
        return True

    try:
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = gmail_user
        msg["To"] = to_email
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(gmail_user, gmail_password)
            smtp.send_message(msg)

        logger.info(f"[MAIL SENT] To: {to_email}")
        return True
    except Exception as e:
        logger.error(f"[MAIL ERROR] To: {to_email} | {str(e)}")
        return False


def send_reclaim_notification(owner_email: str, ip_address: str, nw_id: str, owner_team: str) -> bool:
    """IP 회수 사전 안내 메일 발송"""
    subject = f"[IPAM] IP 회수 작업 사전 안내 - {ip_address}"
    body = f"""안녕하세요,

IPAM 시스템에서 아래 IP에 대한 회수 작업이 금일 예정되어 있습니다.

- IP 주소: {ip_address}
- NW ID: {nw_id}
- 담당 팀: {owner_team}

이의가 있으신 경우 이 메일에 회신해 주세요.
회신이 없을 경우 승인으로 처리됩니다.

감사합니다.
IPAM AI Assistant
"""
    return send_mail(owner_email, subject, body)


def send_error_notification(owner_email: str, error_type: str, ip_address: str, nw_id: str, error_msg: str, sub_task_id: str = "") -> bool:
    """회수 오류 알림 메일 발송 (담당자용) — 조치 진행 여부 회신 요청"""
    subject = f"[IPAM 오류] {error_type} 회수 실패 - {ip_address}"
    body = f"""안녕하세요,

IPAM 시스템에서 아래 IP에 대한 {error_type} 회수 처리 중 오류가 발생했습니다.

- 오류 유형: {error_type}
- IP 주소: {ip_address}
- NW ID: {nw_id}
- 서브작업 ID: {sub_task_id}
- 오류 메시지: {error_msg}

조치가 필요하신 경우 이 메일에 "조치 진행해줘"라고 회신해 주세요.
(/scheduler/failure-reply API 로 회신 내용을 전달하시면 처리됩니다.)

IPAM AI Assistant
"""
    return send_mail(owner_email, subject, body)


def send_dhcp_action_completion(owner_email: str, ip_address: str, nw_id: str, sub_task_id: str) -> bool:
    """DHCP 실패 조치 완료 메일 발송 (담당자용)"""
    subject = f"[IPAM] DHCP 회수 실패 조치 완료 - {ip_address}"
    body = f"""안녕하세요,

요청하신 DHCP 회수 실패 조치가 완료되었습니다.

[처리 내용]
- 서브작업 ID: {sub_task_id}
- IP 주소: {ip_address}
- NW ID: {nw_id}
- 조치: NTOSS 작업없음(취소) 처리 완료

해당 IP는 이후 IP 회수 작업 대상으로 재관리됩니다.

IPAM AI Assistant
"""
    return send_mail(owner_email, subject, body)


def send_device_action_completion(owner_email: str, ip_address: str, nw_id: str,
                                   original_sub_task_id: str, new_sub_task_id: str) -> bool:
    """장비 회수 실패 조치 완료 메일 발송 (담당자용)"""
    subject = f"[IPAM] 장비 회수 실패 조치 완료 - {ip_address}"
    body = f"""안녕하세요,

요청하신 장비 회수 실패 조치가 완료되었습니다.

[처리 내용]
- 원본 서브작업 ID: {original_sub_task_id}
- 신규 서브작업 ID: {new_sub_task_id}
- IP 주소: {ip_address}
- NW ID: {nw_id}

[조치 순서]
1. 신규 서브작업({new_sub_task_id}) 생성 완료
2. IP {ip_address} 신규 서브작업에 재할당 완료
3. 신규 서브작업({new_sub_task_id}) 완료 처리
4. 원본 서브작업({original_sub_task_id}) 작업없음(취소) 처리 완료

IPAM AI Assistant
"""
    return send_mail(owner_email, subject, body)
