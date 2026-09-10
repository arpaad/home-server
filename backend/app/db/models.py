"""Aggregates every ORM model so that ``Base.metadata`` is complete.

Alembic imports this module to see the full schema. A model that is not
reachable from here is invisible to autogenerate and will be dropped by the
next revision, so every ORM module belongs in this list.
"""

from app.db.base import Base

__all__ = ["Base"]
