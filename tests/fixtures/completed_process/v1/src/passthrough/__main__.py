from __future__ import annotations

import argparse

import ktnode as kt

from .process import Process


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the completed Python acceptance fixture")
    parser.add_argument("--package", required=True)
    parser.add_argument("--runtime", required=True)
    args = parser.parse_args()
    kt.run(args.package, args.runtime, Process())


if __name__ == "__main__":
    main()
