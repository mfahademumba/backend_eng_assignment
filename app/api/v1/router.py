from app.api.v1.workspaces import router as workspaces_router
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")
router.include_router(workspaces_router)
