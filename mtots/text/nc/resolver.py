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
    seen = {'_prelude', '_main'}
    name_file_node_pairs = [('_prelude', prelude_file_node)]
    name_file_node_pairs.extend(_collect_file_nodes(node, seen))
    name_file_node_pairs.append(('_main', node))
    global_scope = Scope(None)
    file_scope_map = {
        import_name: Scope(global_scope)
        for import_name, _ in name_file_node_pairs
    }
    for import_name, file_scope in file_scope_map.items():
        file_scope['@prefix'] = import_name + '.'

    def _run_resolve_pass(resolver):
        for import_name, file_node in name_file_node_pairs:
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
    _run_resolve_pass(_resolve_expressions)

    assert global_scope.parent is None
    return {node.name: node for node in global_scope.table.values()}


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
def _resolve_expressions(on):

    @on(cst.File)
    def r(node, scope):
        for stmt in node.statements:
            _resolve_expressions(stmt, scope)

    @on(cst.Class)
    def r(node, outer_scope):
        # TODO: Once methods are needed, add code here
        pass

    @on(cst.Function)
    def r(node, outer_scope):
        function = outer_scope[node.name]
        fscope = function.scope
        assert fscope.parent is outer_scope
        if node.body is not None:
            function.body = _eval_expression(node.body, fscope)

        if function.native and function.body:
            with fscope.push_mark(function.mark):
                raise fscope.error(f'Native functions cannot have bodies')

        if not function.native and not function.body:
            with fscope.push_mark(function.mark):
                raise fscope.error(f'Normal functions must have bodies')


@util.multimethod(1)
def _eval_expression(on):

    @on(cst.Int)
    def r(node, scope):
        return ast.Int(
            mark=node.mark,
            type=ast.INT,
            value=node.value,
        )

    @on(cst.String)
    def r(node, scope):
        return ast.String(
            mark=node.mark,
            type=ast.STRING,
            value=node.value,
        )

    @on(cst.Name)
    def r(node, scope):
        decl = scope[node.value]
        decl_types = (ast.Parameter, ast.LocalVariableDeclaration)
        if not isinstance(decl, decl_types):
            with scope.push_mark(node.mark):
                raise scope.error(f'{node.value} is not a variable')
        return ast.LocalVariable(
            mark=node.mark,
            type=decl.type,
            declaration=decl,
        )

    @on(cst.Block)
    def r(node, outer_scope):
        block_scope = Scope(outer_scope)
        exprs = tuple(
            _eval_expression(e, block_scope) for e in node.expressions
        )
        if exprs:
            type_ = exprs[-1].type
        else:
            type_ = ast.VOID
        return ast.Block(
            mark=node.mark,
            type=type_,
            expressions=exprs,
        )

    @on(cst.FunctionCall)
    def r(node, scope):
        with scope.push_mark(node.mark):
            fn = scope[node.name]
            if not isinstance(fn, ast.Function):
                marks = (
                    [fn.mark] if isinstance(fn, (ast.Markable, base.Node))
                    else []
                )
                with scope.push_mark(*marks):
                    raise scope.error(f'{node.name} is not a function')
        if len(node.arguments) != len(fn.parameters):
            with scope.push_mark(node.mark, fn.mark):
                raise scope.error(
                    f'Expected {len(fn.parameters)} args '
                    f'but got {len(node.arguments)} parameters')
        type_param_bindings = {}
        args = []
        for param, cst_arg in zip(fn.parameters, node.arguments):
            raw_arg = _eval_expression(cst_arg, scope)
            unbound_param_type = param.type
            param_type = _bind_param_type(
                unbound_param_type,
                raw_arg.type,
                type_param_bindings,
                scope,
            )
            arg = _convert_type(param_type, raw_arg)
            if arg is None:
                with scope.push_mark(cst_arg.mark, param.mark):
                    raise scope.error(
                        f'Expected parameter {repr(param.name)} '
                        f'to be type {param_type} but got {raw_arg.type}')
            args.append(arg)
        return_type = _bind_param_type(
            fn.return_type,
            None,
            type_param_bindings,
            scope,
        )
        if fn.type_parameters:
            type_arguments_list = []
            for type_param in fn.type_parameters:
                type_arguments_list.append(
                    type_param_bindings.pop(type_param))
            assert not type_param_bindings, type_param_bindings
            type_arguments = tuple(type_arguments_list)
        else:
            type_arguments = None
        return ast.FunctionCall(
            mark=node.mark,
            type=return_type,
            function=fn,
            type_arguments=type_arguments,
            arguments=tuple(args),
        )


def _bind_param_type(param_type, arg_type, type_param_bindings, scope):
    if isinstance(param_type, ast.TypeParameter):
        if param_type in type_param_bindings:
            real_param_type = type_param_bindings[param_type]
            if arg_type is not None and real_param_type != arg_type:
                raise scope.error(
                    f'binding {arg_type} to {param_type} failed '
                    f'({type_param_bindings})')
            return real_param_type
        else:
            type_param_bindings[param_type] = arg_type
            return arg_type
    elif isinstance(param_type, ast.ReifiedType):
        if (isinstance(arg_type, ast.ReifiedType) and
                param_type.class_ == arg_type.class_ and
                len(param_type.type_arguments) ==
                    len(arg_type.type_arguments)):
            type_arguments = tuple(
                _bind_param_type(p, a, type_param_bindings, scope)
                for p, a in zip(
                    param_type.type_arguments,
                    arg_type.type_arguments,
                )
            )
            return ast.ReifiedType(
                mark=param_type.mark,
                class_=param_type.class_,
                type_arguments=type_arguments,
            )
    else:
        if arg_type is None or param_type == arg_type:
            return param_type
        else:
            raise scope.error(
                f'binding {arg_type} to {param_type} failed '
                f'({type_param_bindings})'
            )


def _convert_type(type_, expr):
    if expr.type.usable_as(type_):
        return expr


def _expect_type(type_, expr):
    result = _convert_type(type_, expr)
    if result is None:
        with scope.push_mark(expr.mark):
            raise scope.error(f'Expected {type_} here')
    return result


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
    int main() = {
        print("Hello world!")
        0
    }
    """)

    @test.throws(errors.KeyError)
    def duplicate_class():
        load(r"""
        class Foo {}
        class Foo {}
        """)
