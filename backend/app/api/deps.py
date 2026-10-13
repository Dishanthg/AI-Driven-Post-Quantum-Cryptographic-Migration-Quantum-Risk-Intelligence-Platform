from __future__ import annotations

from app.core.security import ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER, get_current_user, require_role
from app.db.session import get_db

# convenience composite dependencies used across routers
require_viewer = require_role(ROLE_VIEWER, ROLE_ANALYST, ROLE_ADMIN)  # any authenticated user
require_analyst = require_role(ROLE_ANALYST, ROLE_ADMIN)  # can trigger scans/assessments/migrations
require_admin = require_role(ROLE_ADMIN)

__all__ = ["get_current_user", "get_db", "require_admin", "require_analyst", "require_viewer"]
