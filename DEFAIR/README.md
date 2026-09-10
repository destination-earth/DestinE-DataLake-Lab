---
title: "DEFAIR"
author: "EUMETSAT"
---

<img src="../img/DestinE-banner.jpg"
     alt="Destination Earth banner"
/>
Materials to learn how to use **DEFAIR** ,  **(Destination Earth Framework for AI-Ready Data)** provides tools and workflows for preparing AI-ready datasets within the Destination Earth ecosystem.

This folder contains examples to help you get started with DEFAIR as well as more structured ML use cases examples.

# Notebooks Overview

- [DEFAIR Quick Start](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/DEDL_DEFAIR_quick_start.ipynb)
  Introduction to DEFAIR and its core features.

- [DEFAIR readers & writers](DEDL_DEFAIR_readers_writers_tour.ipynb) Overview of the available DEFAIR readers and writers, with practical usage examples.

- [DEFAIR Monthly air temperature regression](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/DEFAIR/Monthly_air_temperature_regression.ipynb)  estimates the mean 2 m air temperature of June 2026 over Central and Western Europe from satellite observations of surface temperature alone, using the DEFAIR AI-ready data framework end to end. 

# Documentation

Additional information is available in the DestinE Data Lake documentation:

https://destine-data-lake-docs.data.destination-earth.eu/en/latest/index.html

# Prerequisites
- Python 3.12
- The following instructions asuumes that the users have the latest DEFAIR artifact archive

# Installation Instructions

-----
## Installing DEFAIR in Insula
Follow the steps below to create a dedicated DEFAIR environment and kernel in Insula code.

### 1. Upload the DEFAIR distribution
Upload the latest DEFAIR artifact archive (https://gitlab.eumetsat.int/defair/defair-core/-/jobs/2263273/artifacts/browse/dist) to your Insula workspace and extract its contents.

```bash
unzip artifacts.zip
```

### 2. Create a dedicated environment

Open a terminal window (File-> New-> Terminal) and run the following command to create a new environment:

```bash
python -m venv /home/jovyan/defair_venv
```

### 3. Activate the environment

```bash
source /home/jovyan/defair_venv/bin/activate
```

### 4. Install the required dependencies

Install required dependencies for these example Notebooks:
     
```bash

python -m pip install -r /home/jovyan/datalake-lab-insula/DEFAIR/requirements-insula.txt \
       ./dist/defair-0.4.0rc2-py3-none-any.whl \
       ./dist/defair_data-0.4.0rc2-py3-none-any.whl \
       ./dist/defair_ops-0.4.0rc2-py3-none-any.whl
```

### 5. Install defair kernel

```bash
     python -m ipykernel install --user --name defair_env --display-name "Python (defair)"
```

Select the kernel defair from the top-right menu of these notebooks.

### 6. Run DEFAIR notebooks

When opening a DEFAIR notebook, select the **Python (defair)** kernel from the JupyterLab kernel list.

### 7. Verification

To verify the installation open a new notebook selecting the **Python (defair)** kernel and run:

```python
import defair 
print(defair.__version__)"
```

If the command executes successfully and prints the installed version, DEFAIR is ready to use.


-----
## Installing DEFAIR in DEDL STACK JupyterLab

Follow the steps below to create a dedicated DEFAIR environment and kernel in DEDL JupyterLab.

### 1. Upload the DEFAIR distribution

Upload the latest DEFAIR artifact archive (https://gitlab.eumetsat.int/defair/defair-core/-/jobs/2263273/artifacts/browse/dist) to your Insula workspace and extract its contents.

```bash
unzip artifacts.zip
```

### 2. Create a dedicated environment

Open a terminal window (File-> New-> Terminal) and run the following command to create a new environment:

```bash
python -m venv /home/jovyan/defair_venv
```

### 3. Activate the environment

```bash
source /home/jovyan/defair_venv/bin/activate
```

### 4. Install the required dependencies

Install required dependencies for these example Notebooks:
     
```bash

python -m pip install -r /home/jovyan/DestinE-DataLake-Lab/DEFAIR/requirements-stack.txt \
       ./dist/defair-0.4.0rc2-py3-none-any.whl \
       ./dist/defair_data-0.4.0rc2-py3-none-any.whl \
       ./dist/defair_ops-0.4.0rc2-py3-none-any.whl
```

### 5. Install defair kernel

```bash
     python -m ipykernel install --user --name defair_env --display-name "Python (defair)"
```

Select the kernel defair from the top-right menu of these notebooks.

### 6. Run DEFAIR notebooks

When opening a DEFAIR notebook, select the **Python (defair)** kernel from the JupyterLab kernel list.

### 7. Verification

To verify the installation open a new notebook selecting the **Python (defair)** kernel and run:

```python
import defair 
print(defair.__version__)"
```

If the command executes successfully and prints the installed version, DEFAIR is ready to use.

-----
## Installing DEFAIR locally

https://cloudferro-dedl-staging.readthedocs-hosted.com/en/latest/working_with_ai_in_the_data_lake/defair/installation.html

# Troubleshooting

If you encounter any issues:

1. Log in to the DESP platform.
2. Open a support ticket at: https://platform.destine.eu/contact/
3. When submitting the ticket, select "DEFAIR" as the affected service.
4. The support team will assist you in diagnosing and resolving the issue.

# Additional Resources
For more information about DEFAIR, please refer to the documentation:

https://cloudferro-dedl-staging.readthedocs-hosted.com/en/latest/working_with_ai_in_the_data_lake/defair