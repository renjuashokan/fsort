from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from .config import Config
from .service import FsortService

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("face-sort-api")

app = FastAPI(
    title="face-sort API",
    description="Local HTTP API for persistent offline face management",
    version="0.1.0",
)

# Global progress tracking for the extraction background task
progress_state: dict[str, Any] = {
    "status": "idle",
    "message": "",
    "processed": 0,
    "total": 0,
}


class ExtractRequest(BaseModel):
    input_root: str


class RenameRequest(BaseModel):
    person: str
    new_name: str
    input_root: str | None = None


class MergeRequest(BaseModel):
    target: str
    source: str
    input_root: str | None = None


class SplitRequest(BaseModel):
    person: str
    input_root: str | None = None


class OrganizeRequest(BaseModel):
    input_root: str | None = None


def get_service() -> FsortService:
    if not hasattr(app.state, "cache_root") or not hasattr(app.state, "output_root"):
        raise HTTPException(
            status_code=500,
            detail="Server paths are not configured. Run through CLI.",
        )
    cache_root = Path(app.state.cache_root)
    output_root = Path(app.state.output_root)
    config_path = Path(getattr(app.state, "config_path", "config.yaml"))
    config = Config.load(config_path)
    return FsortService(cache_root, output_root, config)


def run_extract_task(input_path: Path, service: FsortService) -> None:
    global progress_state
    progress_state["status"] = "running"
    progress_state["message"] = "Starting face extraction..."
    progress_state["processed"] = 0
    progress_state["total"] = 0

    def on_progress(processed: int, total: int) -> None:
        progress_state["processed"] = processed
        progress_state["total"] = total
        progress_state["message"] = f"Processed {processed} of {total} files."

    try:
        results = service.extract(
            input_path, show_progress=False, progress_callback=on_progress
        )
        progress_state["status"] = "completed"
        progress_state[
            "message"
        ] = f"Extraction completed. Scanned: {results['scanned']}, Processed: {results['processed']}, Skipped: {results['skipped']}, Failed: {results['failed']}, Deleted: {results['deleted']}."
    except Exception as e:
        logger.exception("Extraction background task failed")
        progress_state["status"] = "failed"
        progress_state["message"] = f"Extraction failed: {str(e)}"


@app.get("/people")
def get_people() -> list[dict[str, Any]]:
    service = get_service()
    return [p.to_dict() for p in service.list_people()]


@app.get("/stats")
def get_stats() -> dict[str, int]:
    service = get_service()
    return service.stats()


@app.get("/verify")
def get_verify() -> dict[str, Any]:
    service = get_service()
    errors = service.verify()
    return {"ok": len(errors) == 0, "errors": errors}


@app.post("/rename")
def post_rename(req: RenameRequest) -> dict[str, str]:
    service = get_service()
    try:
        in_root = Path(req.input_root) if req.input_root else None
        msg = service.rename(req.person, req.new_name, in_root)
        return {"status": "success", "message": msg}
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/merge")
def post_merge(req: MergeRequest) -> dict[str, str]:
    service = get_service()
    try:
        in_root = Path(req.input_root) if req.input_root else None
        msg = service.merge(req.target, req.source, in_root)
        return {"status": "success", "message": msg}
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/split")
def post_split(req: SplitRequest) -> dict[str, str]:
    service = get_service()
    try:
        in_root = Path(req.input_root) if req.input_root else None
        msg = service.split(req.person, in_root)
        return {"status": "success", "message": msg}
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/organize")
def post_organize(req: OrganizeRequest) -> dict[str, Any]:
    service = get_service()
    try:
        in_root = Path(req.input_root) if req.input_root else None
        results = service.organize(in_root)
        return {"status": "success", "results": results}
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/extract")
def post_extract(
    req: ExtractRequest, background_tasks: BackgroundTasks
) -> dict[str, str]:
    global progress_state
    service = get_service()
    input_path = Path(req.input_root).resolve()

    if not input_path.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Input directory does not exist: {req.input_root}",
        )

    if progress_state["status"] == "running":
        raise HTTPException(
            status_code=400, detail="An extraction task is already running."
        )

    background_tasks.add_task(run_extract_task, input_path, service)
    return {
        "status": "started",
        "message": "Extraction background task has started.",
    }


@app.get("/progress")
def get_progress() -> dict[str, Any]:
    return progress_state
