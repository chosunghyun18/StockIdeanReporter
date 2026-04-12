"""MiroFish REST API client.

Wraps the MiroFish Flask backend (localhost:5001) with a clean Python interface.

Full flow:
  1. build_graph()      — create knowledge graph from seed texts
  2. create_simulation() — attach simulation to the graph
  3. prepare_simulation() — generate agent profiles + config (async, poll until done)
  4. start_simulation()   — run agent interaction rounds
  5. wait_simulation()    — poll until simulation completes
  6. generate_report()    — trigger ReportAgent
  7. get_report()         — fetch final report text
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Optional

import requests


class MiroFishError(Exception):
    """Raised when the MiroFish API returns a non-success response."""


@dataclass
class SimulationResult:
    """Result returned after a full simulation + report cycle."""

    simulation_id: str
    report_id: str
    report_text: str
    total_rounds: int
    entities_count: int


class MiroFishClient:
    """HTTP client for the MiroFish backend.

    Args:
        base_url: MiroFish Flask server URL (e.g. http://localhost:5001).
        timeout: Default HTTP request timeout in seconds.
        poll_interval: Seconds between status-polling requests.
        max_poll: Maximum number of polling attempts before giving up.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:5001",
        timeout: int = 60,
        poll_interval: int = 5,
        max_poll: int = 120,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.max_poll = max_poll
        self._session = requests.Session()

    # ── low-level helpers ─────────────────────────────────────────────────────

    def _post(self, path: str, payload: dict) -> dict:
        url = f"{self.base_url}{path}"
        resp = self._session.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success", True):
            raise MiroFishError(f"MiroFish error [{path}]: {data.get('error')}")
        return data.get("data", data)

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        url = f"{self.base_url}{path}"
        resp = self._session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success", True):
            raise MiroFishError(f"MiroFish error [{path}]: {data.get('error')}")
        return data.get("data", data)

    def _poll(self, path: str, done_statuses: set[str], error_statuses: set[str]) -> dict:
        """Poll a status endpoint until completion or error."""
        for _ in range(self.max_poll):
            data = self._get(path)
            status = data.get("status", "")
            if status in done_statuses:
                return data
            if status in error_statuses:
                raise MiroFishError(f"Task failed at {path}: status={status}")
            time.sleep(self.poll_interval)
        raise MiroFishError(f"Polling timed out at {path} after {self.max_poll} attempts")

    # ── public API ────────────────────────────────────────────────────────────

    def build_graph(self, project_id: str, seed_texts: dict[str, str]) -> str:
        """Create a MiroFish knowledge graph from seed texts.

        Args:
            project_id: Unique project identifier.
            seed_texts: Dict mapping agent role → seed text
                        e.g. {"macro": "...", "sentiment": "...", "earnings": "..."}.

        Returns:
            graph_id assigned by MiroFish.
        """
        combined_seed = "\n\n".join(
            f"=== {role.upper()} ===\n{text}"
            for role, text in seed_texts.items()
        )
        result = self._post(
            "/api/graph/build",
            {"project_id": project_id, "seed_text": combined_seed},
        )
        return result["graph_id"]

    def create_simulation(self, project_id: str, graph_id: str) -> str:
        """Create a simulation instance.

        Args:
            project_id: Parent project ID.
            graph_id: Graph ID from build_graph().

        Returns:
            simulation_id.
        """
        result = self._post(
            "/api/simulation/create",
            {
                "project_id": project_id,
                "graph_id": graph_id,
                "enable_reddit": True,
                "enable_twitter": False,
            },
        )
        return result["simulation_id"]

    def prepare_simulation(
        self,
        simulation_id: str,
        entity_types: Optional[list[str]] = None,
    ) -> None:
        """Prepare agent profiles and simulation config. Blocks until ready.

        Args:
            simulation_id: Simulation ID from create_simulation().
            entity_types: Agent entity types to include.
        """
        result = self._post(
            "/api/simulation/prepare",
            {
                "simulation_id": simulation_id,
                "entity_types": entity_types or ["Analyst"],
                "use_llm_for_profiles": True,
                "parallel_profile_count": 3,
            },
        )
        task_id = result["task_id"]
        # Poll until preparation completes
        for _ in range(self.max_poll):
            status_data = self._post(
                "/api/simulation/prepare/status",
                {"task_id": task_id, "simulation_id": simulation_id},
            )
            status = status_data.get("status", "")
            if status == "completed":
                return
            if status in {"failed", "error"}:
                raise MiroFishError(f"Prepare failed: {status_data}")
            time.sleep(self.poll_interval)
        raise MiroFishError("prepare_simulation timed out")

    def start_simulation(self, simulation_id: str, max_rounds: int = 10) -> None:
        """Start simulation execution.

        Args:
            simulation_id: Simulation ID.
            max_rounds: Number of agent interaction rounds.
        """
        self._post(
            "/api/simulation/start",
            {
                "simulation_id": simulation_id,
                "platform": "reddit",
                "max_rounds": max_rounds,
                "enable_graph_memory_update": False,
            },
        )

    def wait_simulation(self, simulation_id: str) -> dict:
        """Block until simulation finishes running.

        Args:
            simulation_id: Simulation ID.

        Returns:
            Final run-status dict.
        """
        for _ in range(self.max_poll):
            data = self._get(f"/api/simulation/{simulation_id}/run-status")
            status = data.get("runner_status", "")
            if status in {"completed", "stopped", "finished"}:
                return data
            if status in {"error", "failed"}:
                raise MiroFishError(f"Simulation failed: {data}")
            time.sleep(self.poll_interval)
        raise MiroFishError("wait_simulation timed out")

    def generate_report(self, simulation_id: str, graph_id: str, requirement: str) -> str:
        """Trigger ReportAgent to generate a report.

        Args:
            simulation_id: Completed simulation ID.
            graph_id: Graph ID used by the simulation.
            requirement: Natural-language report requirement
                         e.g. "SPY ETF 롱/숏/중립 확률과 근거를 분석해줘".

        Returns:
            report_id.
        """
        result = self._post(
            "/api/report/generate",
            {
                "simulation_id": simulation_id,
                "graph_id": graph_id,
                "simulation_requirement": requirement,
            },
        )
        report_id = result["report_id"]
        task_id   = result["task_id"]
        # Poll until report generation completes
        for _ in range(self.max_poll):
            status_data = self._get(f"/api/report/generate/status/{task_id}")
            status = status_data.get("status", "")
            if status == "completed":
                return report_id
            if status in {"failed", "error"}:
                raise MiroFishError(f"Report generation failed: {status_data}")
            time.sleep(self.poll_interval)
        raise MiroFishError("generate_report timed out")

    def get_report(self, report_id: str) -> str:
        """Fetch the generated report text.

        Args:
            report_id: Report ID from generate_report().

        Returns:
            Full report text string.
        """
        data = self._get(f"/api/report/{report_id}")
        return data.get("report_text") or data.get("content") or str(data)

    def run_full_pipeline(
        self,
        project_id: str,
        seed_texts: dict[str, str],
        max_rounds: int = 10,
        report_requirement: str = "SPY ETF의 롱/숏/중립 방향과 확률, 핵심 근거를 분석해줘.",
    ) -> SimulationResult:
        """Execute the complete MiroFish pipeline end-to-end.

        Args:
            project_id: Unique identifier for this analysis run.
            seed_texts: Agent seed texts from seed_builder.build_all_seeds().
            max_rounds: Simulation interaction rounds.
            report_requirement: Instruction for the ReportAgent.

        Returns:
            SimulationResult with report text and metadata.
        """
        graph_id      = self.build_graph(project_id, seed_texts)
        simulation_id = self.create_simulation(project_id, graph_id)
        self.prepare_simulation(simulation_id)
        self.start_simulation(simulation_id, max_rounds=max_rounds)
        run_status = self.wait_simulation(simulation_id)
        report_id  = self.generate_report(simulation_id, graph_id, report_requirement)
        report_text = self.get_report(report_id)

        return SimulationResult(
            simulation_id=simulation_id,
            report_id=report_id,
            report_text=report_text,
            total_rounds=run_status.get("total_rounds", max_rounds),
            entities_count=run_status.get("entities_count", 0),
        )
