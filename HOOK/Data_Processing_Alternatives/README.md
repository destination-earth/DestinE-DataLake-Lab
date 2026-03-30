# Data Processing Alternatives

Here we show some data processing alternatives that may be of use to you.

## Airflow

### Airflow Getting Started

- This project shows how to run airflow in a simple standalone mode (airflow standalone). This allows you to get started quickly and understand the main concepts.
  - [airflow-getting-started](https://github.com/destination-earth/DestinE-DataLake-Lab/tree/main/HOOK/Data_Processing_Alternatives/airflow/airflow-getting-started)

### Airflow on Kubernetes

- Here we show how to run airflow on Kubernetes using the official Helm chart. This is a more production-ready setup and allows you to scale your airflow instance as needed.
- When running this section references airflow-kubernetes-dags, which contains some example DAGs that you can use to test your airflow setup.
  - [airflow-on-kubernetes](https://github.com/destination-earth/DestinE-DataLake-Lab/tree/main/HOOK/Data_Processing_Alternatives/airflow/airflow-kubernetes)

### Airflow Kubernetes DAGs

- This section is intended to be used in conjunction with the airflow on kubernetes section. It contains some example DAGs that you can use to test your airflow setup.
- You should copy the code and create your own reposoitory from it. It is then referenced in helm/overide-values.yaml and used with the gitSync mechanism in airflow that allows you to pull the DAGs from a git repository. This way you can easily manage your DAGs and keep them in sync with your airflow instance. 
  - [airflow-kubernetes-dags](https://github.com/destination-earth/DestinE-DataLake-Lab/tree/main/HOOK/Data_Processing_Alternatives/airflow/airflow-kubernetes-dags)