from datetime import datetime
from airflow.sdk import dag, task
from airflow.providers.cncf.kubernetes.secret import Secret
from kubernetes.client import models as k8s

default_args = {
    "owner": "airflow",
    "start_date": datetime(2025, 3, 26),
}


@dag(
    dag_id="tutorial_taskflow_api_test5b_kpo_hello_world_python_config_map",
    schedule="@once",
    catchup=False,
    tags=["kpo", "hello_world", "dedl"],
    doc_md="""
    # Tutorial DAG
    This DAG builds on test4 by introducing the use of a ConfigMap to dynamically mount files into the Kubernetes pod.
    In production, bake your code into the image instead of mounting scripts.

    Notice that we use the @task.kubernetes decorator to define a Kubernetes task. In this way we don't really need the ConfigMap and could just put the code directly in the Python function,
    but this is for demonstration purposes to show how you could mount a ConfigMap if needed.

    """,
    default_args=default_args,
)
def tutorial_taskflow_api_test5b_kpo_hello_world_python_config_map():

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

    script_volume = k8s.V1Volume(
        name="airflow-script-vol",
        config_map=k8s.V1ConfigMapVolumeSource(name="my-script"),
    )

    script_mount = k8s.V1VolumeMount(
        name="airflow-script-vol",
        mount_path="/scripts",
    )

    @task.kubernetes(
        task_id="hello_world_task",
        name="hello-world-python-pod",
        namespace="airflow",
        image="python:3.12",
        labels={"foo": "bar"},
        is_delete_operator_pod=True,
        get_logs=True,
        volumes=[script_volume],
        volume_mounts=[script_mount],
        container_resources=k8s.V1ResourceRequirements(
            requests={"cpu": "100m", "memory": "128Mi"},
            limits={"cpu": "500m", "memory": "256Mi"},
        ),
        secrets=[desp_username, desp_password],
    )
    def hello_world_task():
        import os

        # Example: read from mounted ConfigMap file
        try:
            with open("/scripts/script.py", "r") as f:
                print("Mounted script contents:\n", f.read())
        except FileNotFoundError:
            print("No script found in /scripts (did the ConfigMap mount correctly?)")

        username = os.environ.get("DESP_USERNAME")
        print("Hello from Kubernetes Python pod!")
        print("DESP_USERNAME:", username)

    hello_world_task()


dag = tutorial_taskflow_api_test5b_kpo_hello_world_python_config_map()

if __name__ == "__main__":
    print("=== DAG Test Run ===")
    dag.test()
