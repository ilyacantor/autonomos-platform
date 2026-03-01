"""
Demo Orchestrator API — Real E2E Data Flow

Orchestrates the actual AOD → AAM → DCL pipeline by calling each
external service's real API endpoints:

  1. AOD: Fetch latest Farm snapshot → trigger discovery scan
  2. AOD: Export triaged catalog → push candidates to AAM
  3. AAM: Infer pipe definitions from candidates
  4. AAM: Push declared pipes to DCL

Each step makes real HTTP calls. The pipeline runs as a background task
with polling support for the frontend demo runner.
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from enum import Enum

logger = logging.getLogger(__name__)

router = APIRouter()

AOD_BASE_URL = os.getenv("AOD_BASE_URL", "")
AAM_BASE_URL = os.getenv("AAM_BASE_URL", "")
DCL_V2_BASE_URL = os.getenv("DCL_V2_BASE_URL", "")
AOD_API_KEY = os.getenv("AOD_API_KEY", "")


# ── Models ────────────────────────────────────────────────────────────

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStep(BaseModel):
    name: str
    display_name: str
    status: StepStatus
    message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class PipelineJob(BaseModel):
    job_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    steps: List[PipelineStep]
    current_step: int
    total_steps: int
    message: str


PIPELINE_JOBS: Dict[str, PipelineJob] = {}


# ── Helpers ───────────────────────────────────────────────────────────

def _aod_headers() -> Dict[str, str]:
    """Headers for calling AOD (requires X-API-Key)."""
    headers = {"Content-Type": "application/json"}
    if AOD_API_KEY:
        headers["X-API-Key"] = AOD_API_KEY
    return headers


def _aam_headers() -> Dict[str, str]:
    """Headers for calling AAM (no API key required)."""
    return {"Content-Type": "application/json"}


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _mark_step(step: PipelineStep, status: StepStatus, message: str, data: Optional[Dict] = None):
    step.status = status
    step.message = message
    if status == StepStatus.RUNNING:
        step.started_at = _now()
    if status in (StepStatus.SUCCESS, StepStatus.FAILED, StepStatus.SKIPPED):
        step.completed_at = _now()
    if data:
        step.data = data


# ── Pipeline Steps ────────────────────────────────────────────────────

def create_initial_steps() -> List[PipelineStep]:
    return [
        PipelineStep(name="aod_scan", display_name="AOD Discovery Scan", status=StepStatus.PENDING,
                     message="Waiting to scan assets"),
        PipelineStep(name="aod_handoff", display_name="AOD → AAM Handoff", status=StepStatus.PENDING,
                     message="Waiting to export to AAM"),
        PipelineStep(name="aam_infer", display_name="AAM Pipe Inference", status=StepStatus.PENDING,
                     message="Waiting to infer pipes"),
        PipelineStep(name="aam_dcl_push", display_name="AAM → DCL Push", status=StepStatus.PENDING,
                     message="Waiting to push to DCL"),
    ]


async def run_pipeline_background(job_id: str):
    """Run the real E2E pipeline as a background task."""
    import httpx

    job = PIPELINE_JOBS.get(job_id)
    if not job:
        return

    async with httpx.AsyncClient(timeout=60.0) as client:
        run_id = None

        for i, step in enumerate(job.steps):
            _mark_step(step, StepStatus.RUNNING, f"Running {step.display_name}...")
            job.current_step = i + 1
            job.status = "running"
            job.message = f"Step {i + 1}/{job.total_steps}: {step.display_name}"

            try:
                # ── Step 1: AOD Discovery Scan ────────────────────
                if step.name == "aod_scan":
                    if not AOD_BASE_URL:
                        _mark_step(step, StepStatus.SKIPPED, "AOD_BASE_URL not configured")
                        continue

                    # Try to get latest snapshot from Farm via AOD
                    snap_res = await client.get(
                        f"{AOD_BASE_URL}/api/farm/all-snapshots",
                        headers=_aod_headers()
                    )

                    if snap_res.status_code == 200:
                        snapshots = snap_res.json()
                        if snapshots and len(snapshots) > 0:
                            latest = snapshots[0]
                            tenant_id = latest.get("tenant_id", "")
                            snapshot_id = latest.get("snapshot_id") or latest.get("id", "")

                            # Trigger actual discovery scan from Farm snapshot
                            scan_res = await client.post(
                                f"{AOD_BASE_URL}/api/runs/from-farm",
                                headers=_aod_headers(),
                                json={"tenant_id": tenant_id, "snapshot_id": snapshot_id}
                            )

                            if scan_res.status_code == 200:
                                scan_data = scan_res.json()
                                run_id = scan_data.get("run_id")
                                _mark_step(step, StepStatus.SUCCESS,
                                           f"Scan complete: run_id={run_id}",
                                           {"run_id": run_id, **scan_data})
                            else:
                                # Scan failed — try using latest existing run
                                runs_res = await client.get(
                                    f"{AOD_BASE_URL}/api/runs",
                                    headers=_aod_headers()
                                )
                                if runs_res.status_code == 200:
                                    runs = runs_res.json()
                                    if runs and len(runs) > 0:
                                        run_id = runs[0].get("run_id") or runs[0].get("id")
                                        _mark_step(step, StepStatus.SUCCESS,
                                                   f"Using latest run: {run_id}",
                                                   {"run_id": run_id, "mode": "existing_run"})
                                    else:
                                        _mark_step(step, StepStatus.FAILED,
                                                   f"Scan failed ({scan_res.status_code}) and no existing runs")
                                else:
                                    _mark_step(step, StepStatus.FAILED,
                                               f"Scan failed: {scan_res.status_code}")
                        else:
                            # No snapshots — try existing runs
                            runs_res = await client.get(
                                f"{AOD_BASE_URL}/api/runs",
                                headers=_aod_headers()
                            )
                            if runs_res.status_code == 200:
                                runs = runs_res.json()
                                if runs and len(runs) > 0:
                                    run_id = runs[0].get("run_id") or runs[0].get("id")
                                    _mark_step(step, StepStatus.SUCCESS,
                                               f"No snapshots; using latest run: {run_id}",
                                               {"run_id": run_id, "mode": "existing_run"})
                                else:
                                    _mark_step(step, StepStatus.FAILED, "No snapshots and no existing runs")
                            else:
                                _mark_step(step, StepStatus.FAILED, "No Farm snapshots available")
                    else:
                        _mark_step(step, StepStatus.FAILED,
                                   f"Could not reach AOD Farm API: {snap_res.status_code}")

                # ── Step 2: AOD → AAM Handoff ─────────────────────
                elif step.name == "aod_handoff":
                    if not AOD_BASE_URL or not run_id:
                        _mark_step(step, StepStatus.SKIPPED,
                                   "Skipped: no AOD run_id" if not run_id else "AOD_BASE_URL not configured")
                        continue

                    # Export candidates to AAM
                    export_res = await client.post(
                        f"{AOD_BASE_URL}/api/handoff/aam/export",
                        headers=_aod_headers(),
                        params={"run_id": run_id, "status_filter": "all"}
                    )

                    if export_res.status_code == 200:
                        export_data = export_res.json()
                        candidate_count = export_data.get("candidates_sent", export_data.get("count", "?"))
                        _mark_step(step, StepStatus.SUCCESS,
                                   f"Exported {candidate_count} candidates to AAM",
                                   export_data)
                    else:
                        error_detail = ""
                        try:
                            error_detail = export_res.json().get("detail", "")
                        except Exception:
                            error_detail = export_res.text[:200]
                        _mark_step(step, StepStatus.FAILED,
                                   f"Handoff failed ({export_res.status_code}): {error_detail}",
                                   {"status_code": export_res.status_code})

                # ── Step 3: AAM Pipe Inference ────────────────────
                elif step.name == "aam_infer":
                    if not AAM_BASE_URL:
                        _mark_step(step, StepStatus.SKIPPED, "AAM_BASE_URL not configured")
                        continue

                    infer_res = await client.post(
                        f"{AAM_BASE_URL}/api/aam/infer",
                        headers=_aam_headers()
                    )

                    if infer_res.status_code == 200:
                        infer_data = infer_res.json()
                        _mark_step(step, StepStatus.SUCCESS,
                                   f"Inference complete",
                                   infer_data)
                    else:
                        _mark_step(step, StepStatus.FAILED,
                                   f"Inference failed ({infer_res.status_code})")

                # ── Step 4: AAM → DCL Push ────────────────────────
                elif step.name == "aam_dcl_push":
                    if not AAM_BASE_URL:
                        _mark_step(step, StepStatus.SKIPPED, "AAM_BASE_URL not configured")
                        continue

                    push_res = await client.post(
                        f"{AAM_BASE_URL}/api/export/dcl/push",
                        headers=_aam_headers()
                    )

                    if push_res.status_code == 200:
                        push_data = push_res.json()
                        _mark_step(step, StepStatus.SUCCESS,
                                   "Pushed to DCL",
                                   push_data)
                    else:
                        _mark_step(step, StepStatus.FAILED,
                                   f"DCL push failed ({push_res.status_code})")

            except Exception as e:
                logger.error(f"[DEMO] Step {step.name} error: {e}", exc_info=True)
                _mark_step(step, StepStatus.FAILED, f"Error: {str(e)}")

        # ── Finalize ──────────────────────────────────────────────
        failed = [s for s in job.steps if s.status == StepStatus.FAILED]
        if failed:
            job.status = "completed_with_errors"
            job.message = f"Pipeline finished with {len(failed)} error(s)"
        else:
            job.status = "completed"
            job.message = "Pipeline completed successfully"
        job.completed_at = _now()


# ── Endpoints ─────────────────────────────────────────────────────────

class RunPipelineResponse(BaseModel):
    job_id: str
    status: str
    message: str


@router.post(
    "/demo/run_pipeline",
    response_model=RunPipelineResponse,
    summary="Run full E2E demo pipeline",
    description="Starts a background job that runs the real AOD → AAM → DCL pipeline"
)
async def run_pipeline(background_tasks: BackgroundTasks):
    """
    Start the full demo pipeline. No auth required for demo access.
    Returns a job_id for polling via /demo/pipeline_status.
    """
    job_id = str(uuid.uuid4())[:8]

    job = PipelineJob(
        job_id=job_id,
        status="started",
        started_at=_now(),
        steps=create_initial_steps(),
        current_step=0,
        total_steps=4,
        message="Pipeline started"
    )

    PIPELINE_JOBS[job_id] = job
    background_tasks.add_task(run_pipeline_background, job_id)

    logger.info(f"[DEMO] Pipeline started: job_id={job_id}")
    return RunPipelineResponse(job_id=job_id, status="started",
                               message="Pipeline started. Poll /demo/pipeline_status for progress.")


@router.get(
    "/demo/pipeline_status",
    response_model=PipelineJob,
    summary="Get pipeline status"
)
async def get_pipeline_status(job_id: str):
    """Get the current status of a pipeline job. No auth required."""
    job = PIPELINE_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@router.get(
    "/demo/config",
    summary="Get demo service configuration"
)
async def get_demo_config():
    """Returns which external services are configured. No auth required."""
    return {
        "services": {
            "aod": {"configured": bool(AOD_BASE_URL), "url": AOD_BASE_URL[:40] + "..." if len(AOD_BASE_URL) > 40 else AOD_BASE_URL},
            "aam": {"configured": bool(AAM_BASE_URL), "url": AAM_BASE_URL[:40] + "..." if len(AAM_BASE_URL) > 40 else AAM_BASE_URL},
            "dcl_v2": {"configured": bool(DCL_V2_BASE_URL), "url": DCL_V2_BASE_URL[:40] + "..." if len(DCL_V2_BASE_URL) > 40 else DCL_V2_BASE_URL},
        },
        "aod_api_key_set": bool(AOD_API_KEY),
        "ready": bool(AOD_BASE_URL and AAM_BASE_URL),
    }
