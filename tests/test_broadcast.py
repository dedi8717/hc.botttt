from app.database.database import session_scope
from app.database.repositories import user_repo


def test_get_all_telegram_ids_includes_registered_users():
    with session_scope() as session:
        user_repo.get_or_create(session, 800001, "bcast1", "Bcast One")
        user_repo.get_or_create(session, 800002, "bcast2", "Bcast Two")

    with session_scope() as session:
        ids = user_repo.get_all_telegram_ids(session)
        assert 800001 in ids
        assert 800002 in ids


def test_get_all_telegram_ids_excludes_blocked_by_default():
    with session_scope() as session:
        user_repo.get_or_create(session, 800003, "bcast3", "Bcast Three")
        user_repo.set_blocked(session, 800003, True)

    with session_scope() as session:
        ids = user_repo.get_all_telegram_ids(session, exclude_blocked=True)
        assert 800003 not in ids

        ids_including_blocked = user_repo.get_all_telegram_ids(session, exclude_blocked=False)
        assert 800003 in ids_including_blocked
