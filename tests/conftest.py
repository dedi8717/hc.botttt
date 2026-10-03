from __future__ import annotations

import os
import tempfile

import pytest

# Configure environment BEFORE importing any app module.
_tmp_dir = tempfile.mkdtemp()
_db_path = os.path.join(_tmp_dir, "test_bot.db")
os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("OWNER_ID", "111111")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from app.database.database import init_db  # noqa: E402
from app.database.repositories import admin_repo  # noqa: E402
from app.database.database import session_scope  # noqa: E402
from app.config import config  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    init_db()
    with session_scope() as session:
        admin_repo.ensure_owner(session, config.OWNER_ID)
    yield


@pytest.fixture
def owner_id() -> int:
    return config.OWNER_ID
