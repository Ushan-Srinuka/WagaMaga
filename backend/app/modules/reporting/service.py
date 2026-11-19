"""Single-statement count snapshots with live administrator checks and read audit."""

from datetime import timedelta

from sqlalchemy import and_, func, or_, select, true

from app.modules.farms.models import Cultivation, Farm, FarmDeletion
from app.modules.identity.models import User
from app.modules.identity.security import IdentityError
from app.modules.identity.service import active_actor, require_admin, write_audit
from app.modules.reporting import schemas as dto
from app.modules.support.models import SupportTicket


def administrator(db, ids):
    actor = active_actor(db, ids, lock=True)
    require_admin(actor)
    return actor


def farm_filters(owner_id=None):
    filters = [
        User.deleted_at.is_(None),
        User.role == "farmer",
        ~select(FarmDeletion.farm_id).where(FarmDeletion.farm_id == Farm.id).exists(),
    ]
    if owner_id is not None:
        filters.append(Farm.farmer_id == owner_id)
    return filters


def farm_counts(owner_id=None):
    return (
        select(
            func.count().label("farms_total"),
            func.count().filter(Farm.archived_at.is_(None)).label("farms_active"),
            func.count().filter(Farm.archived_at.is_not(None)).label("farms_archived"),
        )
        .select_from(Farm)
        .join(User, User.id == Farm.farmer_id)
        .where(*farm_filters(owner_id))
        .cte("farm_counts")
    )


def cultivation_counts(owner_id=None):
    return (
        select(
            func.count().label("cultivations_total"),
            func.count()
            .filter(and_(Cultivation.archived_at.is_(None), Farm.archived_at.is_(None)))
            .label("cultivations_active"),
            func.count()
            .filter(or_(Cultivation.archived_at.is_not(None), Farm.archived_at.is_not(None)))
            .label("cultivations_archived"),
        )
        .select_from(Cultivation)
        .join(Farm, Farm.id == Cultivation.farm_id)
        .join(User, User.id == Farm.farmer_id)
        .where(*farm_filters(owner_id))
        .cte("cultivation_counts")
    )


def project(row, prefix, cls):
    return cls(**{key: row[f"{prefix}_{key}"] for key in cls.model_fields})


def audit(db, actor_id, target_id, kind, request_id):
    write_audit(
        db,
        actor_id,
        target_id,
        "report_viewed",
        None,
        kind,
        "Administrator viewed count summary",
        request_id,
    )
    db.flush()


def overview(db, ids, request_id):
    actor = administrator(db, ids)
    current = User.deleted_at.is_(None)
    stamp = func.statement_timestamp()
    accounts = select(
        func.count().filter(current).label("accounts_total"),
        func.count().filter(and_(current, User.disabled_at.is_(None))).label("accounts_enabled"),
        func.count()
        .filter(and_(current, User.disabled_at.is_not(None)))
        .label("accounts_disabled"),
        func.count().filter(and_(current, User.role == "farmer")).label("accounts_farmers"),
        func.count().filter(and_(current, User.role == "advisor")).label("accounts_advisors"),
        func.count()
        .filter(and_(current, User.role == "administrator"))
        .label("accounts_administrators"),
        func.count()
        .filter(
            and_(
                current,
                User.role == "farmer",
                User.created_at >= stamp - timedelta(days=30),
                User.created_at <= stamp,
            )
        )
        .label("accounts_new_farmers_30_days"),
        func.count().filter(User.deleted_at.is_not(None)).label("accounts_removed"),
    ).cte("account_counts")
    farms, cultivations = farm_counts(), cultivation_counts()
    support = select(
        func.count().label("support_total"),
        func.count().filter(SupportTicket.status == "open").label("support_open"),
        func.count().filter(SupportTicket.status == "in_progress").label("support_in_progress"),
        func.count().filter(SupportTicket.status == "resolved").label("support_resolved"),
    ).cte("support_counts")
    row = (
        db.execute(
            select(
                stamp.label("generated_at"), *accounts.c, *farms.c, *cultivations.c, *support.c
            ).select_from(
                accounts.join(farms, true()).join(cultivations, true()).join(support, true())
            )
        )
        .mappings()
        .one()
    )
    result = dto.Overview(
        generated_at=row["generated_at"],
        accounts=project(row, "accounts", dto.Accounts),
        farms=project(row, "farms", dto.Records),
        cultivations=project(row, "cultivations", dto.Records),
        support=project(row, "support", dto.Support),
    )
    audit(db, actor.id, actor.id, "overview", request_id)
    return result


def farmer_summary(db, ids, user_id, request_id):
    actor = administrator(db, ids)
    farms, cultivations = farm_counts(user_id), cultivation_counts(user_id)
    row = (
        db.execute(
            select(
                User.id.label("user_id"),
                func.statement_timestamp().label("generated_at"),
                *farms.c,
                *cultivations.c,
            )
            .select_from(User)
            .join(farms, true())
            .join(cultivations, true())
            .where(User.id == user_id, User.role == "farmer", User.deleted_at.is_(None))
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise IdentityError(404, "FARMER_NOT_FOUND", "Farmer account not found.")
    result = dto.FarmerSummary(
        user_id=row["user_id"],
        generated_at=row["generated_at"],
        farms=project(row, "farms", dto.Records),
        cultivations=project(row, "cultivations", dto.Records),
    )
    audit(db, actor.id, user_id, "farmer_summary", request_id)
    return result
