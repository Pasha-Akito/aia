from __future__ import annotations

from collections.abc import Callable, Iterator
import json
import logging
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .errors import AiaError

_DEFAULT_TIMEOUT = object()


class OllamaClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434/api",
        logger: logging.Logger | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.logger = logger or logging.getLogger("aia")
        self.timeout = timeout

    def _request(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout: float | None | object = _DEFAULT_TIMEOUT,
    ) -> Any:
        body = json.dumps(payload).encode() if payload is not None else None
        request = Request(
            f"{self.base_url}/{endpoint}",
            data=body,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            request_timeout = self.timeout if timeout is _DEFAULT_TIMEOUT else timeout
            with urlopen(request, timeout=request_timeout) as response:
                content = response.read()
        except HTTPError as error:
            self.logger.exception("Ollama request failed: %s %s", method, endpoint)
            raise AiaError(f"Ollama request failed ({error.code}). Check the AIA log.") from error
        except TimeoutError as error:
            self.logger.exception("Ollama request timed out: %s %s", method, endpoint)
            raise AiaError("Ollama request timed out. Try again.") from error
        except (URLError, OSError) as error:
            self.logger.exception("Ollama request failed: %s %s", method, endpoint)
            raise AiaError("Ollama unavailable. Check: systemctl status ollama") from error
        if not content:
            return {}
        try:
            return json.loads(content)
        except json.JSONDecodeError as error:
            raise AiaError("Ollama returned an invalid response.") from error

    def installed_models(self) -> list[dict[str, Any]]:
        result = self._request("GET", "tags")
        return list(result.get("models", []))

    def running_models(self) -> list[dict[str, Any]]:
        result = self._request("GET", "ps")
        return list(result.get("models", []))

    def pull(self, model: str, progress: Callable[[int], None] | None = None) -> None:
        self.logger.info("Pulling model %s", model)
        payload = json.dumps({"model": model, "stream": True}).encode()
        request = Request(
            f"{self.base_url}/pull",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        last_percentage = -1
        tracked_total = 0
        try:
            with urlopen(request, timeout=None) as response:
                for raw_line in response:
                    if not raw_line.strip():
                        continue
                    event = json.loads(raw_line)
                    if event.get("error"):
                        raise AiaError(f"Download failed: {event['error']}")
                    completed = event.get("completed")
                    total = event.get("total")
                    if (
                        isinstance(completed, int)
                        and isinstance(total, int)
                        and total > 0
                        and total >= tracked_total
                    ):
                        tracked_total = total
                        percentage = min(100, completed * 100 // total)
                        if progress and percentage != last_percentage:
                            progress(percentage)
                        last_percentage = percentage
                    if event.get("status") == "success" and last_percentage < 100:
                        if progress:
                            progress(100)
                        last_percentage = 100
        except AiaError:
            raise
        except HTTPError as error:
            self.logger.exception("Ollama pull failed for %s", model)
            raise AiaError(f"Download failed ({error.code}). Check the AIA log.") from error
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            self.logger.exception("Ollama pull failed for %s", model)
            raise AiaError("Download failed. Check the AIA log.") from error

    def delete(self, model: str) -> None:
        self.logger.info("Deleting model %s", model)
        self._request("DELETE", "delete", {"model": model})

    def generate(self, model: str, prompt: str) -> Iterator[str]:
        payload = json.dumps(
            {"model": model, "prompt": prompt, "stream": True, "keep_alive": 0}
        ).encode()
        request = Request(
            f"{self.base_url}/generate",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        self.logger.info("Generating with model %s", model)
        try:
            with urlopen(request, timeout=None) as response:
                for raw_line in response:
                    if not raw_line.strip():
                        continue
                    event = json.loads(raw_line)
                    if event.get("error"):
                        raise AiaError(f"Generation failed: {event['error']}")
                    text = event.get("response", "")
                    if text:
                        yield text
        except AiaError:
            raise
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            self.logger.exception("Generation failed for model %s", model)
            raise AiaError("Generation failed. Check the AIA log.") from error

    def request_unload(self, model: str) -> None:
        self.logger.info("Requesting unload for model %s", model)
        self._request(
            "POST", "generate", {"model": model, "prompt": "", "stream": False, "keep_alive": 0}
        )

    def unload_and_verify(self, model: str, attempts: int = 3, delay: float = 0.5) -> bool:
        for attempt in range(1, attempts + 1):
            self.logger.info("Unload attempt %d/%d for %s", attempt, attempts, model)
            try:
                self.request_unload(model)
                loaded = {item.get("name") or item.get("model") for item in self.running_models()}
                if model not in loaded:
                    return True
            except AiaError:
                pass
            if attempt < attempts:
                time.sleep(delay)
        return False
