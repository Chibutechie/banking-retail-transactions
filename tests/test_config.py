import pytest

from pipeline import config


def test_validate_env_reports_missing_project_id(monkeypatch) -> None:
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)

    with pytest.raises(EnvironmentError, match="GCP_PROJECT_ID"):
        config.validate_env()


def test_validate_env_requires_dbt_project(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    dbt_dir = tmp_path / "dbt"
    monkeypatch.setattr(config, "DBT_DIR", dbt_dir)

    with pytest.raises(EnvironmentError, match="dbt project not found"):
        config.validate_env()

    dbt_dir.mkdir()
    (dbt_dir / "dbt_project.yml").write_text("name: test", encoding="utf-8")

    config.validate_env()
