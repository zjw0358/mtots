from . import ast
from . import cst
from . import errors
from . import lexer
from . import parser
from .scopes import Scope
from .ast import apply_reified_bindings
from .ast import get_reified_bindings
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
            import_path = stmt.module
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
    global_scope['@after_resolve_types_callbacks'] = []
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
    for callback in global_scope['@after_resolve_types_callbacks']:
        callback()
    global_scope.table.pop('@after_resolve_types_callbacks')
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

    @on(cst.Import)
    def r(node, scope):
        full_name = f'{node.module}.{node.name}'
        with scope.push_mark(node.mark):
            imported_node = scope.root[full_name]
        alias = node.name if node.alias is None else node.alias
        scope[alias] = imported_node

    @on(cst.Inline)
    def r(node, scope):
        short_name = node.name
        full_name = scope['@prefix'] + short_name
        inline = ast.Inline(
            mark=node.mark,
            name=full_name,
            type=node.type,
            text=node.text,
        )
        with scope.push_mark(node.mark):
            scope[short_name] = inline
            scope.root[full_name] = inline

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
            inheritable=node.is_trait,
            name=full_name,
            base=None,
            type_parameters=None,
            generic=node.type_parameters is not None,
            own_fields=None,
            all_fields=None,
            own_methods=None,
            all_methods=None,
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

    @on(cst.Import)
    def r(node, scope):
        pass

    @on(cst.Inline)
    def r(node, scope):
        pass

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
        class_.own_fields = _compute_own_fields(node.fields, cscope)
        class_.all_fields = _compute_all_fields(class_, cscope)
        class_.own_methods = _compute_own_methods(
            node.methods,
            cscope,
            class_is_native=class_.native,
        )
        class_.all_methods = _compute_all_methods(class_, cscope)
        for members_map in [class_.all_fields, class_.all_methods]:
            for key, member in members_map.items():
                with cscope.push_mark(member.mark):
                    cscope[key] = member

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
                base = scope.root[OBJECT]
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
        if base is not None and not base.inheritable:
            with scope.push_mark(class_.mark, base.mark):
                raise scope.error(
                    f'{base.name} is not a trait class '
                    f'(you can only inherit from traits)')
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

    def _compute_own_fields(cst_fields, scope):
        field_map = {}
        for cst_field in cst_fields:
            field = ast.Field(
                mark=cst_field.mark,
                name=cst_field.name,
                type=_eval_type(cst_field.type, scope),
            )
            field_map[field.name] = field
        return field_map

    def _compute_all_fields(class_, scope):
        field_map = {}
        if class_.base is not None:
            field_map.update(class_.base.all_fields)
        for key, field in class_.own_fields.items():
            if key in field_map:
                with scope.push_mark(field_map[key].mark, field.mark):
                    raise scope.error(f'Field {key} is already inherited')
            field_map[key] = field
        return field_map

    def _compute_own_methods(cst_methods, cscope, class_is_native):
        method_map = {}
        for cst_method in cst_methods:
            mscope = Scope(cscope)
            return_type = _eval_type(cst_method.return_type, cscope)
            parameters = _compute_parameters(cst_method.parameters, mscope)
            method = ast.Method(
                cst=cst_method,
                scope=mscope,
                mark=cst_method.mark,
                abstract=cst_method.abstract,
                return_type=return_type,
                name=cst_method.name,
                parameters=parameters,
                body=None,
            )
            method_map[method.name] = method
        return method_map

    def _compute_all_methods(class_, cscope):
        method_map = {}
        base_method_map = {}
        if class_.base is not None:
            base_method_map.update(class_.base.all_methods)
            method_map.update(base_method_map)
        for key, method in class_.own_methods.items():
            if key in base_method_map:
                base_method = base_method_map[key]
                if not _method_signatures_match(base_method, method):
                    with cscope.push_mark(method.mark, base_method.mark):
                        raise cscope.error(
                            f'Overriding method has mismatched signature')
            method_map[key] = method
        return method_map

    def _method_signatures_match(method_a, method_b):
        return (
            method_a.return_type == method_b.return_type and
            method_a.parameters == method_b.parameters
        )


