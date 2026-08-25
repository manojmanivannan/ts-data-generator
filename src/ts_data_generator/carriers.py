"""Domain-carrying carrier objects for dimension generators.

A :class:`DimensionCarrier` is a ``collections.abc.Generator`` (so
``isinstance(carrier, Generator)`` holds and ``next(carrier)`` works wherever a
plain generator did) that additionally exposes:

* ``.domain`` — the dimension's value domain captured at construction, and
* ``.expandable`` — whether the dimension may expand under
  ``expand_dimensions`` (``True`` for finite explicit-list domains, ``False``
  for numeric ranges / auto-generated names).

The domain is captured eagerly at construction (flag-independent — harmless
when ``expand_dimensions`` is off, the default). The expand/error
classification runs later at expand time. This is the no-introspection /
no-sampling domain-recovery mechanism settled by decision #51: the domain the
parse call site / ``add_dimension`` already holds is carried *on* the dimension
rather than thrown into an opaque generator and introspected back out.

The ``.domain`` shape is deliberately the 1-tuple case of the tuple-domain
detector that linked-dimension composition (MultiItems) will depend on.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Generator
from typing import Any


def dedupe_sort(values: list[Any]) -> list[Any]:
    """Stable de-duplication, then deterministic sort.

    Sorting uses a ``(type-name, string)`` key so mixed-type domains (e.g.
    ints and strings) sort deterministically without raising on cross-type
    comparison. Original values are preserved (the key is for ordering only).
    """
    seen: set[Any] = set()
    distinct = [v for v in values if not (v in seen or seen.add(v))]
    return sorted(distinct, key=lambda v: (type(v).__name__, str(v)))


class DimensionCarrier(Generator, ABC):
    """An infinite iterator that also carries its expandable value domain.

    Subclasses are concrete (see :class:`DomainCarrier` and
    :class:`NonExpandableCarrier`); ``.domain`` and ``.expandable`` are the
    contract the expand path reads with zero ``gi_frame`` access.
    """

    def __init__(self, source: Generator[Any, None, None], func_name: str) -> None:
        self._source = source
        self._func_name = func_name

    @property
    @abstractmethod
    def domain(self) -> list[Any] | None:
        """The dimension's value domain, or ``None`` when non-enumerable."""

    @property
    @abstractmethod
    def expandable(self) -> bool:
        """Whether this dimension may expand under ``expand_dimensions``."""

    @property
    def non_expandable_reason(self) -> str | None:
        """Why this carrier is non-expandable, or ``None`` when expandable."""
        return None

    @property
    def func_name(self) -> str:
        """The originating generator function name (for repr / errors)."""
        return self._func_name

    def send(self, value: Any | None) -> Any:
        return self._source.send(value)

    def throw(self, *args: Any) -> Any:
        return self._source.throw(*args)

    def __next__(self) -> Any:
        return next(self._source)

    def close(self) -> None:
        self._source.close()

    def __repr__(self) -> str:
        return f"<{self._func_name} carrier at {id(self):#x}>"


class DomainCarrier(DimensionCarrier):
    """Expandable carrier with a captured finite explicit-list domain.

    Backs ``random_choice``, ``ordered_choice``, ``constant``, and the static
    list branch of ``add_dimension``. The domain is the sorted-distinct values.
    """

    def __init__(
        self, source: Generator[Any, None, None], domain: list[Any], func_name: str
    ) -> None:
        super().__init__(source, func_name)
        self._domain: list[Any] = dedupe_sort(domain)

    @property
    def domain(self) -> list[Any]:
        return list(self._domain)

    @property
    def expandable(self) -> bool:
        return True


class NonExpandableCarrier(DimensionCarrier):
    """Non-expandable carrier for numeric ranges and auto-generated names.

    ``random_int`` / ``random_float`` draw from a numeric range (enumerating
    ranges risks silent row-count explosion); ``auto_generate_name`` is not a
    finite-domain dimension generator. Both carry ``domain=None`` and a reason
    explaining why they cannot expand.
    """

    def __init__(self, source: Generator[Any, None, None], func_name: str, reason: str) -> None:
        super().__init__(source, func_name)
        self._reason = reason

    @property
    def domain(self) -> None:
        return None

    @property
    def expandable(self) -> bool:
        return False

    @property
    def non_expandable_reason(self) -> str:
        return self._reason
