from . import ast
from . import errors
from . import lexer
from . import types
from mtots import test
from mtots.text import base
from mtots.text.combinator import All
from mtots.text.combinator import Any
from mtots.text.combinator import AnyTokenBut
from mtots.text.combinator import Forward
from mtots.text.combinator import Peek
from mtots.text.combinator import Token
from mtots.util import Scope
import os
import typing


_source_root = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'root',
)


def _import_path_to_file_path(import_path):
    return os.path.join(
        _source_root,
        import_path.replace('.', os.path.sep) + '.nc',
    )

import_stmt = All(
    'import',
    All('ID', All('.', 'ID').map(lambda args: args[1]).repeat())
        .map(lambda args: '.'.join([args[0]] + args[1])),
    Any(
        All('as', 'ID').map(lambda args: args[1]),
        All().map(lambda x: None),
    ),
).fatmap(lambda m: ast.Import(
    mark=m.mark,
    name=m.value[1],
    alias=m.value[1].split('.')[-1] if m.value[2] is None else m.value[2],
))

_prelude_table = {
    symbol: f'{ast.PRELUDE}.{symbol}' for symbol in ast.PRELUDE_SYMBOLS
}

_builtin_mark = base.Mark(
    source=base.Source(
        path='<builtin>',
        data='',
    ),
    start=0,
    end=0,
)

_implicit_imports = tuple(
    ast.Import(
        mark=_builtin_mark,
        alias=key,
        name=value,
    )
    for key, value in _prelude_table.items()
)

_imports_only_parser = All(
    Any(import_stmt).repeat(),
    AnyTokenBut('EOF').repeat().map(lambda args: []),
).flatten().map(tuple)

native = Any('native').optional().map(bool)


def _parse_pattern(pattern, data, file_path, import_path):
    source = base.Source(data=data, path=file_path)
    tokens = lexer.lex(source)
    match_result = (
        All(pattern, Peek('EOF'))
            .map(lambda args: args[0])
            .parse(tokens)
    )
    if not match_result:
        raise match_result.to_error()
    return match_result.value


def _make_import_map(*, imports, module_name):
    all_imports = (
        imports
        if module_name == ast.PRELUDE else
        (_implicit_imports + imports)
    )
    return {imp.alias: imp.name for imp in all_imports}


def _make_importable_id(*, module_name, import_map):
    return Any('ID').map(lambda name:
        import_map.get(name, f'{module_name}.{name}'))


def _make_exportable_id(*, module_name, import_map):
    return Any('ID').map(lambda name: f'{module_name}.{name}')


def _make_module_parser(*, global_variable, function, class_, module_name):

    global_stmt = Any(
        global_variable.map(lambda x: ('var', x)),
        function.map(lambda x: ('func', x)),
        class_.map(lambda x: ('cls', x)),
    )

    module_pattern = All(
        import_stmt.map(lambda x: ('import', x)).repeat(),
        global_stmt.repeat(),
    ).flatten()

    def module_callback(m):
        imports = []
        vars = []
        funcs = []
        clss = []
        for kind, node in m.value:
            if kind == 'import':
                imports.append(node)
            elif kind == 'var':
                vars.append(node)
            elif kind == 'func':
                funcs.append(node)
            elif kind == 'cls':
                clss.append(node)
            else:
                raise base.Error([node.mark], f'FUBAR: {kind}: {node}')
        return ast.Module(
            mark=m.mark,
            name=module_name,
            imports=tuple(imports),
            vars=tuple(vars),
            funcs=tuple(funcs),
            clss=tuple(clss),
        )

    return module_pattern.fatmap(module_callback)


def _make_type_parser(*, importable_id, global_dict):

    def check_class_name(m):
        name = m.value
        if global_dict is not None:
            if name not in global_dict:
                raise base.Error(
                    [m.mark],
                    f'{repr(name)} is not defined',
                )
            if not isinstance(global_dict[name], ast.Class):
                raise base.Error(
                    [m.mark, global_dict[name].mark],
                    f'{repr(name)} is not a type',
                )
        return name

    return Any(
        Any('void').map(lambda x: types.VOID),
        Any('int').map(lambda x: types.INT),
        Any('double').map(lambda x: types.DOUBLE),
        importable_id.fatmap(check_class_name).map(types.ClassType),
    )


