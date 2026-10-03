from enum import IntEnum, auto


class AddAdminState(IntEnum):
    WAIT_ID = auto()
    CHOOSE_ROLE = auto()
