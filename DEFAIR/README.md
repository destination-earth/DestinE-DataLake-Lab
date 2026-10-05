---
title: "DEFAIR"
author: "EUMETSAT"
---

<img src="../img/DestinE-banner.jpg"
     alt="Destination Earth banner"
/>
**DEFAIR (Destination Earth Framework for AI-Ready Data)** learning materials. DEFAIR provides tools and workflows for preparing AI-ready datasets within the Destination Earth ecosystem.

This folder contains a collection of examples ranging from introductory tutorials to more structured machine learning use cases, helping you get started and explore DEFAIR's capabilities.

# DEFAIR Documentation

The complete DEFAIR documentation is available as part of the DestinE Data Lake documentation: [DEFAIR documentation](https://destine-data-lake-docs.data.destination-earth.eu/en/latest/working_with_ai_in_the_data_lake/defair/defair.html)

# Examples Overview

## Getting Started
- [DEDL_DEFAIR_quick_start.ipynb](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/DEFAIR/DEDL_DEFAIR_quick_start.ipynb.ipynb) A hands-on introduction to DEFAIR covering the core concepts and APIs needed to start working with AI-ready Earth observation data.

- [DEDL_DEFAIR_Reading_geostationary_product](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/DEFAIR/DEDL_DEFAIR_Reading_geostationary_product.ipynb)  Demonstrates how to read, explore, and visualize geostationary satellite products with DEFAIR.

- [DEDL_DEFAIR_Reading_polar_orbiter_products](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/DEFAIR/DEDL_DEFAIR_Reading_polar_orbiter_products.ipynb) Demonstrates how to read and work with polar-orbiting satellite products using DEFAIR readers.

- [DEDL_DEFAIR_geo_leo_collocation](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/DEFAIR/DEDL_DEFAIR_geo_leo_collocation.ipynb) Illustrates the collocation of geostationary and low-Earth-orbit (LEO) observations to build harmonized datasets.

- [DEDL_DEFAIR_Building_heterogeneous_data_cube_using_defair](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/DEFAIR/DEDL_DEFAIR_Building_heterogeneous_data_cube_using_defair.ipynb) Demonstrates how to integrate multiple heterogeneous datasets into a common data cube using DEFAIR.

## Machine Learning Use Cases
- [LightningCast_create_data_cube_using_defair](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/DEFAIR/LightningCast_create_data_cube_using_defair.ipynb) Builds the data cube required for the LightningCast use case by combining satellite and auxiliary datasets.
 **Goal**: Learn how to prepare structured training data for deep-learning applications with DEFAIR.

- [DEDL_DEFAIR_Lightning_nowcasting_prediction_with_DeepLearning](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/DEFAIR/DEDL_DEFAIR_Lightning_nowcasting_prediction_with_DL.ipynb) Applies a deep-learning workflow to perform short-term lightning prediction using a DEFAIR-generated data cube.**Goal**: Demonstrate an end-to-end AI workflow, from data preparation to lightning nowcasting.

- [DEDL_DEFAIR_FireIgnition_lightning_with_machine_learning](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/DEFAIR/DEDL_DEFAIR_FireIgnition_lightning_with_machine_learning.ipynb)
 Explores a machine-learning use case focused on predicting lightning-induced fire ignition risk from Earth observation data.
 **Goal**: Show how DEFAIR supports model development for environmental monitoring applications.

# Prerequisites
- Python>= 3.10

# DEFAIR Installation Instructions

[Install DEFAIR locally](https://destine-data-lake-docs.data.destination-earth.eu/en/latest/working_with_ai_in_the_data_lake/defair/installation/installation.html)

# Runnning these notebooks in Insula

When opening a DEFAIR notebook, select the **Python (defair)** kernel from the JupyterLab kernel list.

# Runnning these notebooks in DEDL STACK JupyterLab

When opening a DEFAIR notebook, select the **Python (defair)** kernel from the JupyterLab kernel list.

# Troubleshooting

If you encounter any issues:

1. Log in to the [DESP platform](https://platform.destine.eu).
2. Open a support ticket at: https://platform.destine.eu/contact/
3. When submitting the ticket, select "DEFAIR" as the affected service.
4. The support team will assist you in diagnosing and resolving the issue.
------------
# THE BELOW SECTIONS MUST BE REMOVED ALMOST TOTALLY WHEN THE PREDEFINED KERNELS ARE READY
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