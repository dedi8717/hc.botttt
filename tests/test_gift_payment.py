from app.database.database import session_scope
from app.database.repositories import button_repo, payment_method_repo, user_repo
from app.services import payment_service


def _make_user_button_and_method(telegram_id: int):
    with session_scope() as session:
        user_repo.get_or_create(session, telegram_id, f"user{telegram_id}", "Test")
        button = button_repo.create(session, "هدیه", "Gift Item")
        button_repo.set_price(session, button.id, 100)
        method = payment_method_repo.create(session, "روش تست", "Test Method")
        return button.id, method.id


def test_create_pending_method_payment_and_approve_grants_access():
    telegram_id = 700001
    button_id, method_id = _make_user_button_and_method(telegram_id)

    payment_id = payment_service.create_pending_method_payment(telegram_id, button_id, 100, method_id, "FAKE_FILE_ID")
    assert payment_id is not None
    assert payment_service.user_has_access(telegram_id, button_id) is False

    result = payment_service.approve_payment(payment_id)
    assert result is not None
    assert result["user_telegram_id"] == telegram_id
    assert payment_service.user_has_access(telegram_id, button_id) is True


def test_reject_method_payment_does_not_grant_access():
    telegram_id = 700002
    button_id, method_id = _make_user_button_and_method(telegram_id)

    payment_id = payment_service.create_pending_method_payment(telegram_id, button_id, 100, method_id, "FAKE_FILE_ID")
    result = payment_service.reject_payment(payment_id)
    assert result is not None
    assert payment_service.user_has_access(telegram_id, button_id) is False


def test_double_review_is_rejected():
    telegram_id = 700003
    button_id, method_id = _make_user_button_and_method(telegram_id)

    payment_id = payment_service.create_pending_method_payment(telegram_id, button_id, 100, method_id, "FAKE_FILE_ID")
    first = payment_service.approve_payment(payment_id)
    second = payment_service.approve_payment(payment_id)
    assert first is not None
    assert second is None  # already reviewed - idempotency guard


def test_payment_details_resolve_method_name():
    telegram_id = 700004
    button_id, method_id = _make_user_button_and_method(telegram_id)

    payment_id = payment_service.create_pending_method_payment(telegram_id, button_id, 100, method_id, "FAKE_FILE_ID")
    details = payment_service.get_payment_details(payment_id)
    assert details is not None
    assert details["method_name_fa"] == "روش تست"
    assert details["method_name_en"] == "Test Method"
