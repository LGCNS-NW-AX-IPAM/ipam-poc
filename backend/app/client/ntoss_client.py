import uuid
import random
from datetime import datetime

class NtossClient:
    def create_main_task(self, worker_id: str) -> dict:
        """
        메인 작업 생성 API
        res: { "main_job_id": "..." }
        """
        main_id = f"NTOSS-MAIN-{uuid.uuid4().hex[:6].upper()}"
        return {
            "main_job_id": main_id,
            "worker_id": worker_id,
            "created_at": datetime.now().isoformat()
        }

    def create_sub_task(self, worker_id: str, main_id: str) -> dict:
        """
        서브 작업 생성 API
        res: { "sub_job_id": "..." }
        """
        sub_id = f"NTOSS-SUB-{uuid.uuid4().hex[:6].upper()}"
        return {
            "sub_job_id": sub_id,
            "main_job_id": main_id,
            "worker_id": worker_id,
            "status": "CREATED"
        }

    def register_targets(self, sub_id: str, target_list: list) -> dict:
        """
        서브 작업에 대상 등록 API
        res: { "result": "정상", "count": 20 }
        """
        # target_list 예시: [{"nw_id": "NW01", "ip": "10.1.1.1"}, ...]
        return {
            "result": "정상",
            "sub_job_id": sub_id,
            "registered_count": len(target_list),
            "timestamp": datetime.now().isoformat()
        }

    def reclaim_dhcp(self, task_id: str, nw_id: str, ip: str) -> dict:
        """
        오전 11시: DHCP 서버 IP 회수 API
        res: { "status": "SUCCESS" or "ERROR", "nw_id": "...", "ip": "..." }
        """
        is_success = random.random() > 0.1 # 10% 실패 확률
        return {
            "status": "SUCCESS" if is_success else "ERROR",
            "task_id": task_id,
            "nw_id": nw_id,
            "ip": ip,
            "error_msg": None if is_success else "DHCP Server Connection Timeout"
        }

    def reclaim_device(self, task_id: str, nw_id: str, device_id: str, ip: str) -> dict:
        """
        오후 5시: 장비 IP 회수 API
        res: { "status": "SUCCESS" or "ERROR", "device_id": "...", "ip": "..." }
        """
        is_success = random.random() > 0.05 # 5% 실패 확률
        return {
            "status": "SUCCESS" if is_success else "ERROR",
            "task_id": task_id,
            "nw_id": nw_id,
            "device_id": device_id,
            "ip": ip,
            "error_msg": None if is_success else "Device SNMP Response Error"
        }