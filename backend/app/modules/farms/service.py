"""Owner-scoped Farm Records rules. Caller owns the transaction, including commit."""

from datetime import UTC, datetime, time
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.modules.farms import schemas as dto
from app.modules.farms.history import record_snapshot
from app.modules.farms.models import (
    CropType,
    Cultivation,
    CultivationRevision,
    Farm,
    FarmAuditEvent,
    FarmDeletion,
    FarmObservation,
    FarmRevision,
    ObservationRevision,
)
from app.modules.identity.security import IdentityError, now
from app.modules.identity.service import active_actor


def farmer(db: Session, ids: tuple[UUID, UUID], *, write: bool = False):
    actor = active_actor(db, ids, lock=write)
    if actor.role != "farmer":
        raise IdentityError(403, "ACCESS_DENIED", "Farmer access is required.")
    return actor


def missing():
    return IdentityError(404, "RECORD_NOT_FOUND", "Record not found.")


def farm_for(db, actor_id, farm_id, *, lock=False):
    statement = select(Farm).where(Farm.id == farm_id, Farm.farmer_id == actor_id, visible_farm())
    if lock:
        statement = statement.with_for_update()
    record = db.scalar(statement.execution_options(populate_existing=True))
    if record is None:
        raise missing()
    return record


def visible_farm():
    return ~select(FarmDeletion.farm_id).where(FarmDeletion.farm_id == Farm.id).exists()


def cultivation_for(db, actor_id, cultivation_id, *, farm_id=None, lock=False):
    if farm_id is None:
        farm_id = db.scalar(
            select(Farm.id)
            .join(Cultivation)
            .where(Cultivation.id == cultivation_id, Farm.farmer_id == actor_id)
        )
        if farm_id is None:
            raise missing()
    farm = farm_for(db, actor_id, farm_id, lock=lock)
    statement = select(Cultivation).where(
        Cultivation.id == cultivation_id, Cultivation.farm_id == farm.id
    )
    if lock:
        statement = statement.with_for_update()
    record = db.scalar(statement.execution_options(populate_existing=True))
    if record is None:
        raise missing()
    return farm, record


def observation_for(db, actor_id, cultivation_id, observation_id, *, lock=False):
    farm, cultivation = cultivation_for(db, actor_id, cultivation_id, lock=lock)
    statement = select(FarmObservation).where(
        FarmObservation.id == observation_id, FarmObservation.cultivation_id == cultivation.id
    )
    if lock:
        statement = statement.with_for_update()
    record = db.scalar(statement.execution_options(populate_existing=True))
    if record is None:
        raise missing()
    return farm, cultivation, record


def check_version(record, expected):
    if record.version != expected:
        raise IdentityError(
            409, "RECORD_VERSION_CONFLICT", "The record changed. Reload and review."
        )


def active(farm, cultivation=None):
    if (
        farm.archived_at is not None
        or cultivation is not None
        and cultivation.archived_at is not None
    ):
        raise IdentityError(409, "RECORD_ARCHIVED", "Archived records cannot receive changes.")


def validate_timezone(db, timezone):
    valid = db.scalar(
        text(
            "SELECT EXISTS (SELECT 1 FROM pg_timezone_names WHERE name=:zone "
            "AND name NOT LIKE 'posix/%' AND name NOT LIKE 'right/%')"
        ),
        {"zone": timezone},
    )
    if not valid:
        raise IdentityError(422, "INVALID_TIMEZONE", "Choose a valid IANA timezone.")


def supported_crop(db, crop_id):
    # Catalogue writes belong to controlled migrations; the app role is SELECT-only.
    crop = db.scalar(select(CropType).where(CropType.id == crop_id, CropType.supported.is_(True)))
    if crop is None:
        raise IdentityError(422, "UNSUPPORTED_CROP", "Choose a supported crop.")


def observed_time(value):
    if value > now():
        raise IdentityError(422, "FUTURE_OBSERVATION", "Observation time cannot be in the future.")


def local_today(db, farm, *, at=None):
    return db.scalar(
        text("SELECT CAST(timezone(:zone, :stamp) AS date)"),
        {"zone": farm.timezone, "stamp": at if at is not None else now()},
    )


