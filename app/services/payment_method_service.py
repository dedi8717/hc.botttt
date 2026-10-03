from __future__ import annotations

from dataclasses import dataclass

from app.database.database import session_scope
from app.database.repositories import payment_method_repo
from app.utils.translations import field_for_lang


@dataclass
class PaymentMethodView:
    id: int
    name: str
    instructions: str | None
    is_builtin_stars: bool
    enabled: bool


def _to_view(method, lang: str) -> PaymentMethodView:
    return PaymentMethodView(
        id=method.id,
        name=field_for_lang(method, "name", lang),
        instructions=field_for_lang(method, "instructions", lang) or None,
        is_builtin_stars=method.is_builtin_stars,
        enabled=method.enabled,
    )


def ensure_defaults() -> None:
    """Called once at startup - seeds the built-in Stars method and a
    default Gift method so upgraded bots keep working unchanged."""
    with session_scope() as session:
        payment_method_repo.ensure_builtin_stars(session)
        payment_method_repo.ensure_default_gift_method(session)


def list_all(lang: str) -> list[PaymentMethodView]:
    with session_scope() as session:
        return [_to_view(m, lang) for m in payment_method_repo.get_all(session)]


def get(method_id: int, lang: str) -> PaymentMethodView | None:
    with session_scope() as session:
        method = payment_method_repo.get(session, method_id)
        return _to_view(method, lang) if method else None


def create(name_fa: str, name_en: str) -> int:
    with session_scope() as session:
        method = payment_method_repo.create(session, name_fa, name_en)
        return method.id


def rename(method_id: int, name_fa: str, name_en: str) -> None:
    with session_scope() as session:
        payment_method_repo.rename(session, method_id, name_fa, name_en)


def update_instructions(method_id: int, instructions_fa: str, instructions_en: str) -> None:
    with session_scope() as session:
        payment_method_repo.update_instructions(session, method_id, instructions_fa, instructions_en)


def toggle_enabled(method_id: int) -> bool | None:
    with session_scope() as session:
        method = payment_method_repo.toggle_enabled(session, method_id)
        return method.enabled if method else None


def delete(method_id: int) -> bool:
    with session_scope() as session:
        return payment_method_repo.delete(session, method_id)


def methods_for_button(button_id: int, lang: str, only_enabled: bool = True) -> list[PaymentMethodView]:
    with session_scope() as session:
        methods = payment_method_repo.methods_for_button(session, button_id, only_enabled=only_enabled)
        return [_to_view(m, lang) for m in methods]


def assigned_method_ids(button_id: int) -> set[int]:
    with session_scope() as session:
        return payment_method_repo.get_assigned_method_ids(session, button_id)


def toggle_button_method(button_id: int, method_id: int) -> bool:
    with session_scope() as session:
        return payment_method_repo.toggle_button_method(session, button_id, method_id)
