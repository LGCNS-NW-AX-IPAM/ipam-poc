from sqlalchemy.orm import Session
from sqlalchemy import func, select, and_, delete
from app.models.entities import IpReclaimCandidate, IpReclaimPreview
from app.models.enums import CandidateStatus

class ReclaimRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_balanced_candidates(self, team_limit: int = 4, total_limit: int = 20):
        """
        ORM 기반 팀별 균형 추출 로직
        """
        # 1. 윈도우 함수 정의 (팀별로 파티션을 나누고 무작위 정렬 후 순번 부여)
        window_func = func.row_number().over(
            partition_by=IpReclaimCandidate.owner_team,
            order_by=func.rand()
        ).label("team_rn")

        # 2. 서브쿼리 생성: 모든 컬럼 + 순번(team_rn) 포함
        # filter: 오늘 날짜의 READY 상태인 후보들
        subq = (
            select(IpReclaimCandidate, window_func)
            .where(
                and_(
                    IpReclaimCandidate.candidate_status == CandidateStatus.READY,
                    IpReclaimCandidate.extraction_date == func.curdate()
                )
            )
            .subquery()
        )

        # 3. 메인 쿼리: 서브쿼리 결과에서 팀별 순번이 team_limit 이하인 것만 필터링
        # 최종적으로 전체 limit 적용
        stmt = (
            select(subq)
            .where(subq.c.team_rn <= team_limit)
            .order_by(func.rand())
            .limit(total_limit)
        )

        result = self.db.execute(stmt).fetchall()
        return result

    def save_to_preview(self, session_id: str, requester_id: str, candidates: list):
        """추출된 후보들을 Preview 테이블에 저장"""
        preview_items = [
            IpReclaimPreview(
                session_id=session_id,
                requester_id=requester_id,
                candidate_id=c.candidate_id,
                nw_id=c.nw_id,
                ip_address=c.ip_address,
                owner_team=c.owner_team,
                owner_email=c.owner_email,
                item_status="READY"
            ) for c in candidates
        ]
        
        self.db.add_all(preview_items)
        self.db.commit()
        return preview_items

    def clear_preview(self, session_id: str):
        """세션 종료 시 프리뷰 삭제"""
        stmt = delete(IpReclaimPreview).where(IpReclaimPreview.session_id == session_id)
        self.db.execute(stmt)
        self.db.commit()