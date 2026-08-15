from __future__ import annotations

import json
import unittest

from aia.discovery import LibraryClient


class StubLibrary(LibraryClient):
    def __init__(self, responses: dict[str, object]) -> None:
        super().__init__()
        self.responses = responses

    def _read(self, url: str) -> bytes:
        value = self.responses[url]
        if isinstance(value, bytes):
            return value
        return json.dumps(value).encode()


class DiscoveryTests(unittest.TestCase):
    def test_popularity_order_variant_fit_and_installed_exclusion(self) -> None:
        root = LibraryClient.REGISTRY_URL
        responses = {
            LibraryClient.LIBRARY_URL: (
                b'<a href="/library/popular">general assistant</a>'
                b'<a href="/library/second">second</a>'
            ),
            "https://ollama.com/library/popular/tags": (
                b'<a href="/library/popular:1b">1b</a>'
                b'<a href="/library/popular:7b">7b</a>'
                b'<a href="/library/popular:Q4_K_M">quant</a>'
            ),
            f"{root}/popular/manifests/1b": {"layers": [{"size": 1_000}]},
            f"{root}/popular/manifests/7b": {"layers": [{"size": 7_000}]},
        }
        models = StubLibrary(responses).candidates(5_000, {"second:latest"})
        self.assertEqual([model.name for model in models], ["popular:1b"])
        self.assertEqual(models[0].size_bytes, 1_000)

    def test_specialized_models_are_excluded_from_live_metadata(self) -> None:
        responses = {
            LibraryClient.LIBRARY_URL: (
                b'<a href="/library/embedder">An embedding model</a>'
                b'<a href="/library/assistant">A general assistant</a>'
            )
        }
        self.assertEqual(StubLibrary(responses).popular_names(), ["assistant"])

    def test_discovery_is_limited_to_twenty_one(self) -> None:
        root = LibraryClient.REGISTRY_URL
        names = [f"model{number}" for number in range(25)]
        responses: dict[str, object] = {
            LibraryClient.LIBRARY_URL: "".join(
                f'<a href="/library/{name}">{name}</a>' for name in names
            ).encode()
        }
        for name in names:
            responses[f"https://ollama.com/library/{name}/tags"] = (
                f'<a href="/library/{name}:1b">1b</a>'.encode()
            )
            responses[f"{root}/{name}/manifests/1b"] = {"layers": [{"size": 100}]}
        models = StubLibrary(responses).candidates(1_000, set())
        self.assertEqual(len(models), 21)


if __name__ == "__main__":
    unittest.main()
