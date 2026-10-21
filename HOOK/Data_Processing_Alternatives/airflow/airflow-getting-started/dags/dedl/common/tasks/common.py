import json

from airflow.sdk import task
from dedl.common.config.collections import fetch_collection_ids


@task(task_display_name="Show run parameters")
def show_params(**kwargs) -> None:

    params = kwargs["params"]
    print(
        f"This DAG was triggered with the following parameters:\n\n{json.dumps(params, indent=4)}\n"
    )

    # Best-effort only: this is a demo call to the DEDL HDA STAC API, not
    # required for the pipeline itself, so a network hiccup here shouldn't
    # fail (or burn retries on) an otherwise-healthy run.
    try:
        hda_collections = fetch_collection_ids()
        print(f"Fetched {len(hda_collections)} collections from HDA STAC API.")
    except Exception as exc:
        print(f"Could not fetch collections from HDA STAC API (non-fatal): {exc}")

    json_object = {
        "run_conf": kwargs["params"],
    }

    return json_object
