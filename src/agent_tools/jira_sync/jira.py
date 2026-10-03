from __future__ import annotations

from typing import Any

import httpx

from .models import CreatedIssue, Ticket


class JiraError(RuntimeError):
    pass


class JiraClient:
    def __init__(self, base_url: str, email: str, api_token: str, *, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(
            base_url=self.base_url,
            auth=(email, api_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=timeout,
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "JiraClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _request(self, method: str, url: str, **kwargs: Any) -> Any:
        response = self.client.request(method, url, **kwargs)
        if response.is_error:
            detail = response.text
            try:
                data = response.json()
                detail = str(data.get("errorMessages") or data.get("errors") or data)
            except Exception:
                pass
            raise JiraError(f"Jira API {response.status_code}: {detail}")
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def get_issue(self, key: str) -> dict[str, Any]:
        return self._request("GET", f"/rest/api/3/issue/{key}")

    def issue_exists(self, key: str) -> bool:
        response = self.client.get(f"/rest/api/3/issue/{key}")
        if response.status_code == 404:
            return False
        if response.is_error:
            raise JiraError(f"Jira API {response.status_code}: {response.text}")
        return True

    def create_issue(self, fields: dict[str, Any]) -> CreatedIssue:
        data = self._request("POST", "/rest/api/3/issue", json={"fields": fields})
        return CreatedIssue.model_validate(data)

    def update_issue(self, key: str, fields: dict[str, Any]) -> None:
        self._request("PUT", f"/rest/api/3/issue/{key}", json={"fields": fields})
