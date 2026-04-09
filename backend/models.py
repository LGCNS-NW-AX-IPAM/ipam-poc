from backend.app.core.database import Base, engine
from sqlalchemy import Column, Integer, String, DateTime, Enum
import datetime

# 예시: 메인 작업 테이블
class ReclamationMainTask(Base):
    __tablename__ = "reclamation_main_tasks"
    
    job_id = Column(Integer, primary_key=True, index=True)
    status = Column(String(20), default="Ready")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# 💡 여기서 create_all을 호출합니다!
def init_db():
    # Base에 연결된 모든 테이블 모델을 DB에 생성합니다.
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("테이블 생성 완료!")