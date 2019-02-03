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


def that(x):
    if not x:
        raise AssertionError(f'Assertion failed')


def run_tests(pkg):
    all_tests_count = 0
    failed_tests_count = 0
    passed_tests_count = 0
    module_names = module_finder.find(pkg)
    failing_modules = []
    for module_name in module_names:
        importlib.import_module(module_name)
    for module_name in module_names:
        tests = _tests_table[module_name]
        sys.stdout.write(f'testing {module_name}...')
        has_failing_test = False
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
                    failed_tests_count += 1
                    has_failing_test = True
        else:
            sys.stdout.write(f' no tests\n')
        if has_failing_test:
            failing_modules.append(module_name)
    assert passed_tests_count + failed_tests_count == all_tests_count, (
        passed_tests_count,
        failed_tests_count,
        all_tests_count,
    )
    if failed_tests_count == 0:
        print(f'All tests pass! (of {all_tests_count})')
        return 0
    else:
        print(f'{failed_tests_count} failed of {all_tests_count}')
        return 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pkg', default='mtots', nargs='?')
    args = parser.parse_args()
    sys.exit(run_tests(args.pkg))


if __name__ == '__main__':
    from mtots import test
    test.main()

