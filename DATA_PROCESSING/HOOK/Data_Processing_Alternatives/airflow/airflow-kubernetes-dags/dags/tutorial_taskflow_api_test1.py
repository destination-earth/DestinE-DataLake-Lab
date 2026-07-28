#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from __future__ import annotations

# [START tutorial]
# [START import_module]
import json

import pendulum

from airflow.sdk import dag, task

from dedl.airflow.common import show_params


# [END import_module]


# [START instantiate_dag]
@dag(
    schedule=None,
    start_date=pendulum.datetime(2021, 1, 1, tz="UTC"),
    catchup=False,
    tags=["dedl", "example"],
)
def tutorial_taskflow_api_test1():
    """
    ### TaskFlow API tutorial DAG
    Demonstrates a minimal Extract-Transform-Load flow implemented with the
    Airflow TaskFlow API.

    The DAG also calls a reusable helper task (`show_params`) to illustrate
    how shared task utilities can be imported from project modules.

    Reference:
    https://airflow.apache.org/docs/apache-airflow/stable/tutorial_taskflow_api.html
    """
    # [END instantiate_dag]

    # [START extract]
    @task()
    def extract():
        """
        #### Extract task
        Simulates data extraction by loading a hardcoded JSON payload.
        """
        data_string = '{"1001": 301.27, "1002": 433.21, "1003": 502.22}'

        order_data_dict = json.loads(data_string)
        return order_data_dict

    # [END extract]

    # [START transform]
    @task(multiple_outputs=True)
    def transform(order_data_dict: dict):
        """
        #### Transform task
        Computes the total order value from the extracted order dictionary.
        """
        total_order_value = 0

        for value in order_data_dict.values():
            total_order_value += value

        return {"total_order_value": total_order_value}

    # [END transform]

    # [START load]
    @task()
    def load(total_order_value: float):
        """
        #### Load task
        Simulates loading by printing the computed total value.
        """

        print(f"Total order value is: {total_order_value:.2f}")

    # [END load]

    # [START main_flow]
    # Print the parameters captured for this DAG run.
    show_params()
    order_data = extract()
    order_summary = transform(order_data)
    load(order_summary["total_order_value"])
    # [END main_flow]


# [START dag_invocation]
dag_instance = tutorial_taskflow_api_test1()
# [END dag_invocation]

# [END tutorial]
if __name__ == "__main__":

    from dotenv import load_dotenv
    import os

    # Load local test values from .env (if present).
    load_dotenv()

    toto = os.getenv("TOTO", "No TOTO value found in .env file")

    # Access the generated DAG id (useful when extending local test scenarios).
    dag_id = dag_instance.dag_id

    # Simulate a DAG run locally with run configuration values.
    # This mirrors values that would normally be supplied via Airflow UI/CLI.
    dag_instance.test(
        run_conf={
            "toto": toto,
        }
    )
