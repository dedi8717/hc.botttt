from app.database.database import session_scope
from app.database.repositories import button_repo, content_repo


def _make_button():
    with session_scope() as session:
        b = button_repo.create(session, "محتوا", "Content")
        return b.id


def test_add_text_content():
    button_id = _make_button()
    with session_scope() as session:
        content_repo.create(session, button_id, "text", text_fa="متن", text_en="Text")

    with session_scope() as session:
        contents = content_repo.get_for_button(session, button_id)
        assert len(contents) == 1
        assert contents[0].content_type == "text"


def test_edit_content_text_and_caption():
    button_id = _make_button()
    with session_scope() as session:
        c = content_repo.create(session, button_id, "photo", file_id="ABC123", caption_fa="قدیمی", caption_en="Old")
        content_id = c.id

    with session_scope() as session:
        content_repo.update_caption(session, content_id, "fa", "جدید")
        c = content_repo.get(session, content_id)
        assert c.caption_fa == "جدید"
        assert c.caption_en == "Old"


def test_delete_content():
    button_id = _make_button()
    with session_scope() as session:
        c = content_repo.create(session, button_id, "text", text_fa="حذف من", text_en="Delete me")
        content_id = c.id

    with session_scope() as session:
        assert content_repo.delete(session, content_id) is True
        assert content_repo.get(session, content_id) is None


def test_content_ordering_move():
    button_id = _make_button()
    with session_scope() as session:
        c1 = content_repo.create(session, button_id, "text", text_fa="1", text_en="1")
        c2 = content_repo.create(session, button_id, "text", text_fa="2", text_en="2")
        pos1, pos2 = c1.position, c2.position

    with session_scope() as session:
        content_repo.move_position(session, c2.id, "up")
        c1b = content_repo.get(session, c1.id)
        c2b = content_repo.get(session, c2.id)
        assert c1b.position == pos2
        assert c2b.position == pos1
