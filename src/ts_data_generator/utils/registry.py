"""Lightweight registry for CLI-pluggable types (dimensions, trends, anomalies)."""

from __future__ import annotations

import importlib
import logging
from collections.abc import Callable

from ts_data_generator.exceptions import RegistryError


class Registry:
    """A registry of CLI-pluggable types discovered via module reflection.

    Args:
        module: The importable module (or module path string) to search.
        name_filter: Optional predicate to filter names (e.g., exclude
            private names). Called with the attribute name string.
        base_class: Optional base class to filter against (e.g., only
            collect subclasses of a given ABC). When provided, each
            candidate must be a class that issubclass of *base_class*.

    Example:
        >>> registry = Registry(
        ...     "ts_data_generator.utils.functions",
        ...     name_filter=lambda n: not n.startswith("_"),
        ... )
        >>> fn = registry.get("linear")
    """

    def __init__(
        self,
        module: str | object,
        *,
        name_filter: Callable[[str], bool] | None = None,
        base_class: type | None = None,
    ) -> None:
        if isinstance(module, str):
            self._module = importlib.import_module(module)
        else:
            self._module = module
        self._name_filter = name_filter
        self._base_class = base_class

    def get(self, name: str) -> type | Callable:
        """Look up *name* in the module.

        Returns:
            The matching class or callable.

        Raises:
            RegistryError: If *name* is not found in the module.
        """
        try:
            obj = getattr(self._module, name)
        except AttributeError:
            available = self.list_available()
            logging.warning("'%s' not found in %s", name, self._module.__name__)
            raise RegistryError(
                f"'{name}' is not a valid option. "
                f"Available: {', '.join(available)}"
            ) from None

        if self._base_class is not None:
            if not isinstance(obj, type) or not issubclass(obj, self._base_class):
                available = self.list_available()
                raise RegistryError(
                    f"'{name}' is not a valid option. "
                    f"Available: {', '.join(available)}"
                )

        return obj

    def list_available(self) -> list[str]:
        """List all public names in the module matching the filter."""
        items = []
        for attr_name in dir(self._module):
            if attr_name.startswith("_"):
                continue
            if self._name_filter and not self._name_filter(attr_name):
                continue
            obj = getattr(self._module, attr_name)
            if self._base_class is not None:
                if not isinstance(obj, type) or not issubclass(obj, self._base_class):
                    continue
            items.append(attr_name)
        return sorted(items)
