"""Accessibility checks for live (Playwright) tests.

Registered as a pytest plugin through the `pytest11` entry point, so downstream
projects get `check_a11y` from installing froide without any conftest wiring.
"""

import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from axe_playwright_python.base import AxeResults
    from playwright.async_api import Page


# Axe result types - findings marked as "incomplete" can imply severe bugs, so we include them.
RESULT_TYPES = ["violations", "incomplete"]

# Axe options, see https://github.com/dequelabs/axe-core/blob/develop/doc/API.md#options-parameter
DEFAULT_AXE_OPTIONS: dict = {
    "resultTypes": RESULT_TYPES,
}


@pytest.fixture
def check_a11y(request, snapshot_regression, a11y_axe_options, pytestconfig):
    """Assert that a page turns up nothing new since the last snapshot.

    The snapshot is named after the test, `suffix` is appended to that. `context` and
    `options` are passed to `axe.run()`, so the full axe-core API is available:
    https://github.com/dequelabs/axe-core/blob/develop/doc/API.md#api-name-axerun
    """
    try:
        from axe_playwright_python.async_playwright import Axe
    except ImportError:
        Axe = None
    if Axe is None:
        pytest.fail(
            "Accessibility checks need the axe-core bindings: install `froide[a11y]`.",
            pytrace=False,
        )

    axe = Axe()
    strict = pytestconfig.getoption("a11y_strict")

    async def _check_a11y(
        page: "Page",
        *,
        suffix: str | None = None,
        context: str | list | dict | None = None,
        options: dict | None = None,
    ) -> None:
        results = await axe.run(
            page, context=context, options={**a11y_axe_options, **(options or {})}
        )
        snapshot_regression.check(
            "\n".join(f"{finding}" for finding in _findings(results)),
            extension=".txt",
            basename=_basename(request.node.name, suffix),
            check_fn=lambda obtained, expected: _compare(
                obtained, expected, results, strict
            ),
        )

    return _check_a11y


def _compare(
    obtained_path: Path,
    expected_path: Path,
    results: "AxeResults",
    strict: bool,
) -> None:
    obtained = _read_findings(obtained_path)
    # Under --a11y-strict nothing counts as recorded, so every finding is reported.
    expected = set() if strict else _read_findings(expected_path)

    appeared = sorted(obtained - expected)
    resolved = sorted(expected - obtained)

    if not appeared:
        if not resolved:
            return

        raise AssertionError(
            f"Accessibility findings gone: {', '.join(resolved)}\n"
            "Re-record the snapshot with --force-regen, review the diff and commit."
        )

    label = "Accessibility findings" if strict else "New accessibility findings"
    lines = [f"{label}: {', '.join(appeared)}"]

    lines.extend(_report(results, finding) for finding in appeared)
    if not strict:
        lines.append(
            "Fix the page. If this is accepted debt, record it with --force-regen, "
            "review the diff and commit."
        )

    if resolved:
        lines.append(f"\nAccessibility findings gone: {', '.join(resolved)}")
        lines.append(
            "Re-record with --force-regen once the new findings above are dealt "
            "with - it records those as accepted debt too."
        )

    raise AssertionError("\n".join(lines))


def _report(results: "AxeResults", finding: str) -> str:
    """Render the axe report for one recorded finding."""
    from axe_playwright_python.base import AxeResults

    result_type, _, rule = finding.partition(":")

    # `generate_report()` only reads `violations`, so hand it the array this
    # finding came from.
    return AxeResults({"violations": results.response[result_type]}).generate_report(
        violation_id=rule
    )


def pytest_addoption(parser):
    group = parser.getgroup("froide")
    group.addoption(
        "--a11y-strict",
        action="store_true",
        default=False,
        help=(
            "Ignore the recorded snapshots and fail on every accessibility "
            "finding, so the full axe report for each one is shown. The snapshots "
            "are left untouched."
        ),
    )


@pytest.fixture(scope="session")
def a11y_axe_options() -> dict:
    """Options passed to every `axe.run()`.

    Override in a conftest to check a different set of rules.
    """
    return DEFAULT_AXE_OPTIONS


@pytest.fixture(scope="session")
def snapshot_dirname() -> str:
    """Directory, relative to a test module, that regression data is kept in.

    Override in a conftest to keep snapshots somewhere else.
    """
    return "snapshots"


@pytest.fixture
def snapshot_regression(
    request: pytest.FixtureRequest, tmp_path: Path, snapshot_dirname: str
):
    """`file_regression`, with the recorded data nested one directory deeper.

    pytest-regressions puts the directory of a module next to the module
    itself, e.g. tests/test_module. This fixture adds a directory for
    collecting all the snapshots, still organized in subdirectories per module,
    e.g. tests/snapshots/test_module.
    """
    from pytest_datadir.plugin import LazyDataDir
    from pytest_regressions.file_regression import FileRegressionFixture

    module = Path(request.path)
    datadir = module.parent / snapshot_dirname / module.stem
    return FileRegressionFixture(LazyDataDir(datadir, tmp_path), datadir, request)


def _findings(results: "AxeResults") -> list[str]:
    """The `<result type>:<rule id>` label of every finding on the page."""
    return sorted(
        {
            f"{result_type}:{finding['id']}"
            for result_type in RESULT_TYPES
            for finding in results.response[result_type]
        }
    )


def _basename(node_name: str, suffix: str | None) -> str:
    """The snapshot name: the test's own name plus an optional suffix."""
    name = re.sub(r"[\W]", "_", node_name).rstrip("_")
    return f"{name}_{suffix}" if suffix else name


def _read_findings(path: Path) -> set[str]:
    return {line.strip() for line in path.read_text().splitlines() if line.strip()}
