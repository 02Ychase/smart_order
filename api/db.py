import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_URL = "mysql+mysqlconnector://root:password@localhost:3306/smart_order"


def _resolve_repo_root_from_worktree(project_root: Path) -> Path | None:
    git_pointer = project_root / ".git"
    if not git_pointer.is_file():
        return None

    first_line = git_pointer.read_text(encoding="utf-8").splitlines()[0].strip()
    if not first_line.startswith("gitdir:"):
        return None

    gitdir = Path(first_line.split(":", 1)[1].strip())
    if not gitdir.is_absolute():
        gitdir = (project_root / gitdir).resolve()

    if len(gitdir.parents) < 3 or gitdir.parent.name != "worktrees":
        return None

    return gitdir.parents[2]


def _resolve_dotenv_paths(project_root: Path) -> list[Path]:
    dotenv_paths = [project_root / ".env"]
    repo_root = _resolve_repo_root_from_worktree(project_root)
    if repo_root is not None:
        dotenv_paths.append(repo_root / ".env")
    return dotenv_paths


def resolve_database_url(project_root: Path | None = None) -> str:
    root = (project_root or PROJECT_ROOT).resolve()
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    for dotenv_path in _resolve_dotenv_paths(root):
        if not dotenv_path.exists():
            continue
        database_url = dotenv_values(dotenv_path).get("DATABASE_URL")
        if database_url:
            return str(database_url)

    return DEFAULT_DATABASE_URL


for dotenv_path in _resolve_dotenv_paths(PROJECT_ROOT):
    if dotenv_path.exists():
        load_dotenv(dotenv_path, override=False)

DATABASE_URL = resolve_database_url(PROJECT_ROOT)


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)



def get_db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
