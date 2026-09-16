"""Demo datasets API routes."""

from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

from app.config import settings
from app.demos.generate import DEMO_CATALOG, ensure_demo_files

router = APIRouter(prefix="/demos", tags=["demos"])


@router.get("")
def list_demos():
    """Lists available built-in demo datasets with descriptive metadata."""
    demo_dir = Path(settings.DATA_DIR) / "demos"
    ensure_demo_files(demo_dir)

    demos_list = []
    for demo_id, meta in DEMO_CATALOG.items():
        csv_path = demo_dir / f"{demo_id}.csv"
        sample_rows = []
        if csv_path.exists():
            with open(csv_path, "r") as f:
                sample_rows = [f.readline().strip() for _ in range(5)]

        demos_list.append({
            "id": demo_id,
            "name": meta["name"],
            "description": meta["description"],
            "time_column": meta["time_column"],
            "target_column": meta["target_column"],
            "sample_csv": "\n".join(sample_rows),
        })
    return {"demos": demos_list}


@router.get("/{demo_id}/csv")
def get_demo_csv(demo_id: str):
    """Returns raw CSV data for a built-in demo dataset."""
    if demo_id not in DEMO_CATALOG:
        raise HTTPException(status_code=404, detail="Demo dataset not found")

    demo_dir = Path(settings.DATA_DIR) / "demos"
    paths = ensure_demo_files(demo_dir)
    csv_path = paths[demo_id]

    return FileResponse(
        csv_path,
        media_type="text/csv",
        filename=f"{demo_id}.csv",
    )
