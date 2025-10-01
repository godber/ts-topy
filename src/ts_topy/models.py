"""Pydantic models for Teraslice API responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Worker(BaseModel):
    """Active worker on a node."""

    worker_id: int | None = None
    assignment: str
    pid: int | None = None

    @field_validator("worker_id", "pid", mode="before")
    @classmethod
    def parse_int_or_na(cls, v: Any) -> int | None:
        """Parse integer or return None for N/A values."""
        if v is None or v == "N/A" or v == "":
            return None
        if isinstance(v, int):
            return v
        try:
            return int(v)
        except (ValueError, TypeError):
            return None


class Node(BaseModel):
    """Teraslice cluster node."""

    node_id: str
    hostname: str
    pid: int | None = None
    node_version: str
    teraslice_version: str
    total: int | None = None  # Total worker slots
    state: str
    available: int | None = None  # Available worker slots
    active: list[Worker] = []  # Active workers

    @field_validator("pid", "total", "available", mode="before")
    @classmethod
    def parse_int_or_na(cls, v: Any) -> int | None:
        """Parse integer or return None for N/A values."""
        if v is None or v == "N/A" or v == "":
            return None
        if isinstance(v, int):
            return v
        try:
            return int(v)
        except (ValueError, TypeError):
            return None


class ClusterState(BaseModel):
    """Overall cluster state containing all nodes."""

    nodes: dict[str, Node]

    model_config = ConfigDict(extra="allow")

    @property
    def total_nodes(self) -> int:
        """Total number of nodes in the cluster."""
        return len(self.nodes)

    @property
    def total_workers(self) -> int:
        """Total worker slots across all nodes."""
        return sum(node.total for node in self.nodes.values() if node.total is not None)

    @property
    def active_workers(self) -> int:
        """Total active workers across all nodes."""
        return sum(len(node.active) for node in self.nodes.values())

    @property
    def available_workers(self) -> int:
        """Total available worker slots across all nodes."""
        return sum(node.available for node in self.nodes.values() if node.available is not None)


class Controller(BaseModel):
    """Execution controller (slicer) information."""

    ex_id: str
    job_id: str
    name: str
    workers_available: int = 0
    workers_active: int = 0
    workers_joined: int = 0
    workers_reconnected: int = 0
    workers_disconnected: int = 0
    failed: int = 0
    subslices: int = 0
    queued: int = 0
    slice_range_expansion: int = 0
    processed: int = 0
    slicers: int = 0
    subslice_by_key: int = 0
    started: datetime | None = None

    model_config = ConfigDict(extra="allow")


class Operation(BaseModel):
    """Job or execution operation configuration."""

    op: str = Field(alias="_op")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Job(BaseModel):
    """Teraslice job configuration and status."""

    name: str
    lifecycle: str
    workers: int
    operations: list[Operation]
    job_id: str
    created: datetime = Field(alias="_created")
    updated: datetime = Field(alias="_updated")
    context: str = Field(alias="_context")
    active: bool | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class SlicerStats(BaseModel):
    """Statistics for an execution slicer."""

    workers_active: int = 0
    workers_joined: int = 0
    queued: int = 0
    job_duration: int = 0
    subslice_by_key: int = 0
    failed: int = 0
    subslices: int = 0
    slice_range_expansion: int = 0
    processed: int = 0
    workers_available: int = 0
    workers_reconnected: int = 0
    workers_disconnected: int = 0
    slicers: int = 0
    started: datetime | None = None
    queuing_complete: datetime | None = None

    model_config = ConfigDict(extra="allow")


class ExecutionContext(BaseModel):
    """Teraslice execution context state."""

    ex_id: str
    job_id: str
    name: str
    lifecycle: str
    analytics: bool = False
    max_retries: int = 0
    probation_window: int = 0
    slicers: int = 0
    workers: int = 0
    operations: list[Operation] = []
    created: datetime = Field(alias="_created")
    updated: datetime = Field(alias="_updated")
    context: str = Field(alias="_context")
    status: str = Field(alias="_status")
    slicer_hostname: str | None = None
    slicer_port: int | None = None
    has_errors: bool = Field(default=False, alias="_has_errors")
    slicer_stats: SlicerStats | None = Field(default=None, alias="_slicer_stats")

    model_config = ConfigDict(populate_by_name=True, extra="allow")
