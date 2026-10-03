import os

from app.services import membership_service


def test_membership_not_required_by_default():
    # conftest.py doesn't set REQUIRED_CHANNEL, so this should be disabled.
    assert membership_service.membership_required() is False


def test_channel_join_link_empty_when_not_configured():
    assert membership_service.channel_join_link() == ""


def test_channel_join_link_derived_from_username(monkeypatch):
    monkeypatch.setattr(membership_service.config, "REQUIRED_CHANNEL", "@mychannel")
    monkeypatch.setattr(membership_service.config, "REQUIRED_CHANNEL_LINK", "")
    assert membership_service.channel_join_link() == "https://t.me/mychannel"


def test_channel_join_link_prefers_explicit_link(monkeypatch):
    monkeypatch.setattr(membership_service.config, "REQUIRED_CHANNEL", "@mychannel")
    monkeypatch.setattr(membership_service.config, "REQUIRED_CHANNEL_LINK", "https://t.me/+customInvite")
    assert membership_service.channel_join_link() == "https://t.me/+customInvite"


def test_membership_required_when_channel_set(monkeypatch):
    monkeypatch.setattr(membership_service.config, "REQUIRED_CHANNEL", "@mychannel")
    assert membership_service.membership_required() is True
