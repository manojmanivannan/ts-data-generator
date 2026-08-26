"""Project-root conftest.

Applies to all collected tests, including doctests collected from
``src/ts_data_generator`` (the core docstring surface scoped in
``pyproject.toml`` ``testpaths`` via ``--doctest-modules``).

Per the ratified docstring convention (ticket 02, ``docs/docstrings.md`` §3),
every `Example` writes its own explicit ``from ts_data_generator import ...``
imports so it reads correctly standalone and in the IDE hover. The
``doctest_namespace`` fixture below is a safety net only — it injects
``pandas`` (as ``pd``) and the ``ts_data_generator`` package root so a stray
reference resolves without forcing import boilerplate into every example.
"""

import pandas as pd
import pytest

import ts_data_generator


@pytest.fixture(autouse=True)
def _doctest_namespace(doctest_namespace):
    """Inject ``pd`` and the package root into every doctest's globals."""
    doctest_namespace["pd"] = pd
    doctest_namespace["ts_data_generator"] = ts_data_generator