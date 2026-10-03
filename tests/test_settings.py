from app.database.database import session_scope
from app.database.repositories import settings_repo


def test_setting_defaults_to_none():
    with session_scope() as session:
        assert settings_repo.get(session, "does_not_exist") is None


def test_set_and_get_setting():
    with session_scope() as session:
        settings_repo.set(session, "stars_recipient", "@example_user")

    with session_scope() as session:
        assert settings_repo.get(session, "stars_recipient") == "@example_user"


def test_overwrite_setting():
    with session_scope() as session:
        settings_repo.set(session, "stars_recipient", "@first")
        settings_repo.set(session, "stars_recipient", "@second")

    with session_scope() as session:
        assert settings_repo.get(session, "stars_recipient") == "@second"
