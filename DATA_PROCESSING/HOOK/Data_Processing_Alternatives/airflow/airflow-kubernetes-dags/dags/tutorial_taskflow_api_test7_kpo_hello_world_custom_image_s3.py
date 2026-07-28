from datetime import datetime
from airflow.sdk import dag, task
from airflow.providers.cncf.kubernetes.secret import Secret
from kubernetes.client import models as k8s

# -----------------------------
# Default DAG arguments
# -----------------------------
default_args = {
    "owner": "airflow",
    "start_date": datetime(2025, 3, 26),
}


# -----------------------------
# DAG definition
# -----------------------------
@dag(
    dag_id="tutorial_taskflow_api_test7_kpo_hello_world_custom_image_s3",
    schedule="@once",
    catchup=False,
    tags=["kpo", "hello_world", "dedl"],
    doc_md="""
    # Tutorial DAG
    This DAG runs a custom Python image in Kubernetes, demonstrates secure credential usage, 
    See Dockerfile-defair at the root of this project for details on the custom image, which includes the Defair library and its dependencies.

    Defair logging, listing available readers, and accessing S3 buckets using environment-injected secrets.
    """,
    default_args=default_args,
)
def tutorial_taskflow_api_test7_kpo_hello_world_custom_image_s3():

    # -----------------------------
    # Kubernetes Secrets
    # -----------------------------
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

    my_s3_access_key_id = Secret(
        deploy_type="env",
        deploy_target="MY_S3_ACCESS_KEY_ID",
        secret="my-s3-credentials",
        key="my_s3_access_key_id",
    )

    my_s3_secret_access_key = Secret(
        deploy_type="env",
        deploy_target="MY_S3_SECRET_ACCESS_KEY",
        secret="my-s3-credentials",
        key="my_s3_secret_access_key",
    )

    # -----------------------------
    # Kubernetes Python task
    # -----------------------------
    @task.kubernetes(
        task_id="hello_world_task",
        name="hello-world-python-pod",
        namespace="airflow",
        image="registry.central.data.destination-earth.eu/eum_jess_private/destine_datalakelab_kpo_example_defair:latest",
        image_pull_policy="Always",
        labels={"foo": "bar"},
        is_delete_operator_pod=True,
        get_logs=True,
        container_resources=k8s.V1ResourceRequirements(
            requests={"cpu": "100m", "memory": "128Mi"},
            limits={"cpu": "500m", "memory": "256Mi"},
        ),
        image_pull_secrets=[{"name": "harborcred"}],
        secrets=[
            desp_username,
            desp_password,
            my_s3_access_key_id,
            my_s3_secret_access_key,
        ],
        do_xcom_push=True,
    )
    def hello_world_task():
        import os, sys, logging, boto3, botocore

        print("##### hello_world_task in pod #####")

        # -----------------------
        # Helper functions inside the task
        # -----------------------
        def get_desp_credentials():
            return os.environ.get("DESP_USERNAME"), os.environ.get("DESP_PASSWORD")

        def setup_defair_logging():
            from defair.logging import setup_logging

            # Human-readable output
            setup_logging(log_level="INFO")
            # JSON output for log aggregation
            setup_logging(log_level="DEBUG", json_output=True)
            # Per-module logging
            setup_logging(
                log_level="WARNING",
                module_levels={
                    "defair_data": "DEBUG",
                    "defair_ops": "INFO",
                },
            )

        def list_available_readers():
            from defair_data.readers import list_readers

            return list_readers()

        def list_s3_buckets():
            access_key = os.environ.get("MY_S3_ACCESS_KEY_ID")
            secret_key = os.environ.get("MY_S3_SECRET_ACCESS_KEY")
            s3 = boto3.resource(
                "s3",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                endpoint_url="https://s3.central.data.destination-earth.eu",
            )
            bucket_names = []
            bucket_contents = {}
            for bucket in s3.buckets.all():
                bucket_names.append(bucket.name)
                try:
                    bucket_contents[bucket.name] = [
                        obj.key for obj in bucket.objects.all()
                    ]
                except botocore.exceptions.ClientError as e:
                    logging.error(f"Could not access bucket '{bucket.name}': {e}")
                    bucket_contents[bucket.name] = None
            return bucket_names, bucket_contents

        # -----------------------
        # Main task logic
        # -----------------------
        username, password = get_desp_credentials()
        print("DESP_USERNAME:", username)

        setup_defair_logging()

        readers = list_available_readers()
        print("Available readers:", readers)

        bucket_names, bucket_contents = list_s3_buckets()
        print("Buckets available:", bucket_names)
        for bucket, objects in bucket_contents.items():
            print(f"Contents of bucket '{bucket}': {objects}")

        return {
            "desp_username": username,
            "readers": readers,
            "buckets": bucket_names,
            "bucket_contents": bucket_contents,
        }

    # New Airflow task that logs the pod output
    @task
    def log_result(result: dict):
        print("=== Logging Pod Result ===")
        print(result)
        print("=== End of Pod Result ===")

    # -----------------------------
    # Call the Kubernetes task
    # -----------------------------
    result = hello_world_task()
    log_result(result)


# -----------------------------
# Instantiate the DAG
# -----------------------------
dag = tutorial_taskflow_api_test7_kpo_hello_world_custom_image_s3()

# -----------------------------
# Local dry-run / test
# -----------------------------
if __name__ == "__main__":
    print("=== DAG Test Run ===")
    dag.test()
