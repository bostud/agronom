"""Application-wide settings and constants.

Standard library only, so every layer (including the domain) can import it.
Values that vary per environment are read from environment variables.
"""

from __future__ import annotations

import os

# Database
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://agronom:agronom@localhost:5432/agronom"
)

# Geodesy
GEOD_ELLIPSOID = "WGS84"
SQ_METERS_PER_HECTARE = 10_000.0

# Field rules
MIN_POLYGON_AREA_HA = 0.1

# Pagination
MAX_LIMIT = 100
DEFAULT_LIMIT = 20
DEFAULT_OFFSET = 0
