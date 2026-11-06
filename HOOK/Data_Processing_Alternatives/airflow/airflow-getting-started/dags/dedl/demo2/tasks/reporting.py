from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, TypedDict

from airflow.sdk import task


class RunReportDict(TypedDict):
    """Data contract: generate_run_report task output"""
    criteria: dict[str, Any]
    downloads: dict[str, Any]
    transforms: list[dict[str, Any]]
    visualisations: list[dict[str, Any]]
    generated_at: str


def build_run_report(
    criteria: dict[str, Any],
    search_results_dict: dict[str, Any],
    transform_results: list[dict[str, Any]],
    visualise_results: list[dict[str, Any]],
) -> RunReportDict:
    """
    Build a global run report from the outputs already produced by the pipeline.

    Pure function (dict-in/dict-out): no Airflow, eodag, or S3 imports, so it
    can be unit tested directly with plain fixtures.

    Args:
        criteria: The params/config the run used (search_limit, channels,
                  search dates, collection id, reprojection settings)
        search_results_dict: extract() output; provides download_records and
                              success/failure counts
        transform_results: Outputs of the mapped transform_one task instances
        visualise_results: Outputs of the mapped visualise_one task instances

    Returns:
        RunReportDict: criteria, download stats, per-product transform
                       durations, per-channel visualisation durations
    """
    download_records = search_results_dict.get("download_records", [])

    return {
        "criteria": criteria,
        "downloads": {
            "attempted": len(download_records),
            "succeeded": search_results_dict.get("num_downloads_succeeded", 0),
            "failed": search_results_dict.get("num_downloads_failed", 0),
            "records": download_records,
        },
        "transforms": [
            {
                "nat_file": result["nat_file"],
                "zarr_path": result["zarr_path"],
                "duration_seconds": result["duration_seconds"],
            }
            for result in transform_results
        ],
        "visualisations": [
            {
                "channel": result["channel"],
                "duration_seconds": result["duration_seconds"],
                "video_s3_uri": result["video_s3_uri"],
            }
            for result in visualise_results
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@task(task_display_name="Generate run report", trigger_rule="all_done")
def generate_run_report(
    criteria: dict[str, Any],
    search_results_dict: dict[str, Any],
    transform_results: list[dict[str, Any]],
    visualise_results: list[dict[str, Any]],
) -> RunReportDict:
    """
    #### Report task: build and log a global report for the run

    Runs with trigger_rule="all_done" so it still reports download/transform
    successes and failures even if a later step (load/visualise) fails.

    Returns:
        RunReportDict: printed to task logs and returned as this task's XCom
    """
    report = build_run_report(
        criteria=criteria,
        search_results_dict=search_results_dict,
        transform_results=transform_results,
        visualise_results=visualise_results,
    )

    print(f"Run report:\n\n{json.dumps(report, indent=2, default=str)}\n")

    return report
