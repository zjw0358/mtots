"""
Utility for testing code in mtots
"""
from . import module_finder
import argparse
import collections
import importlib
import inspect
import os
import sys
import time
import traceback


_tests_table = collections.defaultdict(lambda: [])

_slow_tests = set()


def case(f, slow=False):
    module = inspect.getmodule(f)
    module_name = module.__name__
    _tests_table[module_name].append(f)
    if slow:
        _slow_tests.add(f)


def slow(f):
    return case(f, slow=True)


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
        if message is not None:
            equal(message, actual_message)
    return wrapper

def run_tests(pkg, run_slow_tests=False):
    all_tests_count = 0
    all_modules_count = 0
    passed_tests_count = 0
    skipped_tests_count = 0
    module_names = module_finder.find(pkg)
    failed_tests = []
    failed_imports = []
    test_duration_table = {}
    all_tests_start_time = time.time()
    for module_name in module_names:
        all_modules_count += 1
        tests = _tests_table[module_name]
        sys.stdout.write(f'testing {module_name}...')
        try:
            import_start_time = time.time()
            importlib.import_module(module_name)
            import_end_time = time.time()
            import_duration = import_end_time - import_start_time
            sys.stdout.write(
                f' (import: {format(import_duration, ".2f")}s)',
            )
        except BaseException as e:
            sys.stdout.write(f' IMPORT FAILED\n')
            traceback.print_exc()
            failed_imports.append(module_name)
            continue
        if tests:
            sys.stdout.write('\n')
            for test in tests:
                full_test_name = f'{module_name}.{test.__name__}'
                sys.stdout.write(f'  {test.__name__} ')
                if not run_slow_tests and test in _slow_tests:
                    sys.stdout.write('SKIP (skipping slow test)\n')
                    skipped_tests_count += 1
                    continue
                all_tests_count += 1
                try:
                    test_start_time = time.time()
                    test()
                    test_end_time = time.time()
                    test_duration = test_end_time - test_start_time
                    sys.stdout.write(
                        f'PASS ({format(test_duration, ".2f")}s)\n',
                    )
                    passed_tests_count += 1
                    test_duration_table[full_test_name] = test_duration
                except BaseException as e:
                    traceback.print_exc()
                    sys.stdout.write(f'FAIL\n')
                    failed_tests.append(full_test_name)
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
    all_tests_end_time = time.time()
    all_tests_duration = all_tests_end_time - all_tests_start_time
    tests_by_duration = sorted(
        test_duration_table,
        key=lambda test: test_duration_table[test],
        reverse=True,
    )
    print(f'10 slowest running tests:')
    for test_name in tests_by_duration[:10]:
        formatted_duration = format(test_duration_table[test_name], '.2f')
        print(f'  {test_name.ljust(50)} {formatted_duration.rjust(20)}s')
    print(f'All tests took {format(all_tests_duration, ".2f")}s')
    if not run_slow_tests:
        print(
            f'{skipped_tests_count} slow tests skipped '
            '(rerun with --all to run them)'
        )
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
    parser.add_argument(
        '--all',
        default=False,
        action='store_true',
        help='If set, also runs slow tests',
    )
    args = parser.parse_args()
    sys.exit(run_tests(args.pkg, run_slow_tests=args.all))


if __name__ == '__main__':
    from mtots import test
    test.main()

