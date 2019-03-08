from . import ast
from . import cst
from . import errors
from . import lexer
from . import parser
from .scopes import Scope
from mtots import test
from mtots import util
import os

_source_root = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'root',
)

OBJECT = 'Object'


def load(data, *, path='<string>'):
    return resolve(parser.parse(data=data, path=path))


def _import_path_to_file_path(import_path):
    return os.path.join(
        _source_root,
        import_path.replace('.', os.path.sep) + '.nc',
    )


def _flatten(node: cst.File, include_prelude=True):
    statements = []
    seen = set()
    if include_prelude:
        statements.extend(
            _import_flattened_file_statements('_prelude', seen))
    statements.extend(_flatten_file_to_statements(node, seen))
    return cst.File(
        mark=node.mark,
        statements=tuple(statements),
    )


def _import_flattened_file_statements(import_path: str, seen: set):
    if import_path not in seen:
        seen.add(import_path)
        file_path = _import_path_to_file_path(import_path)
        with open(file_path) as f:
            data = f.read()
        imported_file_node = parser.parse(data, path=file_path)
        yield from _flatten_file_to_statements(
            node=imported_file_node,
            seen=seen,
        )


def _flatten_file_to_statements(node: cst.File, seen: set):
    for stmt in node.statements:
        if isinstance(stmt, cst.Import):
            import_path = stmt.name
            if import_path not in seen:
                yield from _import_flattened_file_statements(
                    import_path=import_path,
                    seen=seen,
                )
        else:
            yield stmt


def resolve(node: cst.File):
    flattened_node = _flatten(node)
    scope = Scope(None)
    _resolve_all(flattened_node, scope)
    assert scope.parent is None
    return dict(scope.table)


def _resolve_all(node, scope):
    _resolve_global_names(node, scope)
    _resolve_fields(node, scope)


@util.multimethod(1)
def _resolve_global_names(on):
    """With forward resolve, we merely collect all global symbols
    """

    @on(cst.File)
    def r(node, scope):
        assert scope.parent is None
        for stmt in node.statements:
            _resolve_global_names(stmt, scope)

    @on(cst.Function)
    def r(node, scope):
        func = ast.Function(
            mark=node.mark,
            complete=False,
            native=node.native,
            return_type=None,
            name=node.name,
            type_parameters=None,
            generic=node.type_parameters is not None,
            parameters=None,
            body=None,
        )
        with scope.push_mark(node.mark):
            scope[func.name] = func

    @on(cst.Class)
    def r(node, scope):
        class_ = ast.Class(
            mark=node.mark,
            complete=False,
            cst=node,
            native=node.native,
            name=node.name,
            base=None,
            type_parameters=None,
            generic=node.type_parameters is not None,
            fields=None,
        )
        with scope.push_mark(node.mark):
            scope[class_.name] = class_


def _compute_base_class_node(class_, stmt, scope):
    if stmt.base is None:
        if class_.name == OBJECT:
            base = None
        else:
            base = scope[OBJECT]
    elif isinstance(stmt.base, (cst.Typename. cst.ReifiedType)):
        base = scope[stmt.base.name]
    else:
        base = scope[stmt]
    if base and not base.complete:
        with scope.push_mark(class_.mark, base.mark):
            raise scope.error(f'Incomplete base type')


def _resolve_fields(node, scope):
    for stmt in node.statements:
        if isinstance(stmt, cst.Class):
            class_ = scope[stmt.name]
            base = _compute_base_class_node(class_, stmt, scope)
            class_.base = base
            field_map = {}
            for field_node in stmt.fields:
                field = ast.Field(
                    mark=field_node.mark,
                    name=field_node.name,
                    type=_eval_type(field_node.type, scope),
                )
                field_map[field.name] = field
            class_.fields = field_map
            class_.complete = True


@util.multimethod(1)
def _eval_type(on):

    @on(cst.VoidType)
    def r(node, scope):
        return ast.VOID

    @on(cst.BoolType)
    def r(node, scope):
        return ast.BOOL

    @on(cst.IntType)
    def r(node, scope):
        return ast.INT

    @on(cst.DoubleType)
    def r(node, scope):
        return ast.DOUBLE

    @on(cst.StringType)
    def r(node, scope):
        return ast.STRING

    @on(cst.Typename)
    def r(node, scope):
        with scope.push_mark(node.mark):
            class_ = scope[node.name]
            with scope.push_mark(class_.mark):
                if not isinstance(class_, (ast.Class, ast.TypeParameter)):
                    raise scope.error(f'{repr(node.name)} is not a type')
                if isinstance(class_, ast.Class) and class_.generic:
                    raise scope.error(
                        f'{repr(node.name)} is a generic class')
        return class_

    @on(cst.ReifiedType)
    def r(node, scope):
        with scope.push_mark(node.mark):
            class_ = scope[node.name]
            with scope.push_mark(class_.mark):
                if not isinstance(class_, ast.Class):
                    raise scope.error(f'{repr(node.name)} is not a class')
                if not class_.generic:
                    raise scope.error(
                        f'{repr(node.name)} is not a generic class')
                cst_type_parameters = class_.cst.type_parameters
                param_len = len(cst_type_parameters)
                arg_len = len(node.type_arguments)
                if arg_len != param_len:
                    raise scope.error(
                        f'Expected {param_len} type args but got '
                        f'{arg_len} args')

        type_parameters = []
        class_scope = Scope(scope)
        for cst_tparam in cst_type_parameters:
            with class_scope.push_mark(cst_tparam.mark):
                tparam = ast.TypeParameter(
                    mark=cst_tparam.mark,
                    name=cst_tparam.name,
                    base=(
                        None if cst_tparam.base is None else
                        _eval_type(cst_tparam.base, class_scope)
                    ),
                )
                type_parameters.append(tparam)
                class_scope[tparam.name] = tparam
        class_.type_parameters = type_parameters

        type_arguments = [
            _eval_type(e, class_scope)
            for e in node.type_arguments
        ]

        return ast.ReifiedType(
            mark=node.mark,
            class_=class_,
            type_arguments=type_arguments,
        )


@test.case
def test_sanity():
    # Just check that this loads without throwing
    load(r"""
    class Foo {
        List[T] list
    }
    native List[T] pair(T a, T b)
    int main() = 0
    """)

    @test.throws(errors.KeyError)
    def duplicate_class():
        load('class Object {}')
