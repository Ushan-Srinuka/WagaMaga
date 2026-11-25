#!/bin/sh
# Run inside the local PostgreSQL container after seeding the dedicated test database.
set -eu

: "${TEST_DB_NAME:?Missing test database name}"
: "${APP_DB_NAME:?Missing application database name}"
: "${POSTGRES_USER:?Missing database owner}"
: "${APP_DB_USER:?Missing application role}"

case "$TEST_DB_NAME" in
  *_test) ;;
  *) echo "Expected a disposable _test database" >&2; exit 1 ;;
esac
if [ "$TEST_DB_NAME" = "$APP_DB_NAME" ]; then
  echo "Test and application databases must be different" >&2
  exit 1
fi

archive=$(mktemp)
restored_db="wagamaga_restore_$$_test"
created=false
cleanup() {
  rm -f -- "$archive"
  if [ "$created" = true ]; then
    dropdb --username "$POSTGRES_USER" "$restored_db"
  fi
}
trap cleanup EXIT

verify() {
  psql --username "$POSTGRES_USER" --dbname "$1" --no-psqlrc --quiet --tuples-only \
    --no-align --set ON_ERROR_STOP=1 --set app_role="$APP_DB_USER" <<'SQL'
SELECT version_num, (SELECT extversion FROM pg_extension WHERE extname = 'vector')
FROM alembic_version;

SELECT 'seeded=' || (EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')
   AND (SELECT count(*) FROM farm_tasks) > 0
   AND (SELECT count(*) FROM farm_task_events) > 1
   AND (SELECT count(*) FROM farm_forecasts) > 0
   AND (SELECT count(*) FROM weather_refresh_schedules WHERE enabled) > 0
   AND (SELECT count(*) FROM weather_review_notices) > 0
   AND (SELECT count(*) FROM notifications WHERE event_type = 'weather_review') > 0
   AND EXISTS (
       SELECT 1 FROM task_plan_decisions d
       JOIN task_plans p ON (p.id, p.version, p.action_hash) =
                              (d.plan_id, d.plan_version, d.action_hash)
       JOIN farm_task_events e ON (e.task_id, e.version) = (d.task_id, d.task_version)
       WHERE p.action_type = 'reschedule_task' AND d.outcome = 'accepted'
   ))::text;

SELECT 'protected=' || (has_table_privilege(:'app_role', 'farm_task_events', 'SELECT')
   AND NOT has_table_privilege(:'app_role', 'farm_task_events', 'UPDATE')
   AND NOT has_table_privilege(:'app_role', 'weather_review_notices', 'UPDATE')
   AND NOT has_table_privilege(:'app_role', 'task_plan_decisions', 'DELETE'))::text;

SET ROLE :"app_role";
SELECT 'documents=' || (EXISTS (
    SELECT 1
    FROM knowledge_evaluation_decisions d
    JOIN knowledge_demo_versions v ON v.id = d.version_id
    JOIN knowledge_source_pdfs p ON p.version_id = v.id
    WHERE v.title = 'Synthetic restore reference'
      AND v.status = 'published' AND p.state = 'ready'
      AND v.checksum = encode(sha256(p.original), 'hex')
      AND d.case_id = 'CH-01' AND d.outcome = 'suitable'
      AND d.approved_excerpt <> ''
      AND position(d.approved_excerpt IN (p.pages ->> (d.page_number - 1))) > 0
) AND EXISTS (
    SELECT 1
    FROM knowledge_passages passage
    JOIN knowledge_demo_versions v ON v.id = passage.version_id
    JOIN knowledge_source_pdfs p ON p.version_id = v.id
    WHERE v.title = 'Synthetic restore reviewed PDF'
      AND v.status = 'published' AND p.state = 'ready'
      AND v.checksum = encode(sha256(p.original), 'hex')
      AND passage.page_number = 1
      AND passage.body = (p.pages ->> (passage.page_number - 1))
))::text;
RESET ROLE;

SELECT 'farm:' || md5(coalesce(string_agg(to_jsonb(f)::text, ',' ORDER BY id), '')) FROM farms f
UNION ALL SELECT 'task:' || md5(string_agg(to_jsonb(t)::text, ',' ORDER BY id)) FROM farm_tasks t
UNION ALL SELECT 'event:' || md5(string_agg(to_jsonb(e)::text, ',' ORDER BY task_id, version))
    FROM farm_task_events e
UNION ALL SELECT 'forecast:' || md5(string_agg(to_jsonb(f)::text, ',' ORDER BY farm_id))
    FROM farm_forecasts f
UNION ALL SELECT 'rule:' || md5(string_agg(to_jsonb(r)::text, ',' ORDER BY cultivation_id))
    FROM weather_alert_rules r
UNION ALL SELECT 'alert:' || md5(string_agg(to_jsonb(a)::text, ',' ORDER BY task_id, due_date))
    FROM weather_task_alerts a
UNION ALL SELECT 'schedule:' || md5(string_agg(to_jsonb(s)::text, ',' ORDER BY farm_id))
    FROM weather_refresh_schedules s
UNION ALL SELECT 'weather-review:' || md5(string_agg(to_jsonb(r)::text, ',' ORDER BY cultivation_id, due_date))
    FROM weather_review_notices r
UNION ALL SELECT 'notification:' || md5(string_agg(to_jsonb(n)::text, ',' ORDER BY id))
    FROM notifications n WHERE event_type = 'weather_review'
UNION ALL SELECT 'plan:' || md5(string_agg(to_jsonb(p)::text, ',' ORDER BY id)) FROM task_plans p
UNION ALL SELECT 'decision:' || md5(string_agg(to_jsonb(d)::text, ',' ORDER BY plan_id))
    FROM task_plan_decisions d
UNION ALL SELECT 'source:' || md5(string_agg(to_jsonb(v)::text, ',' ORDER BY id))
    FROM knowledge_demo_versions v
UNION ALL SELECT 'source-decision:' || md5(string_agg(to_jsonb(d)::text, ',' ORDER BY version_id, revision))
    FROM knowledge_demo_decisions d
UNION ALL SELECT 'pdf:' || md5(string_agg(to_jsonb(p)::text, ',' ORDER BY version_id))
    FROM knowledge_source_pdfs p
UNION ALL SELECT 'citation:' || md5(string_agg(to_jsonb(d)::text, ',' ORDER BY case_id, revision))
    FROM knowledge_evaluation_decisions d
UNION ALL SELECT 'passage:' || md5(coalesce(string_agg(to_jsonb(p)::text, ',' ORDER BY id), ''))
    FROM knowledge_passages p
ORDER BY 1;
SQL
}

before=$(verify "$TEST_DB_NAME")
if ! printf '%s\n' "$before" | grep -Fxq 'seeded=true'; then
  echo "Expected pgvector plus synthetic forecast and accepted reschedule evidence" >&2
  exit 1
fi
if ! printf '%s\n' "$before" | grep -Fxq 'protected=true'; then
  echo "Expected restricted application privileges on the backup source" >&2
  exit 1
fi
if ! printf '%s\n' "$before" | grep -Fxq 'documents=true'; then
  echo "Expected an intact original PDF and a resolvable synthetic citation" >&2
  exit 1
fi
pg_dump --username "$POSTGRES_USER" --dbname "$TEST_DB_NAME" --format custom --file "$archive"
createdb --username "$POSTGRES_USER" --template template0 "$restored_db"
created=true
pg_restore --username "$POSTGRES_USER" --dbname "$restored_db" --single-transaction "$archive"
after=$(verify "$restored_db")
if [ "$before" != "$after" ]; then
  echo "Restored evidence or privileges differ from the backup source" >&2
  exit 1
fi
echo "Restore verified for synthetic farms, tasks, forecasts, PDF bytes, extracted text and citations."
exit 0
