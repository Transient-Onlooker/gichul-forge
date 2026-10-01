# Documentation

Gichul Forge의 설계 자료와 구현 점검 기록을 모아 둔 디렉터리입니다.

## Architecture

- [Mermaid 차트 전체 모음](./architecture/mermaid-charts.md)
- [Mermaid 원본 파일](./architecture/mermaid/)

## Audits

- [구현 점검](./audits/implementation-audit.md)
- [노드별 구현 매핑](./audits/node-audit.csv)
- [검증 기록](./audits/validation.md)

## 문서 유지 원칙

- 루트에는 실행에 직접 필요한 파일과 대표 README만 둡니다.
- 설계 자료는 `docs/architecture/`에 둡니다.
- 특정 시점의 검증·점검 결과는 `docs/audits/`에 둡니다.
- 기능 변경 후 검증 결과가 달라지면 audit 문서도 함께 갱신합니다.
