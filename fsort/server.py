from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
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


class ReassignRequest(BaseModel):
    media_id: int
    person_id: str | None = None
    input_root: str | None = None


class CreatePersonRequest(BaseModel):
    name: str


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


# --- REST API Endpoints ---

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


# --- New Paginated, Search, & Thumbnail API Endpoints ---

@app.get("/api/people")
def api_get_people(
    skip: int = 0,
    limit: int = 30,
    sort_by: str = "name",
    order: str = "asc",
    search: str | None = None,
) -> dict[str, Any]:
    service = get_service()
    total, items = service.list_people_paginated(
        skip=skip, limit=limit, sort_by=sort_by, order=order, search=search
    )
    return {"total": total, "skip": skip, "limit": limit, "items": items}


@app.get("/api/person/{person_id}")
def api_get_person(person_id: str) -> dict[str, Any]:
    service = get_service()
    if person_id == "_unknown":
        return {"id": "_unknown", "display_name": "Unknown", "embedding_count": 0}
    if person_id == "_multiple":
        return {"id": "_multiple", "display_name": "Multiple Faces", "embedding_count": 0}

    people = service.list_people()
    for p in people:
        if p.id == person_id:
            return p.to_dict()
    raise HTTPException(status_code=404, detail="Person not found")


@app.get("/api/person/{person_id}/media")
def api_get_person_media(
    person_id: str,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "filename",
    order: str = "asc",
) -> dict[str, Any]:
    service = get_service()
    total, items = service.list_person_media_paginated(
        person_id=person_id, skip=skip, limit=limit, sort_by=sort_by, order=order
    )
    return {"total": total, "skip": skip, "limit": limit, "items": items}


@app.get("/api/media/{media_id}")
def api_get_media_file(media_id: int):
    service = get_service()
    with service.store._get_connection() as conn:
        row = conn.execute("SELECT path FROM media WHERE id = ?", (media_id,)).fetchone()
    if not row or not Path(row["path"]).is_file():
        raise HTTPException(status_code=404, detail="Media file not found")
    return FileResponse(row["path"])


