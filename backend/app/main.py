from __future__ import annotations
import uuid
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from .models import JobSnapshot, JobInput, ConsentState, MetadataPatch, AssetPatch, ContinueRequest, ResolveIssueRequest
from .settings import get_settings
from .storage import store
from .workflow import build_initial_step_states, parse_workflow_nodes
from .services.ingestion import save_uploads
from .services.curriculum import curriculum_for
from .worker import run_until_review, continue_processing, finalize_job

settings = get_settings()
app = FastAPI(title="MERMIAD Python Backend", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": "mermiad-backend", "env": settings.app_env}


@app.get("/api/config")
def config() -> dict:
    data = settings.public_config()
    data["workflowNodeCount"] = len(parse_workflow_nodes())
    return data


@app.get("/api/workflow")
def workflow() -> dict:
    return {"nodes": [n.model_dump() for n in parse_workflow_nodes()]}


@app.get("/api/curriculum")
def curriculum(subject: str = "공통수학1") -> dict:
    return {"units": [u.model_dump() for u in curriculum_for(subject)]}


@app.post("/api/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    subject: str = Form(...),
    grade: str | None = Form(None),
    outputMode: str = Form("primary"),
    aiOcrProcessing: bool = Form(False),
    personalDataRisk: bool = Form(False),
    storageRetention: bool = Form(False),
) -> dict:
    job_id = uuid.uuid4().hex
    job_dir = store.job_dir(job_id)
    saved = await save_uploads(files, job_dir, settings.max_upload_mb)
    consent = ConsentState(aiOcrProcessing=aiOcrProcessing, personalDataRisk=personalDataRisk, storageRetention=storageRetention)
    job = JobSnapshot(
        id=job_id,
        input=JobInput(subject=subject, outputMode=outputMode, consent=consent, uploadIds=[str(p) for p in saved]),
        steps=build_initial_step_states(),
    )
    store.save(job)
    background_tasks.add_task(run_until_review, job_id)
    return {"jobId": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> JobSnapshot:
    try:
        return store.get(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")


@app.patch("/api/jobs/{job_id}/metadata")
def patch_metadata(job_id: str, patch: MetadataPatch) -> JobSnapshot:
    try:
        job = store.get(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    job.metadata = patch.metadata
    return store.save(job)


@app.patch("/api/jobs/{job_id}/assets/{asset_id}")
def patch_asset(job_id: str, asset_id: str, patch: AssetPatch) -> JobSnapshot:
    try:
        job = store.get(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    for asset in job.assets:
        if asset.id == asset_id:
            if patch.role is not None: asset.role = patch.role
            if patch.questionRange is not None: asset.questionRange = patch.questionRange
            if patch.answerRange is not None: asset.answerRange = patch.answerRange
            if patch.confidence is not None: asset.confidence = patch.confidence
            return store.save(job)
    raise HTTPException(status_code=404, detail="asset not found")


@app.post("/api/jobs/{job_id}/continue")
def continue_job(job_id: str, body: ContinueRequest, background_tasks: BackgroundTasks) -> dict:
    try:
        job = store.get(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status not in {"needs_review", "running"}:
        raise HTTPException(status_code=409, detail=f"job status is {job.status}")
    background_tasks.add_task(continue_processing, job_id)
    return {"ok": True}


@app.post("/api/jobs/{job_id}/issues/{issue_id}/resolve")
def resolve_issue(job_id: str, issue_id: str, body: ResolveIssueRequest) -> JobSnapshot:
    try:
        job = store.get(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    for issue in job.issues:
        if issue.id == issue_id:
            issue.resolved = True
            issue.resolution = body.resolution
            return store.save(job)
    raise HTTPException(status_code=404, detail="issue not found")


@app.post("/api/jobs/{job_id}/finalize")
def finalize(job_id: str) -> JobSnapshot:
    try:
        return finalize_job(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")


@app.get("/api/jobs/{job_id}/download")
def download(job_id: str) -> FileResponse:
    try:
        job = store.get(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    if not job.result.finalPdfPath:
        raise HTTPException(status_code=404, detail="final PDF not ready")
    path = Path(job.result.finalPdfPath)
    if not path.exists():
        raise HTTPException(status_code=404, detail="final PDF file missing")
    return FileResponse(path, media_type="application/pdf", filename="MERMIAD_final.pdf")


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str) -> dict:
    store.delete(job_id)
    return {"ok": True}
