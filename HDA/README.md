<img src="../img/DestinE-banner.jpg"
     alt="Destination Earth banner"
/>

# DestinE Harmonised Data Access (HDA)

<img style="float:left; width:5%" src="../img/EUMETSAT-icon.png"/> **Author:** EUMETSAT 
<br>

Materials to learn how to use Harmonised Data Access API and examples 

**Notebooks**
- Discover, access and visualise *Digital twins data* with HDA
  - [How to use the HDA API by sending a few HTTP requests](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/DataLake-Lab-EarlyUserTesting/HDA/HDA-REST-quick-start.ipynb)
  - [Plot any Climate DT parameter](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/DataLake-Lab-EarlyUserTesting/HDA/ClimateDT-ParameterPlotter.ipynb)
  - [Climate Adaptation Digital Twin data](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/DataLake-Lab-EarlyUserTesting/HDA/DEDL-HDA-EO.ECMWF.DAT.DT_CLIMATE.ipynb)
  - [Discover and visualise Sentinel-3 OLCI products example](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/DataLake-Lab-EarlyUserTesting/HDA/DEDL-HDA-EO.EUM.DAT.SENTINEL-3.OL_1_ERR___.ipynb)

Further information available in DestinE Data Lake documentation: https://destine-data-lake-docs.data.destination-earth.eu/en/latest/index.html

>**Additional ressources:**
>- DestinE Data Portfolio: https://hda.data.destination-earth.eu/ui/catalog
>- DataLake Priority services: https://hda.data.destination-earth.eu/ui/services 
>- HDA SWAGGER UI: https://hda.data.destination-earth.eu/docs/
>- DestinE-DataLake-Lab: https://github.com/destination-earth/DestinE-DataLake-Lab

<br>

**DestinE Core Platform Insula Users**
<br>
Please perform the following and select my_env kernel when running the provided Notebooks<br>

Open a terminal window (File, New, Terminal) and run the following commands in sequence:

Create a virtual environment: 
     
     python -m venv /home/jovyan/my_env

Activate it: 
     
     source /home/jovyan/my_env/bin/activate

Install required dependencies for this example Notebooks:

     pip install -r /home/jovyan/datalake-lab/requirements.txt

Verify the installation:
     
     pip list | grep destinelab

This should give:

destinelab         0.9

Install kernel my_env. Run the command:

     python -m ipykernel install --name my_env --user

Select the kernel my_env from the top-right menu of these notebooks.

Users who already have a previous version of the 'my_env' environment installed, should delete the kernel before running the steps above. To delete the my_env kernel please run the following command: 'jupyter kernelspec uninstall my_env' from a terminal window.
