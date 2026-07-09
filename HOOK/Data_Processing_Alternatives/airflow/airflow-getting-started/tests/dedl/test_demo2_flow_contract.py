from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DAGS_PATH = PROJECT_ROOT / "dags"
if str(DAGS_PATH) not in sys.path:
    sys.path.insert(0, str(DAGS_PATH))

from airflow.sdk.definitions.param import DagParam  # noqa: E402
from dedl.eodag.eodag_helper import filter_and_sort_nat_files  # noqa: E402
from dedl import tutorial_taskflow_api_demo2 as demo2  # noqa: E402


def test_transform_contract_ignores_stale_folder_files() -> None:
    stale_folder_files = [
        "/home/eouser/eodag_downloads/msg_hrseviri/old_20260701091531.nat",
        "/home/eouser/eodag_downloads/msg_hrseviri/old_20260701093000.nat",
    ]

    extract_output = {
        "search_results": 2,
        "downloaded_nat_files": [
            "/home/eouser/eodag_downloads/msg_hrseviri/new_20260708091531.nat",
            "/home/eouser/eodag_downloads/msg_hrseviri/new_20260708093000.nat",
        ],
    }

    selected_for_transform = filter_and_sort_nat_files(
        extract_output["downloaded_nat_files"]
    )

    assert [path.name for path in selected_for_transform] == [
        "new_20260708091531.nat",
        "new_20260708093000.nat",
    ]
    assert all(path.name.startswith("new_") for path in selected_for_transform)
    assert all(path.name not in {Path(p).name for p in stale_folder_files} for path in selected_for_transform)


def test_channel_param_resolves_from_dag_run_conf(monkeypatch) -> None:
    monkeypatch.setattr(
        demo2,
        "get_current_context",
        lambda: {
            "dag_run": SimpleNamespace(conf={"channel": "ch1"}),
            "params": {},
        },
    )

    channel_param = DagParam(demo2.dag, "channel", default="ch9")

    assert demo2._normalize_channel(channel_param) == "ch1"


def test_channels_param_resolves_from_dag_run_conf(monkeypatch) -> None:
    monkeypatch.setattr(
        demo2,
        "get_current_context",
        lambda: {
            "dag_run": SimpleNamespace(conf={"channels": ["ch1", "ch9"]}),
            "params": {},
        },
    )

    channels_param = DagParam(demo2.dag, "channels", default="ch9")

    assert demo2._normalize_channels(channels_param) == ["ch1", "ch9"]


def test_normalize_channels_deduplicates_list_entries() -> None:
    assert demo2._normalize_channels(["ch1", "ch9", "ch1"]) == ["ch1", "ch9"]


def test_normalize_channels_rejects_string_input() -> None:
    try:
        demo2._normalize_channels("ch1")
    except TypeError as exc:
        assert str(exc) == "channels must be a list of strings"
    else:
        raise AssertionError("Expected TypeError for string channel input")
