from app.database.database import session_scope
from app.database.repositories import button_repo, payment_method_repo


def _make_button(name="محصول"):
    with session_scope() as session:
        button = button_repo.create(session, name, name)
        button_repo.set_price(session, button.id, 100)
        return button.id


def test_builtin_stars_seeded_and_not_deletable():
    with session_scope() as session:
        stars = payment_method_repo.ensure_builtin_stars(session)
        assert stars.is_builtin_stars is True
        stars_id = stars.id

    with session_scope() as session:
        # calling again must not create a duplicate
        stars2 = payment_method_repo.ensure_builtin_stars(session)
        assert stars2.id == stars_id

    with session_scope() as session:
        assert payment_method_repo.delete(session, stars_id) is False
        assert payment_method_repo.get(session, stars_id) is not None


def test_create_custom_method_and_edit_instructions():
    with session_scope() as session:
        method = payment_method_repo.create(session, "کارت به کارت", "Card Transfer")
        method_id = method.id

    with session_scope() as session:
        payment_method_repo.update_instructions(session, method_id, "6037-xxxx", "6037-xxxx")
        method = payment_method_repo.get(session, method_id)
        assert method.instructions_fa == "6037-xxxx"


def test_delete_custom_method():
    with session_scope() as session:
        method = payment_method_repo.create(session, "حذف من", "Delete Me")
        method_id = method.id

    with session_scope() as session:
        assert payment_method_repo.delete(session, method_id) is True
        assert payment_method_repo.get(session, method_id) is None


def test_button_with_no_assignment_gets_all_enabled_methods_by_default():
    button_id = _make_button("بدون انتخاب")
    with session_scope() as session:
        payment_method_repo.ensure_builtin_stars(session)
        payment_method_repo.create(session, "روش ۱", "Method 1")

    with session_scope() as session:
        methods = payment_method_repo.methods_for_button(session, button_id)
        assert len(methods) >= 2  # at least stars + the custom one


def test_explicit_button_assignment_restricts_methods():
    button_id = _make_button("انتخاب‌شده")
    with session_scope() as session:
        stars = payment_method_repo.ensure_builtin_stars(session)
        payment_method_repo.create(session, "روش ۲", "Method 2")
        # explicitly assign ONLY stars to this button
        payment_method_repo.toggle_button_method(session, button_id, stars.id)

    with session_scope() as session:
        methods = payment_method_repo.methods_for_button(session, button_id)
        assert len(methods) == 1
        assert methods[0].is_builtin_stars is True


def test_toggle_button_method_add_and_remove():
    button_id = _make_button("تاگل")
    with session_scope() as session:
        method = payment_method_repo.create(session, "روش ۳", "Method 3")
        method_id = method.id

    with session_scope() as session:
        now_assigned = payment_method_repo.toggle_button_method(session, button_id, method_id)
        assert now_assigned is True

    with session_scope() as session:
        now_assigned = payment_method_repo.toggle_button_method(session, button_id, method_id)
        assert now_assigned is False


def test_disabled_method_excluded_from_button_methods():
    button_id = _make_button("غیرفعال")
    with session_scope() as session:
        method = payment_method_repo.create(session, "روش ۴", "Method 4")
        method_id = method.id
        payment_method_repo.toggle_button_method(session, button_id, method_id)
        payment_method_repo.toggle_enabled(session, method_id)  # disable it

    with session_scope() as session:
        methods = payment_method_repo.methods_for_button(session, button_id, only_enabled=True)
        assert all(m.id != method_id for m in methods)
