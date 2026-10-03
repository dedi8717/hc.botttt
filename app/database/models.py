from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utcnow() -> dt.datetime:
    return dt.datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str | None] = mapped_column(String(5), nullable=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # OWNER / ADMIN / MODERATOR
    added_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

    permissions: Mapped[list["AdminPermission"]] = relationship(
        back_populates="admin", cascade="all, delete-orphan"
    )


class AdminPermission(Base):
    __tablename__ = "admin_permissions"
    __table_args__ = (UniqueConstraint("admin_id", "permission", name="uq_admin_permission"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("admins.id", ondelete="CASCADE"))
    permission: Mapped[str] = mapped_column(String(50), nullable=False)

    admin: Mapped["Admin"] = relationship(back_populates="permissions")


class Button(Base):
    __tablename__ = "buttons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("buttons.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name_fa: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    price: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(10), default="XTR")
    is_free: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


# Self-referential relationship declared separately (needs the class to exist first).
Button.children = relationship(
    "Button",
    backref="parent",
    remote_side=[Button.id],
    cascade="all, delete-orphan",
    single_parent=True,
    order_by="Button.position",
)

Button.contents = relationship(
    "Content", back_populates="button", cascade="all, delete-orphan", order_by="Content.position"
)


class Content(Base):
    __tablename__ = "contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    button_id: Mapped[int] = mapped_column(ForeignKey("buttons.id", ondelete="CASCADE"), index=True)
    content_type: Mapped[str] = mapped_column(String(20), nullable=False)  # text/photo/video/document
    text_fa: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    caption_fa: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    button: Mapped["Button"] = relationship(back_populates="contents")


class Payment(Base):
    """A recorded payment (Stars or a custom manually-reviewed method)."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    button_id: Mapped[int] = mapped_column(ForeignKey("buttons.id", ondelete="CASCADE"))
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="XTR")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/paid/failed
    provider_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class UserAccess(Base):
    """Stub granting a user access to a paid button after a successful payment."""

    __tablename__ = "user_access"
    __table_args__ = (UniqueConstraint("user_id", "button_id", name="uq_user_button_access"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    button_id: Mapped[int] = mapped_column(ForeignKey("buttons.id", ondelete="CASCADE"))
    granted_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class Settings(Base):
    """Generic key/value settings table for future configurable options."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)


class PaymentMethod(Base):
    """
    An admin-configurable way to pay. One row (`is_builtin_stars=True`)
    is the automatic Telegram Stars invoice and is created automatically
    at startup - it can be renamed/enabled/disabled/assigned per button
    like any other method, but never deleted and has no editable
    instructions (the "instructions" shown to the user for Stars is
    generated in code, not stored here).

    Every other row is a custom, manually-reviewed method (card
    transfer, crypto, gift card, etc.): the user sends a receipt photo
    after reading `instructions_fa`/`instructions_en`, and an admin
    approves or rejects it, exactly like the original Gift flow - Gift
    itself is now just the first custom method, seeded at startup.
    """

    __tablename__ = "payment_methods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name_fa: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    instructions_fa: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructions_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_builtin_stars: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ButtonPaymentMethod(Base):
    """
    Which payment methods are offered for a given button. If a button
    has NO rows here at all, every currently-enabled payment method is
    offered by default (so existing buttons keep working exactly as
    before this feature existed, with no admin action required). Once
    an admin explicitly picks methods for a button, only those (that
    are still individually enabled) are shown.
    """

    __tablename__ = "button_payment_methods"
    __table_args__ = (
        UniqueConstraint("button_id", "payment_method_id", name="uq_button_payment_method"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    button_id: Mapped[int] = mapped_column(ForeignKey("buttons.id", ondelete="CASCADE"))
    payment_method_id: Mapped[int] = mapped_column(ForeignKey("payment_methods.id", ondelete="CASCADE"))
