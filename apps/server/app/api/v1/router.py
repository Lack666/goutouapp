"""Single place to assemble the versioned API."""

from fastapi import APIRouter

from app.api.v1.agent_runs import router as agent_runs_router
from app.api.v1.chat_imports import router as chat_imports_router
from app.api.v1.erasure import router as erasure_router
from app.api.v1.imported_analysis import router as imported_analysis_router
from app.api.v1.lifecycle_erasure import router as lifecycle_router
from app.api.v1.memory import router as memory_router
from app.api.v1.resources import router as resources_router
from app.api.v1.status import router as status_router

router = APIRouter(prefix="/api/v1")
router.include_router(status_router)
router.include_router(agent_runs_router)
router.include_router(chat_imports_router)
router.include_router(memory_router)
router.include_router(resources_router)
router.include_router(erasure_router)
router.include_router(lifecycle_router)
router.include_router(imported_analysis_router)
