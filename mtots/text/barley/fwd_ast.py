from mtots.text import base
from mtots.util.dataclasses import dataclass
from typing import List
from typing import Optional


Node = base.Node


@dataclass
class Module(Node):
    entries: List['Entry']


@dataclass
class Entry(Node):
    name: str
    type: str
