"""
Utility for testing code in mtots
"""
import argparse
import collections
import importlib
import traceback
import inspect
import os
import sys
from . import module_finder


_tests_table = collections.defaultdict(lambda: [])


def case(f):
    module = inspect.getmodule(f)
    module_name = module.__name__
    _tests_table[module_name].append(f)


def equal(a, b):
    if not (a == b):
        raise AssertionError(f'Expected {a} to equal {b}')


def that(x, message='Assertion failed'):
    if not x:
        raise AssertionError(message)


def throws(exc_type, message=None):
    def wrapper(f):
        try:
            f()
        except exc_type as e:
            if message is not None:
                actual_message = str(e)
        else:
            raise AssertionError(f'Expected {exc_type} to be thrown')
        equal(message, actual_message)
    return wrapper

def run_tests(pkg):
    all_tests_count = 0
    all_modules_count = 0
    passed_tests_count = 0
    module_names = module_finder.find(pkg)
    failed_tests = []
    failed_imports = []
    for module_name in module_names:
        all_modules_count += 1
        tests = _tests_table[module_name]
        sys.stdout.write(f'testing {module_name}...')
        try:
            importlib.import_module(module_name)
        except BaseException as e:
            sys.stdout.write(f' IMPORT FAILED\n')
            traceback.print_exc()
            failed_imports.append(module_name)
            continue
        if tests:
            sys.stdout.write('\n')
            for test in tests:
                sys.stdout.write(f'  {test.__name__} ')
                all_tests_count += 1
                try:
                    test()
                    sys.stdout.write(f'PASS\n')
                    passed_tests_count += 1
                except BaseException as e:
                    traceback.print_exc()
                    sys.stdout.write(f'FAIL\n')
                    failed_tests.append(f'{module_name}.{test.__name__}')
        else:
            sys.stdout.write(f' no tests\n')
    failed_tests_count = len(failed_tests)
    assert passed_tests_count + failed_tests_count == all_tests_count, (
        passed_tests_count,
        failed_tests_count,
        all_tests_count,
    )
    assert all_modules_count == len(module_names), (
        all_modules_count,
        len(module_names),
    )
    passed_imports_count = all_modules_count - len(failed_imports)
    print(f'{passed_imports_count}/{all_modules_count} imports succeeded')
    print(f'{passed_tests_count}/{all_tests_count} tests passed')
    if failed_tests or failed_imports:
        if failed_imports:
            print(
                f'The following {len(failed_imports)} modules '
                f'could not be imported'
            )
            for module_name in failed_imports:
                print(f'  {module_name}')
        if failed_tests:
            print(f'The following {len(failed_tests)} tests failed')
            for test_name in failed_tests:
                print(f'  {test_name}')
        return 1
    else:
        print('All tests pass!')
        return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pkg', default='mtots', nargs='?')
    args = parser.parse_args()
    sys.exit(run_tests(args.pkg))


if __name__ == '__main__':
    from mtots import test
    test.main()

