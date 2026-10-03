from enum import IntEnum, auto


class AddContentState(IntEnum):
    WAIT_CONTENT = auto()
    CAPTION_FA = auto()
    CAPTION_EN = auto()


class EditContentState(IntEnum):
    CHOOSE_FIELD = auto()
    NEW_TEXT = auto()
    NEW_MEDIA = auto()
    NEW_CAPTION_FA = auto()
    NEW_CAPTION_EN = auto()
