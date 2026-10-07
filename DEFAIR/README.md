---
title: "DEFAIR"
author: "EUMETSAT"
---

<img src="../img/DestinE-banner.jpg"
     alt="Destination Earth banner"
/>
**DEFAIR (Destination Earth Framework for AI-Ready Data)** learning materials. DEFAIR provides tools and workflows for preparing AI-ready datasets within the Destination Earth ecosystem.

This folder contains a collection of examples ranging from introductory tutorials to more structured machine learning use cases, helping you get started and explore DEFAIR's capabilities.


## DEFAIR Documentation

The official DEFAIR documentation is available within the DestinE Data Lake documentation:

- [DEFAIR documentation](https://destine-data-lake-docs.data.destination-earth.eu/en/latest/working_with_ai_in_the_data_lake/defair/defair.html)


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

## Prerequisites
 
To run these notebooks you will need:
 
- Python 3.10 or newer
- A configured DEFAIR environment, either:
- Locally
- On [Insula](https://code.insula.destine.eu)
- On the [DEDL STACK JupyterLab](https://jupyter.central.data.destination-earth.eu) platform

## DEFAIR environment prepared locally

[Install DEFAIR locally](https://destine-data-lake-docs.data.destination-earth.eu/en/latest/working_with_ai_in_the_data_lake/defair/installation/installation.html)

## Running the notebooks on Insula

Insula provides a pre-configured Jupyter kernel named **Python (datalake-lab)** that can be used to run the notebooks in this repository.

When opening a notebook, simply select **Python (datalake-lab)** from the available kernels.

## Important
 
Insula provides a pre-configured kernel named **Python (datalake-lab)**.
 
For most users, **no additional installation is required**. Simply open the notebook and select the **Python (datalake-lab)** kernel from the JupyterLab kernel list.
 
Only follow the setup instructions below if the **Python (datalake-lab)** kernel is not available.

### 1. Create a dedicated environment

Open a terminal window (File-> New-> Terminal) and run the following command to create a new environment:

```bash
python -m venv /home/jovyan/datalake_venv
```

### 2. Activate the environment

```bash
source /home/jovyan/datalake_venv/bin/activate
```

### 3. Install the required dependencies

Install required dependencies for these example Notebooks:
     
```bash

python -m pip install -r /home/jovyan/datalake-lab-insula/DEFAIR/requirements-insula.txt 
```

### 4. Install defair kernel

```bash
     python -m ipykernel install --user --name datalake_venv --display-name "my-datalake-lab"
```

### 5. Run DEFAIR notebooks

When opening a DEFAIR notebook, select the **"my-datalake-lab"** kernel from the JupyterLab kernel list.

### 6. Verification

To verify the installation open a new notebook selecting the **Python (defair)** kernel and run:

```python
import defair 
print(defair.__version__)"
```

If the command executes successfully and prints the installed version, DEFAIR is ready to use.

# Runnning these notebooks in DEDL STACK JupyterLab

DEDL STACK JupyterLab has an already prepared kernel to run the provided DestinE-DataLake-Lab examples that is called **Python (defair)**
When opening a DEFAIR notebook, select the **Python (defair)** kernel from the JupyterLab kernel list.

## Important
 
DEDL STACK JupyterLab provides a pre-configured kernel named **Python (defair)**.
 
For most users, **no additional installation is required**. Simply open the notebook and select the **Python (defair)** kernel from the JupyterLab kernel list.
 
Only follow the setup instructions below if the **Python (defair)** kernel is not available.

If the **Python (defair)** kernel is not available, you can create your own dedicated environment and register a custom kernel named **my-defair** by following the instructions below.

### 1. Create a dedicated environment

Open a terminal window (File-> New-> Terminal) and run the following command to create a new environment:

```bash
python -m venv /home/jovyan/defair_venv
```

### 2. Activate the environment

```bash
source /home/jovyan/defair_venv/bin/activate
```

### 3. Install the required dependencies

Install required dependencies for these example Notebooks:
     
```bash

python -m pip install  "defair[notebooks]==0.4.3" "numpy==2.3.4" "xarray==2025.11.0"
```
> **Note:** some notebooks in this folder requires also the torch and cartopy packages to run. To save space in your JupyterLab server install the torch and cartopy packages packages only when you want to run the notebooks that import the 2 packages
>
> ```bash
> pip install torch cartopy
> ```

### 4. Install defair kernel

```bash
     python -m ipykernel install --user --name defair_venv --display-name "my-defair"
```

### 5. Run DEFAIR notebooks

When opening a DEFAIR notebook, select the **"my-defair"** kernel from the JupyterLab kernel list.

### 6. Verification

To verify the installation open a new notebook selecting the **my-defair** kernel and run:

```python
import defair 
print(defair.__version__)"
```

If the command executes successfully and prints the installed version, DEFAIR is ready to use.


# Troubleshooting

If you encounter any issues:

1. Log in to the [DESP platform](https://platform.destine.eu).
2. Open a support ticket at: https://platform.destine.eu/contact/
3. When submitting the ticket, select "DEFAIR" as the affected service.
4. The support team will assist you in diagnosing and resolving the issue.
   
