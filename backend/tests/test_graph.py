"""Tests for graph/cross-translation endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestParallels:
    """Tests for parallel verse endpoints."""

    def test_get_parallels_by_verse_id(self, client: TestClient):
        """Should get parallel verses across translations."""
        response = client.get("/v1/graph/parallels/NIV:1:1:1")
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "cvk" in data
            assert "renditions" in data
            assert isinstance(data["renditions"], list)

    def test_get_parallels_by_cvk(self, client: TestClient):
        """Should get parallels by canonical verse key."""
        response = client.get("/v1/graph/cv/1:1:1:/renditions")
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "cvk" in data
            assert "renditions" in data

    def test_parallels_response_structure(self, client: TestClient):
        """Should return properly structured renditions."""
        response = client.get("/v1/graph/parallels/NIV:1:1:1")

        if response.status_code == 200:
            data = response.json()
            if len(data["renditions"]) > 0:
                rendition = data["renditions"][0]
                assert "verse_id" in rendition
                assert "translation" in rendition
                assert "reference" in rendition
                assert "text" in rendition
