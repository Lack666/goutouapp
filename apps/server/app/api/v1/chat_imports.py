"""Authenticated HTTP adapter for the independent import services."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import get_authenticated_actor, get_db
from app.chat_import import FORMAT_WECHAT_MARKDOWN_V1
from app.chat_import.artifacts import CHUNK_BYTES, ArtifactStoreError, UploadTooLarge
from app.schemas.chat_import import (
    FinalizeRequest,
    ImportJobResponse,
    ImportReceiptResponse,
    RelationshipBindingRequest,
    RelationshipMessagePageResponse,
    SpeakerBindingRequest,
)
from app.services.agent_service import AuthenticatedActor
from app.services.import_jobs import ImportJobService
from app.services.import_merge import page_relationship_messages
from app.services.import_workflow import (
    ImportWorkflowError,
    ImportWorkflowErrorCode,
)


class ImportRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def limited_form(request: Request):
            if request.method != "POST" or request.url.path != "/api/v1/chat-imports":
                return await handler(request)
            try:
                # Cache a stricter parse before FastAPI's automatic form parse.
                await request.form(max_files=1, max_fields=2, max_part_size=1024**2)
                return await handler(request)
            finally:
                await request.close()

        return limited_form


router = APIRouter(tags=["chat-import"], route_class=ImportRoute)


def _workflow(request: Request):
    return request.app.state.import_workflow


@router.post("/chat-imports", response_model=ImportJobResponse, status_code=201)
async def upload_chat_import(
    request: Request,
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    file: Annotated[UploadFile, File()],
    source_timezone: Annotated[str, Form()],
    source_format: Annotated[str | None, Form()] = None,
) -> ImportJobResponse:
    if not source_timezone.strip() or len(source_timezone) > 100:
        raise ImportWorkflowError(ImportWorkflowErrorCode.INVALID_UPLOAD)
    if source_format is not None and source_format != FORMAT_WECHAT_MARKDOWN_V1:
        raise ImportWorkflowError(ImportWorkflowErrorCode.UNSUPPORTED_FORMAT)
    store = request.app.state.import_artifact_store
    try:
        writer = store.begin(request.scope.get("admission_artifact_key"))
    except OSError:
        raise ArtifactStoreError from None
    size = 0
    try:
        while chunk := await file.read(CHUNK_BYTES):
            size += len(chunk)
            if size > request.app.state.settings.max_chat_import_bytes:
                raise UploadTooLarge
            writer.write(chunk)
        artifact = writer.finish()
    except BaseException as exc:
        try:
            writer.abort()
        except OSError:
            from app.services.import_workflow import _cleanup_warning

            _cleanup_warning()
            request.app.state.resource_admission.record("cleanup_failure")
        if isinstance(exc, OSError) and not isinstance(exc, ConnectionError):
            raise ArtifactStoreError from None
        raise
    finally:
        await file.close()
    view = await run_in_threadpool(
        _workflow(request).register_uploaded,
        actor,
        artifact,
        source_timezone=source_timezone,
        source_format=source_format,
    )
    return ImportJobResponse.model_validate(view)


@router.get("/chat-imports/{job_id}", response_model=ImportJobResponse)
def inspect_chat_import(
    job_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    request: Request,
) -> ImportJobResponse:
    return ImportJobResponse.model_validate(_workflow(request).inspect(actor, job_id))


@router.put("/chat-imports/{job_id}/speakers", response_model=ImportJobResponse)
def bind_speaker(
    job_id: UUID,
    body: SpeakerBindingRequest,
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    db: Annotated[Session, Depends(get_db)],
) -> ImportJobResponse:
    view = ImportJobService(db).set_speaker_binding(
        actor,
        job_id,
        body.raw_speaker_label,
        body.binding_kind,
        body.person_id,
        expected_revision=body.expected_revision,
    )
    return ImportJobResponse.model_validate(view)


@router.put("/chat-imports/{job_id}/relationship", response_model=ImportJobResponse)
def bind_relationship(
    job_id: UUID,
    body: RelationshipBindingRequest,
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    db: Annotated[Session, Depends(get_db)],
) -> ImportJobResponse:
    view = ImportJobService(db).set_relationship_binding(
        actor, job_id, body.relationship_id, expected_revision=body.expected_revision
    )
    return ImportJobResponse.model_validate(view)


@router.post("/chat-imports/{job_id}/ready", response_model=ImportJobResponse)
def mark_chat_import_ready(
    job_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    db: Annotated[Session, Depends(get_db)],
) -> ImportJobResponse:
    return ImportJobResponse.model_validate(ImportJobService(db).mark_ready(actor, job_id))


@router.post("/chat-imports/{job_id}/finalize", response_model=ImportReceiptResponse)
def finalize_chat_import(
    job_id: UUID,
    body: FinalizeRequest,
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    request: Request,
) -> ImportReceiptResponse:
    result = _workflow(request).finalize(actor, job_id, body.expected_revision)
    return ImportReceiptResponse.model_validate(result)


@router.post("/chat-imports/{job_id}/cancel", response_model=ImportJobResponse)
def cancel_chat_import(
    job_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    request: Request,
) -> ImportJobResponse:
    return ImportJobResponse.model_validate(_workflow(request).cancel(actor, job_id))


@router.get(
    "/relationships/{relationship_id}/messages", response_model=RelationshipMessagePageResponse
)
def relationship_messages(
    relationship_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
) -> RelationshipMessagePageResponse:
    try:
        page = page_relationship_messages(db, actor, relationship_id, limit=limit, cursor=cursor)
    except ValueError:
        raise ImportWorkflowError(ImportWorkflowErrorCode.INVALID_UPLOAD) from None
    return RelationshipMessagePageResponse.model_validate(page, from_attributes=True)
