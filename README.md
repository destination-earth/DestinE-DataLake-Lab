<img src="./img/DestinE-banner.jpg"
     alt="Destination Earth banner"
/>

# DestinE-DataLake-Lab

<img style="float:left; width:5%" src="./img/EUMETSAT-icon.png"/> **Author:** EUMETSAT

Destination Earth Data Lake Laboratory, this repository provides example notebooks and supporting documentation for accessing and processing data through the DestinE Data Lake services:
- [Harmonised Data Access](https://github.com/destination-earth/DestinE-DataLake-Lab/tree/main/HDA) (Juypter notebooks examples on how to use HDA for *DestinE Data Portfolio* data access)
- [STACK service](https://github.com/destination-earth/DestinE-DataLake-Lab/tree/main/STACK) (Juypter notebook examples on how to use DASK for near data processing)
- [HOOK service](https://github.com/destination-earth/DestinE-DataLake-Lab/tree/main/HOOK) (Juypter notebook examples on how to use HOOK for workflows)
- [DEFAIR framework](https://github.com/destination-earth/DestinE-DataLake-Lab/tree/main/DEFAIR) (Juypter notebook examples on how to use DEFAIR- Destination Earth Framework for AI-Ready Data)


Further information available in DestinE Data Lake documentation: https://destine-data-lake-docs.data.destination-earth.eu/en/latest/index.html


>**Additional ressources:**
>- DestinE Data Portfolio: https://hda.data.destination-earth.eu/ui/catalog
>- DataLake Priority services: https://hda.data.destination-earth.eu/ui/services 
>- HDA SWAGGER UI: https://hda.data.destination-earth.eu/docs/
>

<br>

## Notebooks Execution Environment

These notebooks in this repository are designed to run in the [**DEDL STACK**](https://jupyter.central.data.destination-earth.eu/hub/) environment using the default **Python DEDL** kernel.

The file  [`dedl-python-kernel-packages.txt`](dedl-python-kernel-packages.txt)  contains the list of packages available in the default Python DEDL kernel and can be used as a reference when reproducing the environment locally.
> **Note:** This file was generated from the DEDL Stack environment using:
>
> ```bash
> pip list --format=freeze > dedl-python-kernel-packages.txt
> ```


### Availability in Insula

A subset of these notebooks is also available to Insula users through the Insula Code environment:

https://code.insula.destine.eu/hub/

When running the notebooks in Insula, please follow the environment-specific instructions provided below. 

## Running the notebooks on Insula

Insula provides a pre-configured Jupyter kernel named **Python (datalake-lab)** that can be used to run the notebooks in this repository.

When opening a notebook, simply select **Python (datalake-lab)** from the available kernels.
 
Insula provides a pre-configured kernel named **Python (datalake-lab)**.
 
For most users, **no additional installation is required**. Simply open the notebook and select the **Python (datalake-lab)** kernel from the JupyterLab kernel list.

## ⚠️ Important

The predefined kernels are not yet available in DEDL STACK and Insula.
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

python -m pip install -r /home/jovyan/datalake-lab-insula/requirements-insula.txt 
```

### 4. Install defair kernel

```bash
     python -m ipykernel install --user --name datalake_venv --display-name "my-datalake-lab"
```

### 5. Run DEFAIR notebooks

When opening a DEFAIR notebook, select the **"my-datalake-lab"** kernel from the JupyterLab kernel list.


> ⚠️ **Kernel update notice**
>
> Users who created the `my_datalake_lab` kernel before October 2026 should recreate it by following the installation steps below.
>
> First, remove the existing kernel:
>
> ```bash
> jupyter kernelspec uninstall my_datalake_lab
> ```
>
>
> Then follow the instructions in this section to create a new environment and install the latest version of the kernel.


> 💡 **Keeping notebooks up to date**
>
> To ensure you are using the latest versions of the notebooks available in this repository, you may occasionally need to update your local clone.
>
> If you have modified notebooks locally, Git may not automatically replace them with newer versions from the repository. To reset your local copy and retrieve the latest notebook versions:
>
> 1. Select any file or notebook within the repository in the left file browser.
> 2. Open **Git** from the top menu.
> 3. Choose **Reset to Remote**.
>
> This action discards all local changes and makes your local branch exactly match the corresponding branch on the remote repository.
>
> **Warning:** Any local modifications to notebooks or other files will be permanently lost.
>

##### Troubleshooting

If the `my_datalake_lab` kernel does not appear in the notebook interface:

1. Verify that the kernel was installed successfully:
    - Confirm that my_datalake_lab appears in the output.
    - Refresh the browser page and reopen the notebook.
    - If necessary, recreate the kernel following the instructions above.