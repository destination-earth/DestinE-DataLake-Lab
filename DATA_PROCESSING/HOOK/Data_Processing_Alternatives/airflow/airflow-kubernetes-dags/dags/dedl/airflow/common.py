import json
from airflow.sdk import task


@task(task_display_name="Show used parameters")
def show_params(**kwargs) -> dict[str, object]:
    """
    #### Show parameters task
    Prints the DAG run parameters and returns them as a small payload.

    This demonstrates that shared project code can expose reusable Airflow tasks
    and be imported into DAG modules.
    """
    params = kwargs["params"]
    print(
        f"This DAG was triggered with the following parameters:\n\n{json.dumps(params, indent=4)}\n"
    )

    json_object = {
        "run_conf": kwargs["params"],
    }

    return json_object
