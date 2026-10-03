#!/usr/bin/env python3
"""Verify that generated starter failures survive the outer KTM command."""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess


ASSERTION_NEEDLE = 'self.assertEqual(Process.__mro__[1].__name__, "Node")'
STEP_TODO = 'raise NotImplementedError("TODO: implement step")'


def run_ktm(
    *,
    ktm: str,
    home: pathlib.Path,
    platform: str,
    project: pathlib.Path,
    log: pathlib.Path,
    expect_success: bool,
    diagnostics: tuple[str, ...] = (),
) -> str:
    log.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [ktm, "test", "--offline", "--platform", platform],
        cwd=project,
        env={**os.environ, "HOME": str(home)},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log.write_text(result.stdout)
    if expect_success and result.returncode != 0:
        raise SystemExit(f"expected generated project test to pass; see {log}")
    if not expect_success and result.returncode == 0:
        raise SystemExit(f"outer ktm test accepted a deliberate failure; see {log}")
    for diagnostic in diagnostics:
        if diagnostic not in result.stdout:
            raise SystemExit(f"missing diagnostic {diagnostic!r}; see {log}")
    return result.stdout


def verify(args: argparse.Namespace) -> None:
    project = args.project.resolve()
    home = args.home.resolve()
    logs = args.log_dir.resolve()
    test_file = project / "tests" / "test_smoke.py"
    test_backup = test_file.with_suffix(".py.kin14-baseline")
    shutil.copy2(test_file, test_backup)

    try:
        run_ktm(
            ktm=args.ktm,
            home=home,
            platform=args.platform,
            project=project,
            log=logs / "baseline.log",
            expect_success=True,
        )

        text = test_backup.read_text()
        if ASSERTION_NEEDLE not in text:
            raise SystemExit("generated unittest assertion seam is missing")
        test_file.write_text(
            text.replace(
                ASSERTION_NEEDLE,
                'self.fail("KIN-14 deliberate assertion failure")',
                1,
            )
        )
        run_ktm(
            ktm=args.ktm,
            home=home,
            platform=args.platform,
            project=project,
            log=logs / "assertion-failure.log",
            expect_success=False,
            diagnostics=("KIN-14 deliberate assertion failure",),
        )

        test_file.write_text(
            "import deliberately_missing_kin14_dependency\n" + test_backup.read_text()
        )
        run_ktm(
            ktm=args.ktm,
            home=home,
            platform=args.platform,
            project=project,
            log=logs / "import-failure.log",
            expect_success=False,
            diagnostics=("ModuleNotFoundError", "deliberately_missing_kin14_dependency"),
        )

        test_file.write_text(test_backup.read_text())
        process_file = project / "src" / next((project / "src").iterdir()).name / "process.py"
        process_backup = process_file.with_suffix(".py.kin52-baseline")
        shutil.copy2(process_file, process_backup)
        try:
            source = process_backup.read_text()
            if STEP_TODO not in source:
                raise SystemExit("generated step TODO seam is missing")
            process_file.write_text(source.replace(STEP_TODO, "return kt.NextStep.CONTINUE", 1))
            run_ktm(
                ktm=args.ktm,
                home=home,
                platform=args.platform,
                project=project,
                log=logs / "missing-step-todo.log",
                expect_success=False,
                diagnostics=("TODO: implement step",),
            )
        finally:
            shutil.move(process_backup, process_file)

        shutil.copy2(test_backup, test_file)
        run_ktm(
            ktm=args.ktm,
            home=home,
            platform=args.platform,
            project=project,
            log=logs / "restored-green.log",
            expect_success=True,
        )
    finally:
        if test_backup.exists():
            shutil.move(test_backup, test_file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=pathlib.Path, required=True)
    parser.add_argument("--home", type=pathlib.Path, required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--log-dir", type=pathlib.Path, required=True)
    parser.add_argument("--ktm", default="ktm")
    return parser.parse_args()


if __name__ == "__main__":
    verify(parse_args())
