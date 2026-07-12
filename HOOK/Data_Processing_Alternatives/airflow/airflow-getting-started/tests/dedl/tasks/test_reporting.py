from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DAGS_PATH = PROJECT_ROOT / "dags"
if str(DAGS_PATH) not in sys.path:
    sys.path.insert(0, str(DAGS_PATH))

from dedl.tasks.reporting import build_run_report  # noqa: E402

CRITERIA = {
    "search_limit": 5,
    "channels": ["ch1", "ch9"],
    "search_start": "2026-05-17T00:00:00Z",
    "search_end": "2026-05-18T00:00:00Z",
    "dedl_collection_id": "EO.EUM.DAT.MSG.HRSEVIRI",
}


def test_build_run_report_counts_successful_and_failed_downloads() -> None:
    search_results_dict = {
        "download_records": [
            {
                "product_id": "p1",
                "title": "p1",
                "status": "success",
                "duration_seconds": 1.5,
                "error": None,
                "downloaded_path": "/tmp/p1",
            },
            {
                "product_id": "p2",
                "title": "p2",
                "status": "failed",
                "duration_seconds": 0.4,
                "error": "boom",
                "downloaded_path": None,
            },
        ],
        "num_downloads_succeeded": 1,
        "num_downloads_failed": 1,
    }

    report = build_run_report(
        criteria=CRITERIA,
        search_results_dict=search_results_dict,
        transform_results=[],
        visualise_results=[],
    )

    assert report["downloads"]["attempted"] == 2
    assert report["downloads"]["succeeded"] == 1
    assert report["downloads"]["failed"] == 1
    assert report["downloads"]["records"] == search_results_dict["download_records"]
    assert report["criteria"] == CRITERIA


def test_build_run_report_includes_transform_and_visualisation_durations() -> None:
    transform_results = [
        {"nat_file": "a.nat", "zarr_path": "a.zarr", "duration_seconds": 3.2},
        {"nat_file": "b.nat", "zarr_path": "b.zarr", "duration_seconds": 2.1},
    ]
    visualise_results = [
        {"channel": "ch1", "duration_seconds": 4.0, "video_s3_uri": "s3://bucket/ch1.mp4"},
    ]

    report = build_run_report(
        criteria=CRITERIA,
        search_results_dict={
            "download_records": [],
            "num_downloads_succeeded": 0,
            "num_downloads_failed": 0,
        },
        transform_results=transform_results,
        visualise_results=visualise_results,
    )

    assert report["transforms"] == [
        {"nat_file": "a.nat", "zarr_path": "a.zarr", "duration_seconds": 3.2},
        {"nat_file": "b.nat", "zarr_path": "b.zarr", "duration_seconds": 2.1},
    ]
    assert report["visualisations"] == [
        {"channel": "ch1", "duration_seconds": 4.0, "video_s3_uri": "s3://bucket/ch1.mp4"},
    ]


def test_build_run_report_handles_all_downloads_failed() -> None:
    search_results_dict = {
        "download_records": [
            {
                "product_id": "p1",
                "title": "p1",
                "status": "failed",
                "duration_seconds": 0.1,
                "error": "network error",
                "downloaded_path": None,
            },
        ],
        "num_downloads_succeeded": 0,
        "num_downloads_failed": 1,
    }

    report = build_run_report(
        criteria=CRITERIA,
        search_results_dict=search_results_dict,
        transform_results=[],
        visualise_results=[],
    )

    assert report["downloads"]["succeeded"] == 0
    assert report["downloads"]["failed"] == 1
    assert report["transforms"] == []
    assert report["visualisations"] == []


def test_build_run_report_sets_generated_at_timestamp() -> None:
    report = build_run_report(
        criteria=CRITERIA,
        search_results_dict={
            "download_records": [],
            "num_downloads_succeeded": 0,
            "num_downloads_failed": 0,
        },
        transform_results=[],
        visualise_results=[],
    )

    assert isinstance(report["generated_at"], str)
    assert report["generated_at"]
