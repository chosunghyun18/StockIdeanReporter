"""Tests for mirofish/client.py — all HTTP calls are mocked."""

from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest
import requests

from mirofish.client import MiroFishClient, MiroFishError, SimulationResult


BASE = "http://localhost:5001"


def _client(**kwargs) -> MiroFishClient:
    return MiroFishClient(base_url=BASE, poll_interval=0, max_poll=5, **kwargs)


def _resp(data: dict, success: bool = True, status_code: int = 200):
    """Build a mock requests.Response."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = {"success": success, "data": data}
    mock.raise_for_status = MagicMock()
    return mock


# ── _post / _get error handling ───────────────────────────────────────────────

class TestLowLevel:
    def test_raises_mirofish_error_on_success_false(self):
        client = _client()
        bad_resp = MagicMock()
        bad_resp.raise_for_status = MagicMock()
        bad_resp.json.return_value = {"success": False, "error": "something broke"}
        with patch.object(client._session, "post", return_value=bad_resp):
            with pytest.raises(MiroFishError, match="something broke"):
                client._post("/api/test", {})

    def test_raises_on_http_error(self):
        client = _client()
        bad_resp = MagicMock()
        bad_resp.raise_for_status.side_effect = requests.HTTPError("404")
        with patch.object(client._session, "post", return_value=bad_resp):
            with pytest.raises(requests.HTTPError):
                client._post("/api/test", {})


# ── build_graph ───────────────────────────────────────────────────────────────

class TestBuildGraph:
    def test_returns_graph_id(self):
        client = _client()
        with patch.object(client._session, "post", return_value=_resp({"graph_id": "g_123"})):
            gid = client.build_graph("proj_1", {"macro": "text"})
        assert gid == "g_123"

    def test_combines_seed_texts(self):
        client = _client()
        seeds = {"macro": "macro text", "sentiment": "sentiment text"}
        captured = []
        def fake_post(url, json=None, timeout=None):
            captured.append(json)
            return _resp({"graph_id": "g_x"})
        with patch.object(client._session, "post", side_effect=fake_post):
            client.build_graph("proj_1", seeds)
        payload = captured[0]
        assert "macro text" in payload["seed_text"]
        assert "sentiment text" in payload["seed_text"]


# ── create_simulation ─────────────────────────────────────────────────────────

class TestCreateSimulation:
    def test_returns_simulation_id(self):
        client = _client()
        with patch.object(client._session, "post", return_value=_resp({"simulation_id": "sim_1"})):
            sid = client.create_simulation("proj_1", "g_1")
        assert sid == "sim_1"

    def test_sends_graph_id(self):
        client = _client()
        captured = []
        def fake_post(url, json=None, timeout=None):
            captured.append(json)
            return _resp({"simulation_id": "sim_x"})
        with patch.object(client._session, "post", side_effect=fake_post):
            client.create_simulation("proj_1", "g_999")
        assert captured[0]["graph_id"] == "g_999"


# ── prepare_simulation ────────────────────────────────────────────────────────

class TestPrepareSimulation:
    def test_polls_until_completed(self):
        # prepare_simulation polls via _post (not _get)
        client = _client()
        post_responses = [
            _resp({"task_id": "t_1", "simulation_id": "sim_1"}),  # initial POST
            _resp({"status": "processing"}),                        # poll 1
            _resp({"status": "completed"}),                         # poll 2
        ]
        with patch.object(client._session, "post", side_effect=post_responses):
            client.prepare_simulation("sim_1")  # should not raise

    def test_raises_on_failed_status(self):
        client = _client()
        with patch.object(client._session, "post", return_value=_resp({"task_id": "t_1", "simulation_id": "s"})), \
             patch.object(client._session, "get", return_value=MagicMock(
                 raise_for_status=MagicMock(),
                 json=MagicMock(return_value={"success": True, "data": {"status": "failed"}})
             )):
            with pytest.raises(MiroFishError):
                client.prepare_simulation("sim_1")

    def test_raises_on_timeout(self):
        client = MiroFishClient(base_url=BASE, poll_interval=0, max_poll=2)
        with patch.object(client._session, "post", return_value=_resp({"task_id": "t_1", "simulation_id": "s"})), \
             patch.object(client._session, "get", return_value=MagicMock(
                 raise_for_status=MagicMock(),
                 json=MagicMock(return_value={"success": True, "data": {"status": "processing"}})
             )):
            with pytest.raises(MiroFishError, match="timed out"):
                client.prepare_simulation("sim_1")


# ── wait_simulation ───────────────────────────────────────────────────────────

class TestWaitSimulation:
    def test_returns_data_on_completed(self):
        client = _client()
        run_data = {"runner_status": "completed", "total_rounds": 10}
        with patch.object(client._session, "get", return_value=MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"success": True, "data": run_data})
        )):
            result = client.wait_simulation("sim_1")
        assert result["total_rounds"] == 10

    def test_raises_on_error_status(self):
        client = _client()
        with patch.object(client._session, "get", return_value=MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"success": True, "data": {"runner_status": "error"}})
        )):
            with pytest.raises(MiroFishError):
                client.wait_simulation("sim_1")


# ── get_report ────────────────────────────────────────────────────────────────

class TestGetReport:
    def test_returns_report_text(self):
        client = _client()
        with patch.object(client._session, "get", return_value=MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"success": True, "data": {"report_text": "롱 70%"}})
        )):
            text = client.get_report("r_1")
        assert text == "롱 70%"


# ── run_full_pipeline ─────────────────────────────────────────────────────────

class TestRunFullPipeline:
    def test_returns_simulation_result(self):
        client = _client()
        seeds = {"macro": "m", "sentiment": "s", "earnings": "e"}

        with patch.object(client, "build_graph", return_value="g_1"), \
             patch.object(client, "create_simulation", return_value="sim_1"), \
             patch.object(client, "prepare_simulation"), \
             patch.object(client, "start_simulation"), \
             patch.object(client, "wait_simulation", return_value={"total_rounds": 10, "entities_count": 3}), \
             patch.object(client, "generate_report", return_value="r_1"), \
             patch.object(client, "get_report", return_value="분석 결과: 롱 72%"):
            result = client.run_full_pipeline("proj_test", seeds)

        assert isinstance(result, SimulationResult)
        assert result.simulation_id == "sim_1"
        assert result.report_id == "r_1"
        assert "롱 72%" in result.report_text
        assert result.total_rounds == 10
