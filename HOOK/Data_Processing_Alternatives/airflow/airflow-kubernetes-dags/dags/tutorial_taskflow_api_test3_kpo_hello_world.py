from datetime import datetime
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.providers.cncf.kubernetes.secret import Secret

from kubernetes.client import models as k8s

# Default DAG arguments
default_args = {
    "owner": "airflow",
    "start_date": datetime(2025, 3, 26),
}

# Define the DAG
with DAG(
    dag_id="tutorial_taskflow_api_test3_kpo_hello_world",
    schedule="@once",
    catchup=False,
    tags=["kpo", "hello_world", "dedl"],
    doc_md="""
    # Tutorial DAG
    This DAG demonstrates the use of the KubernetesPodOperator to run a simple "Hello World" task in a Kubernetes pod. 
    The operator allows you to specify the image, commands, and other configurations for the pod that will execute the task.
    """,
) as dag:

    example_kpo = KubernetesPodOperator(
        task_id="hello_world_task",
        name="hello-world",
        namespace="airflow",
        image="hello-world",
        labels={"foo": "bar"},
        is_delete_operator_pod=True,  # Delete pod after completion
        get_logs=True,  # Stream logs to Airflow UI
    )


# -----------------------------
# Local test / dry-run section
# -----------------------------
if __name__ == "__main__":
    # Dry-run: prints what would happen without executing a pod
    # print("=== Dry Run ===")
    # example_kpo.dry_run()

    # Optional: uncomment below to actually run the DAG locally in test mode
    print("=== DAG Test Run ===")
    dag.test()
