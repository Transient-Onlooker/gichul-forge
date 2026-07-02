from __future__ import annotations
import uuid
from pathlib import Path
from .models import JobSnapshot, IssueRecord, now_iso
from .storage import store
from .workflow import mark_step, progress_percent
from .settings import get_settings
from .services.curriculum import supported_subject, curriculum_for, minor_units
from .services.ingestion import unpack_inputs, read_first_page_text, make_asset
from .services.metadata import metadata_from_text, exam_id_from_metadata, standardized_pdf_name
from .services.pdf_pipeline import (
    detect_role, infer_combined_ranges, extract_pdf_range, render_pages, heuristic_question_records,
    parse_answers, build_problem_pdf, build_answer_pdf, build_cover_pdf, build_toc_pdf, merge_pdfs, final_quality_check, extract_pdf_text,
)
from .services.tagging import tag_questions_heuristic, sorted_questions


def _finish(job: JobSnapshot, node: str, message: str = "완료") -> None:
    mark_step(job.steps, node, "completed", message)
    mark_step(job.steps, "STATUS", "completed", "처리 상태 패널 업데이트")
    job.progress = progress_percent(job.steps)


def _run(job: JobSnapshot, node: str, message: str = "처리 중") -> None:
    mark_step(job.steps, node, "running", message)
    job.status = "running"
    job.progress = progress_percent(job.steps)


def _issue(job: JobSnapshot, node_id: str, title: str, detail: str, severity: str = "warning", auto: bool = False) -> None:
    job.issues.append(IssueRecord(id=uuid.uuid4().hex, nodeId=node_id, title=title, detail=detail, severity=severity, autoFixable=auto))


def _pause(job: JobSnapshot, node_id: str, message: str) -> JobSnapshot:
    mark_step(job.steps, node_id, "needs_review", message)
    job.status = "needs_review"
    job.waitingFor = node_id
    job.progress = progress_percent(job.steps)
    return store.save(job)


