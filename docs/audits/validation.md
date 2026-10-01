# Validation

최종 갱신: 2026-10-01

## 현재 자동 검증

GitHub Actions의 `.github/workflows/ci.yml`에서 아래 검사를 수행합니다.

### 프론트엔드

기준: Node.js 24, pnpm 12.8.1

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm lint
pnpm typecheck
pnpm build
pnpm audit --prod --audit-level=high
```

검증 항목:

- 잠금 파일 기반 재현 설치
- ESLint
- TypeScript strict type check
- Next.js production build
- production dependency high 이상 취약점 검사

### 백엔드

기준: Python 3.14

```bash
cd backend
python -m pip install -r requirements.txt
python -m pip check
python -m compileall app
python -c "from app.main import app; from app.workflow import parse_workflow_nodes; assert app.title == 'Gichul Forge Backend'; assert len(parse_workflow_nodes()) == 161"
```

검증 항목:

- 의존성 설치 및 충돌 검사
- Python bytecode compile
- FastAPI 앱 import
- 워크플로 노드 161개 파싱

### 컨테이너

```bash
cp .env.local.example .env.local
docker compose build
```

프론트엔드와 백엔드 검증이 모두 통과한 뒤 두 Docker 이미지를 빌드합니다.

## 2026-10-01 현대화 검증

의존성/도구 체인 현대화 과정에서 다음을 확인했습니다.

- pnpm 12.8.1 잠금 파일 재생성: 통과
- 프론트엔드 pnpm frozen install: 통과
- ESLint: 통과
- TypeScript type check: 통과
- Next.js production build: 통과
- Python 3.14 의존성 설치: 통과
- Python compile/import: 통과
- Docker Compose build: 통과

최종 merge 전 CI에는 production dependency audit, `pip check`, 161개 워크플로 노드 파싱 검사도 포함합니다.

## 기존 파이프라인 샘플 검증

2026-07 초기 구현 당시 1페이지 테스트 PDF로 아래 흐름이 검증되었습니다.

- Mermaid 파싱 노드 수: 161
- `run_until_review`: `needs_review`, waitingFor=`E16`
- `continue_processing`: 최종 PDF 생성 성공, waitingFor=`S2`
- `finalize_job`: `completed`, progress=`100`, downloadReady=`true`

이 샘플 PDF end-to-end 실행은 2026-10-01 의존성 현대화 과정에서 다시 수행한 검사가 아닙니다. 현재 자동 CI는 설치, 정적 검사, 앱 import, 워크플로 파싱, production build와 Docker build를 검증합니다.

## 노드 점검

[`node-audit.csv`](./node-audit.csv)에 Mermaid 원문 161개 노드의 ID, 라벨, 그룹, 구현 위치와 반영 상태를 기록합니다.
