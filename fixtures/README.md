# Synthetic fixtures

Future V0 fixtures belong here: synthetic actors/cultivations, reviewed-source metadata and explicitly labelled weather recordings. No real farmer information, credentials or unreviewed agricultural claims should be committed.

FR-B's explicit `farm_records` pytest fixture is in backend/tests/conftest.py: two synthetic owners, fixed synthetic farm/cultivation/observation UUIDs, private versioned snapshots and audit events. It uses only the guarded dedicated `_test` database and creates no development records. Migration `0005_farm_records` seeds only the supported chilli reference row. There is no farm seed CLI or startup seed; sources/weather fixtures remain future V0 work.