def _make_combined_parser(
        *,
        module_name,
        importable_id,
        exportable_id,
        type_,
        expression,
        block,
        global_dict,
        module_scope):

    # We can perform some basic validations if the global_dict
    # is available to us.
    validate = global_dict is not None

    global_variable = All(
        type_, exportable_id, '=', expression.required(), Any(';').required(),
    ).fatmap(lambda m: ast.GlobalVariable(
        mark=m.mark,
        type=m.value[0],
        name=m.value[1],
        expr=m.value[3] if global_dict is None else m.value[3](global_dict),
    ))

    parameter = All(type_, 'ID').fatmap(lambda m: ast.Parameter(
        mark=m.mark,
        type=m.value[0],
        name=m.value[1],
    ))

    parameters = All(
        '(',
        parameter.join(',').map(tuple),
        ')',
    ).map(lambda args: tuple(args[1]))

    ############
    # Function
    ############
    function_pattern = All(
        native,                           # 0: native
        type_,                            # 1: return type
        exportable_id,                    # 2: name
        parameters,                       # 3: parameters
        Any(
            block,
            Any(';').map(lambda x: None),
        ),                                # 4: body
    )

    def function_callback(m):
        native = m.value[0]
        rtype = m.value[1]
        name = m.value[2]
        params = m.value[3]
        body_thunk = m.value[4]

        if body_thunk is None:
            body = None
        else:
            scope = Scope(module_scope)
            for param in params:
                scope[param.name] = param
            body = body_thunk(scope)

        if validate:
            if native and body:
                raise base.Error(
                    [m.mark], 'Native functions cannot have a body')

            if not native and not body:
                raise base.Error(
                    [m.mark], 'Non-native functions must have a body')

        return ast.Function(
            mark=m.mark,
            rtype=rtype,
            name=name,
            params=params,
            body=body,
        )

    function = function_pattern.fatmap(function_callback)

    ############
    # Field
    ############

    field_thunk = (
        All(type_, 'ID', ';')
            .fatmap(lambda m: lambda scope: ast.Field(
                mark=m.mark,
                type=m.value[0],
                name=f'{scope["@class_name"]}.{m.value[1]}',
            ))
    )

    #################
    # Method (thunk)
    #################

    method_pattern = All(
        type_,                            # 0: return type
        'ID',                             # 1: name
        parameters,                       # 2: parameters
        Any(
            block,
            Any(';').map(lambda x: None),
        ),                                # 3: body
    )

    def method_callback(m):
        def inner_callback(outer_scope):
            scope = Scope(outer_scope)
            rtype = m.value[0]
            name = f'{scope["@class_name"]}#{m.value[1]}'
            params = m.value[2]
            body_thunk = m.value[3]
            if body_thunk is None:
                body = None
            else:
                for param in params:
                    scope[param.name] = param
                body = body_thunk(scope)
            return ast.Method(
                mark=m.mark,
                rtype=rtype,
                name=name,
                params=params,
                body=body,
            )
        return inner_callback

    method_thunk = method_pattern.fatmap(method_callback)

    ############
    # Class
    ############

    base_class = Any(
        All(':', importable_id).map(lambda args: args[1]),
        All().map(lambda args: None),
    )

    class_pattern = All(
        native,                  # 0: native
        'class',                 # 1
        exportable_id,           # 2: name
        base_class,              # 3: base/super class
        '{',                     # 4
        field_thunk.repeat(),    # 5: fields
        method_thunk.repeat(),   # 6: methods
        '}',                     # 7
    )

    def class_callback(m):
        native = m.value[0]
        class_name = m.value[2]
        declared_base = m.value[3]
        field_thunks = m.value[5]
        method_thunks = m.value[6]
        base = (
            ast.OBJECT
            if declared_base is None
                and class_name != ast.OBJECT else
            declared_base
        )
        scope = Scope(module_scope)
        scope['@class_name'] = class_name
        fields = tuple(ft(scope) for ft in field_thunks)
        methods = tuple(mt(scope) for mt in method_thunks)
        if validate:
            for method in methods:
                if native and method.body:
                    raise base.Error(
                        [m.mark, method.mark],
                        'Native classes cannot have method bodies',
                    )
                if not native and not method.body:
                    raise base.Error(
                        [m.mark, method.mark],
                        'Non-native classes cannot have native methods',
                    )
            if native and fields:
                raise base.Error(
                    [m.mark, fields[0].mark],
                    'Native classes cannot have fields',
                )
        return ast.Class(
            mark=m.mark,
            native=native,
            name=class_name,
            base=base,
            fields=fields,
            methods=methods,
        )

    class_ = class_pattern.fatmap(class_callback)

    module = _make_module_parser(
        global_variable=global_variable,
        function=function,
        class_=class_,
        module_name=module_name,
    )

    return module


