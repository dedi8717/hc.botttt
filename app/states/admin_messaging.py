from enum import IntEnum, auto


class DirectMessageState(IntEnum):
    WAIT_USER_ID = auto()
    WAIT_CONTENT = auto()


class BroadcastState(IntEnum):
    WAIT_CONTENT = auto()
    CONFIRM = auto()
