"""rstates = return states"""
from .types import Type
from mtots import util


class ReturnState:
    "Describe the state of what a function returns after a given statement"


@util.dataclass
class Returns(ReturnState):
    "Indicates that a return statement that returns given type encountered"
    type: Type


@util.dataclass
class NoReturn(ReturnState):
    "Indicates that no return statement may have been encountered"

    def __hash__(self):
        return hash(NoReturn)
