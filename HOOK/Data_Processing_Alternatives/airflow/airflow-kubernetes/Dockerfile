#Dockerfile
# https://hub.docker.com/r/apache/airflow/tags?name=3.1.7

FROM apache/airflow:3.1.7

ENV AIRFLOW_VERSION=3.1.7

# Allows basic auth on API so can trigger dags using api
ENV AIRFLOW__API__AUTH_BACKENDS="airflow.api.auth.backend.jwt"

COPY requirements.txt /

RUN echo "Airflow version: ${AIRFLOW_VERSION}"

RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /requirements.txt

# RUN pip install --no-cache-dir "apache-airflow[cncf.kubernetes]"
                                