---
title: "DEFAIR"
author: "Author: EUMETSAT"
---

<img src="../img/DestinE-banner.jpg"
     alt="Destination Earth banner"
/>



Materials to learn how to use **DEFAIR** , Destination Earth Framework for preparing AI-Ready Data

**Notebook**
- [DEFAIR Quickstart](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/DEFAIR/DEDL_DEFAIR_quick_start.ipynb): Quick start using DEFAIR, key features
- [DEFAIR heatwaves cube creation](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/DEFAIR/DEDL_DEFAIR_heatwaves_cube.ipynb)

Further information available in DestinE Data Lake documentation: https://destine-data-lake-docs.data.destination-earth.eu/en/latest/index.html


**How To Install DEFAIR in DEDL Jupyterlab**

Install  a dedicated DEFAIR environment and kernels in the DEDL JupyterLab: 

- upload the last DEFAIR artifacts archive into your DEDL JupyterLab and unzip the archive

- open a terminal and create the defair environment.

  
```bash
conda create -n defair python=3.12
```


- activate the defair environment: 

```bash
conda activate defair
```

- install DEFAIR wheelspip 

```bash
install dist/*.whl
```

- explicitly install tenacity needed for the HDA source plugin: 
```bash
pip install tenacity
```
- install ipykernel in the defair environment: 
```bash
conda install ipykernel
```
- install the “Python (defair)“ kernel to run defair notebooks. To run a DEFAIR notebook, you then choose the "Python (defair)"
```bash
kernel.python -m ipykernel install --user --name defair-env --display-name "Python (defair)"
```