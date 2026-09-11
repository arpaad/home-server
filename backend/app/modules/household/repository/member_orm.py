"""ORM mapping for household members."""

from uuid import UUID, uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HouseholdMemberORM(Base):
    """A person in the household. Identified, not authenticated."""

    __tablename__ = "household_members"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
