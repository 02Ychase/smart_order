from pathlib import Path


REQUIRED_REQUIREMENTS = {
    "sqlalchemy>=2.0.36",
    "alembic>=1.14.0",
    "passlib[bcrypt]>=1.7.4",
    "python-jose[cryptography]>=3.3.0",
    "pytest>=8.2.0",
    "httpx>=0.27.0",
}


REQUIRED_PYPROJECT = {
    "SQLAlchemy>=2.0.36",
    "alembic>=1.14.0",
    "passlib[bcrypt]>=1.7.4",
    "python-jose[cryptography]>=3.3.0",
    "pytest>=8.2.0",
    "httpx>=0.27.0",
}


def test_requirements_contains_phase1_dependencies() -> None:
    contents = Path("requirements.txt").read_text(encoding="utf-8")

    for requirement in REQUIRED_REQUIREMENTS:
        assert requirement in contents



def test_pyproject_contains_phase1_dependencies() -> None:
    contents = Path("pyproject.toml").read_text(encoding="utf-8")

    for requirement in REQUIRED_PYPROJECT:
        assert requirement in contents
