from fastapi import APIRouter

from app.api import routes_auth, routes_tasks, routes_workspaces

api_router = APIRouter()
api_router.include_router(routes_auth.router)
api_router.include_router(routes_workspaces.router)
api_router.include_router(routes_tasks.router)