@app.get("/api/media/{media_id}/thumbnail")
def api_get_media_thumbnail(media_id: int):
    service = get_service()
    with service.store._get_connection() as conn:
        row = conn.execute("SELECT path, media_type FROM media WHERE id = ?", (media_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Media not found")

    path = Path(row["path"])
    media_type = row["media_type"]
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Source media file not found")

    thumb_cache_dir = service.cache_root / "thumbs"
    thumb_cache_dir.mkdir(parents=True, exist_ok=True)
    thumb_path = thumb_cache_dir / f"{media_id}.jpg"

    if thumb_path.is_file():
        return FileResponse(thumb_path)

    import cv2
    try:
        if media_type == "video":
            cap = cv2.VideoCapture(str(path))
            if not cap.isOpened():
                raise Exception("Cannot open video")
            ok, frame = cap.read()
            cap.release()
            if not ok or frame is None:
                raise Exception("Cannot read frame")
            img = frame
        else:
            img = cv2.imread(str(path))
            if img is None:
                raise Exception("Cannot read image")

        h, w = img.shape[:2]
        max_size = 400
        if w > h:
            new_w = max_size
            new_h = int(h * (max_size / w))
        else:
            new_h = max_size
            new_w = int(w * (max_size / h))

        thumb = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(thumb_path), thumb)
        return FileResponse(thumb_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate thumbnail: {e}")


@app.get("/api/person/{person_id}/thumbnail")
def api_get_person_thumbnail(person_id: str):
    service = get_service()

    if person_id in ("_unknown", "_multiple"):
        svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
            <rect width="100%" height="100%" fill="#374151"/>
            <text x="50%" y="55%" font-family="system-ui" font-size="32" fill="#9CA3AF" text-anchor="middle" dominant-baseline="middle">?</text>
        </svg>"""
        return Response(content=svg, media_type="image/svg+xml")

    thumb_cache_dir = service.cache_root / "thumbs"
    thumb_cache_dir.mkdir(parents=True, exist_ok=True)
    thumb_path = thumb_cache_dir / f"person_{person_id}.jpg"

    if thumb_path.is_file():
        return FileResponse(thumb_path)

    with service.store._get_connection() as conn:
        row = conn.execute(
            """
            SELECT f.media_id, f.bbox_x, f.bbox_y, f.bbox_w, f.bbox_h, f.frame, m.path, m.media_type
            FROM faces f
            JOIN media m ON f.media_id = m.id
            WHERE f.person_id = ?
            ORDER BY f.confidence DESC, f.id ASC LIMIT 1
            """,
            (person_id,)
        ).fetchone()

    if not row:
        svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
            <rect width="100%" height="100%" fill="#4B5563"/>
            <text x="50%" y="55%" font-family="system-ui" font-size="36" fill="#F3F4F6" text-anchor="middle" dominant-baseline="middle">👤</text>
        </svg>"""
        return Response(content=svg, media_type="image/svg+xml")

    path = Path(row["path"])
    media_type = row["media_type"]
    if not path.is_file():
        svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
            <rect width="100%" height="100%" fill="#4B5563"/>
            <text x="50%" y="55%" font-family="system-ui" font-size="36" fill="#F3F4F6" text-anchor="middle" dominant-baseline="middle">👤</text>
        </svg>"""
        return Response(content=svg, media_type="image/svg+xml")

    import cv2
    try:
        if row["frame"] is not None:
            cap = cv2.VideoCapture(str(path))
            if not cap.isOpened():
                raise Exception("Cannot open video")
            cap.set(cv2.CAP_PROP_POS_FRAMES, row["frame"])
            ok, frame = cap.read()
            cap.release()
            if not ok or frame is None:
                raise Exception("Cannot read frame")
            img = frame
        else:
            img = cv2.imread(str(path))
            if img is None:
                raise Exception("Cannot read image")

        h_img, w_img = img.shape[:2]
        x = row["bbox_x"] if row["bbox_x"] is not None else 0
        y = row["bbox_y"] if row["bbox_y"] is not None else 0
        w = row["bbox_w"] if row["bbox_w"] is not None else w_img
        h = row["bbox_h"] if row["bbox_h"] is not None else h_img

        pad_x = int(w * 0.15)
        pad_y = int(h * 0.15)
        crop_x = max(0, x - pad_x)
        crop_y = max(0, y - pad_y)
        crop_w = min(w_img - crop_x, w + 2 * pad_x)
        crop_h = min(h_img - crop_y, h + 2 * pad_y)

        crop = img[crop_y : crop_y + crop_h, crop_x : crop_x + crop_w]
        if crop.size > 0:
            thumb = cv2.resize(crop, (256, 256), interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(thumb_path), thumb)
            return FileResponse(thumb_path)
    except Exception:
        pass

    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
        <rect width="100%" height="100%" fill="#4B5563"/>
        <text x="50%" y="55%" font-family="system-ui" font-size="36" fill="#F3F4F6" text-anchor="middle" dominant-baseline="middle">👤</text>
    </svg>"""
    return Response(content=svg, media_type="image/svg+xml")


@app.post("/api/person/rename")
def api_post_rename(req: RenameRequest) -> dict[str, str]:
    service = get_service()
    try:
        in_root = Path(req.input_root) if req.input_root else None
        msg = service.rename(req.person, req.new_name, in_root)
        return {"status": "success", "message": msg}
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/person/merge")
def api_post_merge(req: MergeRequest) -> dict[str, str]:
    service = get_service()
    try:
        in_root = Path(req.input_root) if req.input_root else None
        msg = service.merge(req.target, req.source, in_root)
        return {"status": "success", "message": msg}
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/media/reassign")
def api_post_reassign(req: ReassignRequest) -> dict[str, str]:
    service = get_service()
    try:
        in_root = Path(req.input_root) if req.input_root else None
        service.reassign_media(req.media_id, req.person_id, in_root)
        return {"status": "success", "message": "Media reassigned successfully."}
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/person/create")
def api_post_create(req: CreatePersonRequest) -> dict[str, Any]:
    service = get_service()
    try:
        person = service.create_person(req.name)
        return {"status": "success", "person": person.to_dict()}
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/search")
def api_get_search(query: str) -> dict[str, Any]:
    service = get_service()
    return service.search(query)


# --- Frontend Static Assets Serving & SPA Fallback ---

ui_dist = Path(__file__).parent.parent / "ui" / "dist"

# Serve static bundles (JS, CSS)
if ui_dist.is_dir():
    assets_dir = ui_dist / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


@app.get("/{fallback_path:path}")
def spa_fallback(fallback_path: str):
    if fallback_path.startswith("api") or fallback_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")

    index_file = ui_dist / "index.html"
    if index_file.is_file():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))

    # Fallback message if UI is not yet built
    return HTMLResponse(
        content="""
        <html>
        <head><title>FaceSort</title></head>
        <body style="font-family: system-ui, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #111827; color: #F3F4F6;">
            <div style="text-align: center; max-width: 500px; padding: 2rem; border-radius: 0.5rem; background: #1F2937; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                <h1 style="margin: 0 0 1rem 0;">FaceSort Web UI</h1>
                <p style="color: #9CA3AF; line-height: 1.5;">The frontend project has been configured. Build it using <code style="background: #111827; padding: 0.2rem 0.4rem; border-radius: 0.25rem;">npm run build</code> inside the <code style="background: #111827; padding: 0.2rem 0.4rem; border-radius: 0.25rem;">ui/</code> directory to start managing your library via the web.</p>
            </div>
        </body>
        </html>
        """
    )
