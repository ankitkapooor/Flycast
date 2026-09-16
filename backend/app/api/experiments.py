"""Experiment execution, polling, and results retrieval API routes."""

import json
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings
from app.jobs.manager import get_job_manager
from app.jobs.models import ExperimentCreateResponse, ExperimentStatusResponse, JobStatus
from app.demos.generate import DEMO_CATALOG, ensure_demo_files

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("", response_model=ExperimentCreateResponse)
async def create_experiment(
    request: Request,
    file: Optional[UploadFile] = File(None),
    demo_id: Optional[str] = Form(None),
    time_column: Optional[str] = Form(None),
    target_column: Optional[str] = Form(None),
    feature_columns: Optional[str] = Form(None),
    forecast_horizon: int = Form(5),
    run_control: bool = Form(False),
):
    """Submits a new time-series forecasting experiment to the connectome reservoir."""
    manager = get_job_manager()

    # Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    if not manager.check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {settings.RATE_LIMIT_PER_HOUR} experiment submissions per hour.",
        )

    # Validate horizon
    if forecast_horizon < 1 or forecast_horizon > settings.MAX_FORECAST_HORIZON:
        raise HTTPException(
            status_code=400,
            detail=f"Forecast horizon must be between 1 and {settings.MAX_FORECAST_HORIZON} steps.",
        )

    # Acquire CSV bytes
    csv_bytes: bytes
    if file and file.filename:
        # File size check (5 MB limit)
        contents = await file.read()
        max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
        if len(contents) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Uploaded file exceeds maximum allowed size of {settings.MAX_UPLOAD_MB} MB.",
            )
        csv_bytes = contents
    elif demo_id:
        if demo_id not in DEMO_CATALOG:
            raise HTTPException(status_code=404, detail=f"Unknown demo dataset '{demo_id}'")
        demo_dir = Path(settings.DATA_DIR) / "demos"
        paths = ensure_demo_files(demo_dir)
        with open(paths[demo_id], "rb") as f:
            csv_bytes = f.read()
        if not target_column:
            target_column = DEMO_CATALOG[demo_id]["target_column"]
        if not time_column:
            time_column = DEMO_CATALOG[demo_id]["time_column"]
    else:
        raise HTTPException(
            status_code=400,
            detail="Either a CSV file or a valid demo_id must be provided.",
        )

    # Parse feature columns
    features_list: List[str] = []
    if feature_columns:
        features_list = [f.strip() for f in feature_columns.split(",") if f.strip()]

    # Enqueue experiment
    try:
        exp_id = manager.submit_experiment(
            csv_bytes=csv_bytes,
            time_column=time_column,
            target_column=target_column,
            feature_columns=features_list,
            forecast_horizon=forecast_horizon,
            run_control=run_control,
            demo_id=demo_id,
            client_ip=client_ip,
        )
        return ExperimentCreateResponse(id=exp_id, status=JobStatus.QUEUED)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not schedule experiment: {str(e)}")


@router.get("/{exp_id}", response_model=ExperimentStatusResponse)
def get_experiment_status(exp_id: str):
    """Returns current execution progress, status enum, and diagnostics."""
    manager = get_job_manager()
    status = manager.get_status(exp_id)
    if not status:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return status


@router.get("/{exp_id}/results")
def get_experiment_results(exp_id: str):
    """Returns complete evaluation metrics, editorial copy, and chart series."""
    manager = get_job_manager()
    status = manager.get_status(exp_id)
    if not status:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if status.status == JobStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail=status.error or "Experiment computation failed.",
        )
    if status.status != JobStatus.COMPLETE:
        raise HTTPException(
            status_code=425,
            detail=f"Experiment is still running ({status.progress}% complete)",
        )

    result = manager.get_result(exp_id)
    chart = manager.get_chart_data(exp_id)

    if not result:
        raise HTTPException(status_code=404, detail="Result records missing on disk")

    return {
        "status": "complete",
        "result": result,
        "chart": chart,
    }


@router.get("/{exp_id}/predictions.csv")
def download_predictions_csv(exp_id: str):
    """Downloads forecast observations and predictions as CSV."""
    manager = get_job_manager()
    path = manager.get_predictions_path(exp_id)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="Predictions CSV file not available")
    return FileResponse(
        path,
        media_type="text/csv",
        filename=f"flycast_predictions_{exp_id[:8]}.csv",
    )


@router.get("/{exp_id}/experiment.json")
def download_experiment_json(exp_id: str):
    """Downloads complete reproducible experiment metadata and metrics as JSON."""
    manager = get_job_manager()
    path = manager.get_experiment_json_path(exp_id)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="Experiment JSON not available")
    return FileResponse(
        path,
        media_type="application/json",
        filename=f"flycast_experiment_{exp_id[:8]}.json",
    )


@router.delete("/{exp_id}")
def delete_experiment(exp_id: str):
    """Cancels and purges experiment artifacts."""
    manager = get_job_manager()
    success = manager.delete_experiment(exp_id)
    if not success:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"status": "deleted", "id": exp_id}
