from app.core.database import Base, engine, SessionLocal
from app.models.entities import IPReclaimCandidate
import random

def init_db():
    Base.metadata.drop_all(bind=engine) # Start fresh for PoC
    Base.metadata.create_all(bind=engine)
    
    # Insert mock candidates
    db = SessionLocal()
    teams = ["인프라팀", "플랫폼팀", "보안팀", "데이터팀", "클라우드팀", "솔루션팀"]
    managers = ["김철수", "이영희", "박지민", "최동혁", "정미경", "한상우"]
    
    candidates = []
    for i in range(1, 51):
        team_idx = i % len(teams)
        candidates.append(IPReclaimCandidate(
            nw_id=f"NW{str(i).zfill(3)}",
            ip=f"10.100.{team_idx}.{i}",
            team=teams[team_idx],
            manager=managers[team_idx]
        ))
    
    db.add_all(candidates)
    db.commit()
    db.close()
    print("Database initialized with mock data.")

if __name__ == "__main__":
    init_db()
