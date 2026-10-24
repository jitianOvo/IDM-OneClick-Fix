# -*- coding: utf-8 -*-
import argparse
import sys

from . import fixer


def build_parser():
    parser = argparse.ArgumentParser(
        prog="idmfix",
        description="IDM one-click unlock and update lockdown",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("install", help="apply the patch (default)")
    sub.add_parser("status", help="show current state")
    return parser


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        argv = ["install"]
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "status":
        return fixer.status()
    return fixer.install()


if __name__ == "__main__":
    sys.exit(main())