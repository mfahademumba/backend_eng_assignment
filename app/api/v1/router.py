from fastapi import APIRouter

from app.api.v1.access_check import router as access_check_router
from app.api.v1.auth import router as auth_router
from app.api.v1.resource_policies import router as resource_policies_router
from app.api.v1.resources import router as resources_router
from app.api.v1.workspace_users import router as workspace_users_router
from app.api.v1.workspaces import router as workspaces_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(workspaces_router)
router.include_router(workspace_users_router)
router.include_router(resources_router)
router.include_router(resource_policies_router)
router.include_router(access_check_router)
