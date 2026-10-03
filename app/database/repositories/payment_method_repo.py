from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import ButtonPaymentMethod, PaymentMethod


def get(session: Session, method_id: int) -> PaymentMethod | None:
    return session.get(PaymentMethod, method_id)


def get_all(session: Session, only_enabled: bool = False) -> list[PaymentMethod]:
    stmt = select(PaymentMethod).order_by(PaymentMethod.position, PaymentMethod.id)
    if only_enabled:
        stmt = stmt.where(PaymentMethod.enabled == True)  # noqa: E712
    return session.execute(stmt).scalars().all()


def _next_position(session: Session) -> int:
    max_pos = session.execute(select(func.max(PaymentMethod.position))).scalar()
    return (max_pos or 0) + 1


def create(
    session: Session,
    name_fa: str,
    name_en: str,
    instructions_fa: str | None = None,
    instructions_en: str | None = None,
    is_builtin_stars: bool = False,
) -> PaymentMethod:
    method = PaymentMethod(
        name_fa=name_fa,
        name_en=name_en,
        instructions_fa=instructions_fa,
        instructions_en=instructions_en,
        is_builtin_stars=is_builtin_stars,
        enabled=True,
        position=_next_position(session),
    )
    session.add(method)
    session.flush()
    return method


def ensure_builtin_stars(session: Session) -> PaymentMethod:
    """Idempotently ensures the automatic Telegram Stars method exists."""
    existing = session.execute(
        select(PaymentMethod).where(PaymentMethod.is_builtin_stars == True)  # noqa: E712
    ).scalar_one_or_none()
    if existing:
        return existing
    return create(session, "⭐ Stars", "⭐ Stars", is_builtin_stars=True)


def ensure_default_gift_method(session: Session) -> PaymentMethod:
    """Idempotently seeds a 'Gift' method so upgraded bots keep offering
    the same manual-receipt option they had before this feature existed."""
    existing = session.execute(
        select(PaymentMethod).where(PaymentMethod.name_en == "Gift", PaymentMethod.is_builtin_stars == False)  # noqa: E712
    ).scalar_one_or_none()
    if existing:
        return existing
    return create(session, "🎁 گیفت", "🎁 Gift")


def rename(session: Session, method_id: int, name_fa: str, name_en: str) -> PaymentMethod | None:
    method = get(session, method_id)
    if method:
        method.name_fa = name_fa
        method.name_en = name_en
        session.flush()
    return method


def update_instructions(
    session: Session, method_id: int, instructions_fa: str, instructions_en: str
) -> PaymentMethod | None:
    method = get(session, method_id)
    if method:
        method.instructions_fa = instructions_fa
        method.instructions_en = instructions_en
        session.flush()
    return method


def toggle_enabled(session: Session, method_id: int) -> PaymentMethod | None:
    method = get(session, method_id)
    if method:
        method.enabled = not method.enabled
        session.flush()
    return method


def delete(session: Session, method_id: int) -> bool:
    method = get(session, method_id)
    if not method or method.is_builtin_stars:
        return False
    session.delete(method)
    session.flush()
    return True


# ---------- Per-button assignment ----------

def get_assigned_method_ids(session: Session, button_id: int) -> set[int]:
    rows = session.execute(
        select(ButtonPaymentMethod.payment_method_id).where(ButtonPaymentMethod.button_id == button_id)
    ).scalars().all()
    return set(rows)


def methods_for_button(session: Session, button_id: int, only_enabled: bool = True) -> list[PaymentMethod]:
    assigned_ids = get_assigned_method_ids(session, button_id)
    if not assigned_ids:
        # No explicit selection yet -> offer every currently-enabled method.
        return get_all(session, only_enabled=only_enabled)

    stmt = select(PaymentMethod).where(PaymentMethod.id.in_(assigned_ids)).order_by(
        PaymentMethod.position, PaymentMethod.id
    )
    if only_enabled:
        stmt = stmt.where(PaymentMethod.enabled == True)  # noqa: E712
    return session.execute(stmt).scalars().all()


def toggle_button_method(session: Session, button_id: int, method_id: int) -> bool:
    """Returns True if the method is now assigned to the button, False if removed."""
    existing = session.execute(
        select(ButtonPaymentMethod).where(
            ButtonPaymentMethod.button_id == button_id, ButtonPaymentMethod.payment_method_id == method_id
        )
    ).scalar_one_or_none()
    if existing:
        session.delete(existing)
        session.flush()
        return False
    session.add(ButtonPaymentMethod(button_id=button_id, payment_method_id=method_id))
    session.flush()
    return True
