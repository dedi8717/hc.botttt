from app.database.database import session_scope
from app.database.repositories import button_repo


def test_create_and_rename_button():
    with session_scope() as session:
        b = button_repo.create(session, "آموزش", "Education")
        button_id = b.id

    with session_scope() as session:
        button_repo.rename(session, button_id, "آموزش جدید", "New Education")
        b = button_repo.get(session, button_id)
        assert b.name_fa == "آموزش جدید"
        assert b.name_en == "New Education"


def test_nested_button_and_deep_nesting():
    with session_scope() as session:
        root = button_repo.create(session, "فیلم", "Movies")
        child = button_repo.create(session, "اکشن", "Action", parent_id=root.id)
        grandchild = button_repo.create(session, "۲۰۲۰", "2020", parent_id=child.id)

    with session_scope() as session:
        children_of_root = button_repo.get_children(session, root.id)
        assert len(children_of_root) == 1
        assert children_of_root[0].id == child.id

        children_of_child = button_repo.get_children(session, child.id)
        assert len(children_of_child) == 1
        assert children_of_child[0].id == grandchild.id


def test_delete_button_cascades_to_children():
    with session_scope() as session:
        root = button_repo.create(session, "پارنت", "Parent")
        child = button_repo.create(session, "چایلد", "Child", parent_id=root.id)
        child_id = child.id
        root_id = root.id

    with session_scope() as session:
        assert button_repo.delete(session, root_id) is True

    with session_scope() as session:
        assert button_repo.get(session, root_id) is None
        assert button_repo.get(session, child_id) is None


def test_disable_button_hides_from_enabled_query():
    with session_scope() as session:
        b = button_repo.create(session, "پنهان", "Hidden")
        button_id = b.id
        button_repo.toggle_enabled(session, button_id)  # now disabled

    with session_scope() as session:
        enabled_children = button_repo.get_children(session, None, only_enabled=True)
        assert all(x.id != button_id for x in enabled_children)

        all_children = button_repo.get_children(session, None, only_enabled=False)
        assert any(x.id == button_id for x in all_children)


def test_move_position_up_and_down():
    with session_scope() as session:
        a = button_repo.create(session, "A", "A")
        b = button_repo.create(session, "B", "B")
        pos_a, pos_b = a.position, b.position

    with session_scope() as session:
        button_repo.move_position(session, b.id, "up")
        a2 = button_repo.get(session, a.id)
        b2 = button_repo.get(session, b.id)
        assert a2.position == pos_b
        assert b2.position == pos_a


def test_circular_parent_prevention():
    with session_scope() as session:
        root = button_repo.create(session, "ریشه", "Root")
        child = button_repo.create(session, "فرزند", "Child", parent_id=root.id)

    with session_scope() as session:
        # Trying to move root under its own child must fail.
        ok, reason = button_repo.move_to_parent(session, root.id, child.id)
        assert ok is False
        assert reason == "circular"

        # A button cannot become its own parent either.
        ok2, reason2 = button_repo.move_to_parent(session, root.id, root.id)
        assert ok2 is False
        assert reason2 == "circular"


def test_button_with_content_and_children_can_coexist():
    from app.database.repositories import content_repo

    with session_scope() as session:
        b = button_repo.create(session, "ترکیبی", "Combo")
        content_repo.create(session, b.id, "text", text_fa="سلام", text_en="Hello")
        button_repo.create(session, "زیر", "Sub", parent_id=b.id)
        button_id = b.id

    with session_scope() as session:
        contents = content_repo.get_for_button(session, button_id)
        children = button_repo.get_children(session, button_id)
        assert len(contents) == 1
        assert len(children) == 1
