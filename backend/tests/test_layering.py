"""The API layer talks to services, never to repositories.

The prototype's routes called the repository directly, which is how business
rules end up duplicated across endpoints and how a second client reaches the
data by a path that skips one. This test fails the build if that returns.
"""

import ast
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent / "app"


def imported_modules(source: Path) -> set[str]:
    """Return every module name imported by a Python file.

    Args:
        source: The file to read.

    Returns:
        The dotted module names it imports.
    """
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


class TestLayering(unittest.TestCase):
    def test_no_api_module_imports_a_repository(self):
        offenders: list[str] = []

        for source in APP_ROOT.rglob("api/*.py"):
            for module in imported_modules(source):
                if ".repository" in module:
                    offenders.append(f"{source.relative_to(APP_ROOT.parent)} imports {module}")

        self.assertEqual(offenders, [], "API modules must go through the service layer")

    def test_the_api_layer_was_actually_scanned(self):
        # A rule that silently scans nothing always passes.
        self.assertNotEqual(list(APP_ROOT.rglob("api/*.py")), [])

    def test_no_domain_module_imports_sqlalchemy(self):
        offenders: list[str] = []

        for source in APP_ROOT.rglob("domain/*.py"):
            for module in imported_modules(source):
                if module.split(".")[0] == "sqlalchemy":
                    offenders.append(f"{source.relative_to(APP_ROOT.parent)} imports {module}")

        self.assertEqual(offenders, [], "the domain must stay ORM-free")


if __name__ == "__main__":
    unittest.main()
