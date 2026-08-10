from fastapi import APIRouter

from app.api import (
    account,
    attachments,
    auth,
    backup,
    boms,
    dashboard,
    inventory,
    locations,
    organizers,
    parts,
    projects,
    reservations,
    search,
    shopping_lists,
    suppliers,
    transactions,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(account.router)
api_router.include_router(parts.router)
api_router.include_router(locations.router)
api_router.include_router(inventory.router)
api_router.include_router(transactions.router)
api_router.include_router(search.router)
api_router.include_router(dashboard.router)
api_router.include_router(projects.router)
api_router.include_router(boms.router)
api_router.include_router(reservations.router)
api_router.include_router(shopping_lists.router)
api_router.include_router(suppliers.router)
api_router.include_router(organizers.router)
api_router.include_router(attachments.router)
api_router.include_router(backup.router)