def farm_view(record):
    return dto.FarmOut.model_validate(record).model_copy(
        update={"effective_archived": record.archived_at is not None}
    )


def cultivation_view(farm, record, today):
    return dto.CultivationOut.model_validate(record).model_copy(
        update={
            "effective_archived": farm.archived_at is not None or record.archived_at is not None,
            "planned": record.planting_date > today,
        }
    )


def observation_view(farm, cultivation, record):
    return dto.ObservationOut.model_validate(record).model_copy(
        update={
            "effective_archived": farm.archived_at is not None
            or cultivation.archived_at is not None
        }
    )


def paged(db, statement, query, project):
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    records = db.scalars(
        statement.offset((query.page - 1) * query.page_size).limit(query.page_size)
    )
    return {
        "items": [project(row) for row in records],
        "total": total,
        "page": query.page,
        "page_size": query.page_size,
    }


def retain(db, record, actor_id, operation, request_id, *, farm_id=None, cultivation_id=None):
    db.flush()
    if isinstance(record, Farm):
        revision, parent = FarmRevision, "farm_id"
        farm_id = record.id
    elif isinstance(record, Cultivation):
        revision, parent = CultivationRevision, "cultivation_id"
        farm_id, cultivation_id = record.farm_id, record.id
    else:
        revision, parent = ObservationRevision, "observation_id"
        cultivation_id = record.cultivation_id
    stamp = now()
    db.add(
        revision(
            **{parent: record.id},
            version=record.version,
            snapshot=record_snapshot(record),
            changed_by=actor_id,
            changed_at=stamp,
        )
    )
    db.add(
        FarmAuditEvent(
            actor_id=actor_id,
            farm_id=farm_id,
            cultivation_id=cultivation_id,
            observation_id=record.id if isinstance(record, FarmObservation) else None,
            operation=operation,
            entity_version=record.version,
            request_id=request_id,
            created_at=stamp,
        )
    )
    db.flush()


def merged(record, data, schema):
    values = {name: getattr(record, name) for name in schema.model_fields}
    values.update(data.model_dump(exclude_unset=True, exclude={"expected_version"}))
    try:
        return schema.model_validate(values).model_dump()
    except ValidationError:
        raise IdentityError(
            422, "INVALID_RECORD", "Check the record fields and paired values."
        ) from None


def assign(record, values):
    changed = any(getattr(record, key) != value for key, value in values.items())
    if changed:
        for key, value in values.items():
            setattr(record, key, value)
        record.version += 1
        record.updated_at = now()
    return changed


def list_crops(db, ids, query):
    farmer(db, ids)
    return paged(
        db,
        select(CropType).where(CropType.supported.is_(True)).order_by(CropType.code, CropType.id),
        query,
        dto.CropOut.model_validate,
    )


def list_farms(db, ids, query):
    actor = farmer(db, ids)
    statement = select(Farm).where(Farm.farmer_id == actor.id, visible_farm())
    if query.status != "all":
        statement = statement.where(
            Farm.archived_at.is_(None)
            if query.status == "active"
            else Farm.archived_at.is_not(None)
        )
    if query.q.strip():
        statement = statement.where(Farm.name.icontains(query.q.strip(), autoescape=True))
    return paged(db, statement.order_by(Farm.created_at.desc(), Farm.id), query, farm_view)


def get_farm(db, ids, farm_id):
    actor = farmer(db, ids)
    return farm_view(farm_for(db, actor.id, farm_id))


def create_farm(db, ids, data, request_id):
    actor = farmer(db, ids, write=True)
    validate_timezone(db, data.timezone)
    stamp = now()
    record = Farm(farmer_id=actor.id, **data.model_dump(), created_at=stamp, updated_at=stamp)
    db.add(record)
    retain(db, record, actor.id, "farm_created", request_id)
    return farm_view(record)


def update_farm(db, ids, farm_id, data, request_id):
    actor = farmer(db, ids, write=True)
    record = farm_for(db, actor.id, farm_id, lock=True)
    check_version(record, data.expected_version)
    active(record)
    values = merged(record, data, dto.FarmCreate)
    validate_timezone(db, values["timezone"])
    if assign(record, values):
        retain(db, record, actor.id, "farm_updated", request_id)
    return farm_view(record)


