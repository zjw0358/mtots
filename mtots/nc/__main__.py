from . import cxx
from . import resolver
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(prog='mtots.text.nc')
    parser.add_argument('path')
    args = parser.parse_args()
    with open(args.path) as f:
        data = f.read()
    node = resolver.load(data, path=args.path)
    sys.stdout.write(f'{cxx.render(node)}')


if __name__ == '__main__':
    main()
