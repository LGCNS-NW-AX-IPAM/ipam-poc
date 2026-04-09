# 🌐 IPAM AI Reclamation Agent PoC

본 프로젝트는 **LG CNS 통신사업부** IP 관리 업무의 효율화를 위해, AI 에이전트(Gemini + LangGraph)를 활용하여 IP 회수 프로세스를 자동화하는 개념검증(PoC) 프로토타입입니다.

## 🚀 프로젝트 핵심 요약
- **UI**: ChatGPT 스타일의 React 대화형 인터페이스.
- **Orchestrator**: LangGraph를 통한 사용자 의도(Intent) 분석 및 워크플로우 제어.
- **Business Logic**: IP 회수 후보 추출 및 회수 작업 진행 관리
- **External System**: NTOSS API 연동 Mocking 및 Gmail 알림 발송.

---

## 🛠 Tech Stack
- **Frontend**: React, Tailwind CSS, Lucide-React, Axios
- **Backend**: Python 3.11+, FastAPI, LangChain, LangGraph
- **LLM**: Google Gemini 2.5 Flash (Google Generative AI)
- **Database**: MySQL 8.0+ (SQLAlchemy ORM)

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
      │   ├── llm/                # AI 에이전트 (LangGraph, Intent Analyzer)
      │   ├── models/             # SQLAlchemy 테이블 정의
      │   ├── schemas/            # Pydantic (Request/Response DTO)
      │   ├── core/               # 설정 (config.py, database.py)
      │   └── client/             # 외부 시스템 클라이언트 (NtossClient)
      ├── .env                    # 환경 변수
      ├── main.py                 # 앱 엔트리 포인트
      └── requirements.txt

## ⚙️ 설치 및 실행 방법

### 1. Database (MySQL) 설정 -- (작성필요)
MySQL 클라이언트에서 아래 스크립트를 실행하여 PoC용 데이터베이스와 테이블을 생성합니다.

CREATE DATABASE IF NOT EXISTS ipam_db;
USE ipam_db;

CREATE TABLE IF NOT EXISTS ip_candidates (
    candidate_id INT AUTO_INCREMENT PRIMARY KEY,
    extracted_date DATE NOT NULL,
    nw_id VARCHAR(50) NOT NULL,
    ip_address VARCHAR(20) NOT NULL,
    team_name VARCHAR(100) NOT NULL,
    manager_email VARCHAR(100) NOT NULL,
    manager_name VARCHAR(50) NOT NULL
);

INSERT INTO ip_candidates (extracted_date, nw_id, ip_address, team_name, manager_email, manager_name)
VALUES (CURDATE(), 'NW_SEOUL_01', '10.123.45.67', '인프라팀', 'donghyuk454@gmail.com', '이동혁');

### 2. Backend 설정 (/backend)
터미널에서 백엔드 폴더로 이동하여 환경을 구성합니다.

cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt

.env 파일 생성: backend/ 폴더 내에 아래 내용을 입력합니다.

서버 실행:
python3 main.py

### 3. Frontend 설정 (/frontend)
새 터미널 탭에서 프런트엔드를 실행합니다.

cd frontend
npm install
npm start

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