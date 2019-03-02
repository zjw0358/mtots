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
