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

OBJECT = '_prelude.Object'


def load(data, *, path='<string>'):
    return resolve(parser.parse(data=data, path=path))


def _import_path_to_file_path(import_path):
    return os.path.join(
        _source_root,
        import_path.replace('.', os.path.sep) + '.nc',
    )


def _find_and_parse(import_path: str):
    file_path = _import_path_to_file_path(import_path)
    with open(file_path) as f:
        data = f.read()
    return parser.parse(data, path=file_path)


def _collect_file_nodes(node: cst.File, seen: set):
    for stmt in node.statements:
        if isinstance(stmt, cst.Import):
            import_path, _short_name = stmt.name.rsplit('.', 1)
            if import_path not in seen:
                seen.add(import_path)
                imported_node = _find_and_parse(import_path)
                yield from _collect_file_nodes(imported_node, seen)
                yield import_path, imported_node


def resolve(node: cst.File):
    prelude_file_node = _find_and_parse('_prelude')
    file_nodes = [('_prelude', prelude_file_node)]
    file_nodes.extend(_collect_file_nodes(node, set()))
    file_nodes.append(('_main', node))
    global_scope = Scope(None)
    file_scope_map = {
        import_name: Scope(global_scope)
        for import_name, _ in file_nodes
    }
    for import_name, file_scope in file_scope_map.items():
        file_scope['@prefix'] = import_name + '.'

    def _run_resolve_pass(resolver):
        for import_name, file_node in file_nodes:
            file_scope = file_scope_map[import_name]
            resolver(file_node, file_scope)

    _run_resolve_pass(_resolve_global_names)

    # Elevate everything in '_prelude' to be globally available
    prelude_scope = file_scope_map['_prelude']
    for key, prelude_entry_node in prelude_scope.table.items():
        if key.startswith('@'):
            continue
        full_name = prelude_entry_node.name
        assert full_name.startswith('_prelude.'), full_name
        short_name = full_name[len('_prelude.'):]
        assert '.' not in short_name, short_name
        assert full_name == '_prelude.' + short_name, (full_name, short_name)
        global_scope[short_name] = prelude_entry_node

    _run_resolve_pass(_resolve_types)
    # TODO: _run_resolve_pass(resolve_expressions)

    assert global_scope.parent is None
    return dict(global_scope.table)


@util.multimethod(1)
def _resolve_global_names(on):
    """With forward resolve, we merely collect all global symbols
    """

    @on(cst.File)
    def r(node, scope):
        assert scope.parent is not None
        assert scope.parent.parent is None
        for stmt in node.statements:
            _resolve_global_names(stmt, scope)

    @on(cst.Function)
    def r(node, scope):
        short_name = node.name
        full_name = scope['@prefix'] + short_name
        func = ast.Function(
            mark=node.mark,
            cst=node,
            scope=Scope(scope),
            native=node.native,
            return_type=None,
            name=full_name,
            type_parameters=None,
            generic=node.type_parameters is not None,
            parameters=None,
            body=None,
        )
        with scope.push_mark(node.mark):
            scope.root[full_name] = func
            scope[short_name] = func

    @on(cst.Class)
    def r(node, scope):
        short_name = node.name
        full_name = scope['@prefix'] + short_name
        class_ = ast.Class(
            mark=node.mark,
            cst=node,
            scope=Scope(scope),
            native=node.native,
            name=full_name,
            base=None,
            type_parameters=None,
            generic=node.type_parameters is not None,
            fields=None,
        )
        with scope.push_mark(node.mark):
            scope.root[full_name] = class_
            scope[short_name] = class_


@util.multimethod(1)
def _resolve_types(on):
    """Resolve types for top level entities:

        * class definitions
            * generic parameter bound types
            * base/super type,
            * field types
        * function definitions
            * generic parameter bound types
            * parameter types
            * return type
    """

    @on(cst.File)
    def r(node, scope):
        for stmt in node.statements:
            _resolve_types(stmt, scope)

    @on(cst.Class)
    def r(node, outer_scope):
        class_ = outer_scope[node.name]
        cscope = class_.scope
        assert cscope.parent is outer_scope
        class_.base = _compute_base(class_, node.base, cscope)
        if class_.generic:
            class_.type_parameters = _compute_type_parameters(
                node.type_parameters,
                cscope,
            )
        class_.fields = _compute_fields(node.fields, cscope)

    @on(cst.Function)
    def r(node, outer_scope):
        function = outer_scope[node.name]
        fscope = function.scope
        assert fscope.parent is outer_scope
        if function.generic:
            function.type_parameters = _compute_type_parameters(
                node.type_parameters,
                fscope,
            )
        function.parameters = _compute_parameters(node.parameters, fscope)
        function.return_type = _eval_type(node.return_type, fscope)

    def _compute_base(class_, cst_base, scope):
        if cst_base is None:
            if class_.name == OBJECT:
                base = None
            else:
                base = scope[OBJECT]
                assert isinstance(base, ast.Class)
        else:
            base = _eval_type(cst_base, scope)
            if isinstance(base, ast.Class):
                base_class_node = base
            elif isinstance(base, ast.ReifiedType):
                base_class_node = base.class_
            else:
                with scope.push_mark(cst_base.mark):
                    raise scope.error('Not an inheritable type')
        return base

    def _compute_parameters(cst_parameters, scope):
        parameters = []
        for cst_param in cst_parameters:
            param = ast.Parameter(
                mark=cst_param.mark,
                type=_eval_type(cst_param.type, scope),
                name=cst_param.name,
            )
            parameters.append(param)
            with scope.push_mark(param.mark):
                scope[param.name] = param
        return parameters

    def _compute_type_parameters(cst_type_parameters, scope):
        type_parameters = []
        for cst_tparam in cst_type_parameters:
            tparam = ast.TypeParameter(
                mark=cst_tparam.mark,
                name=cst_tparam.name,
                base=(
                    None if cst_tparam.base is None else
                    _eval_type(cst_tparam.base, scope)
                ),
            )
            type_parameters.append(tparam)
            with scope.push_mark(cst_tparam.mark):
                scope[tparam.name] = tparam
        return type_parameters

    def _compute_fields(cst_fields, scope):
        field_map = {}
        for cst_field in cst_fields:
            field = ast.Field(
                mark=cst_field.mark,
                name=cst_field.name,
                type=_eval_type(cst_field.type, scope),
            )
            field_map[field.name] = field
        return field_map


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

        type_arguments = [
            _eval_type(e, scope)
            for e in node.type_arguments
        ]

        # NOTE: The type parameter constraints are not validated here
        # because in order to do so, we need to know the full class
        # hierarchies to be able to do this, but sometimes we need
        # to evaluate types in the process of finding out the hierarchies.
        # In fact, we don't even know if class_.type_parameters
        # is ready yet.

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
        List[int] list
    }
    native List[T] pair[T](T a, T b)
    int main() = 0
    """)

    @test.throws(errors.KeyError)
    def duplicate_class():
        load(r"""
        class Foo {}
        class Foo {}
        """)
