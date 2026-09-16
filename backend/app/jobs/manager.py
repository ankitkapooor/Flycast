"""Experiment job manager with bounded thread pool and filesystem persistence."""

import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

from app.config import settings
from app.brain.loader import get_brain
from app.forecasting.pipeline import run_experiment_pipeline, PipelineResult
from app.jobs.models import JobStatus, ExperimentStatusResponse, ExperimentConfig
from app.jobs.cleanup import cleanup_expired_experiments

logger = logging.getLogger("flycast.jobs.manager")


class JobManager:
    def __init__(self):
        self.executor = ThreadPoolExecutor(
            max_workers=settings.MAX_CONCURRENT_JOBS,
            thread_name_prefix="flycast-worker",
        )
        self.statuses: Dict[str, ExperimentStatusResponse] = {}
        self.ip_submissions: Dict[str, list] = {}

    def check_rate_limit(self, client_ip: Optional[str]) -> bool:
        """Checks if client IP exceeded hourly submission limit."""
        if not client_ip:
            return True
        now = datetime.now(timezone.utc).timestamp()
        cutoff = now - 3600
        
        times = self.ip_submissions.get(client_ip, [])
        times = [t for t in times if t > cutoff]
        self.ip_submissions[client_ip] = times

        if len(times) >= settings.RATE_LIMIT_PER_HOUR:
            return False
        times.append(now)
        return True

    def submit_experiment(
        self,
        csv_bytes: bytes,
        time_column: Optional[str] = None,
        target_column: Optional[str] = None,
        feature_columns: Optional[list] = None,
        forecast_horizon: int = 5,
        run_control: bool = False,
        demo_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> str:
        """Enqueues a new experiment and returns its unique ID."""
        exp_id = str(uuid.uuid4())
        now_str = datetime.now(timezone.utc).isoformat()

        # Setup experiment storage
        exp_dir = settings.experiments_dir / exp_id
        exp_dir.mkdir(parents=True, exist_ok=True)

        # Save uploaded dataset
        dataset_path = exp_dir / "dataset.csv"
        with open(dataset_path, "wb") as f:
            f.write(csv_bytes)

        # Save config
        config = ExperimentConfig(
            id=exp_id,
            time_column=time_column,
            target_column=target_column,
            feature_columns=feature_columns or [],
            forecast_horizon=forecast_horizon,
            run_control=run_control,
            demo_id=demo_id,
            client_ip=client_ip,
        )
        with open(exp_dir / "config.json", "w") as f:
            f.write(config.model_dump_json(indent=2))

        # Initialize status
        status_resp = ExperimentStatusResponse(
            id=exp_id,
            status=JobStatus.QUEUED,
            progress=0,
            message="Queued for execution...",
            created_at=now_str,
            updated_at=now_str,
        )
        self.statuses[exp_id] = status_resp
        self._persist_status(exp_dir, status_resp)

        # Submit task
        self.executor.submit(
            self._execute_job,
            exp_id=exp_id,
            exp_dir=exp_dir,
            csv_bytes=csv_bytes,
            config=config,
        )
        return exp_id

    def get_status(self, exp_id: str) -> Optional[ExperimentStatusResponse]:
        """Returns cached or filesystem-stored job status."""
        if exp_id in self.statuses:
            return self.statuses[exp_id]
        
        status_file = settings.experiments_dir / exp_id / "status.json"
        if status_file.exists():
            try:
                with open(status_file, "r") as f:
                    data = json.load(f)
                resp = ExperimentStatusResponse(**data)
                self.statuses[exp_id] = resp
                return resp
            except Exception:
                pass
        return None

    def get_result(self, exp_id: str) -> Optional[Dict[str, Any]]:
        """Reads result.json for an experiment."""
        result_file = settings.experiments_dir / exp_id / "result.json"
        if result_file.exists():
            with open(result_file, "r") as f:
                return json.load(f)
        return None

    def get_chart_data(self, exp_id: str) -> Optional[Dict[str, Any]]:
        """Reads chart.json for an experiment."""
        chart_file = settings.experiments_dir / exp_id / "chart.json"
        if chart_file.exists():
            with open(chart_file, "r") as f:
                return json.load(f)
        return None

    def get_predictions_path(self, exp_id: str) -> Optional[Path]:
        """Returns path to predictions.csv if present."""
        path = settings.experiments_dir / exp_id / "predictions.csv"
        return path if path.exists() else None

    def get_experiment_json_path(self, exp_id: str) -> Optional[Path]:
        """Returns path to result.json if present."""
        path = settings.experiments_dir / exp_id / "result.json"
        return path if path.exists() else None

    def delete_experiment(self, exp_id: str) -> bool:
        """Deletes experiment files and status cache."""
        self.statuses.pop(exp_id, None)
        exp_dir = settings.experiments_dir / exp_id
        if exp_dir.exists():
            import shutil
            shutil.rmtree(exp_dir, ignore_errors=True)
            return True
        return False

    def _persist_status(self, exp_dir: Path, status_resp: ExperimentStatusResponse):
        try:
            with open(exp_dir / "status.json", "w") as f:
                f.write(status_resp.model_dump_json(indent=2))
        except Exception as e:
            logger.error("Failed to persist status: %s", e)

    def _execute_job(
        self,
        exp_id: str,
        exp_dir: Path,
        csv_bytes: bytes,
        config: ExperimentConfig,
    ):
        """Worker thread entry point."""
        logger.info("Starting experiment %s", exp_id)
        brain = get_brain()

        def progress_cb(stage: str, progress: int, msg: str):
            now_str = datetime.now(timezone.utc).isoformat()
            st_enum = getattr(JobStatus, stage.upper(), JobStatus.RUNNING_BRAIN)
            resp = ExperimentStatusResponse(
                id=exp_id,
                status=st_enum,
                progress=progress,
                message=msg,
                created_at=self.statuses[exp_id].created_at,
                updated_at=now_str,
            )
            self.statuses[exp_id] = resp
            self._persist_status(exp_dir, resp)

        try:
            res: PipelineResult = run_experiment_pipeline(
                experiment_id=exp_id,
                csv_bytes=csv_bytes,
                brain=brain,
                time_column=config.time_column,
                target_column=config.target_column,
                feature_columns=config.feature_columns,
                forecast_horizon=config.forecast_horizon,
                run_control=config.run_control,
                leak=settings.RESERVOIR_LEAK,
                recurrent_gain=settings.RESERVOIR_GAIN,
                input_gain=settings.INPUT_GAIN,
                seed=settings.CONNECTOME_SEED,
                progress_cb=progress_cb,
            )

            # Save results, predictions, chart
            with open(exp_dir / "result.json", "w") as f:
                json.dump(res.result_dict, f, indent=2)

            res.predictions_df.write_csv(exp_dir / "predictions.csv")

            with open(exp_dir / "chart.json", "w") as f:
                json.dump(res.chart_data, f, indent=2)

            # Mark complete
            now_str = datetime.now(timezone.utc).isoformat()
            done_resp = ExperimentStatusResponse(
                id=exp_id,
                status=JobStatus.COMPLETE,
                progress=100,
                message="The fly has spoken.",
                created_at=self.statuses[exp_id].created_at,
                updated_at=now_str,
            )
            self.statuses[exp_id] = done_resp
            self._persist_status(exp_dir, done_resp)
            logger.info("Experiment %s completed successfully", exp_id)

        except Exception as e:
            logger.exception("Experiment %s failed: %s", exp_id, e)
            now_str = datetime.now(timezone.utc).isoformat()
            err_resp = ExperimentStatusResponse(
                id=exp_id,
                status=JobStatus.FAILED,
                progress=100,
                message=f"Experiment failed: {str(e)}",
                error=str(e),
                created_at=self.statuses[exp_id].created_at,
                updated_at=now_str,
            )
            self.statuses[exp_id] = err_resp
            self._persist_status(exp_dir, err_resp)


_JOB_MANAGER: Optional[JobManager] = None


def get_job_manager() -> JobManager:
    global _JOB_MANAGER
    if _JOB_MANAGER is None:
        _JOB_MANAGER = JobManager()
    return _JOB_MANAGER
