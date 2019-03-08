"""Scope here means a chained dictionary.

Like javascript Objects.
"""
from . import errors
import contextlib


class Scope:
    def __init__(self, parent):
        self.parent = parent
        self.table = {}
        if parent is None:
            self.stack = []
        else:
            self.stack = parent.stack

    def __getitem__(self, key):
        if key in self.table:
            return self.table[key]
        elif self.parent is None:
            raise errors.KeyError(self.stack, f'{repr(key)} not defined')
        return self.parent[key]

    def __setitem__(self, key, value):
        if key in self.table:
            with self.push_mark(self.table[key].mark):
                raise errors.KeyError(
                    self.stack, f'{repr(key)} already defined')
        self.table[key] = value

    def __contains__(self, key):
        return key in self.table or key in self.parent

    def __iter__(self):
        yield from self.table

        for key in self.parent:
            if key not in self.table:
                yield key

    def error(self, message):
        return errors.TypeError(self.stack, message)

    @contextlib.contextmanager
    def push_mark(self, *marks):
        self.stack.extend(marks)
        try:
            yield
        finally:
            for _ in marks:
                self.stack.pop()

