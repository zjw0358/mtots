from . import ast
from . import c
from . import parser
import argparse
import os
import shutil


GENERATED_C_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'generated',
)


def _gen_triples(root_imports, *, main_file_path):
    """Generate triples of (import_path, header, source)
    for sources that need to be generated.
    """
    stack = list(root_imports)
    added = set(stack)

    while stack:
        import_path = stack.pop()

        if import_path == parser.MAIN_IMPORT_PATH:
            source = parser.parse_source_file(
                file_path=main_file_path,
                import_path=parser.MAIN_IMPORT_PATH,
            )
            header = parser.parse_header_file(
                file_path=main_file_path,
                import_path=parser.MAIN_IMPORT_PATH,
            )
        else:
            source = parser.load_source(import_path)
            header = parser.load_header(import_path)

        yield import_path, header, source

        for imp in source.imports:
            if isinstance(imp, ast.AbsoluteImport) and imp.path not in added:
                added.add(imp.path)
                stack.append(imp.path)


def _write_out_c_files(triples, *, debug_info):

    shutil.rmtree(GENERATED_C_DIR, ignore_errors=True)
    os.mkdir(GENERATED_C_DIR)

    for import_path, header, source in triples:
        forward_path = c.forward_path_from_import_path(import_path)
        header_path = c.header_path_from_import_path(import_path)
        source_path = c.source_path_from_import_path(import_path)
        full_forward_path = os.path.join(GENERATED_C_DIR, forward_path)
        full_header_path = os.path.join(GENERATED_C_DIR, header_path)
        full_source_path = os.path.join(GENERATED_C_DIR, source_path)

        c_forward_data = c.gen_forward(header)
        with open(full_forward_path, 'w') as f:
            f.write(c_forward_data)

        c_header_data = c.gen_header(header)
        with open(full_header_path, 'w') as f:
            f.write(c_header_data)

        c_source_data = c.gen_source(source, debug_info=debug_info)
        with open(full_source_path, 'w') as f:
            f.write(c_source_data)


def _make_c_blob(triples, *, debug_info):
    imports = set()
    inc = []
    fwd = []
    hdr = []
    src = []

    for import_path, header, source in triples:
        imports.update(source.imports)
        fwd.append(c.gen_forward(header, includes=False))
        hdr.append(c.gen_header(header, includes=False))
        src.append(c.gen_source(
            source,
            includes=False,
            debug_info=debug_info,
        ))

    for imp in imports:
        if isinstance(imp, ast.AngleBracketImport):
            inc.append(f'#include <{imp.path}>\n')
        elif isinstance(imp, ast.QuoteImport):
            inc.append(f'#include "{imp.path}"\n')

    return ''.join(map(''.join, [inc, fwd, hdr, src]))


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('main_file_path')
    argparser.add_argument(
        '--blob',
        '-b',
        action='store_true',
        default=False,
    )
    argparser.add_argument(
        '--no-debug-info',
        action='store_false',
        dest='debug_info',
        default=True,
    )

    args = argparser.parse_args()

    main_file_path = args.main_file_path

    triples = _gen_triples(
        root_imports=[parser.MAIN_IMPORT_PATH],
        main_file_path=main_file_path,
    )

    if args.blob:
        print(_make_c_blob(triples, debug_info=args.debug_info))
    else:
        _write_out_c_files(triples, debug_info=args.debug_info)


if __name__ == '__main__':
    main()
