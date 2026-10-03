"""
Two kinds of payment, both ending in the same place: a `UserAccess` row
that unlocks a button for a user.

1. Telegram Stars (currency="XTR") - a native Bot API invoice. Telegram
   handles the charge itself; `record_successful_stars_payment` just
   records it and grants access the moment Telegram confirms success.
   Stars paid this way always land in the bot's own Stars balance - the
   Bot API has no way to route a payment to a different Telegram account.

2. Any admin-created custom payment method (Gift, card transfer,
   crypto, etc. - see `payment_method_service`) - a manual,
   receipt-based flow. The user sends a photo of their receipt, it's
   forwarded to every admin with the `manage_payments` permission (plus
   the Owner), and an admin taps Approve or Reject. `approve_payment`
   grants access immediately; `reject_payment` just notifies the user
   so they can retry.

Custom-method payments are tagged in `Payment.currency` as
"METHOD:<payment_method_id>" rather than getting their own database
column, so this feature needed no changes to the existing `payments`
table schema.
"""
from __future__ import annotations

from app.database.database import session_scope
from app.database.models import Payment, User, UserAccess
from app.database.repositories import button_repo, payment_method_repo, user_repo

METHOD_CURRENCY_PREFIX = "METHOD:"


def user_has_access(telegram_id: int, button_id: int) -> bool:
    with session_scope() as session:
        user = user_repo.get_by_telegram_id(session, telegram_id)
        if not user:
            return False
        access = session.query(UserAccess).filter_by(user_id=user.id, button_id=button_id).first()
        return access is not None


# ---------- Telegram Stars ----------

def record_successful_stars_payment(
    telegram_id: int, button_id: int, amount: int, telegram_charge_id: str
) -> int | None:
    """Called after Telegram confirms a successful Stars payment. Records
    the payment and grants access. `telegram_charge_id` (from
    `successful_payment.telegram_payment_charge_id`) is stored so the
    transaction can be looked up/refunded later if needed."""
    with session_scope() as session:
        user = user_repo.get_by_telegram_id(session, telegram_id)
        if not user:
            return None

        payment = Payment(
            user_id=user.id,
            button_id=button_id,
            amount=amount,
            currency="XTR",
            status="paid",
            provider_ref=telegram_charge_id,
        )
        session.add(payment)
        session.flush()

        existing = session.query(UserAccess).filter_by(user_id=user.id, button_id=button_id).first()
        if not existing:
            session.add(UserAccess(user_id=user.id, button_id=button_id))

        return payment.id


# ---------- Custom payment methods (manual receipt review) ----------

def create_pending_method_payment(
    telegram_id: int, button_id: int, amount: int, method_id: int, receipt_file_id: str
) -> int | None:
    """Creates a pending Payment row for a receipt submitted against a
    specific custom payment method. `receipt_file_id` (the Telegram
    file_id of the receipt photo) is stored in `provider_ref` so it can
    be re-sent without re-uploading."""
    with session_scope() as session:
        user = user_repo.get_by_telegram_id(session, telegram_id)
        if not user:
            return None
        payment = Payment(
            user_id=user.id,
            button_id=button_id,
            amount=amount,
            currency=f"{METHOD_CURRENCY_PREFIX}{method_id}",
            status="pending",
            provider_ref=receipt_file_id,
        )
        session.add(payment)
        session.flush()
        return payment.id


def get_payment_details(payment_id: int) -> dict | None:
    with session_scope() as session:
        payment = session.get(Payment, payment_id)
        if not payment:
            return None
        user = session.get(User, payment.user_id)
        button = button_repo.get(session, payment.button_id)

        method_name_fa = method_name_en = None
        if payment.currency and payment.currency.startswith(METHOD_CURRENCY_PREFIX):
            try:
                method_id = int(payment.currency[len(METHOD_CURRENCY_PREFIX):])
                method = payment_method_repo.get(session, method_id)
                if method:
                    method_name_fa, method_name_en = method.name_fa, method.name_en
            except ValueError:
                pass

        return {
            "id": payment.id,
            "status": payment.status,
            "amount": payment.amount,
            "currency": payment.currency,
            "method_name_fa": method_name_fa,
            "method_name_en": method_name_en,
            "receipt_file_id": payment.provider_ref,
            "user_telegram_id": user.telegram_id if user else None,
            "user_display": (user.username or user.first_name or str(user.telegram_id)) if user else "?",
            "button_id": payment.button_id,
            "button_name_fa": button.name_fa if button else "",
            "button_name_en": button.name_en if button else "",
        }


def approve_payment(payment_id: int) -> dict | None:
    """Marks the payment paid and grants access. Returns None if the
    payment doesn't exist or was already reviewed (idempotency guard
    against double-tapping Approve/Reject)."""
    with session_scope() as session:
        payment = session.get(Payment, payment_id)
        if not payment or payment.status != "pending":
            return None
        payment.status = "paid"
        user = session.get(User, payment.user_id)
        existing = (
            session.query(UserAccess)
            .filter_by(user_id=payment.user_id, button_id=payment.button_id)
            .first()
        )
        if not existing:
            session.add(UserAccess(user_id=payment.user_id, button_id=payment.button_id))
        return {"user_telegram_id": user.telegram_id if user else None, "button_id": payment.button_id}


def reject_payment(payment_id: int) -> dict | None:
    with session_scope() as session:
        payment = session.get(Payment, payment_id)
        if not payment or payment.status != "pending":
            return None
        payment.status = "failed"
        user = session.get(User, payment.user_id)
        return {"user_telegram_id": user.telegram_id if user else None}