def _make_header_parser(
        module_name: str,
        imports: typing.Tuple[ast.Import, ...]):
    import_map = _make_import_map(imports=imports, module_name=module_name)
    importable_id = _make_importable_id(
        module_name=module_name,
        import_map=import_map,
    )
    exportable_id = _make_exportable_id(
        module_name=module_name,
        import_map=import_map,
    )

    type_ = _make_type_parser(
        importable_id=importable_id,
        global_dict=None,
    )

    # for any statement or expression we want to skip over.
    blob = Forward(lambda: Any(
        AnyTokenBut('{', '}', '(', ')', ';', ','),
        All('(', blob.repeat(), ')'),
        brace_blob,
    ))
    inner_blob = Forward(lambda: Any(
        AnyTokenBut('{', '}'),
        brace_blob,
    ))
    brace_blob = All('{', inner_blob.repeat(), '}')

    return _make_combined_parser(
        module_name=module_name,
        importable_id=importable_id,
        exportable_id=exportable_id,
        type_=type_,
        expression=blob.repeat().map(lambda x: None),
        block=brace_blob.map(lambda x: None),
        global_dict=None,
        module_scope=None,
    )


_header_cache = {}


def load_header(import_path):
    if import_path not in _header_cache:
        file_path = _import_path_to_file_path(import_path)
        _header_cache[import_path] = parse_header_file(
            file_path=file_path,
            import_path=import_path,
        )
    return _header_cache[import_path]


def parse_header_file(file_path, import_path='MAIN'):
    with open(file_path) as f:
        data = f.read()
    return parse_header(
        data=data,
        file_path=file_path,
        import_path=import_path,
    )


def _parse_imports(data, file_path, import_path):
    return _parse_pattern(
        pattern=_imports_only_parser,
        data=data,
        file_path=file_path,
        import_path=import_path,
    )


def parse_header(data, file_path='<string>', import_path='MAIN'):
    imports = _parse_imports(
        data=data,
        file_path=file_path,
        import_path=import_path,
    )
    return _parse_pattern(
        pattern=_make_header_parser(
            module_name=import_path,
            imports=imports,
        ),
        data=data,
        file_path=file_path,
        import_path=import_path,
    )


def _get_all_globals_without_prelude(header: ast.Module, global_dict):
    if header.name not in global_dict['@modules']:
        for imp in header.imports:
            _get_all_globals_without_prelude(
                load_header(imp.module), global_dict)
        for node in header.vars + header.funcs + header.clss:
            if node.name in global_dict:
                raise base.Error(
                    [node.mark, global_dict[node.name].mark],
                    f'Duplicate definition of {node.name}',
                )
            global_dict[node.name] = node
        global_dict['@modules'].add(header.name)
    return global_dict


def _get_all_globals(header: ast.Module):
    global_dict = {
        '@modules': set(),
    }
    _get_all_globals_without_prelude(load_header(ast.PRELUDE), global_dict)
    _get_all_globals_without_prelude(header, global_dict)
    return global_dict


