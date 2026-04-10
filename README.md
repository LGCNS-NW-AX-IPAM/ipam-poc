# 🌐 IPAM AI Reclamation Agent PoC

본 프로젝트는 **LG CNS 통신사업부** IP 관리 업무의 효율화를 위해, AI 에이전트(Gemini + LangGraph)를 활용하여 IP 회수 프로세스를 자동화하는 개념검증(PoC) 프로토타입입니다.

## 🚀 프로젝트 핵심 요약
- **Intelligent Routing**: Master Router가 질문을 분석하여 '후보 추출'과 '진행 관리' 전용 에이전트로 업무를 배분합니다.
- **Reasoning-based Querying**: LLM이 DB 조회 전 파라미터를 설계하고, 왜 그렇게 조회했는지 판단 근거를 사용자에게 설명합니다.
- **Collaborative Architecture**: 에이전트가 도메인별(Candidate/Reclaim)로 분리되어 있어 Git 충돌 방지 및 개별 고도화에 최적화되어 있습니다.
- **Stateless Synchronization**: React-FastAPI 간 세션 상태 공유를 통해 대화 맥락과 추출된 데이터를 유지합니다.

---

## 🛠 Tech Stack
- **Frontend**: React, Tailwind CSS, Lucide-React, Axios
- **Backend**: Python 3.11+, FastAPI, LangChain, LangGraph
- **LLM**: Google Gemini 2.5 Flash (Google Generative AI)
- **Database**: MySQL 8.0+ (SQLAlchemy ORM)
- **External Interface**: NTOSS API (Mocking), Gmail SMTP

---

## 🏗 System Architecture

### Multi-Agent Workflow
1. **Master Router**: 입력을 분석하여 도메인(`Candidate`, `Reclaim`, `Chat`)을 분류합니다.
2. **Sub-Agents**: 각 도메인 전문가 에이전트가 독립적인 그래프를 통해 의도 분석 및 DB 조회를 수행합니다.

---

## 📂 디렉토리 구조
```text
ipam-poc/
├── frontend/                # React 프론트엔드
│   ├── src/App.js           # 메인 채팅 로직
│   ├── tailwind.config.js   # 스타일 설정
│   └── package.json         # 의존성 패키지
└── backend/
      ├── app/
      │   ├── api/                # FastAPI Endpoints (Route 설정)
      │   ├── services/           # 비즈니스 로직 (IP 회수 시퀀스, 메일 발송 등)
      │   ├── repositories/       # 데이터 접근 (SQLAlchemy CRUD)
      │   ├── llm/                # AI 에이전트 및 Orchestrator(Router)
      │   ├── models/             # SQLAlchemy 테이블 정의
      │   ├── schemas/            # Pydantic (Request/Response DTO)
      │   ├── core/               # 설정 (config.py, database.py)
      │   └── client/             # 외부 시스템 클라이언트 (NtossClient)
      ├── .env                    # 환경 변수
      ├── main.py                 # 앱 엔트리 포인트
      └── requirements.txt
```

## ⚙️ 설치 및 실행 방법

### 1. Database (MySQL) 설정 -- (작성중)
MySQL 클라이언트에서 아래 스크립트를 실행하여 PoC용 데이터베이스와 테이블을 생성합니다.
```sql
CREATE DATABASE IF NOT EXISTS ipam_db;
USE ipam_db;

-- 1. IP 회수 후보 테이블 (Candidate)
CREATE TABLE ip_reclaim_candidate (
    candidate_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    extraction_batch_id VARCHAR(50),
    extraction_date DATE,
    nw_id VARCHAR(50),
    ip_address VARCHAR(45),
    owner_team VARCHAR(100),
    owner_email VARCHAR(255),
    status VARCHAR(20) DEFAULT 'READY' -- READY, IN_PROGRESS, DONE
);

-- 2. IP 회수 작업 메인 테이블 (Job)
CREATE TABLE ip_reclaim_job (
    ip_reclaim_job_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    main_task_id VARCHAR(100), -- NTOSS 메인 ID
    sub_task_id VARCHAR(100),  -- NTOSS 서브 ID
    requester_id VARCHAR(100),
    job_status VARCHAR(20),    -- READY, PROCESSING, COMPLETED
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. IP 회수 작업 상세 테이블 (Job Item)
CREATE TABLE ip_reclaim_job_item (
    ip_reclaim_job_item_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ip_reclaim_job_id BIGINT,
    ip_address VARCHAR(45),
    owner_team VARCHAR(100),
    item_status VARCHAR(20),   -- READY, FAILED, RELEASED
    FOREIGN KEY (ip_reclaim_job_id) REFERENCES ip_reclaim_job(ip_reclaim_job_id)
);
```

### 2. Backend 설정 (/backend)
터미널에서 백엔드 폴더로 이동하여 환경을 구성합니다.
```shell
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```
.env 파일 생성: backend/ 폴더 내에 아래 내용을 입력합니다.

서버 실행:
```shell
python3 main.py
```

### 3. Frontend 설정 (/frontend)
새 터미널 탭에서 프런트엔드를 실행합니다.

```shell
cd frontend
npm install
npm start
```

## 🤖 주요 대화 시나리오 (PoC Scenario, 작성필요)

* 작업 시작: "오늘 IP 회수할 거 리스트 뽑아줘"
    * 에이전트가 START 인텐트를 분석하여 DB에서 오늘 날짜의 후보군을 조회합니다. (팀당 최대 4개 제한 로직 작동)
* 최종 확정: "응, 그대로 진행해" 또는 "확정"
    * 에이전트가 CONFIRM 인텐트를 파악하여 NTOSS API(Mock)를 호출하고 작업 등록 및 관리자 메일을 발송합니다.
* 일반 대화: "너는 누구니?" 또는 "도움말"
    * Gemini가 시스템의 정체성과 처리 가능한 업무를 자연어로 안내합니다.

## ⚠️ 개발 참고 사항

* CORS 설정: main.py에 React(3000포트) 접속 허용 설정이 되어 있어 프런트엔드와 즉시 통신이 가능합니다.
* Gmail 발송: 보안 정책상 Google 계정의 일반 비밀번호는 작동하지 않습니다. 반드시 [Google 계정 > 보안 > 2단계 인증 > 앱 비밀번호]에서 생성한 16자리 코드를 사용하세요.
* API Mocking: NTOSS 시스템 연동은 ntoss_client.py에서 가상으로 구현되어 있습니다. 실제 시스템 연동 시 해당 클래스의 내부 로직만 실제 호출 코드로 교체하면 됩니다.