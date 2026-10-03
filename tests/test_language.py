from app.services import user_service


def test_user_registration_has_no_language_by_default():
    user_service.register_or_update(90001, "alice", "Alice")
    assert user_service.get_language(90001) is None


def test_set_and_switch_language():
    user_service.register_or_update(90002, "bob", "Bob")
    user_service.set_language(90002, "fa")
    assert user_service.get_language(90002) == "fa"

    user_service.set_language(90002, "en")
    assert user_service.get_language(90002) == "en"
