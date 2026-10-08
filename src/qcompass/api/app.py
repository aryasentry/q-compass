"""Loopback-only FastAPI application for the local web interface."""

from pathlib import Path
import re
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from qcompass.api.repository import CorruptResource, LocalRepository, ResourceNotFound, TokenConflict
from qcompass.experiments.runner import RunConfig
from qcompass.paths import project_root


IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,199}$")
LOOPBACK_HOST = re.compile(r"^(?:localhost|127\.0\.0\.1|\[::1\])(?::[0-9]{1,5})?$")
ALLOWED_ORIGINS = {"http://localhost:3000", "http://127.0.0.1:3000"}


class WebRunConfig(RunConfig):
    @field_validator("dataset_id")
    @classmethod
    def safe_dataset_id(cls, value):
        if not IDENTIFIER.fullmatch(value):
            raise ValueError("dataset_id has an invalid format")
        return value

    @field_validator("ranker_path")
    @classmethod
    def no_browser_ranker_path(cls, value):
        if value is not None:
            raise ValueError("ranker_path is not accepted from the web API")
        return value


class JobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    config: WebRunConfig
    token: str = Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,199}$")


class DownloadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,199}$")


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _identifier(value: str) -> str:
    if not IDENTIFIER.fullmatch(value):
        raise _error(400, "invalid_identifier", "Identifier has an invalid format")
    return value


def _translate(exc: Exception, corrupt_code: str = "corrupt_resource") -> HTTPException:
    if isinstance(exc, ResourceNotFound):
        return _error(404, "not_found", str(exc))
    if isinstance(exc, TokenConflict):
        return _error(409, "token_conflict", str(exc))
    return _error(409, corrupt_code, str(exc))


def create_app(root: Path | None = None, launch_worker: bool = True) -> FastAPI:
    selected_root = Path(root or project_root()).resolve()
    repository = LocalRepository(selected_root)
    application = FastAPI(title="Q-Compass local API")
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "[::1]", "::1"],
    )

    @application.middleware("http")
    async def protect_mutations(request: Request, call_next):
        if not LOOPBACK_HOST.fullmatch(request.headers.get("host", "").lower()):
            return JSONResponse(
                status_code=400,
                content={"detail": {"code": "invalid_host", "message": "Loopback host required"}},
            )
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            if request.headers.get("X-QCompass-Client") != "local-ui":
                return JSONResponse(
                    status_code=403,
                    content={"detail": {"code": "invalid_client", "message": "Local UI header required"}},
                )
            origin = request.headers.get("Origin")
            if origin is not None and origin not in ALLOWED_ORIGINS:
                return JSONResponse(
                    status_code=403,
                    content={"detail": {"code": "invalid_origin", "message": "Browser origin is not allowed"}},
                )
            if request.url.path in {"/api/jobs", "/api/downloads"}:
                media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if media_type != "application/json":
                    return JSONResponse(
                        status_code=415,
                        content={
                            "detail": {"code": "unsupported_media_type", "message": "JSON body required"}
                        },
                    )
        return await call_next(request)

    @application.get("/api/health")
    def health():
        return {"status": "ok", "mode": "simulation", "worker_threads": 4}

    @application.get("/api/datasets")
    def datasets():
        records, warnings = repository.list_datasets()
        return {"datasets": records, "warnings": warnings}

    @application.get("/api/datasets/{dataset_id}")
    def dataset(dataset_id: str):
        try:
            return repository.dataset(_identifier(dataset_id))
        except (ResourceNotFound, CorruptResource) as exc:
            raise _translate(exc, "corrupt_dataset") from exc

    @application.post("/api/datasets/{dataset_id}/verify")
    def verify_dataset(dataset_id: str):
        try:
            return repository.verify_dataset(_identifier(dataset_id))
        except (ResourceNotFound, CorruptResource) as exc:
            raise _translate(exc, "corrupt_dataset") from exc

    @application.get("/api/runs")
    def runs(limit: int = Query(default=50, ge=1, le=200)):
        records, warnings = repository.list_runs(limit)
        return {"runs": records, "warnings": warnings}

    @application.get("/api/runs/{run_id}")
    def run(run_id: str):
        try:
            return repository.run(_identifier(run_id))
        except (ResourceNotFound, CorruptResource) as exc:
            raise _translate(exc, "corrupt_run") from exc

    @application.get("/api/runs/{run_id}/export")
    def export_run(run_id: str, format: Literal["json", "csv"] = "json"):
        try:
            body, media_type, filename = repository.export_run(_identifier(run_id), format)
            return Response(
                content=body,
                media_type=media_type,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        except (ResourceNotFound, CorruptResource) as exc:
            raise _translate(exc, "corrupt_run") from exc

    @application.get("/api/jobs")
    def jobs():
        try:
            return {"jobs": repository.list_jobs()}
        except CorruptResource as exc:
            raise _translate(exc, "corrupt_job_store") from exc

    @application.get("/api/jobs/{job_id}")
    def job(job_id: str):
        try:
            record, events = repository.job(_identifier(job_id))
            return {"job": record, "events": events}
        except (ResourceNotFound, CorruptResource) as exc:
            raise _translate(exc) from exc

    @application.post("/api/jobs", status_code=202)
    def submit_job(body: JobRequest):
        try:
            job_id, created = repository.submit_experiment(body.config.model_dump(), body.token)
        except (ResourceNotFound, CorruptResource, TokenConflict) as exc:
            raise _translate(exc, "corrupt_dataset") from exc
        if launch_worker and created:
            from qcompass.experiments.worker import start_worker

            start_worker(selected_root)
        return {"job_id": job_id}

    @application.post("/api/jobs/{job_id}/cancel")
    def cancel_job(job_id: str):
        try:
            return repository.cancel_job(_identifier(job_id))
        except ResourceNotFound as exc:
            raise _translate(exc) from exc

    @application.post("/api/downloads", status_code=202)
    def submit_download(body: DownloadRequest):
        try:
            job_id, created = repository.submit_download(body.token)
        except TokenConflict as exc:
            raise _translate(exc) from exc
        if launch_worker and created:
            from qcompass.experiments.worker import start_worker

            start_worker(selected_root)
        return {"job_id": job_id}

    return application


app = create_app()