def archive_farm(db, ids, farm_id, data, request_id):
    actor = farmer(db, ids, write=True)
    record = farm_for(db, actor.id, farm_id, lock=True)
    check_version(record, data.expected_version)
    if record.archived_at is None:
        assign(record, {"archived_at": now()})
        retain(db, record, actor.id, "farm_archived", request_id)
    return farm_view(record)


def restore_farm(db, ids, farm_id, data, request_id):
    actor = farmer(db, ids, write=True)
    record = farm_for(db, actor.id, farm_id, lock=True)
    check_version(record, data.expected_version)
    if record.archived_at is not None:
        assign(record, {"archived_at": None})
        retain(db, record, actor.id, "farm_restored", request_id)
    return farm_view(record)


def delete_farm(db, ids, farm_id, data, request_id):
    actor = farmer(db, ids, write=True)
    record = farm_for(db, actor.id, farm_id, lock=True)
    check_version(record, data.expected_version)
    if record.archived_at is None:
        raise IdentityError(409, "ARCHIVE_REQUIRED", "Archive the farm before deleting it.")
    if data.confirmation_name != record.name:
        raise IdentityError(422, "CONFIRMATION_MISMATCH", "Enter the current farm name to confirm.")
    record.version += 1
    record.updated_at = now()
    retain(db, record, actor.id, "farm_deleted", request_id)
    db.add(
        FarmDeletion(
            farm_id=record.id,
            deleted_by=actor.id,
            deleted_at=now(),
            entity_version=record.version,
        )
    )
    db.flush()
    return dto.FarmDeleted(id=record.id)


def list_cultivations(db, ids, farm_id, query):
    actor = farmer(db, ids)
    farm = farm_for(db, actor.id, farm_id)
    statement = select(Cultivation).where(Cultivation.farm_id == farm.id)
    if query.status == "active":
        statement = statement.where(Cultivation.archived_at.is_(None), farm.archived_at is None)
    elif query.status == "archived":
        statement = statement.where(
            or_(Cultivation.archived_at.is_not(None), farm.archived_at is not None)
        )
    if query.crop_type_id is not None:
        statement = statement.where(Cultivation.crop_type_id == query.crop_type_id)
    today = local_today(db, farm)
    return paged(
        db,
        statement.order_by(Cultivation.created_at.desc(), Cultivation.id),
        query,
        lambda row: cultivation_view(farm, row, today),
    )


def get_cultivation(db, ids, farm_id, cultivation_id):
    actor = farmer(db, ids)
    farm, record = cultivation_for(db, actor.id, cultivation_id, farm_id=farm_id)
    return cultivation_view(farm, record, local_today(db, farm))


def create_cultivation(db, ids, farm_id, data, request_id):
    actor = farmer(db, ids, write=True)
    farm = farm_for(db, actor.id, farm_id, lock=True)
    active(farm)
    supported_crop(db, data.crop_type_id)
    stamp = now()
    record = Cultivation(farm_id=farm.id, **data.model_dump(), created_at=stamp, updated_at=stamp)
    db.add(record)
    retain(db, record, actor.id, "cultivation_created", request_id)
    return cultivation_view(farm, record, local_today(db, farm))


def update_cultivation(db, ids, farm_id, cultivation_id, data, request_id):
    actor = farmer(db, ids, write=True)
    farm, record = cultivation_for(db, actor.id, cultivation_id, farm_id=farm_id, lock=True)
    check_version(record, data.expected_version)
    active(farm, record)
    values = merged(record, data, dto.CultivationCreate)
    changed_crop = values["crop_type_id"] != record.crop_type_id
    if changed_crop or "crop_type_id" in data.model_fields_set:
        supported_crop(db, values["crop_type_id"])
    if changed_crop or values["planting_date"] != record.planting_date:
        values.update(
            confirmed_stage=None, confirmed_by=None, confirmed_at=None, estimated_stage=None
        )
    if assign(record, values):
        retain(db, record, actor.id, "cultivation_updated", request_id)
    return cultivation_view(farm, record, local_today(db, farm))


def archive_cultivation(db, ids, farm_id, cultivation_id, data, request_id):
    actor = farmer(db, ids, write=True)
    farm, record = cultivation_for(db, actor.id, cultivation_id, farm_id=farm_id, lock=True)
    check_version(record, data.expected_version)
    if record.archived_at is None:
        active(farm, record)
        assign(record, {"archived_at": now()})
        retain(db, record, actor.id, "cultivation_archived", request_id)
    return cultivation_view(farm, record, local_today(db, farm))


