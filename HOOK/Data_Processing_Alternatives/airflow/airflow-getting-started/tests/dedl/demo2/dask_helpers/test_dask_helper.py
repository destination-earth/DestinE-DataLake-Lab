from __future__ import annotations

import sys
import types
from pathlib import Path

import dask
import dask.array as da
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DAGS_PATH = PROJECT_ROOT / "dags"
if str(DAGS_PATH) not in sys.path:
    sys.path.insert(0, str(DAGS_PATH))

from dedl.demo2.dask_helpers.dask_helper import (  # noqa: E402
    _airflow_cli_main_as_module,
    local_process_cluster,
)


def test_zero_workers_leaves_default_scheduler() -> None:
    with local_process_cluster(0) as client:
        assert client is None
        assert da.ones(10, chunks=5).sum().compute() == 10


def test_process_cluster_computes_then_shuts_down() -> None:
    from dask.distributed import Client
    from defair_data.dask_manager import DaskClientManager

    with local_process_cluster(1) as client:
        assert client is not None
        assert Client.current() is client
        assert da.ones(10, chunks=5).sum().compute() == 10

    assert client.status == "closed"
    assert DaskClientManager().get_client() is None
    # Global default is restored: computes again on the local scheduler.
    with dask.config.set(scheduler="threads"):
        assert da.ones(10, chunks=5).sum().compute() == 10


def test_falls_back_to_threads_when_workers_do_not_start(monkeypatch: pytest.MonkeyPatch) -> None:
    # Workers that never come up (e.g. a broken start method) must neither hang
    # the task nor leave a client registered: the block runs on threads.
    from dask.distributed import Client
    from defair_data.dask_manager import DaskClientManager

    def never_ready(self, n_workers, timeout=None):
        raise TimeoutError

    monkeypatch.setattr(Client, "wait_for_workers", never_ready)
    with local_process_cluster(1, startup_timeout=1) as client:
        assert client is None
        assert da.ones(10, chunks=5).sum().compute() == 10

    assert DaskClientManager().get_client() is None


def test_airflow_cli_main_is_described_as_module_only_inside_context(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_main = types.ModuleType("__main__")
    fake_main.__file__ = "/venv/bin/airflow"
    fake_main.__spec__ = None
    monkeypatch.setitem(sys.modules, "__main__", fake_main)

    with _airflow_cli_main_as_module():
        assert fake_main.__spec__.name == "airflow.__main__"
    assert fake_main.__spec__ is None


def test_other_main_scripts_are_left_untouched(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_main = types.ModuleType("__main__")
    fake_main.__file__ = "/project/dags/dedl/demo2/tutorial_taskflow_api_demo2.py"
    fake_main.__spec__ = None
    monkeypatch.setitem(sys.modules, "__main__", fake_main)

    with _airflow_cli_main_as_module():
        assert fake_main.__spec__ is None