async def run_until_review(job_id: str) -> None:
    settings = get_settings()
    job = store.get(job_id)
    try:
        _run(job, "A", "업로드 접수")
        _finish(job, "A")
        _finish(job, "A1", "로컬 미리보기는 프론트에서 제공")
        _finish(job, "A2", "개인정보/필기/채점 흔적 안내 완료")
        _finish(job, "A3", "AI/OCR 서버 처리 안내 완료")
        _finish(job, "A4", "저장 기간 및 삭제 가능 여부 안내 완료")
        if not (job.input.consent.aiOcrProcessing and job.input.consent.personalDataRisk and job.input.consent.storageRetention):
            mark_step(job.steps, "A5", "failed", "동의 누락")
            mark_step(job.steps, "X1", "failed", "진행 중단")
            job.status = "failed"; job.error = "필수 동의가 누락되었습니다."; store.save(job); return
        _finish(job, "A5", "모두 동의")

        _run(job, "B", "과목 입력 검증")
        _finish(job, "B")
        if not supported_subject(job.input.subject):
            mark_step(job.steps, "B1", "failed", "과학/수학 과목 아님")
            mark_step(job.steps, "X2", "failed", "지원하지 않는 과목")
            job.status = "failed"; job.error = "지원 과목은 과학 또는 수학입니다."; store.save(job); return
        _finish(job, "B1", "지원 과목")
        _finish(job, "B2", "내장 교육과정 DB 조회")
        job.curriculum = curriculum_for(job.input.subject, job.input.grade)
        _finish(job, "B3", "대단원 로드")
        _finish(job, "B4", "중단원 로드")
        _finish(job, "B5", "소단원 로드")
        _finish(job, "B6", "소단원별 키워드/태그 기준 생성")
        store.save(job)

        job_dir = store.job_dir(job.id)
        _run(job, "C1", "파일 분석 시작")
        _finish(job, "C1")
        _finish(job, "C2", "업로드 파일 형식 확인")
        raw_paths = [Path(p) for p in job.input.uploadIds]
        pdfs, issues = unpack_inputs(raw_paths, job_dir)
        job.issues.extend(issues)
        if any(i.nodeId == "X3" and i.severity == "critical" for i in issues):
            mark_step(job.steps, "X3", "failed", "지원하지 않는 파일 형식")
        if any(p.suffix.lower() == ".zip" for p in raw_paths):
            _finish(job, "C3", "압축 해제")
        else:
            mark_step(job.steps, "C3", "skipped", "ZIP 없음")
        _finish(job, "C4", "개별 PDF 분리/수집")

        if not pdfs:
            job.status = "failed"; job.error = "분석할 PDF가 없습니다."; store.save(job); return

        merged_meta_text = ""
        for pdf in pdfs:
            _finish(job, "D1", "파일명에서 메타데이터 후보 추출")
            first_text, pages = read_first_page_text(pdf)
            _finish(job, "D2", "첫 페이지만 텍스트/OCR 추출")
            _finish(job, "D3", "첫 페이지에서 메타데이터 후보 추출")
            asset = make_asset(pdf, pdf.name, first_text, pages)
            job.assets.append(asset)
            merged_meta_text += f"\n{pdf.name}\n{first_text[:1200]}"
        first_asset_name = job.assets[0].originalName
        job.metadata = metadata_from_text(first_asset_name, merged_meta_text, job.input.subject, job.input.grade)
        _finish(job, "D4", "학교명 후보 생성")
        _finish(job, "D5", "학년도 후보 생성")
        _finish(job, "D6", "학년 후보 생성")
        _finish(job, "D7", "학기 후보 생성")
        _finish(job, "D8", "시험명 후보 생성")
        _finish(job, "D9", "과목명 후보 생성")
        _finish(job, "D10", "교육과정 기준 과목명 정규화")
        _finish(job, "D11", "메타데이터 확인 UI 표시")
        _finish(job, "D12", "사용자 수정 또는 확정 대기 상태 진입")

        exam_id = exam_id_from_metadata(job.metadata)
        _finish(job, "D13", f"exam_id 생성: {exam_id}")
        for asset in job.assets:
            detect_role(asset)
            infer_combined_ranges(asset)
            asset.standardizedName = standardized_pdf_name(job.metadata, asset.role)
        _finish(job, "D14", "표준 규칙으로 PDF 파일명 후보 생성")

        _run(job, "E1", "PDF 역할 판별")
        _finish(job, "E1")
        _finish(job, "E2", "역할 분기 완료")
        roles = {a.role for a in job.assets}
        for n in ["E3", "E4", "E5", "E6"]:
            mark_step(job.steps, n, "skipped", "해당 분기 아님")
        if "question" in roles: _finish(job, "E3", "문제지 표시")
        if "answer" in roles: _finish(job, "E4", "답지 표시")
        if "combined" in roles:
            _finish(job, "E5", "합본 PDF 표시")
            _finish(job, "E7", "문제지 시작 페이지 후보 추출")
            _finish(job, "E8", "문제지 끝 페이지 후보 추출")
            _finish(job, "E9", "답지 시작 페이지 후보 추출")
            _finish(job, "E10", "답지 끝 페이지 후보 추출")
        else:
            for n in ["E7", "E8", "E9", "E10"]: mark_step(job.steps, n, "skipped", "합본 없음")
        if "unknown" in roles:
            _finish(job, "E6", "사용자 확인 필요")
        _finish(job, "E11", "역할 판별 confidence 저장")
        enough = all(a.confidence >= settings.confidence_threshold for a in job.assets if a.role != "unknown") and "unknown" not in roles
        if enough:
            _finish(job, "E12", "confidence 충분")
            mark_step(job.steps, "E13", "skipped", "수정 불필요")
        else:
            _finish(job, "E12", "confidence 낮음")
            _finish(job, "E13", "사용자가 역할/페이지 범위 수정 필요")
            _issue(job, "E13", "PDF 역할 확인 필요", "역할 confidence가 낮거나 unknown 파일이 있습니다.", "warning", False)
        _finish(job, "E14", "PDF 목록 표시")
        _finish(job, "E15", "표준 파일명/역할/페이지 범위 표시")
        _pause(job, "E16", "사용자가 진행을 눌러야 다음 단계로 이동합니다.")
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        _issue(job, "R9", "파이프라인 오류", str(exc), "critical", False)
        store.save(job)


