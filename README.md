# Gichul Forge

기출 PDF/ZIP을 업로드하면 과목·교육과정 기준으로 문항을 분리하고, NVIDIA NIM 기반 OCR/비전/태깅을 거쳐 단원별 문제 모음집 PDF를 생성하는 웹서비스입니다.

현재 구조는 **Next.js/React/TypeScript 프론트엔드 + Python/FastAPI 백엔드**로 구성되어 있습니다.

## 주요 기능

- PDF/ZIP 업로드 및 문제지·답지 역할 판별
- 2022 개정 교육과정 기반 단원 태깅
- NVIDIA NIM 기반 OCR, 비전, 메타데이터 추출, 태깅, QA
- 문항 이미지 추출 및 검수
- 단원별 재배치와 문제/답지 PDF 생성
- 사용자 확인이 필요한 항목을 위한 검수 큐
- 워크플로 상태 추적 및 Mermaid 설계 문서

## 빠른 실행

```bash
cp .env.local.example .env.local
# .env.local에 NVIDIA_NIM_API_KEY와 필요한 모델명을 설정

docker compose up --build
```

- 프론트엔드: http://localhost:3000
- 백엔드 API 문서: http://localhost:8000/docs

Windows에서는 루트의 `run.bat`으로 로컬 개발 서버를 시작할 수 있습니다.

## 로컬 개발

### 백엔드

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.local.example ../.env.local
uvicorn app.main:app --reload --port 8000
```

### 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

## 환경 변수

예시는 [`.env.local.example`](./.env.local.example)에 있습니다.

주요 항목:

- `NEXT_PUBLIC_API_BASE_URL`
- `NVIDIA_NIM_API_KEY`
- `NVIDIA_NIM_*_MODEL`
- `RETENTION_DAYS`
- `MAX_UPLOAD_MB`
- `CONFIDENCE_THRESHOLD`
- `MERMIAD_KOREAN_FONT_PATH`

## 2022 개정 교육과정 데이터

백엔드는 최초 실행 시 `backend/app/data/curriculum_2022_seed.json`을 읽어 교육과정 DB를 구성합니다.

이 seed는 초기 운영용 골격이므로 실제 운영 전에는 공식 교육과정 원문을 기준으로 단원·성취기준·키워드를 검증하고 보강해야 합니다.

## 주요 API

- `GET /api/health`
- `GET /api/config`
- `GET /api/curriculum`
- `POST /api/jobs`
- `GET /api/jobs/{job_id}`
- `PATCH /api/jobs/{job_id}/metadata`
- `PATCH /api/jobs/{job_id}/assets/{asset_id}`
- `POST /api/jobs/{job_id}/continue`
- `POST /api/jobs/{job_id}/issues/{issue_id}/resolve`
- `POST /api/jobs/{job_id}/finalize`
- `GET /api/jobs/{job_id}/download`
- `DELETE /api/jobs/{job_id}`

## 저장소 구조

```text
backend/                    FastAPI 백엔드 및 PDF/OCR/태깅 파이프라인
frontend/                   Next.js 프론트엔드
docs/
  architecture/             Mermaid 설계 문서와 원본
  audits/                   구현 점검 및 검증 기록
docker-compose.yml          로컬 컨테이너 실행
run.bat                     Windows 로컬 개발 런처
```

문서 인덱스는 [`docs/README.md`](./docs/README.md)를 참고하세요.

## 문서

- [아키텍처 및 Mermaid 다이어그램](./docs/architecture/mermaid-charts.md)
- [구현 노드 점검](./docs/audits/implementation-audit.md)
- [검증 기록](./docs/audits/validation.md)
- [노드별 구현 매핑](./docs/audits/node-audit.csv)

## 운영 전 확인 사항

1. 실제 사용할 NVIDIA NIM 모델의 접근 권한과 모델명
2. PDF 렌더링 성능 및 동시 작업 큐 제한
3. 업로드 자료의 저작권·개인정보 고지와 처리 정책
4. 저장 기간 및 삭제 정책의 실제 구현
5. 다양한 학교 시험지 형식에 대한 OCR/문항 추출 회귀 테스트

> `docs/audits/`의 검증 기록은 작성 당시 상태를 나타냅니다. 이후 코드 변경 시 다시 검증해 갱신해야 합니다.
