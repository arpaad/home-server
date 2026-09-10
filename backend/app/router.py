"""Registers every module's routes on one router."""

from fastapi import APIRouter

from app.modules.household.api.routes import router as household_router
from app.modules.shopping.api.routes import router as shopping_router

api_router = APIRouter()
api_router.include_router(shopping_router)
api_router.include_router(household_router)