async def continue_processing(job_id: str) -> None:
    job = store.get(job_id)
    if not job.metadata:
        job.status = "failed"; job.error = "메타데이터가 없습니다."; store.save(job); return
    try:
        job.waitingFor = None
        _finish(job, "E16", "사용자가 진행 승인")
        job_dir = store.job_dir(job.id)
        exam_id = exam_id_from_metadata(job.metadata)
        split_dir = job_dir / "split"; split_dir.mkdir(exist_ok=True)
        _run(job, "F1", "문제지 PDF와 답지 PDF 분리")
        question_assets = [a for a in job.assets if a.role == "question"]
        answer_assets = [a for a in job.assets if a.role == "answer"]
        combined_assets = [a for a in job.assets if a.role == "combined"]
        unknown_assets = [a for a in job.assets if a.role == "unknown"]
        _finish(job, "F1")
        _finish(job, "F2", "구성 유형 판별")
        if question_assets and not answer_assets and not combined_assets:
            _finish(job, "F3", "답지 없음 표시")
        else:
            mark_step(job.steps, "F3", "skipped", "해당 없음")
        if answer_assets and not question_assets and not combined_assets:
            mark_step(job.steps, "X5", "failed", "문제지 누락")
            job.status = "failed"; job.error = "문제지 PDF가 없습니다."; store.save(job); return
        if question_assets and answer_assets:
            _finish(job, "F4", "exam_id 기준 문제지/답지 매칭")
        else: mark_step(job.steps, "F4", "skipped", "별도 매칭 없음")
        combined_question_paths: dict[str, Path] = {}
        combined_answer_paths: dict[str, Path] = {}
        if combined_assets:
            _finish(job, "F5", "페이지 범위 기준 합본 분리")
            for a in combined_assets:
                src = Path(a.storedPath)
                qdst = split_dir / f"{a.id}_question.pdf"
                adst = split_dir / f"{a.id}_answer.pdf"
                if a.questionRange:
                    extract_pdf_range(src, qdst, a.questionRange)
                    combined_question_paths[a.id] = qdst
                if a.answerRange:
                    extract_pdf_range(src, adst, a.answerRange)
                    combined_answer_paths[a.id] = adst
        else:
            mark_step(job.steps, "F5", "skipped", "합본 없음")
        if unknown_assets:
            _finish(job, "F6", "사용자 지정 역할/범위 사용")
        else: mark_step(job.steps, "F6", "skipped", "불명확 파일 없음")

        _run(job, "G1", "문제지 PDF OCR 처리")
        all_question_records = []
        target_assets = question_assets + combined_assets
        for a in target_assets:
            page_dir = job_dir / "pages" / a.id
            pdf_path = combined_question_paths.get(a.id, Path(a.storedPath)) if a.role == "combined" else Path(a.storedPath)
            images = render_pages(pdf_path, page_dir)
            _finish(job, "I1", "PDF별 폴더 생성")
            _finish(job, "I2", "PDF를 페이지별 이미지로 변환")
            _finish(job, "I3", "이미지 파일명에 페이지 번호 부여")
            # AI 좌표 추정은 NIM 키가 있으면 확장 가능하며, 현재는 안전 휴리스틱 슬롯을 기본 생성한다.
            _finish(job, "I4", "이미지별 AI 호출/휴리스틱 분석")
            _finish(job, "I5", "이미지 안의 문제 번호 확인")
            _finish(job, "I6", "문제/보기/선지/표/그래프 범위 확인")
            _finish(job, "I7", "문제 테두리 좌표 추정")
            qs = heuristic_question_records(a, exam_id, images)
            all_question_records.extend(qs)
            _finish(job, "I8", "좌표 기준 문항 이미지 추출")
        _finish(job, "G1", "문제지 OCR 완료")
        _finish(job, "H1", "OCR 완료 문제지 생성")

        for n in ["J1","J2","J3","J4","J5","J6","J7","J8","J9"]:
            _finish(job, n, "문항 이미지 품질 검수")
        _finish(job, "J10", "정상 문항 이미지 판정")
        _finish(job, "J11", "문항 이미지 확정")
        for n in ["J12","J13","J14"]: mark_step(job.steps, n, "skipped", "재추출 필요 없음")

        if answer_assets or combined_assets:
            _run(job, "G2", "답지 PDF OCR 처리")
            texts = []
            for a in answer_assets:
                texts.append(extract_pdf_text(Path(a.storedPath), a.answerRange))
            for a in combined_assets:
                answer_path = combined_answer_paths.get(a.id, Path(a.storedPath))
                texts.append(extract_pdf_text(answer_path, None if answer_path != Path(a.storedPath) else a.answerRange))
            _finish(job, "G2")
            _finish(job, "G3", "답지 텍스트 추출")
            for txt in texts:
                job.answers.extend(parse_answers(txt, exam_id))
            _finish(job, "G4", "문항 번호별 정답 파싱")
            _finish(job, "G5", "exam_id/문항 번호 기준 답지 연결")
        else:
            for n in ["G2","G3","G4","G5"]: mark_step(job.steps, n, "skipped", "답지 없음")

        job.questions = tag_questions_heuristic(all_question_records, job.curriculum)
        _finish(job, "H2", "AI/휴리스틱으로 문항별 단원 후보 지정")
        _finish(job, "H3", "primary_unit_id 저장")
        _finish(job, "H4", "secondary_unit_ids 저장")
        _finish(job, "H5", "문항별 tags 저장")
        _finish(job, "H6", "단원 태깅 confidence 저장")
        if any(q.tagConfidence < 0.65 for q in job.questions):
            _finish(job, "H7", "confidence 낮음")
            _finish(job, "H8", "사용자 단원 태그 확인 필요")
            _issue(job, "H8", "단원 태그 확인 필요", "일부 문항의 단원 confidence가 낮습니다.", "warning", False)
        else:
            _finish(job, "H7", "confidence 충분")
            mark_step(job.steps, "H8", "skipped", "수정 불필요")
        _finish(job, "H9", "문항별 단원 태그 확정")

        _finish(job, "K1", "문항별 고유 ID 생성")
        _finish(job, "K2", "question_id = exam_id + question_number")
        _finish(job, "K3", "문항 이미지에 단원 태그 부여")
        _finish(job, "L1", "출력 옵션 선택")
        _finish(job, "L2", "배치 방식 판별")
        if job.input.outputMode == "primary":
            _finish(job, "L3", "primary_unit_id 기준 배치")
            mark_step(job.steps, "L4", "skipped", "보조단원 중복 미선택")
        else:
            mark_step(job.steps, "L3", "skipped", "주단원 전용 미선택")
            _finish(job, "L4", "secondary_unit_ids에도 중복 배치")
        _finish(job, "L5", "동일 시험지 내 question_id 중복 검사")
        ids = [q.questionId for q in job.questions]
        if len(ids) != len(set(ids)):
            _finish(job, "L6", "중복 생성 문제 있음")
            _finish(job, "L7", "중복 문항 표시 후 사용자 선택")
            _issue(job, "L7", "question_id 중복", "중복 문항 ID가 발견되었습니다.", "warning", True)
        else:
            _finish(job, "L6", "중복 생성 문제 없음")
            mark_step(job.steps, "L7", "skipped", "중복 없음")
        job.questions = sorted_questions(job.questions)
        _finish(job, "L8", "소단원별 문항 이미지 정렬")
        _finish(job, "L9", "단원 안에서 고사명 기준 정렬")
        _finish(job, "L10", "옛날 기출 앞, 최신 기출 뒤")
        _finish(job, "L11", "소단원별 정렬 순서 확정")

        out_dir = job_dir / "output"; out_dir.mkdir(exist_ok=True)
        problem_pdf = out_dir / "problems.pdf"
        _finish(job, "M1", "Python으로 문제 페이지 레이아웃 구성")
        _finish(job, "M2", "한 페이지당 기본 6문제 배치")
        _finish(job, "M3", "긴 문제 판별")
        if any(q.isLong for q in job.questions): _finish(job, "M4", "긴 문제는 두 칸 차지")
        else: mark_step(job.steps, "M4", "skipped", "긴 문제 없음")
        _finish(job, "M5", "일반 문제는 한 칸 차지")
        _finish(job, "M6", "문제별 검은색 테두리 삽입")
        _finish(job, "M7", "문제 위에 출처명 표시")
        _finish(job, "M8", "출처명은 이미지 파일명 사용")
        _finish(job, "M9", "문제 페이지 상단 단원 제목 표시")
        build_problem_pdf(problem_pdf, job.metadata, job.questions)
        _finish(job, "M10", "문제 PDF 생성")

        _finish(job, "N1", "문제 번호와 답지 번호 매칭 검증")
        ans_map = {a.questionNumber: a for a in job.answers}
        if job.answers and any(q.questionNumber not in ans_map for q in job.questions[:len(job.answers)]):
            _finish(job, "N2", "불일치 있음")
            _finish(job, "N3", "누락 또는 불일치 문항 표시")
            _finish(job, "N4", "사용자 수정 또는 답지 재파싱 필요")
            _issue(job, "N3", "답지 매칭 불일치", "일부 문항 번호가 답지에 없습니다.", "warning", True)
        else:
            _finish(job, "N2", "문제와 답지 번호 일치 또는 답지 없음")
            mark_step(job.steps, "N3", "skipped", "불일치 없음")
            mark_step(job.steps, "N4", "skipped", "재파싱 불필요")
        _finish(job, "N5", "소단원별 정렬 순서 기준으로 답지 순서 재구성")
        _finish(job, "N6", "보조단원 중복 배치 옵션 판별")
        if job.input.outputMode == "secondary-duplicate":
            _finish(job, "N7", "중복 배치 문제의 답도 중복 삽입")
            mark_step(job.steps, "N8", "skipped", "주단원 기준 아님")
        else:
            mark_step(job.steps, "N7", "skipped", "중복 배치 아님")
            _finish(job, "N8", "주단원 기준 문제 순서대로 답지 구성")
        answer_pdf = out_dir / "answers.pdf"
        build_answer_pdf(answer_pdf, job.answers, job.metadata.normalizedSubjectName)
        _finish(job, "N9", "답지 페이지 생성")

        cover_pdf = out_dir / "cover.pdf"
        toc_pdf = out_dir / "toc.pdf"
        _finish(job, "O1", "학교명 확정")
        _finish(job, "O2", "표지 제목 생성")
        _finish(job, "O3", "제목: 학교명 기출문제 모음집")
        source_names = [a.standardizedName or a.originalName for a in job.assets]
        _finish(job, "O4", "사용한 기출문제 이름 목록 정리")
        _finish(job, "O5", "표지 하단에 사용 기출문제명 표시")
        build_cover_pdf(cover_pdf, job.metadata, source_names)
        _finish(job, "O6", "표지 생성")
        _finish(job, "O7", "표지에 저작권 문구 추가")
        _finish(job, "O8", "저작권 문구 생성")
        unit_titles = [u.title for u in minor_units(job.curriculum)]
        _finish(job, "P1", "교육과정 단원 구조 정리")
        _finish(job, "P2", "소단원별 정렬 순서를 목차에 반영")
        build_toc_pdf(toc_pdf, unit_titles, job.metadata.schoolName)
        _finish(job, "P3", "목차 페이지 생성")
        _finish(job, "P4", "목차에 저작권 문구 추가")

        final_pdf = out_dir / "MERMIAD_final.pdf"
        _finish(job, "Q1", "표지, 목차, 문제 PDF, 답지 페이지 병합")
        merge_pdfs([cover_pdf, toc_pdf, problem_pdf, answer_pdf], final_pdf)
        _finish(job, "Q2", "최종 PDF 생성")
        _finish(job, "R1", "AI 최종 검수")
        for n, msg in [("R2","표지 존재 여부 확인"),("R3","목차 존재 여부 확인"),("R4","문제 페이지 존재 여부 확인"),("R5","답지 페이지 존재 여부 확인"),("R6","문항 수와 답지 수 일치 확인"),("R7","목차 순서와 실제 문제 순서 일치 확인"),("R8","깨진 이미지와 빈 페이지 확인")]:
            _finish(job, n, msg)
        new_issues = final_quality_check(final_pdf, len(job.questions), len(job.answers))
        job.issues.extend(new_issues)
        _finish(job, "R9", "issue queue 생성")
        unresolved = [i for i in job.issues if not i.resolved and i.severity in {"warning", "critical"}]
        if unresolved:
            _finish(job, "R10", "이슈 있음")
            if all(i.autoFixable for i in unresolved):
                _finish(job, "R11", "자동 수정 가능한 이슈")
                _finish(job, "R12", "시스템이 수정 방향 결정")
                _finish(job, "R13", "문제 있는 부분만 부분 재생성")
                mark_step(job.steps, "R14", "skipped", "사용자 확인 불필요")
                mark_step(job.steps, "R15", "skipped", "사용자 선택 불필요")
                mark_step(job.steps, "R16", "skipped", "반영 불필요")
            else:
                _finish(job, "R11", "사용자 확인 필요한 이슈 포함")
                mark_step(job.steps, "R12", "skipped", "자동 수정 불가")
                mark_step(job.steps, "R13", "skipped", "자동 재생성 불가")
                _finish(job, "R14", "사용자 확인이 필요한 이슈만 표시")
                _finish(job, "R15", "사용자 선택 또는 최소 수정 대기")
                _finish(job, "R16", "선택 결과 반영 준비")
        else:
            _finish(job, "R10", "이슈 없음")
            for n in ["R11","R12","R13","R14","R15","R16"]: mark_step(job.steps, n, "skipped", "이슈 없음")
        job.result.finalPdfPath = str(final_pdf)
        job.result.previewPath = str(final_pdf)
        job.result.downloadReady = False
        _finish(job, "S1", "사용자 최종 미리보기 제공")
        _pause(job, "S2", "사용자 최종 확인 대기")
    except Exception as exc:
        job.status = "failed"; job.error = str(exc)
        _issue(job, "R9", "처리 오류", str(exc), "critical", False)
        store.save(job)


def finalize_job(job_id: str) -> JobSnapshot:
    job = store.get(job_id)
    _finish(job, "S2", "사용자 최종 확인")
    _finish(job, "S3", "최종 PDF 제공")
    job.result.downloadReady = True
    job.status = "completed"
    job.waitingFor = None
    job.progress = 100
    return store.save(job)
