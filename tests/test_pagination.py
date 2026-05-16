"""Tests for crumdbob.pagination — HAL-style pagination helper."""

from __future__ import annotations

import pytest

from crumdbob.pagination import Page, paginate


class TestPaginate:
    def test_basic_shape(self):
        page = paginate(
            ["a", "b", "c"],
            limit=10,
            offset=0,
            total=3,
            base_url="/api/v1/things",
        )
        result = page.to_dict()
        assert result["items"] == ["a", "b", "c"]
        assert result["pagination"]["limit"] == 10
        assert result["pagination"]["offset"] == 0
        assert result["pagination"]["total"] == 3
        assert result["pagination"]["has_more"] is False
        assert result["links"]["self"].startswith("/api/v1/things?")

    def test_first_page_has_no_prev(self):
        page = paginate([1, 2], limit=2, offset=0, total=10, base_url="/x")
        result = page.to_dict()
        assert result["links"]["prev"] is None
        assert result["links"]["next"] is not None
        assert "offset=2" in result["links"]["next"]

    def test_last_page_has_no_next(self):
        page = paginate([9, 10], limit=2, offset=8, total=10, base_url="/x")
        result = page.to_dict()
        assert result["links"]["next"] is None
        assert result["links"]["prev"] is not None
        assert "offset=6" in result["links"]["prev"]

    def test_middle_page_has_both(self):
        page = paginate([3, 4], limit=2, offset=2, total=10, base_url="/x")
        result = page.to_dict()
        assert result["links"]["prev"] is not None
        assert result["links"]["next"] is not None
        assert result["links"]["first"] is not None
        assert "offset=0" in result["links"]["first"]

    def test_has_more_heuristic_when_total_unknown(self):
        """Without a total, we infer has_more by checking if items == limit."""
        # Full page → assume more exists
        page_full = paginate([1, 2, 3], limit=3, offset=0, total=None, base_url="/x")
        assert page_full.to_dict()["pagination"]["has_more"] is True

        # Partial page → definitely no more
        page_partial = paginate([1, 2], limit=3, offset=0, total=None, base_url="/x")
        assert page_partial.to_dict()["pagination"]["has_more"] is False

    def test_prev_offset_does_not_go_negative(self):
        page = paginate([1, 2], limit=10, offset=5, total=20, base_url="/x")
        result = page.to_dict()
        # offset 5 - limit 10 would be -5; should clamp to 0
        assert "offset=0" in result["links"]["prev"]

    def test_extra_params_preserved_in_links(self):
        page = paginate(
            [1],
            limit=5,
            offset=0,
            total=10,
            base_url="/api/v1/sessions",
            extra_params={"status": "open", "branch": "main"},
        )
        result = page.to_dict()
        # All links carry the filters forward
        for link_name in ("self", "first", "next"):
            link = result["links"][link_name]
            assert "status=open" in link
            assert "branch=main" in link

    def test_invalid_limit_rejected(self):
        with pytest.raises(ValueError, match="limit must be >= 1"):
            paginate([], limit=0, offset=0)

    def test_invalid_offset_rejected(self):
        with pytest.raises(ValueError, match="offset must be >= 0"):
            paginate([], limit=10, offset=-1)

    def test_empty_items_with_no_total(self):
        page = paginate([], limit=10, offset=0, total=None, base_url="/x")
        result = page.to_dict()
        assert result["items"] == []
        assert result["pagination"]["has_more"] is False


class TestPageDataclass:
    def test_is_generic(self):
        """Page is generic so typed callers get IDE/mypy help."""
        page: Page[str] = paginate(["x"], limit=1, offset=0, total=1)
        assert page.items == ["x"]