@util.multimethod(1)
def _resolve_expressions(on):

    @on(cst.File)
    def r(node, scope):
        for stmt in node.statements:
            _resolve_expressions(stmt, scope)

    @on(cst.Import)
    def r(node, scope):
        pass

    @on(cst.Inline)
    def r(node, scope):
        pass

    @on(cst.Class)
    def r(node, outer_scope):
        class_ = outer_scope[node.name]
        for method in class_.own_methods.values():
            mscope = method.scope
            if method.cst.body is not None:
                method.body = _expect_type(
                    type_=method.return_type,
                    expr=_eval_expression(method.cst.body, mscope),
                    scope=mscope,
                )

            if class_.native and method.body:
                with mscope.push_mark(method.mark):
                    raise mscope.error(
                        f'Methods of native classes cannot have bodies')

            if method.abstract and method.body:
                with mscope.push_mark(method.mark):
                    raise mscope.error(
                        f'Abstract methods cannot have bodies')

            if not method.abstract and not class_.native and not method.body:
                with mscope.push_mark(method.mark):
                    raise mscope.error(
                        f'Normal method is missing body '
                        f'(declare "abstract" to make metho abstract)')

    @on(cst.Function)
    def r(node, outer_scope):
        function = outer_scope[node.name]
        fscope = function.scope
        assert fscope.parent is outer_scope
        if node.body is not None:
            function.body = _expect_type(
                type_=function.return_type,
                expr=_eval_expression(node.body, fscope),
                scope=fscope,
            )

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
        if not isinstance(decl, ast.BaseVariableDeclaration):
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
            if isinstance(exprs[-1], ast.LocalVariableDeclaration):
                with outer_scope.push_mark(exprs[-1].mark):
                    raise outer_scope.error(
                        'Useless variable declaration at end of block')
            type_ = exprs[-1].type
        else:
            type_ = ast.VOID
        return ast.Block(
            mark=node.mark,
            type=type_,
            expressions=exprs,
        )

    @on(cst.LocalVariableDeclaration)
    def r(node, scope):
        expr = _eval_expression(node.expression, scope)
        if node.type is None:
            vartype = expr.type
        else:
            vartype = _eval_type(node.type, scope)
            expr = _expect_type(vartype, expr, scope)

        decl = ast.LocalVariableDeclaration(
            mark=node.mark,
            mutable=bool(node.type),
            name=node.name,
            type=vartype,
            expression=expr,
        )
        scope[decl.name] = decl
        return decl

    @on(cst.New)
    def r(node, scope):
        type_ = _eval_type(node.type, scope)
        if not isinstance(type_, (ast.Class, ast.ReifiedType)):
            with scope.push_mark(node.mark):
                raise scope.error(f'You can only new Class types')

        if isinstance(type_, ast.ReifiedType):
            class_ = type_.class_
        else:
            class_ = type_

        if class_.inheritable:
            with scope.push_mark(node.mark, class_.mark):
                raise scope.error(f'Traits cannot be instantiated')

        return ast.New(
            mark=node.mark,
            type=type_,
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

        raw_args = [_eval_expression(arg, scope) for arg in node.arguments]

        if fn.generic:
            if node.type_arguments is None:
                type_arguments = tuple(_deduce_type_arguments(
                    type_parameters=fn.type_parameters,
                    parameters=fn.parameters,
                    raw_args=raw_args,
                    scope=scope,
                ))
            else:
                type_arguments = tuple(
                    _eval_type(t, scope) for t in node.type_arguments
                )

            generic_bindings = get_reified_bindings(
                type_parameters=fn.type_parameters,
                type_arguments=type_arguments,
            )
        else:
            if node.type_arguments is None:
                type_arguments = None
            else:
                with scope.push_mark(node.mark, fn.mark):
                    raise scope.error(
                        f'{node.name} is not a generic function')

        args = []
        for param, raw_arg in zip(fn.parameters, raw_args):
            if fn.generic:
                param_type = apply_reified_bindings(
                    type=param.type,
                    bindings=generic_bindings,
                )
            else:
                param_type = param.type
            arg = _convert_type(param_type, raw_arg)
            if arg is None:
                with scope.push_mark(raw_arg.mark, param.mark):
                    raise scope.error(
                        f'Expected parameter {repr(param.name)} '
                        f'to be type {param_type} but got {raw_arg.type}')
            args.append(arg)

        if fn.generic:
            return_type = apply_reified_bindings(
                type=fn.return_type,
                bindings=generic_bindings,
            )
        else:
            return_type = fn.return_type

        return ast.FunctionCall(
            mark=node.mark,
            type=return_type,
            function=fn,
            type_arguments=type_arguments,
            arguments=tuple(args),
        )

    @on(cst.MethodCall)
    def r(node, scope):
        owner = _eval_expression(node.owner, scope)
        all_methods = owner.type.all_methods
        if node.name not in all_methods:
            with scope.push_mark(node.mark):
                raise scope.error(
                    f'No such method {node.name} on {owner.type}')
        method = all_methods[node.name]
        raw_args = [_eval_expression(arg, scope) for arg in node.arguments]
        args = []
        for param, raw_arg in zip(method.parameters, raw_args):
            arg = _convert_type(param.type, raw_arg)
            if arg is None:
                with scope.push_mark(raw_arg.mark, param.mark):
                    raise scope.error(
                        f'Expected parameter {repr(param.name)} '
                        f'to be type {param_type} but got {raw_arg.type}')
            args.append(arg)
        return ast.MethodCall(
            mark=node.mark,
            type=method.return_type,
            owner=owner,
            method=method,
            arguments=tuple(args),
        )

    def _unify_types(*, param_type, arg_type, bindings, scope):
        """Help deduce type parameters by looking at the type
        of the value argument types, and the unbound parameter types,
        and greedily binding type parameters.
        """
        if isinstance(param_type, ast.TypeParameter):
            if param_type in bindings:
                reified_param_type = bindings[param_type]
                if reified_param_type == arg_type:
                    return reified_param_type
            else:
                bindings[param_type] = arg_type
                return arg_type
        elif isinstance(param_type, ast.ReifiedType):
            if (isinstance(arg_type, ast.ReifiedType) and
                    param_type.class_ == arg_type.class_ and
                    len(param_type.type_arguments) ==
                        len(arg_type.type_arguments)):
                type_arguments = [
                    _unify_types(p, a, bindings, scope)
                    for p, a in zip(
                        param_type.type_arguments,
                        arg_type.type_arguments,
                    )
                ]
                return ast.ReifiedType(
                    mark=param_type.mark,
                    class_=param_type.class_,
                    type_arguments=type_arguments,
                )
        elif param_type == arg_type:
            return arg_type
        raise scope.error(
            f'binding {arg_type} to {param_type} failed '
            f'({bindings})')

    def _deduce_type_arguments(
            *, type_parameters, parameters, raw_args, scope):
        bindings = {}
        for param, raw_arg in zip(parameters, raw_args):
            _unify_types(
                param_type=param.type,
                arg_type=raw_arg.type,
                bindings=bindings,
                scope=scope,
            )
        type_args = []
        for type_param in type_parameters:
            type_args.append(bindings.pop(type_param))
        assert not bindings, bindings
        return type_args


def _convert_type(type_, expr):
    if expr.type.usable_as(type_):
        return expr
    if type_ == ast.VOID:
        return ast.Block(
            mark=expr.mark,
            type=ast.VOID,
            expressions=(
                expr,
                ast.Block(
                    mark=expr.mark,
                    type=ast.VOID,
                    expressions=(),
                ),
            ),
        )


def _expect_type(type_, expr, scope):
    result = _convert_type(type_, expr)
    if result is None:
        with scope.push_mark(expr.mark):
            raise scope.error(f'Expected {type_} here but got {expr.type}')
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

        type_arguments = tuple(
            _eval_type(e, scope)
            for e in node.type_arguments
        )

        reified_type = ast.ReifiedType(
            mark=node.mark,
            class_=class_,
            type_arguments=type_arguments,
        )

        def _validate_reified_type():
            # We play this callback dance because we need to sometimes
            # call _eval_type before all types have fully materialized.
            # E.g. class_.type_parameters might not be ready yet.
            # So for cases in which they aren't, we save the validation
            # code in a callback to be called at a later point
            # after all types have been fully resolved.
            for tparam, targ, cst_targ in zip(
                    class_.type_parameters,
                    type_arguments,
                    node.type_arguments):
                if (tparam.base is not None and
                        not targ.usable_as(tparam.base)):
                    with scope.push_mark(cst_targ.mark, tparam.mark):
                        raise scope.error(
                            f'{targ} is not usable as {tparam.base}')

        if '@after_resolve_types_callbacks' in scope.root.table:
            scope.root['@after_resolve_types_callbacks'].append(
                _validate_reified_type,
            )
        else:
            _validate_reified_type()

        return reified_type


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
