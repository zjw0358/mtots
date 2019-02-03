"""
mtots module finder.
Finds all modules under a particular package in mtots.
We can't really write tests for this because the testing
mechanism depends on this module.
"""
import os


mtots_dir = os.path.dirname(os.path.realpath(__file__))


def _find_modules(*, pkg, path):
    if os.path.isfile(path + '.py'):
        yield pkg
    elif os.path.isdir(path):
        for name in os.listdir(path):
            if name.startswith(('.', '_')):
                continue

            if name.endswith('.py'):
                basename = name[:-len('.py')]
            else:
                basename = name

            if '.' in basename:
                continue

            yield from _find_modules(
                pkg=f'{pkg}.{basename}',
                path=os.path.join(path, basename),
            )


def _find_mtots_modules_iter(pkg):
    if pkg == 'mtots':
        yield from _find_modules(pkg=pkg, path=mtots_dir)
    elif pkg.startswith('mtots.'):
        relpath = pkg[len('mtots.'):].replace('.', os.path.sep)
        abspath = os.path.join(mtots_dir, relpath)
        yield from _find_modules(pkg=pkg, path=abspath)
    else:
        raise TypeError(f'Expected a pkg under mtots but got {pkg}')


def find(pkg):
    return tuple(sorted(_find_mtots_modules_iter(pkg)))
