class FieldDomainError(Exception):
    """Base class for all domain errors raised by the field bounded context."""


class InvalidCoordinateError(FieldDomainError):
    """Raised when a latitude/longitude pair is missing or out of range."""


class PolygonNotClosedError(FieldDomainError):
    """Raised when a geometry's first and last vertices do not coincide."""


class SelfIntersectingPolygonError(FieldDomainError):
    """Raised when a geometry's edges self-intersect."""


class PolygonTooSmallError(FieldDomainError):
    """Raised when a geometry's enclosed area is below the minimum (0.1 ha)."""


class MissingFieldAttributeError(FieldDomainError):
    """Raised when a required Field attribute (name, owner, crop, geometry) is absent."""


class InvalidAreaRangeError(FieldDomainError):
    """Raised when a filter's minimum area exceeds its maximum area."""


class InvalidPageRequestError(FieldDomainError):
    """Raised when a pagination limit or offset is out of the allowed bounds."""


class FieldNotFoundError(FieldDomainError):
    """Raised when no field exists with the specified identifier."""
