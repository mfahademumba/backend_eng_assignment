from fastapi import APIRouter

from app.api.v1.workspace_users import router as workspace_users_router
from app.api.v1.workspaces import router as workspaces_router

router = APIRouter(prefix="/api/v1")
router.include_router(workspaces_router)
router.include_router(workspace_users_router)
