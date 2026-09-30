"""
Nigerian Banking Analytics Pipeline

Flow:
Hugging Face → DuckDB validation → BigQuery raw
→ dbt → BigQuery marts → Looker Studio
"""