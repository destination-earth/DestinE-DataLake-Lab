import json

from airflow.sdk import task
from dedl.config.collections import fetch_collection_ids


@task(task_display_name="Show run parameters")
def show_params(**kwargs) -> None:

    params = kwargs["params"]
    print(
        f"This DAG was triggered with the following parameters:\n\n{json.dumps(params, indent=4)}\n"
    )

    HDA_COLLECTIONS = fetch_collection_ids()
    print(f"LOOK==>Fetched {len(HDA_COLLECTIONS)} collections from HDA STAC API.")

    json_object = {
        "run_conf": kwargs["params"],
    }

    return json_object
