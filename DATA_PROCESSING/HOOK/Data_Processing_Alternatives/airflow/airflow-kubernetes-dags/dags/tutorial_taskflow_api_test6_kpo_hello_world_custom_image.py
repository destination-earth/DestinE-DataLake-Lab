from datetime import datetime
from airflow.sdk import dag, task
from airflow.providers.cncf.kubernetes.secret import Secret
from kubernetes.client import models as k8s

default_args = {
    "owner": "airflow",
    "start_date": datetime(2025, 3, 26),
}


@dag(
    dag_id="tutorial_taskflow_api_test6_kpo_hello_world_custom_image",
    schedule="@once",
    catchup=False,
    tags=["kpo", "hello_world", "dedl"],
    doc_md="""
    # Tutorial DAG
    Here we demonstrate how to use the @task.kubernetes decorator to run a task in a Kubernetes pod using a custom image that we have built and pushed to a container registry.
    The custom image is built on top of the official Python image and includes additional dependencies and code needed for the task (See Dockerfile at root of this project for details).
    
    We also show how to inject Kubernetes secrets as environment variables into the pod, which can be used for securely passing credentials without hardcoding them in the DAG or image.
    In the pod code, you would access these secrets as environment variables (e.g., `os.environ['DESP_USERNAME']` and `os.environ['DESP_PASSWORD']` in Python).
    See script-create-secret.sh for how the Kubernetes Secret is created with the values from the .env file.

    Notice that we set `do_xcom_push=True` in the @task.kubernetes decorator, which allows us to return data from the Kubernetes task and pass it to downstream tasks using the TaskFlow API.
    Notice that we pass values from the Kubernetes task to a downstream Python task using the TaskFlow API, which is a more pythonic way to pass data between tasks compared to using XComs directly.
    """,
    default_args=default_args,
)
def tutorial_taskflow_api_test6_kpo_hello_world_custom_image():

    # Kubernetes secrets
    desp_username = Secret(
        deploy_type="env",
        deploy_target="DESP_USERNAME",
        secret="my-desp-secret",
        key="username",
    )

    desp_password = Secret(
        deploy_type="env",
        deploy_target="DESP_PASSWORD",
        secret="my-desp-secret",
        key="password",
    )

    # Task running inside Kubernetes pod
    @task.kubernetes(
        task_id="hello_world_task",
        name="hello-world-python-pod",
        namespace="airflow",
        image="registry.central.data.destination-earth.eu/eum_jess_private/destine_datalakelab_kpo_example:latest",
        image_pull_policy="Always",
        labels={"foo": "bar"},
        is_delete_operator_pod=True,
        get_logs=True,
        container_resources=k8s.V1ResourceRequirements(
            requests={"cpu": "100m", "memory": "128Mi"},
            limits={"cpu": "500m", "memory": "256Mi"},
        ),
        image_pull_secrets=[{"name": "harborcred"}],
        secrets=[desp_username, desp_password],
        do_xcom_push=True,  # Push the result to XCom for the next task
    )
    def hello_world_task():
        import os
        from dedl.tools.print_tool import demo_print

        demo_print()

        username = os.environ.get("DESP_USERNAME")
        print("DESP_USERNAME:", username)

        # return JSON-serializable data for the next task
        return {"username": username, "tool_ran": True}

    # New Airflow task that logs the pod output
    @task
    def log_result(result: dict):
        print("=== Logging Pod Result ===")
        print(result)
        print("=== End of Pod Result ===")

    # Connect tasks
    # This is a pythonic way to pass data between tasks using the TaskFlow API. The output of the Kubernetes task is passed as input to the log_result task. (instead of using XComs directly)
    result = hello_world_task()
    log_result(result)


dag = tutorial_taskflow_api_test6_kpo_hello_world_custom_image()

if __name__ == "__main__":
    print("=== DAG Test Run ===")
    dag.test()
