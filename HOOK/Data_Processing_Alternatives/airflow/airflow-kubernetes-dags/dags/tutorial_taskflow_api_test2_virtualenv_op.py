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
def tutorial_taskflow_api_test2_virtualenv_op():
    """
    ### TaskFlow API Tutorial Documentation
    This is a simple data pipeline example which demonstrates the use of
    the TaskFlow API using three simple tasks for Extract, Transform, and Load.
    Documentation that goes along with the Airflow TaskFlow API tutorial is
    located

    We demonstrate the use of `virtualenv` in the TaskFlow API which allows you to run Python code in an isolated environment with its own dependencies. This is useful for avoiding dependency conflicts and ensuring
    that your tasks have the necessary libraries without affecting the global Python environment.

    If you use the virtualenv feature it is recommended to use system_site_packages=False to ensure that the virtual environment is fully isolated and does not have access to any packages installed in the system Python environment. This helps to prevent dependency conflicts and ensures that your tasks run with only the specified dependencies.

    [here](https://airflow.apache.org/docs/apache-airflow/stable/tutorial_taskflow_api.html)
    """
    # [END instantiate_dag]

    # [START extract]
    @task.virtualenv(
        requirements=["requests==2.32.3"],
        system_site_packages=False,
        multiple_outputs=False,
    )
    def extract():
        """
        #### Extract task
        A simple Extract task to get data ready for the rest of the data
        pipeline. In this case, getting data is simulated by reading from a
        hardcoded JSON string.
        """

        import json               # must be inside the function because of virtualenv
        import requests           # runtime dependency
        
        data_string = '{"1001": 301.27, "1002": 433.21, "1003": 502.22}'

        order_data_dict = json.loads(data_string)
        return order_data_dict

    # [END extract]

    # [START transform]
    @task.virtualenv(
        requirements=["requests==2.32.3"],
        system_site_packages=False,
        multiple_outputs=True,
    )
    def transform(order_data_dict: dict):
        """
        #### Transform task
        A simple Transform task which takes in the collection of order data and
        computes the total order value.
        """
        total_order_value = 0

        for value in order_data_dict.values():
            total_order_value += value

        return {"total_order_value": total_order_value}

    # [END transform]

    # [START load]
    @task.virtualenv(
        requirements=["requests==2.32.3"],
        system_site_packages=False,
        multiple_outputs=False,
    )
    def load(total_order_value: float):
        """
        #### Load task
        A simple Load task which takes in the result of the Transform task and
        instead of saving it to end user review, just prints it out.
        """

        print(f"Total order value is: {total_order_value:.2f}")

    # [END load]

    # [START main_flow]
    # Show the parameters captured from the DAG run
    show_params()    
    order_data = extract()
    order_summary = transform(order_data)
    load(order_summary["total_order_value"])
    # [END main_flow]


# [START dag_invocation]
dag_instance = tutorial_taskflow_api_test2_virtualenv_op()
# [END dag_invocation]

# [END tutorial]
if __name__ == "__main__":

    from dotenv import load_dotenv
    import os

    # Load the .env file used for tests
    load_dotenv()

    toto = os.getenv("TOTO", "No TOTO value found in .env file")

    # get dag_id for test run conf
    dag_id = dag_instance.dag_id

    # This simulates a DAG run for testing purposes, passing in the conf parameters as if they were passed in from the Airflow UI or CLI when triggering a DAG run.
    # This allows you to test how your DAG would behave with different parameters without having to actually trigger runs from the Airflow UI or CLI.
    dag_instance.test(
        run_conf={
            "toto": toto,
        }
    )
