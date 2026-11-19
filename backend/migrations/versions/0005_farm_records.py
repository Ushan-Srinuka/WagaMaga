"""Farm records, immutable private revisions and separate farm audit persistence."""

from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.config import Settings

revision = "0005_farm_records"
down_revision = "0004_in_app_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:

    op.create_table(
        "crop_types",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("supported", sa.Boolean(), nullable=False),
        sa.CheckConstraint("code ~ '^[a-z][a-z0-9_]*$'", name="crop_types_code"),
        sa.CheckConstraint("display_name ~ '[^[:space:]]'", name="crop_types_name"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "farms",
        sa.Column("farmer_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=False),
        sa.Column("timezone", sa.String(length=100), nullable=False),
        sa.Column("latitude", sa.Numeric(), nullable=True),
        sa.Column("longitude", sa.Numeric(), nullable=True),
        sa.Column("area_value", sa.Numeric(), nullable=True),
        sa.Column("area_unit", sa.String(length=4), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("area_unit IN ('ha','acre','m2')", name="farms_area_unit"),
        sa.CheckConstraint("location ~ '[^[:space:]]'", name="farms_location"),
        sa.CheckConstraint("name ~ '[^[:space:]]'", name="farms_name"),
        sa.CheckConstraint("timezone ~ '[^[:space:]]'", name="farms_timezone"),
        sa.CheckConstraint("(area_value IS NULL) = (area_unit IS NULL)", name="farms_area_pair"),
        sa.CheckConstraint(
            "(latitude IS NULL) = (longitude IS NULL)", name="farms_coordinate_pair"
        ),
        sa.CheckConstraint(
            "area_value > 0 AND area_value < 1000000000000 AND area_value = trunc(area_value, 6)",
            name="farms_area_value",
        ),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="farms_latitude"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name="farms_longitude"),
        sa.CheckConstraint("version > 0", name="farms_version"),
        sa.ForeignKeyConstraint(["farmer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_farms_owner_archive_created",
        "farms",
        ["farmer_id", "archived_at", "created_at", "id"],
        unique=False,
    )
    op.create_table(
        "cultivations",
        sa.Column("farm_id", sa.Uuid(), nullable=False),
        sa.Column("crop_type_id", sa.Uuid(), nullable=False),
        sa.Column("planting_date", sa.Date(), nullable=False),
        sa.Column("area_value", sa.Numeric(), nullable=False),
        sa.Column("area_unit", sa.String(length=4), nullable=False),
        sa.Column("soil_notes", sa.Text(), nullable=True),
        sa.Column("estimated_stage", sa.String(length=80), nullable=True),
        sa.Column("confirmed_stage", sa.String(length=80), nullable=True),
        sa.Column("confirmed_by", sa.Uuid(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(confirmed_stage IS NULL AND confirmed_by IS NULL AND confirmed_at IS "
            "NULL) OR (confirmed_stage IS NOT NULL AND confirmed_by IS NOT NULL AND "
            "confirmed_at IS NOT NULL AND confirmed_stage ~ '[^[:space:]]')",
            name="cultivations_confirmation",
        ),
        sa.CheckConstraint("area_unit IN ('ha','acre','m2')", name="cultivations_area_unit"),
        sa.CheckConstraint(
            "area_value > 0 AND area_value < 1000000000000 AND area_value = trunc(area_value, 6)",
            name="cultivations_area_value",
        ),
        sa.CheckConstraint("char_length(soil_notes) <= 2000", name="cultivations_soil_notes"),
        sa.CheckConstraint("estimated_stage IS NULL", name="cultivations_no_estimator"),
        sa.CheckConstraint("isfinite(planting_date)", name="cultivations_planting_date"),
        sa.CheckConstraint("version > 0", name="cultivations_version"),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["crop_type_id"], ["crop_types.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "farm_id", name="uq_cultivations_id_farm"),
    )
    op.create_index("ix_cultivations_crop", "cultivations", ["crop_type_id"], unique=False)
    op.create_index(
        "ix_cultivations_farm_archive_created",
        "cultivations",
        ["farm_id", "archived_at", "created_at", "id"],
        unique=False,
    )
    op.create_table(
        "farm_revisions",
        sa.Column("farm_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("changed_by", sa.Uuid(), nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "jsonb_typeof(snapshot) = 'object' AND snapshot ?& ARRAY['farmer_id','name',"
            "'location','timezone','latitude','longitude','area_value','area_unit',"
            "'archived_at','id','version','created_at','updated_at'] AND snapshot - "
            "ARRAY['farmer_id','name','location','timezone','latitude','longitude',"
            "'area_value','area_unit','archived_at','id','version','created_at',"
            "'updated_at'] = '{}'::jsonb AND (snapshot->>'id' = farm_id::text) IS TRUE "
            "AND (snapshot->>'version' = version::text) IS TRUE",
            name="farm_revisions_snapshot",
        ),
        sa.CheckConstraint("version > 0", name="farm_revisions_version"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("farm_id", "version", name="uq_farm_revisions_version"),
    )
    op.create_table(
        "cultivation_revisions",
        sa.Column("cultivation_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("changed_by", sa.Uuid(), nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "jsonb_typeof(snapshot) = 'object' AND snapshot ?& ARRAY['farm_id',"
            "'crop_type_id','planting_date','area_value','area_unit','soil_notes',"
            "'estimated_stage','confirmed_stage','confirmed_by','confirmed_at',"
            "'archived_at','id','version','created_at','updated_at'] AND snapshot - "
            "ARRAY['farm_id','crop_type_id','planting_date','area_value','area_unit',"
            "'soil_notes','estimated_stage','confirmed_stage','confirmed_by',"
            "'confirmed_at','archived_at','id','version','created_at','updated_at'] = "
            "'{}'::jsonb AND (snapshot->>'id' = cultivation_id::text) IS TRUE AND "
            "(snapshot->>'version' = version::text) IS TRUE",
            name="cultivation_revisions_snapshot",
        ),
        sa.CheckConstraint("version > 0", name="cultivation_revisions_version"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cultivation_id"], ["cultivations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cultivation_id", "version", name="uq_cultivation_revisions_version"),
    )
    op.create_table(
        "farm_observations",
        sa.Column("cultivation_id", sa.Uuid(), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "notes ~ '[^[:space:]]' AND char_length(notes) <= 4000", name="farm_observations_notes"
        ),
        sa.CheckConstraint("isfinite(observed_at)", name="farm_observations_observed_at"),
        sa.CheckConstraint("version > 0", name="farm_observations_version"),
        sa.ForeignKeyConstraint(["cultivation_id"], ["cultivations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "cultivation_id", name="uq_observations_id_cultivation"),
    )
    op.create_index(
        "ix_observations_cultivation_observed",
        "farm_observations",
        ["cultivation_id", "observed_at", "id"],
        unique=False,
    )
    op.create_table(
        "farm_audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("farm_id", sa.Uuid(), nullable=False),
        sa.Column("cultivation_id", sa.Uuid(), nullable=True),
        sa.Column("observation_id", sa.Uuid(), nullable=True),
        sa.Column("operation", sa.String(length=40), nullable=False),
        sa.Column("entity_version", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(operation IN ('farm_created','farm_updated','farm_archived') AND "
            "cultivation_id IS NULL AND observation_id IS NULL) OR (operation IN "
            "('cultivation_created','cultivation_updated','cultivation_archived',"
            "'stage_confirmed') AND cultivation_id IS NOT NULL AND observation_id IS "
            "NULL) OR (operation IN ('observation_created','observation_updated') AND "
            "cultivation_id IS NOT NULL AND observation_id IS NOT NULL)",
            name="farm_audit_operation_parent",
        ),
        sa.CheckConstraint("outcome = 'succeeded'", name="farm_audit_outcome"),
        sa.CheckConstraint("entity_version > 0", name="farm_audit_version"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["cultivation_id", "farm_id"],
            ["cultivations.id", "cultivations.farm_id"],
            name="fk_farm_audit_cultivation_parent",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["observation_id", "cultivation_id"],
            ["farm_observations.id", "farm_observations.cultivation_id"],
            name="fk_farm_audit_observation_parent",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_farm_audit_farm_created",
        "farm_audit_events",
        ["farm_id", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "uq_farm_audit_cultivation_version",
        "farm_audit_events",
        ["cultivation_id", "entity_version"],
        unique=True,
        postgresql_where=sa.text("cultivation_id IS NOT NULL AND observation_id IS NULL"),
    )
    op.create_index(
        "uq_farm_audit_farm_version",
        "farm_audit_events",
        ["farm_id", "entity_version"],
        unique=True,
        postgresql_where=sa.text("cultivation_id IS NULL"),
    )
    op.create_index(
        "uq_farm_audit_observation_version",
        "farm_audit_events",
        ["observation_id", "entity_version"],
        unique=True,
        postgresql_where=sa.text("observation_id IS NOT NULL"),
    )
    op.create_table(
        "observation_revisions",
        sa.Column("observation_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("changed_by", sa.Uuid(), nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "jsonb_typeof(snapshot) = 'object' AND snapshot ?& ARRAY['cultivation_id',"
            "'recorded_by','observed_at','notes','id','version','created_at',"
            "'updated_at'] AND snapshot - ARRAY['cultivation_id','recorded_by',"
            "'observed_at','notes','id','version','created_at','updated_at'] = "
            "'{}'::jsonb AND (snapshot->>'id' = observation_id::text) IS TRUE AND "
            "(snapshot->>'version' = version::text) IS TRUE",
            name="observation_revisions_snapshot",
        ),
        sa.CheckConstraint("version > 0", name="observation_revisions_version"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["observation_id"], ["farm_observations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("observation_id", "version", name="uq_observation_revisions_version"),
    )

    op.bulk_insert(
        sa.table(
            "crop_types",
            sa.column("id", sa.Uuid()),
            sa.column("code", sa.String()),
            sa.column("display_name", sa.String()),
            sa.column("supported", sa.Boolean()),
        ),
        [
            {
                "id": UUID("1e7402ea-35ab-4673-a8de-834c4bb70401"),
                "code": "chilli",
                "display_name": "Chilli",
                "supported": True,
            }
        ],
    )
    # Row identity/parent/creation-author cannot be reassigned around private history.
    op.execute("""
        CREATE FUNCTION public.farm_record_identity_guard() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE field_name text;
        BEGIN
            FOREACH field_name IN ARRAY TG_ARGV LOOP
                IF (to_jsonb(NEW)->field_name) IS DISTINCT FROM (to_jsonb(OLD)->field_name) THEN
                    RAISE EXCEPTION 'Farm record identity is immutable' USING ERRCODE = '23514';
                END IF;
            END LOOP;
            RETURN NEW;
        END;
        $$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.farm_record_identity_guard() FROM PUBLIC")
    for table, columns in (
        ("farms", "'id','farmer_id','created_at'"),
        ("cultivations", "'id','farm_id','created_at'"),
        ("farm_observations", "'id','cultivation_id','recorded_by','created_at'"),
    ):
        op.execute(
            f"CREATE TRIGGER {table}_identity_guard BEFORE UPDATE ON public.{table} "
            f"FOR EACH ROW EXECUTE FUNCTION public.farm_record_identity_guard({columns})"
        )
    role = op.get_bind().dialect.identifier_preparer.quote(Settings().app_db_user)
    for table in ("farms", "cultivations", "farm_observations"):
        op.execute(f"GRANT SELECT, INSERT, UPDATE ON TABLE public.{table} TO {role}")
    op.execute(f"GRANT SELECT ON TABLE public.crop_types TO {role}")
    for table in (
        "farm_revisions",
        "cultivation_revisions",
        "observation_revisions",
        "farm_audit_events",
    ):
        op.execute(f"GRANT SELECT, INSERT ON TABLE public.{table} TO {role}")


def downgrade() -> None:

    op.drop_table("observation_revisions")
    op.drop_index(
        "uq_farm_audit_observation_version",
        table_name="farm_audit_events",
        postgresql_where=sa.text("observation_id IS NOT NULL"),
    )
    op.drop_index(
        "uq_farm_audit_farm_version",
        table_name="farm_audit_events",
        postgresql_where=sa.text("cultivation_id IS NULL"),
    )
    op.drop_index(
        "uq_farm_audit_cultivation_version",
        table_name="farm_audit_events",
        postgresql_where=sa.text("cultivation_id IS NOT NULL AND observation_id IS NULL"),
    )
    op.drop_index("ix_farm_audit_farm_created", table_name="farm_audit_events")
    op.drop_table("farm_audit_events")
    op.drop_index("ix_observations_cultivation_observed", table_name="farm_observations")
    op.drop_table("farm_observations")
    op.drop_table("cultivation_revisions")
    op.drop_table("farm_revisions")
    op.drop_index("ix_cultivations_farm_archive_created", table_name="cultivations")
    op.drop_index("ix_cultivations_crop", table_name="cultivations")
    op.drop_table("cultivations")
    op.drop_index("ix_farms_owner_archive_created", table_name="farms")
    op.drop_table("farms")
    op.drop_table("crop_types")
    op.execute("DROP FUNCTION public.farm_record_identity_guard()")
