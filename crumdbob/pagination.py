"""Pagination helpers for API list endpoints.

Implements offset/limit pagination with HAL-style metadata so clients can
walk a result set without knowing the total size. Total count is included
when cheap to compute, but is optional — the next/prev links work either
way.

Example use in a FastAPI route::

    from crumdbob.pagination import Page, paginate

    @app.get("/api/v1/sessions")
    async def list_sessions(limit: int = 20, offset: int = 0) -> dict:
        items = db.list_sessions(limit=limit, offset=offset)
        total = db.count_sessions()
        return paginate(items, limit=limit, offset=offset, total=total,
                        base_url="/api/v1/sessions").to_dict()
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar
from urllib.parse import urlencode

T = TypeVar("T")


@dataclass
class Page(Generic[T]):
    """A single page of results with navigation metadata."""

    items: list[T]
    limit: int
    offset: int
    total: int | None
    base_url: str
    extra_params: dict[str, str | int]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the JSON shape every paginated endpoint returns."""
        return {
            "items": self.items,
            "pagination": {
                "limit": self.limit,
                "offset": self.offset,
                "total": self.total,
                "has_more": self._has_more(),
            },
            "links": self._links(),
        }

    def _has_more(self) -> bool:
        if self.total is not None:
            return self.offset + len(self.items) < self.total
        # If we got a full page we assume there's more; client can confirm
        # by issuing the next request and getting an empty items list.
        return len(self.items) >= self.limit

    def _build(self, offset: int) -> str:
        params: dict[str, Any] = {**self.extra_params, "limit": self.limit, "offset": offset}
        return f"{self.base_url}?{urlencode(params)}"

    def _links(self) -> dict[str, str | None]:
        next_offset = self.offset + self.limit
        prev_offset = max(0, self.offset - self.limit)
        return {
            "self": self._build(self.offset),
            "first": self._build(0),
            "next": self._build(next_offset) if self._has_more() else None,
            "prev": self._build(prev_offset) if self.offset > 0 else None,
        }


def paginate(
    items: list[T],
    *,
    limit: int,
    offset: int,
    total: int | None = None,
    base_url: str = "",
    extra_params: dict[str, str | int] | None = None,
) -> Page[T]:
    """Wrap a list of items in a Page with navigation metadata.

    Args:
        items: The current page's results.
        limit: Page size used in the query.
        offset: Starting offset of this page.
        total: Total result count, if cheaply available. ``None`` means
            "unknown" — links still work, just ``has_more`` becomes a
            heuristic ("returned a full page → probably more").
        base_url: Path component used to build ``next``/``prev`` links.
            E.g. ``/api/v1/sessions``.
        extra_params: Additional query string parameters to preserve on
            navigation (filters, sort, etc).

    Returns:
        A Page object whose ``.to_dict()`` is the JSON-ready response.
    """
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if offset < 0:
        raise ValueError("offset must be >= 0")
    return Page(
        items=items,
        limit=limit,
        offset=offset,
        total=total,
        base_url=base_url,
        extra_params=extra_params or {},
    )
