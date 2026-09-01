# Superset

This directory stores Superset dashboard and dataset exports once they exist.

Superset will run as a separate Docker service when dashboard development begins. Its metadata database and the DuckDB driver need their own deliberate setup, so it is not included in the minimal MinIO compose file yet. The data pipeline does not depend on Superset being available.
