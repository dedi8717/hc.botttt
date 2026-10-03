from app.database.database import session_scope
from app.database.repositories import button_repo


def test_new_button_defaults_to_free():
    with session_scope() as session:
        b = button_repo.create(session, "رایگان", "Free")
        assert b.is_free is True


def test_set_price_makes_button_paid():
    with session_scope() as session:
        b = button_repo.create(session, "پولی", "Paid")
        button_id = b.id

    with session_scope() as session:
        button_repo.set_price(session, button_id, 200000)
        b = button_repo.get(session, button_id)
        assert b.price == 200000
        assert b.is_free is False


def test_make_free_again():
    with session_scope() as session:
        b = button_repo.create(session, "تغییر", "Toggle")
        button_id = b.id
        button_repo.set_price(session, button_id, 50000)

    with session_scope() as session:
        button_repo.set_free(session, button_id, True)
        b = button_repo.get(session, button_id)
        assert b.is_free is True
        # price value is preserved even while marked free, in case it's toggled back
        assert b.price == 50000
