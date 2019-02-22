import typing
from mtots.text import base


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
                raise base.Error(
                    stack + [old_decl.mark, new_decl.mark],
                    f'{repr(key)} is already defined',
                )
            if not old_decl.match(new_decl):
                raise base.Error(
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
            raise base.Error(stack, f'{repr(key)} is not defined')

    def update(self, scope):
        for key, value in scope.items():
            self.set(key, value, [])
