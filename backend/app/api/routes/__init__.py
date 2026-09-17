from fastapi import APIRouter
from app.api.routes.auth import router as auth_router
from app.api.routes.duos import router as duos_router
from app.api.routes.projects import router as projects_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.reviews import router as reviews_router
from app.api.routes.github import router as github_router
from app.api.routes.progress import router as progress_router
from app.api.routes.streaks import router as streaks_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.webhooks import router as webhooks_router
from app.api.routes.project_collaboration import router as project_collab_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(duos_router)
api_router.include_router(projects_router)
api_router.include_router(tasks_router)
api_router.include_router(reviews_router)
api_router.include_router(github_router)
api_router.include_router(progress_router)
api_router.include_router(streaks_router)
api_router.include_router(notifications_router)
api_router.include_router(webhooks_router)
api_router.include_router(project_collab_router)
