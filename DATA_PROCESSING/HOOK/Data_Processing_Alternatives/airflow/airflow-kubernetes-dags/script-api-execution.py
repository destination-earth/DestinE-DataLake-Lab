import argparse
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

HTTP_TIMEOUT_STANDARD = 30
TERMINAL_DAG_STATES = {"success", "failed", "canceled"}

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TriggerConfig:
    auth_url: str
    api_url: str
    username: str
    password: str
    dag_id: str
    run_id: Optional[str]
    run_conf: Dict[str, Any]
    request_timeout: int
    wait_timeout: int
    poll_interval: int
    log_level: str

class AirflowApiClient:
    def __init__(self, api_url: str, jwt_token: str) -> None:
        if not api_url:
            raise ValueError("api_url is required.")
        if not jwt_token:
            raise ValueError("jwt_token is required.")

        self.api_url = api_url.rstrip("/")
        self.jwt_token = jwt_token

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.jwt_token}",
        }

    @staticmethod
    def get_jwt_token(username: str, password: str, auth_url: str) -> str:
        if not username or not password:
            raise ValueError("Both username and password are required.")
        if not auth_url:
            raise ValueError("auth_url is required.")

        url = f"{auth_url.rstrip('/')}/auth/token"
        data = {"username": username, "password": password}

        response = requests.post(url, json=data, timeout=HTTP_TIMEOUT_STANDARD)
        response.raise_for_status()

        payload = response.json()
        access_token = payload.get("access_token")
        if not access_token:
            raise RuntimeError("Authentication response did not include 'access_token'.")

        return str(access_token)

    def trigger_dag(
        self,
        dag_id: str,
        run_conf: Dict[str, Any],
        run_id: Optional[str] = None,
        timeout: int = HTTP_TIMEOUT_STANDARD,
    ) -> Dict[str, Any]:
        if not dag_id:
            raise ValueError("dag_id is required.")

        run_id = run_id or f"manual__{uuid.uuid4()}"
        url = f"{self.api_url}/dags/{dag_id}/dagRuns"
        data = {
            "dag_run_id": run_id,
            "logical_date": datetime.now(timezone.utc).isoformat(),
            "conf": run_conf or {},
        }

        try:
            response = requests.post(
                url,
                json=data,
                headers=self._headers,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Failed to connect to Airflow API: {exc}") from exc

        if response.status_code not in (200, 201):
            raise RuntimeError(
                f"Failed to trigger DAG {dag_id} "
                f"(HTTP {response.status_code}): {response.text}"
            )

        try:
            dag_run = response.json()
        except ValueError as exc:
            raise RuntimeError("Airflow returned a non-JSON response when triggering DAG.") from exc

        print(f"DAG '{dag_id}' triggered successfully (run_id={run_id})")
        return dag_run

    def wait_for_dag_completion(
        self,
        dag_id: str,
        run_id: str,
        timeout: int = 600,
        poll_interval: int = 10,
    ) -> str:
        elapsed = 0

        while elapsed < timeout:
            try:
                response = requests.get(
                    f"{self.api_url}/dags/{dag_id}/dagRuns/{run_id}",
                    headers=self._headers,
                    timeout=HTTP_TIMEOUT_STANDARD,
                )
                response.raise_for_status()
                payload = response.json()
            except requests.RequestException as exc:
                raise RuntimeError(f"Failed while polling DAG status: {exc}") from exc
            except ValueError as exc:
                raise RuntimeError("Airflow returned invalid JSON while polling DAG status.") from exc

            status = str(payload.get("state", "unknown")).lower()
            logger.debug("DAG run status: %s", status)

            if status in TERMINAL_DAG_STATES:
                return status

            time.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError("DAG run did not finish in time.")


def execute_trigger(config: TriggerConfig) -> Dict[str, Any]:
    jwt_token = AirflowApiClient.get_jwt_token(
        username=config.username,
        password=config.password,
        auth_url=config.auth_url,
    )
    client = AirflowApiClient(api_url=config.api_url, jwt_token=jwt_token)

    dag_run = client.trigger_dag(
        dag_id=config.dag_id,
        run_conf=config.run_conf,
        run_id=config.run_id,
        timeout=config.request_timeout,
    )

    resolved_run_id = str(dag_run.get("dag_run_id") or config.run_id or "")
    if not resolved_run_id:
        raise RuntimeError("Could not determine dag_run_id from Airflow response.")

    print("Waiting for DAG to complete...")
    status = client.wait_for_dag_completion(
        dag_id=config.dag_id,
        run_id=resolved_run_id,
        timeout=config.wait_timeout,
        poll_interval=config.poll_interval,
    )
    print(f"DAG run status: {status}")

    return dag_run


def _build_run_conf(run_conf_raw: str) -> Dict[str, Any]:
    if not run_conf_raw.strip():
        return {}
    parsed = json.loads(run_conf_raw)
    if not isinstance(parsed, dict):
        raise ValueError("run_conf must be a JSON object.")
    return parsed


def _build_config(args: argparse.Namespace) -> TriggerConfig:
    run_id = args.run_id or f"api_triggered__{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
    run_conf = _build_run_conf(args.run_conf)

    if not args.username or not args.password:
        raise ValueError("Both --username and --password are required (or set in env vars).")

    return TriggerConfig(
        auth_url=args.auth_url,
        api_url=args.api_url,
        username=args.username,
        password=args.password,
        dag_id=args.dag_id,
        run_id=run_id,
        run_conf=run_conf,
        request_timeout=args.request_timeout,
        wait_timeout=args.wait_timeout,
        poll_interval=args.poll_interval,
        log_level=args.log_level,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trigger an Airflow DAG run and wait for completion.")
    parser.add_argument(
        "--auth-url",
        default=os.getenv("AIRFLOW_AUTH_URL", "https://airflow.XXXX.YYYY.data.destination-earth.eu"),
        help="Airflow auth base URL.",
    )
    parser.add_argument(
        "--api-url",
        default=os.getenv("AIRFLOW_API_URL", "https://airflow.XXXX.YYYY.data.destination-earth.eu/api/v2"),
        help="Airflow API base URL.",
    )
    parser.add_argument(
        "--username",
        default=os.getenv("AIRFLOW_USERNAME"),
        help="Airflow username.",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("AIRFLOW_PASSWORD"),
        help="Airflow password.",
    )
    parser.add_argument(
        "--dag-id",
        default=os.getenv("AIRFLOW_DAG_ID", "tutorial_taskflow_api_test7_kpo_hello_world_custom_image_s3"),
        help="DAG ID to trigger.",
    )
    parser.add_argument(
        "--run-id",
        default=os.getenv("AIRFLOW_RUN_ID"),
        help="Optional DAG run ID. If omitted, one is generated.",
    )
    parser.add_argument(
        "--run-conf",
        default=os.getenv("AIRFLOW_RUN_CONF", '{"param1": "value1", "param2": "value2"}'),
        help="JSON object for DAG run conf.",
    )
    parser.add_argument(
        "--request-timeout",
        type=int,
        default=int(os.getenv("AIRFLOW_REQUEST_TIMEOUT", str(HTTP_TIMEOUT_STANDARD))),
        help="HTTP timeout in seconds for trigger request.",
    )
    parser.add_argument(
        "--wait-timeout",
        type=int,
        default=int(os.getenv("AIRFLOW_WAIT_TIMEOUT", "600")),
        help="Max seconds to wait for DAG completion.",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=int(os.getenv("AIRFLOW_POLL_INTERVAL", "10")),
        help="Polling interval in seconds.",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level.",
    )
    return parser.parse_args()


# add main block for testing
if __name__ == "__main__":

    # This script demonstrates triggering an Airflow DAG run via the Airflow REST API, then polling for its completion status.
    load_dotenv()
    args = _parse_args()
    config = _build_config(args)

    logging.basicConfig(
        level=getattr(logging, config.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    execute_trigger(config)