def _make_source_parser(module_name: str, header: ast.Module, global_dict):

    def ensure_global_exists(m):
        name = m.value
        if name not in global_dict:
            raise base.Error([m.mark], f'Name {repr(name)} does not exist')
        return name

    import_map = _make_import_map(
        imports=header.imports,
        module_name=module_name,
    )
    importable_id = _make_importable_id(
        module_name=module_name,
        import_map=import_map,
    ).fatmap(ensure_global_exists)
    exportable_id = _make_exportable_id(
        module_name=module_name,
        import_map=import_map,
    ).fatmap(ensure_global_exists)

    type_ = _make_type_parser(
        importable_id=importable_id,
        global_dict=global_dict,
    )

    module_scope = {
        key: global_dict[val]
        for key, val in _prelude_table.items()
    }
    for imp in header.imports:
        if imp.name in global_dict:
            module_scope[imp.name] = global_dict[imp.name]
        else:
            raise base.Error(
                [imp.mark],
                f'{repr(imp.name)} is not defined',
            )

    def get_func_def(scope, name, mark):
        if name not in scope:
            raise base.Error([mark], f'{name} is not defined')
        if not isinstance(scope[name], ast.Function):
            raise base.Error(
                [scope[name].mark, mark], f'{name} is not a function')
        return scope[name]

    def fcall(mark, f, args):
        if len(f.params) != len(args):
            raise base.Error(
                [f.mark, mark],
                f'Expected {len(f.params)} args but got {len(args)}')
        for param, arg in zip(f.params, args):
            if not types.convertible(arg.type, param.type, global_dict):
                raise base.Error(
                    [param.mark, arg.mark],
                    f'Expected type {param.type} but got {arg.type}')
        return ast.FunctionCall(mark=mark, f=f, args=args)

    # TODO
    expression = Forward(lambda: atom)
    args = All(
        '(',
        expression.join(',').fatmap(lambda m: lambda scope:
            tuple(e(scope) for e in m.value)),
        Any(')').required(),
    ).map(lambda args: args[1])
    atom = Any(
        Any('INT').fatmap(lambda m: lambda scope: ast.IntLiteral(
            mark=m.mark,
            value=m.value
        )),
        Any('STR').fatmap(lambda m: lambda scope: ast.StringLiteral(
            mark=m.mark,
            value=m.value,
        )),
        All('ID', args).fatmap(lambda m: lambda scope:
            fcall(
                mark=m.mark,
                f=get_func_def(scope=scope, name=m.value[0], mark=m.mark),
                args=m.value[1](scope),
            ),
        ),
    )
    statement = Forward(lambda: Any(
        block,
        All('return', expression, ';').fatmap(lambda m: lambda scope:
            ast.Return(
                mark=m.mark,
                expr=m.value[1](scope),
            ),
        ),
        All(expression, ';').fatmap(lambda m: lambda scope:
            ast.ExpressionStatement(
                mark=m.mark,
                expr=m.value[0](scope),
            )
        ),
    ))
    block = (
        All('{', statement.repeat(), Any('}').required())
            .fatmap(lambda m: lambda scope: ast.Block(
                mark=m.mark,
                stmts=tuple(stmt(scope) for stmt in m.value[1]),
            ))
    )

    return _make_combined_parser(
        module_name=module_name,
        importable_id=importable_id,
        exportable_id=exportable_id,
        type_=type_,
        expression=expression,
        block=block,
        global_dict=global_dict,
        module_scope=module_scope,
    )


def _parse_source(
        data,
        *,
        global_dict,
        header,
        file_path='<string>',
        import_path='MAIN'):
    return _parse_pattern(
        pattern=_make_source_parser(
            module_name=import_path,
            header=header,
            global_dict=global_dict,
        ),
        data=data,
        file_path=file_path,
        import_path=import_path,
    )


def _load_source(import_path, *, global_dict):
    header = load_header(import_path)
    data = header.mark.source.data
    file_path = header.mark.source.path
    return _parse_source(
        data=data,
        file_path=file_path,
        import_path=import_path,
        header=header,
        global_dict=global_dict,
    )


def parse(data, file_path='<string>'):
    module_names = {'MAIN', ast.PRELUDE}
    queue = list(_parse_imports(
        data=data,
        file_path=file_path,
        import_path='MAIN',
    ))
    while queue:
        module_name = queue.pop().module
        if module_name not in module_names:
            module_names.add(module_name)
            queue.extend(load_header(module_name).imports)
    header = parse_header(data, file_path=file_path)
    global_dict = _get_all_globals(header=header)
    return {
        module_name:
            _parse_source(
                data,
                header=header,
                file_path=file_path,
                global_dict=global_dict)
            if module_name == 'MAIN' else
            _load_source(module_name, global_dict=global_dict)
        for module_name in module_names
    }


print(parse("""
import stdio.File

int x = 10;

int main() {
    print("Hello world!");
    return 0;
}

class Foo {
    int foo() {
        return 0;
    }
}

"""))


