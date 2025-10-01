"""Teraslice API client."""

from typing import Any

import httpx

from ts_topy.models import ClusterState, Controller, ExecutionContext, Job


class TerasliceClient:
    """Client for interacting with Teraslice cluster API."""

    def __init__(self, base_url: str, timeout: int = 10) -> None:
        """Initialize the Teraslice client.

        Args:
            base_url: Base URL of the Teraslice master (e.g., http://localhost:5678)
            timeout: HTTP request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def _fetch_json(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """Fetch JSON data from an endpoint.

        Args:
            endpoint: API endpoint path (e.g., /v1/cluster/state)
            params: Optional query parameters

        Returns:
            Parsed JSON response

        Raises:
            httpx.HTTPError: If the request fails
        """
        url = f"{self.base_url}{endpoint}"
        response = self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def fetch_cluster_state(self) -> ClusterState:
        """Fetch overall cluster state including nodes and workers.

        Returns:
            ClusterState object
        """
        data = self._fetch_json("/v1/cluster/state")
        return ClusterState(nodes=data)

    def fetch_controllers(self) -> list[Controller]:
        """Fetch active execution controllers.

        Returns:
            List of Controller objects
        """
        data = self._fetch_json("/v1/cluster/controllers")
        return [Controller(**item) for item in data]

    def fetch_jobs(self, size: int | None = None, from_: int | None = None) -> list[Job]:
        """Fetch all jobs.

        Args:
            size: Number of jobs to return (default: API default, usually 100)
            from_: Starting offset for pagination

        Returns:
            List of Job objects
        """
        params = {}
        if size is not None:
            params["size"] = size
        if from_ is not None:
            params["from"] = from_
        data = self._fetch_json("/v1/jobs", params=params if params else None)
        return [Job(**item) for item in data]

    def fetch_job_by_id(self, job_id: str) -> dict[str, Any]:
        """Fetch a single job by ID.

        Args:
            job_id: Job ID to fetch

        Returns:
            Raw JSON response for the job
        """
        return self._fetch_json(f"/v1/jobs/{job_id}")

    def fetch_execution_contexts(self, size: int | None = None, from_: int | None = None) -> list[ExecutionContext]:
        """Fetch all execution contexts.

        Args:
            size: Number of execution contexts to return (default: API default, usually 100)
            from_: Starting offset for pagination

        Returns:
            List of ExecutionContext objects
        """
        params = {}
        if size is not None:
            params["size"] = size
        if from_ is not None:
            params["from"] = from_
        data = self._fetch_json("/v1/ex", params=params if params else None)
        return [ExecutionContext(**item) for item in data]

    def fetch_execution_context_by_id(self, ex_id: str) -> dict[str, Any]:
        """Fetch a single execution context by ID.

        Args:
            ex_id: Execution context ID to fetch

        Returns:
            Raw JSON response for the execution context
        """
        return self._fetch_json(f"/v1/ex/{ex_id}")

    def fetch_all(self) -> dict[str, Any]:
        """Fetch data from all monitoring endpoints.

        Returns:
            Dictionary with keys: cluster_state, controllers, jobs, execution_contexts
        """
        return {
            "cluster_state": self.fetch_cluster_state(),
            "controllers": self.fetch_controllers(),
            "jobs": self.fetch_jobs(),
            "execution_contexts": self.fetch_execution_contexts(),
        }
