from datetime import datetime
from airflow.sdk import dag, task
from airflow.providers.cncf.kubernetes.secret import Secret
from kubernetes.client import models as k8s

default_args = {
    "owner": "airflow",
    "start_date": datetime(2025, 3, 26),
}


@dag(
    dag_id="tutorial_taskflow_api_test4_kpo_hello_world_python_secret",
    schedule="@once",
    catchup=False,
    tags=["kpo", "hello_world", "dedl"],
    doc_md="""
    # Tutorial DAG
    This DAG demonstrates the use of the Kubernetes TaskFlow decorator
    to run a simple "Hello World" task in a Kubernetes pod, with secrets injected
    as environment variables.

    The @task.kubernetes decorator allows you to specify the image, commands, and other configurations for the pod that will execute the task, while also leveraging Airflow's TaskFlow API features for better readability and maintainability.
    It is more pythonic and integrates better with the TaskFlow API compared to directly using KubernetesPodOperator, while still providing the same functionality for running Kubernetes tasks in Airflow.
    """,
    default_args=default_args,
)
def tutorial_taskflow_api_test4_kpo_hello_world_python_secret():

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

    @task.kubernetes(
        task_id="hello_world_task",
        name="hello-world-python-pod",
        namespace="airflow",
        image="python:3.12",
        labels={"foo": "bar"},
        is_delete_operator_pod=True,
        get_logs=True,
        container_resources=k8s.V1ResourceRequirements(
            requests={"cpu": "100m", "memory": "128Mi"},
            limits={"cpu": "500m", "memory": "256Mi"},
        ),
        secrets=[desp_username, desp_password],
    )
    def hello_world_task():
        import os

        username = os.environ.get("DESP_USERNAME")

        print("Hello from Kubernetes Python pod!")
        print("DESP_USERNAME:", username)

    hello_world_task()


dag = tutorial_taskflow_api_test4_kpo_hello_world_python_secret()

# -----------------------------
# Local test / dry-run section
# -----------------------------
if __name__ == "__main__":
    print("=== DAG Test Run ===")
    dag.test()
