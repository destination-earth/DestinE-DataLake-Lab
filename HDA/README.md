<img src="../img/DestinE-banner.jpg"
     alt="Destination Earth banner"
/>

# DestinE Harmonised Data Access (HDA)

<img style="float:left; width:5%" src="../img/EUMETSAT-icon.png"/> **Author:** EUMETSAT 
<br>

Materials to learn how to use Harmonised Data Access API and examples 

**Notebooks**
- Discover, access and visualise *Digital twins data* with HDA
  - [Plot any Climate DT parameter](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/HDA/ClimateDT-ParameterPlotter.ipynb)
  - [Climate Adaptation Digital Twin data](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/HDA/DEDL-HDA-EO.ECMWF.DAT.DT_CLIMATE.ipynb)
  - [Discover and visualise ERA5 products example](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/HDA/DEDL-HDA-EO.ECMWF.DAT.REANALYSIS_ERA5_SINGLE_LEVELS.ipynb)

Further information available in DestinE Data Lake documentation: https://destine-data-lake-docs.data.destination-earth.eu/en/latest/index.html

>**Additional ressources:**
>- DestinE Data Portfolio: https://hda.data.destination-earth.eu/ui/catalog
>- DataLake Priority services: https://hda.data.destination-earth.eu/ui/services 
>- HDA SWAGGER UI: https://hda.data.destination-earth.eu/docs/
>- DestinE-DataLake-Lab: https://github.com/destination-earth/DestinE-DataLake-Lab

<br>

**DestinE Core Platform Insula Users**
<br>
Required Python dependencies are seamleass integrated within Insula Code Lab environment for all users.<br>
For authentication, users need to add the `destinelab` module.

Open a terminal window and run:
    
    pip install destinelab

Verify the installation. Open the terminal and run the command:
     
     python -m cfgrib selfcheck

This should give:

Found: ecCodes v2.34.1.
Your system is ready.

Install kernel my_env. Run the command:

     ipython kernel install --user --name=my_env

Select the kernel my_env from the top-right menu of this notebook