def confirm_stage(db, ids, farm_id, cultivation_id, data, request_id):
    actor = farmer(db, ids, write=True)
    farm, record = cultivation_for(db, actor.id, cultivation_id, farm_id=farm_id, lock=True)
    check_version(record, data.expected_version)
    active(farm, record)
    # Each explicit confirmation is a new event, even with an unchanged reported label/clock.
    record.confirmed_stage, record.confirmed_by, record.confirmed_at = data.stage, actor.id, now()
    record.version += 1
    record.updated_at = now()
    retain(db, record, actor.id, "stage_confirmed", request_id)
    return cultivation_view(farm, record, local_today(db, farm))


def list_observations(db, ids, cultivation_id, query):
    actor = farmer(db, ids)
    farm, cultivation = cultivation_for(db, actor.id, cultivation_id)
    statement = select(FarmObservation).where(FarmObservation.cultivation_id == cultivation.id)
    if query.from_date:
        statement = statement.where(
            FarmObservation.observed_at >= datetime.combine(query.from_date, time.min, UTC)
        )
    if query.to_date:
        statement = statement.where(
            FarmObservation.observed_at <= datetime.combine(query.to_date, time.max, UTC)
        )
    return paged(
        db,
        statement.order_by(FarmObservation.observed_at.desc(), FarmObservation.id),
        query,
        lambda row: observation_view(farm, cultivation, row),
    )


def get_observation(db, ids, cultivation_id, observation_id):
    actor = farmer(db, ids)
    farm, cultivation, record = observation_for(db, actor.id, cultivation_id, observation_id)
    return observation_view(farm, cultivation, record)


def create_observation(db, ids, cultivation_id, data, request_id):
    actor = farmer(db, ids, write=True)
    farm, cultivation = cultivation_for(db, actor.id, cultivation_id, lock=True)
    active(farm, cultivation)
    observed_time(data.observed_at)
    stamp = now()
    record = FarmObservation(
        cultivation_id=cultivation.id,
        recorded_by=actor.id,
        **data.model_dump(),
        created_at=stamp,
        updated_at=stamp,
    )
    db.add(record)
    retain(db, record, actor.id, "observation_created", request_id, farm_id=farm.id)
    return observation_view(farm, cultivation, record)


def update_observation(db, ids, cultivation_id, observation_id, data, request_id):
    actor = farmer(db, ids, write=True)
    farm, cultivation, record = observation_for(
        db, actor.id, cultivation_id, observation_id, lock=True
    )
    check_version(record, data.expected_version)
    active(farm, cultivation)
    values = merged(record, data, dto.ObservationCreate)
    observed_time(values["observed_at"])
    if assign(record, values):
        retain(db, record, actor.id, "observation_updated", request_id, farm_id=farm.id)
    return observation_view(farm, cultivation, record)


def history(db, ids, kind, query, *, farm_id=None, cultivation_id=None, observation_id=None):
    actor = farmer(db, ids)
    if kind == "farm":
        record = farm_for(db, actor.id, farm_id)
        revision, parent, snapshot = FarmRevision, FarmRevision.farm_id, dto.FarmSnapshot
    elif kind == "cultivation":
        _, record = cultivation_for(db, actor.id, cultivation_id, farm_id=farm_id)
        revision, parent, snapshot = (
            CultivationRevision,
            CultivationRevision.cultivation_id,
            dto.CultivationSnapshot,
        )
    elif kind == "observation":
        _, _, record = observation_for(db, actor.id, cultivation_id, observation_id)
        revision, parent, snapshot = (
            ObservationRevision,
            ObservationRevision.observation_id,
            dto.ObservationSnapshot,
        )
    else:
        raise ValueError("Unknown history kind")
    return paged(
        db,
        select(revision).where(parent == record.id).order_by(revision.version.desc()),
        query,
        lambda row: {
            "id": row.id,
            "version": row.version,
            "changed_by": row.changed_by,
            "changed_at": row.changed_at,
            "snapshot": snapshot.model_validate(row.snapshot),
        },
    )
