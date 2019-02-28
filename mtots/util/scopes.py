"""Scope here means a chained dictionary.

Like javascript Objects.
"""


class Scope:
    def __init__(self, parent):
        self.parent = parent
        self.table = {}

    def __getitem__(self, key):
        return self.table[key] if key in self.table else self.parent[key]

    def __setitem__(self, key, value):
        self.table[key] = value

    def __contains__(self, key):
        return key in self.table or key in self.parent

    def __iter__(self):
        yield from self.table

        for key in self.parent:
            if key not in self.table:
                yield key
