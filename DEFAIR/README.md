---
title: "DEFAIR"
author: "EUMETSAT"
---

<img src="../img/DestinE-banner.jpg"
     alt="Destination Earth banner"
/>
Materials to learn how to use **DEFAIR** ,  for AI-Ready Data)** provides tools and workflows for preparing AI-ready datasets within the Destination Earth ecosystem.

This folder contains examples to help you get started with DEFAIR.

## Notebooks

- [DEFAIR Quick Start](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/uick_start.ipynb)
  Introduction to DEFAIR and its core features.

- [DEFAIR Heatwaves Cube Creation](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/DEFAIR/DEDL_DEFAIR) workflow demonstrating the creation of a heatwaves data cube with DEFAIR.

## Documentation

Additional information is available in the DestinE Data Lake documentation:

https://destine-data-lake-docs.data.destination-earth.eu/en/latest/index.html

---

# Installing DEFAIR in DEDL JupyterLab

Follow the steps below to create a dedicated DEFAIR environment and kernel in DEDL JupyterLab.

## 1. Upload the DEFAIR distribution

Upload the latest DEFAIR artifact archive to your DEDL JupyterLab workspace and extract its contents.

## 2. Create a dedicated Conda environment

Open a terminal and create a new environment:

```bash
conda create -n defair python=3.12
```

## 3. Activate the environment

```bash
conda activate defair
```

## 4. Install the DEFAIR package

Install the DEFAIR wheel from the extracted distribution:

```bash
pip install dist/*.whl
```

## 5. Install additional dependencies

Install `tenacity`, which is required by the HDA source plugin:

```bash
pip install tenacity
```

## 6. Install Jupyter kernel support

```bash
conda install ipykernel
```

## 7. Register the DEFAIR kernel

Register the environment as a Jupyter kernel:

```bash
python -m ipykernel install --user --name defair-env --display-name "Python (defair)"
```

## 8. Run DEFAIR notebooks

When opening a DEFAIR notebook, select the **Python (defair)** kernel from the JupyterLab kernel list.

---

## Verification

To verify the installation open a new notebook selecting the **Python (defair)** kernel and run:

```python
import defair 
print(defair.__version__)"
```

If the command executes successfully and prints the installed version, DEFAIR is ready to use.