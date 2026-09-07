<img src="./img/DestinE-banner.jpg"
     alt="Destination Earth banner"
/>

# DestinE-DataLake-Lab

<img style="float:left; width:5%" src="./img/EUMETSAT-icon.png"/> **Author:** EUMETSAT

Destination Earth Data Lake Laboratory, which contains additional information for working with DestinE Data Lake services:
- [Harmonised Data Access](https://github.com/destination-earth/DestinE-DataLake-Lab/tree/main/HDA) (Juypter notebooks examples on how to use HDA for *DestinE Data Portfolio* data access)
- [STACK service](https://github.com/destination-earth/DestinE-DataLake-Lab/tree/main/STACK) (Juypter Notebook examples on how to use DASK for near data processing)
- [HOOK service](https://github.com/destination-earth/DestinE-DataLake-Lab/tree/main/HOOK) (Juypter Notebook examples on how to use HOOK for workflows)


Further information available in DestinE Data Lake documentation: https://destine-data-lake-docs.data.destination-earth.eu/en/latest/index.html


>**Additional ressources:**
>- DestinE Data Portfolio: https://hda.data.destination-earth.eu/ui/catalog
>- DataLake Priority services: https://hda.data.destination-earth.eu/ui/services 
>- HDA SWAGGER UI: https://hda.data.destination-earth.eu/docs/
>

<br>

## Notebooks Execution Environment

These notebooks in this repository are designed to run in the [**DEDL STACK**](https://jupyter.central.data.destination-earth.eu/hub/) environment using the default **Python DEDL** kernel.

For users planning to run these notebooks outside the DEDL Stack environment, the file [`dedl-python-kernel-packages.txt`](dedl-python-kernel-packages.txt) provides the list of libraries currently available in the default **Python DEDL** kernel (obtained via the *pip list --format=freeze > dedl-python-kernel-packages.txt* command in the DEDL STACK) and can be used as a reference when setting up a local environment.


### Availability in Insula

A subset of these notebooks is also available to Insula users through the Insula Code environment:

https://code.insula.destine.eu/hub/

When running the notebooks in Insula, please follow the environment-specific instructions provided below. 

#### DestinE Platform Insula Service Users
<br>
Please perform the following and select my-datalake-lab kernel when running the provided Notebooks<br>

Open a terminal window (File -> New -> Terminal) and run the following commands in sequence:

Create a virtual environment: 
     
     python -m venv /home/jovyan/my-datalake-lab

Activate it: 
     
     source /home/jovyan/my_datalake_lab/bin/activate

Install required dependencies for this example Notebooks:

     pip install -r /home/jovyan/datalake-lab-insula/HDA/insula-requirements.txt

Verify the installation:
     
     pip list | grep destinelab

This should give:

destinelab         1.14

Install kernel my_env. Run the command:

     python -m ipykernel install --name my_datalake_lab --user

**Select the kernel my_datalake_lab from the top-right menu of these notebooks.**

Users who already have a previous version of the 'my_datalake_lab' environment installed, should delete the kernel before running the steps above. 

To delete the my_datalake_lab kernel please run the following command: 'jupyter kernelspec uninstall my_datalake_lab' from a terminal window.