<img src="./img/DestinE-banner.jpg"
     alt="Destination Earth banner"
/>

# DestinE-DataLake-Lab

<img style="float:left; width:5%" src="./img/EUMETSAT-icon.png"/> **Author:** EUMETSAT

Destination Earth Data Lake Laboratory, this repository provides example notebooks and supporting documentation for accessing and processing data through the DestinE Data Lake services:
- [Harmonised Data Access](https://github.com/destination-earth/DestinE-DataLake-Lab/tree/main/HDA) (Juypter notebooks examples on how to use HDA for *DestinE Data Portfolio* data access)
- [STACK service](https://github.com/destination-earth/DestinE-DataLake-Lab/tree/main/STACK) (Juypter notebook examples on how to use DASK for near data processing)
- [HOOK service](https://github.com/destination-earth/DestinE-DataLake-Lab/tree/main/HOOK) (Juypter notebook examples on how to use HOOK for workflows)


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

#### DestinE Platform Insula Service Users
<br>
To run these notebooks in Insula, create the `my_datalake_lab` environment and kernel by following the steps below.<br>

Open a terminal window (File -> New -> Terminal) and run the following commands in sequence:

1. Create a virtual environment.: 
     
     python -m venv /home/jovyan/my_datalake_lab

2. Activate the environment: 
     
     source /home/jovyan/my_datalake_lab/bin/activate

3. Install the required dependencies:

     pip install -r /home/jovyan/datalake-lab-insula/HDA/insula-requirements.txt

4. Verify the installation:
     
     pip list | grep destinelab

     This should give:

     destinelab         1.14

5. Install the Jupyter kernel:

     python -m ipykernel install --name my_datalake_lab --user

6. **Select the `my_datalake_lab` kernel from the notebook kernel menu.**

> ⚠️ **Kernel update notice**
>
> Users who created the `my_datalake_lab` kernel before September 2026 should recreate it by following the installation steps below.
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