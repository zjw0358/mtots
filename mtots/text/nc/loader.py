from . import cst
from . import parser
from mtots.text import base
import collections
import os

_source_root = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'root',
)


def _import_path_to_file_path(import_path):
    return os.path.join(
        _source_root,
        import_path.replace('.', os.path.sep) + '.nc',
    )


def _parse_module(import_path):
    file_path = _import_path_to_file_path(import_path)
    with open(file_path) as f:
        data = f.read()
    return parser.parse(data=data, file_path=file_path)


def load(data, *, file_path='<string>'):
    main_tu = parser.parse(data=data, file_path=file_path)
    seen = {'MAIN'}
    pairs = []
    queue = [('MAIN', main_tu)]
    while queue:
        tu_name, tu = queue.pop()
        pairs.append((tu_name, tu))
        for stmt in tu.stmts:
            if isinstance(stmt, cst.Import):
                import_path = stmt.path
                if import_path not in seen:
                    seen.add(import_path)
                    import_tu = _parse_module(import_path)
                    queue.append((import_path, import_tu))
    return collections.OrderedDict(reversed(pairs))

