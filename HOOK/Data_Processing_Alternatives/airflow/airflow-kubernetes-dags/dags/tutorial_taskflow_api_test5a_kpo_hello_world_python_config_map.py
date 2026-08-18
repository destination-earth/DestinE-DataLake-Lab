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
    dag_id="tutorial_taskflow_api_test5a_kpo_hello_world_python_config_map",
    schedule="@once",
    catchup=False,
    tags=["kpo", "hello_world", "dedl"],
    doc_md="""
    # Tutorial DAG
    This DAG builds on test4 by introducing the use of a ConfigMap to dynamically mount a Python script into the Kubernetes pod. 
    This is for testing purposes only, and allows the rapid injection of code into the pod without needing to bake it into a custom image. 
    In production, it is generally recommended to bake your code into a custom image for better version control and reproducibility.

    Notice that we are not using the @task.kubernetes decorator in this DAG, but instead directly instantiating a KubernetesPodOperator.

    It is perhaps preferred to use the @task.kubernetes decorator for better readability and to leverage Airflow's TaskFlow API features, but both approaches are valid for running Kubernetes tasks in Airflow.
    The secrets are also injected as environment variables, which can be accessed in the mounted script. 
    """,
) as dag:

    # When the Kubernetes pod starts up, takes the value stored as a Kubernetes Secret and injects it into the pod as an envrironment variable.
    # This is a common pattern for securely passing credentials to pods without hardcoding them in the DAG or image.
    # In the pod code, you would access these secrets as environment variables (e.g., `os.environ['DESP_USERNAME']` and `os.environ['DESP_PASSWORD']` in Python).
    # See script-create-secret.sh for how the Kubernetes Secret is created with the values from the .env file.
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

    example_kpo = KubernetesPodOperator(
        task_id="hello_world_task",
        name="hello-world-python-pod",
        namespace="airflow",
        image="python:3.12",
        labels={"foo": "bar"},
        is_delete_operator_pod=True,
        get_logs=True,
        cmds=["python", "/scripts/script.py"],
        volumes=[script_volume],
        volume_mounts=[script_mount],
        container_resources=k8s.V1ResourceRequirements(
            requests={"cpu": "100m", "memory": "128Mi"},
            limits={"cpu": "500m", "memory": "256Mi"},
        ),
        secrets=[desp_username, desp_password],
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
