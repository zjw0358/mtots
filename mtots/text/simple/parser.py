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


def _make_import_map(imports):
    return {imp.alias: imp.name for imp in imports}


def _make_importable_id(*, module_name, import_map):
    return Any('ID').map(lambda name:
        import_map.get(name, f'{module_name}.{name}'))


def _make_exportable_id(*, module_name, import_map):
    return Any('ID').map(lambda name: f'{module_name}.{name}')


def _make_func_parser(
        *,
        constructor,
        type_,
        func_name,
        parameters,
        block,
        module_scope,
        ):

    def handler(mark, native, rtype, name, params, body):
        if module_scope:
            if native and body is not None:
                raise base.Error(
                    [mark], 'native functions should not have a body')
            if not native and body is None:
                raise base.Error(
                    [mark], 'only native functions can have missing body')
        return constructor(
            mark=mark,
            rtype=rtype,
            name=name,
            params=params,
            body=body,
        )

    parser = All(
        native, type_, func_name, parameters, Any(
            block,
            Any(';').map(lambda x: None),
        ),
    ).fatmap(lambda m: handler(
        mark=m.mark,
        native=m.value[0],
        rtype=m.value[1],
        name=m.value[2],
        params=m.value[3],
        body=m.value[4],
    ))

    if module_scope is not None:
        def callback(m):
            if m.value.body is None:
                return m.value
            else:
                scope = Scope(module_scope)
                for param in m.value.params:
                    scope[param.name] = param
                return constructor(
                    mark=m.value.mark,
                    rtype=m.value.rtype,
                    name=m.value.name,
                    params=m.value.params,
                    body=m.value.body(scope),
                )

        parser = parser.fatmap(callback)

    return parser


def _make_field_parser(*, type_):
    return All(type_, 'ID', ';').fatmap(lambda m: ast.Field(
        mark=m.mark,
        type=m.value[0],
        name=m.value[1],
    ))


def _make_class_parser(*, exportable_id, base_class, field, method):
    return All(
        native,            # 0: native
        'class',           # 1
        exportable_id,     # 2: name
        base_class,        # 3: base/super class
        '{',               # 4
        field.repeat(),    # 5: fields
        method.repeat(),   # 6: methods
        '}',               # 7
    ).fatmap(lambda m: ast.Class(
        mark=m.mark,
        native=m.value[0],
        name=m.value[2],
        base=m.value[3],
        fields=tuple(m.value[5]),
        methods=tuple(m.value[6]),
    ))



def _make_module_parser(*, global_variable, function, class_, module_name):
    return All(
        import_stmt.repeat().map(tuple),
        global_variable.repeat().map(tuple),
        function.repeat().map(tuple),
        class_.repeat().map(tuple),
    ).fatmap(lambda m: ast.Module(
        mark=m.mark,
        name=module_name,
        imports=m.value[0],
        vars=m.value[1],
        funcs=m.value[2],
        clss=m.value[3],
    ))


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

    function = _make_func_parser(
        constructor=ast.Function,
        type_=type_,
        func_name=exportable_id,
        parameters=parameters,
        block=block,
        module_scope=module_scope,
    )

    field = _make_field_parser(type_=type_)

    method = _make_func_parser(
        constructor=ast.Method,
        type_=type_,
        func_name='ID',
        parameters=parameters,
        block=block,
        module_scope=module_scope,
    )

    base_class = Any(
        All(':', importable_id).map(lambda args: args[1]),
        All().map(lambda args: None),
    )

    class_ = All(
        native,            # 0: native
        'class',           # 1
        exportable_id,     # 2: name
        base_class,        # 3: base/super class
        '{',               # 4
        field.repeat(),    # 5: fields
        method.repeat(),   # 6: methods
        '}',               # 7
    ).fatmap(lambda m: ast.Class(
        mark=m.mark,
        native=m.value[0],
        name=m.value[2],
        base=
            'lang.Object'
            if m.value[3] is None and m.value[2] != 'lang.Object' else
            m.value[3],
        fields=tuple(m.value[5]),
        methods=tuple(m.value[6]),
    ))

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
    import_map = _make_import_map(imports)
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


def _get_all_globals(header: ast.Module, global_dict=None):
    global_dict = {
        '@modules': set(),
    } if global_dict is None else global_dict

    if header.name != 'lang' and 'lang' not in global_dict['@modules']:
        _get_all_globals(load_header('lang'), global_dict)

    if header.name not in global_dict['@modules']:
        for imp in header.imports:
            _get_all_globals(load_header(imp.module), global_dict)
        for node in header.vars + header.funcs + header.clss:
            if node.name in global_dict:
                raise base.Error(
                    [node.mark, global_dict[node.name].mark],
                    f'Duplicate definition of {node.name}',
                )
            global_dict[node.name] = node
        global_dict['@modules'].add(header.name)
    return global_dict


def _make_source_parser(module_name: str, header: ast.Module, global_dict):

    def ensure_global_exists(m):
        name = m.value
        if name not in global_dict:
            raise base.Error([m.mark], f'Name {repr(name)} does not exist')
        return name

    import_map = _make_import_map(header.imports)
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

    lang_table = {
        'String': 'lang.String',
        'print': 'lang.print',
    }

    module_scope = {key: global_dict[val] for key, val in lang_table.items()}
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
    module_names = {'MAIN'}
    queue = list(_parse_imports(
        data=data,
        file_path=file_path,
        import_path='MAIN',
    )) + [ast.Import(mark=None, name='lang.String', alias='String')]
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


