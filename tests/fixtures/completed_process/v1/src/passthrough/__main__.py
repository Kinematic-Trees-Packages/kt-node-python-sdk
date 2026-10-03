from __future__ import annotations

import argparse

from ktnode import run

from .robot import Robot


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the completed Python acceptance fixture")
    parser.add_argument("--package", required=True)
    parser.add_argument("--runtime", required=True)
    args = parser.parse_args()
    run(args.package, args.runtime, Robot())


if __name__ == "__main__":
    main()
