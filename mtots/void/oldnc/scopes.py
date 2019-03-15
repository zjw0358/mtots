from mtots.util import typing
from mtots.parser import base
from . import errors


class Scope:
    def __init__(self, parent: typing.Optional['Scope']):
        self.parent = parent
        self.table = {}

    def set(
            self,
            key: str,
            new_decl: 'Declaration',
            stack: typing.List[base.Mark]):
        if key in self.table:
            old_decl = self.table[key]
            if isinstance(old_decl, Definition):
                raise errors.TypeError(
                    stack + [old_decl.mark, new_decl.mark],
                    f'{repr(key)} is already defined',
                )
            if not old_decl.match(new_decl):
                raise errors.TypeError(
                    stack + [old_decl.mark, new_decl.mark],
                    f"{repr(key)} declarations don't match",
                )
            if isinstance(new_decl, Definition):
                self.table[key] = new_decl
        else:
            self.table[key] = new_decl

    def get(self, key: str, stack: typing.List[base.Mark]):
        if key in self.table:
            return self.table[key]
        elif self.parent is not None:
            return self.parent.get(key, stack)
        else:
            raise errors.MissingReference(
                stack,
                f'{repr(key)} is not defined',
            )

    def update(self, scope):
        for key, value in scope.items():
            self.set(key, value, [])
