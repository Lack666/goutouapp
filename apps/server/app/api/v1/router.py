"""Single place to assemble the versioned API."""

from fastapi import APIRouter

from app.api.v1.agent_runs import router as agent_runs_router
from app.api.v1.status import router as status_router

router = APIRouter(prefix="/api/v1")
router.include_router(status_router)
router.include_router(agent_runs_router)
