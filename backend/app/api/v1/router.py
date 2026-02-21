from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])

# Routers added as each feature TPRD is implemented:
# from app.api.v1 import auth, products, services, components, resources
# from app.api.v1 import repositories, teams, people, incidents, scorecards
# from app.api.v1 import audit_logs, import_export
# api_router.include_router(auth.router,         prefix="/auth",         tags=["auth"])
# api_router.include_router(products.router,     prefix="/products",     tags=["products"])
# api_router.include_router(services.router,     prefix="/services",     tags=["services"])
# api_router.include_router(components.router,   prefix="/components",   tags=["components"])
# api_router.include_router(resources.router,    prefix="/resources",    tags=["resources"])
# api_router.include_router(repositories.router, prefix="/repositories", tags=["repositories"])
# api_router.include_router(teams.router,        prefix="/teams",        tags=["teams"])
# api_router.include_router(people.router,       prefix="/people",       tags=["people"])
# api_router.include_router(incidents.router,    prefix="/incidents",    tags=["incidents"])
# api_router.include_router(scorecards.router,   prefix="/scorecards",   tags=["scorecards"])
# api_router.include_router(audit_logs.router,   prefix="/audit-logs",   tags=["audit"])
# api_router.include_router(import_export.router,                        tags=["import-export"])
