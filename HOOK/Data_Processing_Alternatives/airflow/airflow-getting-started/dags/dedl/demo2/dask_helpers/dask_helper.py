"""
Give transform_one more CPU cores when asked, and clean up afterwards.

Why: DEFAIR computes through Dask, which by default runs its tasks on threads
in one process. HEALPix reprojection is pure-Python work, and Python's GIL lets
only one thread run Python at a time, so it uses about one core. Running the
tasks in separate worker processes (each with its own GIL) makes them truly
parallel: ~121 s -> ~23 s per file with 16 workers (see docs/demo2.md,
"Speeding up HEALPix").

Usage (transform_one in the demo2 DAG):

    with local_process_cluster(dask_workers):
        ...  # Dask work here runs on the worker processes

- dask_workers = 0 (default): does nothing; DEFAIR keeps using threads.
- dask_workers = N > 0: start N single-threaded worker processes, make them
  the default Dask scheduler and hand them to DEFAIR (docs/defair.md §16.2),
  then shut everything down when the block ends.

Contents:

- local_process_cluster: the context manager. Starts an empty LocalCluster,
  scales it to N workers and waits at most startup_timeout for them. If they
  don't start, it logs a warning and falls back to threads rather than
  hanging. On exit it retires the workers, then closes the client and the
  cluster (DEFAIR closes the client but not the cluster).
- _close_cluster: closes the cluster with a time limit and logs (never raises)
  on failure, so cleanup can't hang or fail a task.
- _airflow_cli_main_as_module: needed only inside Airflow. "spawn" workers
  re-run the parent's __main__ script; in an Airflow task that is the
  `airflow` CLI, which fails in a worker (Airflow gives task processes an
  unusable database URL on purpose) and Dask would restart it forever. While
  the cluster runs, this labels that __main__ as the `airflow.__main__`
  module, which Python's multiprocessing does not re-run. Any other __main__
  (e.g. the DAG file under dag.test()) is left alone. "fork" would avoid the
  problem too, but deadlocked when run from the DAG file, so it isn't used.
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from importlib.machinery import ModuleSpec
from typing import Any

logger = logging.getLogger(__name__)


@contextmanager
def _airflow_cli_main_as_module() -> Iterator[None]:
    """
    Stop spawned worker processes from re-running the `airflow` CLI script.

    multiprocessing "spawn" children re-run the parent's __main__ script
    before starting. Inside an Airflow task, __main__ is the `airflow` console
    script: re-running it imports and initialises Airflow, which fails on the
    deliberately unusable database URL Airflow gives task processes, and the
    Dask nanny then restarts the worker forever.

    That script is equivalent to `python -m airflow`, and multiprocessing
    already skips re-running a main module whose spec name ends in
    ".__main__". So while this context is active, __main__ is described as
    the `airflow.__main__` module. Any other __main__ (e.g. a DAG file run
    directly for dag.test()) is left untouched.
    """
    main = sys.modules.get("__main__")
    main_file = getattr(main, "__file__", None)
    if (
        main is None
        or getattr(main, "__spec__", None) is not None
        or not main_file
        or os.path.basename(main_file) != "airflow"
    ):
        yield
        return

    main.__spec__ = ModuleSpec("airflow.__main__", None)
    try:
        yield
    finally:
        main.__spec__ = None


@contextmanager
def local_process_cluster(
    n_workers: int,
    *,
    start_method: str = "spawn",
    startup_timeout: float = 120.0,
) -> Iterator[Any | None]:
    """
    Run the Dask work inside this block on a local cluster of worker processes.

    DEFAIR computes lazily on Dask's threaded scheduler by default. Some
    transforms are CPU-bound Python that holds the GIL (notably HEALPix
    reprojection of MSG/SEVIRI, which rebuilds pyproj projections per block),
    so threads use about one core. Worker processes sidestep the GIL. This
    follows the "Processes, CPU-bound transform computed by a write" recipe in
    docs/defair.md (section 16.2): single-threaded workers, a client that
    is the process-wide default (so DEFAIR's Zarr write computes on it), and
    handed to DEFAIR via set_dask_client.

    n_workers <= 0 leaves DEFAIR's default (threaded scheduler) untouched and
    yields None. If the workers don't all start within startup_timeout seconds,
    the cluster is closed, a warning is logged and the block runs on the
    default threaded scheduler instead (yields None) rather than hanging.

    start_method is the multiprocessing method used to start workers
    (distributed.worker.multiprocessing-method), applied for the cluster's
    whole lifetime so restarted workers use it too. It stays Dask's default,
    "spawn": "fork" copies a process that already runs threads (Airflow,
    DEFAIR logging, the cluster's own event loop) and was seen to deadlock
    worker start-up when run from the DAG file. Inside Airflow tasks, spawn
    needs _airflow_cli_main_as_module (applied here for the cluster's
    lifetime).

    Both the client and the cluster are closed on exit: DEFAIR's
    close_dask_client() closes the client it owns, but not the LocalCluster it
    was created from. Workers are retired first; closing the client or cluster
    while workers are still connected logs CommClosedError tracebacks (harmless
    but alarming in task logs).
    """
    if n_workers <= 0:
        yield None
        return

    import dask
    from dask.distributed import Client, LocalCluster
    from defair_data.dask_manager import close_dask_client, set_dask_client

    with (
        dask.config.set({"distributed.worker.multiprocessing-method": start_method}),
        _airflow_cli_main_as_module(),
    ):
        # Start with no workers and scale up, so a worker that can't start is
        # caught by wait_for_workers' timeout instead of blocking forever.
        # dashboard_address=None: no dashboard, so concurrently running mapped
        # task instances don't compete for the default dashboard port (8787).
        cluster = LocalCluster(
            n_workers=0,
            threads_per_worker=1,
            processes=True,
            dashboard_address=None,
        )
        client = None
        try:
            client = Client(cluster, set_as_default=True)
            cluster.scale(n_workers)
            try:
                client.wait_for_workers(n_workers, timeout=startup_timeout)
            except TimeoutError:
                logger.warning(
                    "Dask: %d worker processes did not start within %.0f s "
                    "(start method %r); falling back to the threaded scheduler",
                    n_workers,
                    startup_timeout,
                    start_method,
                )
                client.close()
                client = None
                _close_cluster(cluster, timeout=10)
                cluster = None
                yield None
                return

            set_dask_client(client)
            print(
                f"Dask: local process cluster with {n_workers} single-threaded workers "
                f"(start method {start_method!r})"
            )
            yield client
        finally:
            if client is not None:
                try:
                    client.retire_workers(close_workers=True)
                finally:
                    close_dask_client()
            if cluster is not None:
                _close_cluster(cluster, timeout=30)


def _close_cluster(cluster: Any, *, timeout: float) -> None:
    """Close a LocalCluster without hanging the caller.

    Nannies whose workers keep failing to start restart them indefinitely, so
    an unbounded close() can block forever. Bound it, and log rather than fail
    the task over cleanup.
    """
    try:
        cluster.close(timeout=timeout)
    except Exception as exc:  # noqa: BLE001 - cleanup must not fail the task
        logger.warning("Dask: LocalCluster did not close cleanly: %r", exc)
