"""Allowlisted serialization for immutable private record snapshots; no commit boundary."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from app.modules.farms.models import Cultivation, Farm, FarmObservation


def record_snapshot(record: Farm | Cultivation | FarmObservation) -> dict:
    """Call after flush/refresh so server timestamps and version are populated."""
    if type(record) not in (Farm, Cultivation, FarmObservation):
        raise TypeError("Only farm records can be snapshotted")
    result = {}
    for column in record.__table__.columns:
        value = getattr(record, column.name)
        if isinstance(value, (UUID, Decimal)):
            value = str(value)
        elif isinstance(value, (date, datetime)):
            value = value.isoformat()
        result[column.name] = value
    if result["id"] is None or result["version"] is None or result["created_at"] is None:
        raise ValueError("Flush farm records before creating history")
    return result
