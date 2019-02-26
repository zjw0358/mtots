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


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('main_file_path')

    args = argparser.parse_args()

    main_file_path = args.main_file_path

    stack = [parser.MAIN_IMPORT_PATH]
    added = {parser.MAIN_IMPORT_PATH}

    shutil.rmtree(GENERATED_C_DIR, ignore_errors=True)
    os.mkdir(GENERATED_C_DIR)

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

        c_source_data = c.gen_source(source)
        with open(full_source_path, 'w') as f:
            f.write(c_source_data)

        for imp in source.imports:
            if isinstance(imp, ast.AbsoluteImport) and imp.path not in added:
                added.add(imp.path)
                stack.append(imp.path)



if __name__ == '__main__':
    main()
