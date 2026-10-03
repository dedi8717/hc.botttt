from enum import IntEnum, auto


class AddButtonState(IntEnum):
    NAME_FA = auto()
    NAME_EN = auto()
    PARENT = auto()


class RenameButtonState(IntEnum):
    NAME_FA = auto()
    NAME_EN = auto()


class PriceState(IntEnum):
    AMOUNT = auto()


class MoveParentState(IntEnum):
    CHOOSE_PARENT = auto()
