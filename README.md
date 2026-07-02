# MERMIAD Service v2

기출 PDF/ZIP을 업로드하면 과목·교육과정 기준으로 문항을 분리하고, NVIDIA NIM 기반 OCR/비전/태깅을 거쳐 단원별 문제 모음집 PDF를 생성하는 웹서비스입니다.

이번 버전은 **프론트엔드 Next.js/React/TypeScript + 백엔드 Python/FastAPI** 구조입니다. 기존 Next.js API Route 백엔드는 제거했고, 모든 처리 파이프라인은 `backend/`의 Python 서비스 계층에서 동작합니다.

## 핵심 개선점

- Python FastAPI 백엔드 분리
- `.env.local`에서 NVIDIA NIM 모델을 역할별로 직접 선택 가능
- 텍스트, 비전, OCR, 메타데이터, 단원 태깅, QA 모델 분리 설정
- UX 개선: 업로드 마법사, 모델 설정 패널, 실시간 노드 진행률, 검수 큐, 메타데이터/역할 수정, 최종 승인 단계
- Mermaid 원문 161개 노드 전체 파싱 및 상태 패널 반영
- `NODE_AUDIT.csv`, `IMPLEMENTATION_AUDIT.md`에 전체 노드 반영 점검 결과 포함

## 빠른 실행

```bash
cp .env.local.example .env.local
# .env.local에 NVIDIA_NIM_API_KEY와 원하는 모델명을 입력

docker compose up --build
```

브라우저: `http://localhost:3000`  
백엔드 API 문서: `http://localhost:8000/docs`

## 로컬 개발 실행

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

## `.env.local` 모델 설정

```env
NVIDIA_NIM_API_KEY=nvapi-...
NVIDIA_NIM_BASE_URL=https://integrate.api.nvidia.com/v1

# 역할별 모델. 계정에서 접근 가능한 NIM 모델명으로 교체하세요.
NVIDIA_NIM_TEXT_MODEL=nvidia/nemotron-3-ultra-550b-a55b
NVIDIA_NIM_VISION_MODEL=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning
NVIDIA_NIM_OCR_MODEL=nvidia/nemotron-ocr-v2
NVIDIA_NIM_METADATA_MODEL=nvidia/nemotron-3-ultra-550b-a55b
NVIDIA_NIM_TAGGER_MODEL=nvidia/nemotron-3-ultra-550b-a55b
NVIDIA_NIM_QA_MODEL=nvidia/nemotron-3-ultra-550b-a55b
```

프론트 UI의 “모델/서버 설정” 카드에서 백엔드가 읽은 현재 모델명을 확인할 수 있습니다.

## 주요 API

- `GET /api/health`
- `GET /api/config`
- `GET /api/curriculum?subject=수학&grade=고1`
- `POST /api/jobs`
- `GET /api/jobs/{job_id}`
- `PATCH /api/jobs/{job_id}/metadata`
- `PATCH /api/jobs/{job_id}/assets/{asset_id}`
- `POST /api/jobs/{job_id}/continue`
- `POST /api/jobs/{job_id}/issues/{issue_id}/resolve`
- `POST /api/jobs/{job_id}/finalize`
- `GET /api/jobs/{job_id}/download`
- `DELETE /api/jobs/{job_id}`

## 폴더 구조

```text
backend/     Python FastAPI 백엔드, NIM 클라이언트, PDF/OCR/태깅/검수 파이프라인
frontend/    Next.js + React + TypeScript UI
NODE_AUDIT.csv
IMPLEMENTATION_AUDIT.md
```

## Mermaid 설계 다이어그램

이 프로젝트에는 사용자 제공 Mermaid 다이어그램 원본이 포함되어 있습니다. 전체 파이프라인을 단일 차트로 보관하면서도, 개발과 디버깅이 쉽도록 단계별 `.mmd` 파일로 분리했습니다.

### 구성

- `all_mermaid_charts.md`: 모든 Mermaid 코드를 하나의 Markdown 문서로 모은 파일
- `mermaid charts/*.mmd`: 다이어그램별 Mermaid 원본 코드 파일
- `mermaid charts/99_original_single_full_flowchart.mmd`: 원본 단일 전체 Mermaid flowchart

### 다이어그램 파일 목록

- `00_overall_orchestration.mmd`: 0. 전체 오케스트레이션
- `01_upload_consent_subject_validation.mmd`: 1. 업로드, 동의, 과목 검증
- `02_file_format_metadata.mmd`: 2. 파일 형식 확인 및 메타데이터 확정
- `03_pdf_role_detection_split.mmd`: 3. PDF 역할 판별 및 문제지/답지 분리
- `04_ocr_answer_parsing_unit_tagging.mmd`: 4. OCR, 답지 파싱, 단원 태깅
- `05_question_image_extraction_quality_check.mmd`: 5. 문항 이미지 추출 및 품질 검수
- `06_unit_arrangement_problem_pdf_generation.mmd`: 6. 단원별 배치 및 문제 PDF 생성
- `07_answer_cover_toc_final_merge.mmd`: 7. 답지 재구성, 표지, 목차, 최종 병합
- `08_final_review_issue_loop.mmd`: 8. 최종 검수 및 이슈 수정 루프
- `09_ai_call_sequence.mmd`: 9. AI 호출 시점 전용 다이어그램
- `10_status_panel.mmd`: 10. 상태 패널만 따로 분리
- `99_original_single_full_flowchart.mmd`: 원본 단일 전체 Mermaid flowchart

## 실제 운영 전 확인 사항

이 프로젝트는 서비스 가능한 구조를 목표로 작성되어 있지만, 운영 배포 전에는 다음을 반드시 검증하세요.

1. 사용할 NVIDIA NIM 모델의 실제 권한과 모델명
2. 서버의 PDF 렌더링 성능 및 동시 작업 큐 제한
3. 저작권/개인정보 고지 문구의 법무 검토
4. 저장 기간과 삭제 정책의 실제 구현 정책
5. 학교 시험지 PDF 형식별 OCR 정확도 회귀 테스트
