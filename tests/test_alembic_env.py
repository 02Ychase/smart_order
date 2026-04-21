from pathlib import Path
import os
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"


DEFAULT_ALEMBIC_COMMAND = [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"]
APP_DATABASE_URL_COMMAND = [sys.executable, "-c", "from api.db import DATABASE_URL; print(DATABASE_URL)"]


def _run_alembic(dotenv_contents: str, env_overrides: dict[str, str] | None = None) -> str:
    original_env = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else None
    ENV_FILE.write_text(dotenv_contents, encoding="utf-8")

    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    if env_overrides:
        env.update(env_overrides)

    try:
        result = subprocess.run(
            DEFAULT_ALEMBIC_COMMAND,
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        if original_env is None:
            ENV_FILE.unlink(missing_ok=True)
        else:
            ENV_FILE.write_text(original_env, encoding="utf-8")

    combined_output = f"{result.stdout}\n{result.stderr}"
    assert result.returncode == 0, combined_output
    return combined_output



def _read_app_database_url(dotenv_contents: str, env_overrides: dict[str, str] | None = None) -> str:
    original_env = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else None
    ENV_FILE.write_text(dotenv_contents, encoding="utf-8")

    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    if env_overrides:
        env.update(env_overrides)

    try:
        result = subprocess.run(
            APP_DATABASE_URL_COMMAND,
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        if original_env is None:
            ENV_FILE.unlink(missing_ok=True)
        else:
            ENV_FILE.write_text(original_env, encoding="utf-8")

    combined_output = f"{result.stdout}\n{result.stderr}"
    assert result.returncode == 0, combined_output
    return result.stdout.strip()



def test_alembic_uses_database_url_from_dotenv() -> None:
    output = _run_alembic("DATABASE_URL=sqlite:///from-dotenv.db\n")

    assert "Context impl SQLiteImpl" in output
    assert "Context impl MySQLImpl" not in output



def test_alembic_prefers_environment_database_url_over_dotenv() -> None:
    output = _run_alembic(
        "DATABASE_URL=mysql+mysqlconnector://root:password@localhost:3306/smart_order\n",
        {"DATABASE_URL": "sqlite:///from-environment.db"},
    )

    assert "Context impl SQLiteImpl" in output
    assert "Context impl MySQLImpl" not in output



def test_app_db_uses_database_url_from_dotenv() -> None:
    database_url = _read_app_database_url("DATABASE_URL=sqlite:///from-dotenv.db\n")

    assert database_url == "sqlite:///from-dotenv.db"



def test_app_db_prefers_environment_database_url_over_dotenv() -> None:
    database_url = _read_app_database_url(
        "DATABASE_URL=mysql+mysqlconnector://root:password@localhost:3306/smart_order\n",
        {"DATABASE_URL": "sqlite:///from-environment.db"},
    )

    assert database_url == "sqlite:///from-environment.db"
