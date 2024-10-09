<img src="../img/DestinE-banner.jpg"
     alt="Destination Earth banner"
/>

# DestinE Harmonised Data Access (HDA)

<img style="float:left; width:5%" src="../img/EUMETSAT-icon.png"/> **Author:** EUMETSAT 
<br>

Materials to learn how to use Harmonised Data Access API and examples 

**Notebooks**
- [How to use the HDA API sending a few HTTP requests, quick-start](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/HDA/REST/HDA-REST-quick-start.ipynb)
- [How to use the HDA API sending a few HTTP requests, full-version](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/HDA/REST/HDA-full-version.ipynb)  
- [How to use the queryables HDA API to search C3S and Digital Twins data](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/HDA/REST/HDA-Queryables.ipynb)  
- *Discover, access and visualise *Digital twins data* with HDA*
  - [Plot any Climate DT parameter](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/HDA/DestinE%20Digital%20Twins/ClimateDT-ParameterPlotter.ipynb)
  - [Plot any Extreme DT parameter](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/HDA/DestinE%20Digital%20Twins/ExtremeDT-ParameterPlotter.ipynb)
  - [Climate Adaptation Digital Twin data](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/HDA/DestinE%20Digital%20Twins/DEDL-HDA-EO.ECMWF.DAT.DT_CLIMATE.ipynb)
  - [Climate Adaptation Digital Twin data - timeseries](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/HDA/DestinE%20Digital%20Twins/DEDL-HDA-EO.ECMWF.DAT.DT_CLIMATE-Series.ipynb)
  - [Extremes event  Digital Twin data - timeseries](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/HDA/DestinE%20Digital%20Twins/DEDL-HDA-EO.ECMWF.DAT.DT_EXTREMES-Series.ipynb)
  - [Extremes event  Digital Twin data - xarray](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/HDA/DestinE%20Digital%20Twins/DEDL-HDA-EO.ECMWF.DAT.DT_EXTREMES.ipynb)
- Discover, access and visualise *federated data* with HDA
    - [Discover Sentinel-3 OLCI products example](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/HDA/EUM_data/DEDL-HDA-EO.EUM.DAT.SENTINEL-3.OL_1_ERR___.ipynb)
    - [Discover AVHRR Metop products example](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/HDA/EUM_data/DEDL-HDA-EO.EUM.DAT.METOP.AVHRRL1.ipynb)
  - [Discover and visualise ERA5 products example](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/HDA/CDS_data/DEDL-HDA-EO.ECMWF.DAT.REANALYSIS_ERA5_SINGLE_LEVELS.ipynb)
- Discover and access DEDL data using EODAG client
  - [How to use the EODAG client with DEDL data, quick-start](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/HDA/EODAG/HDA-EODAG-quick-start.ipynb)
  - [How to use the EODAG client with DEDL data, full version](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/HDA/EODAG/HDA-EODAG-full-version.ipynb)
- Access DEDL data using PySTAC client
  - [Discover and access DEDL data using PySTAC client](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/HDA/PySTAC/HDA-PyStac-Client.ipynb)


Further information available in DestinE Data Lake documentation: https://destine-data-lake-docs.data.destination-earth.eu/en/latest/index.html


>**Additional ressources:**
>- DestinE Data Portfolio: https://hda.data.destination-earth.eu/ui/catalog
>- DataLake Priority services: https://hda.data.destination-earth.eu/ui/services 
>- HDA SWAGGER UI: https://hda.data.destination-earth.eu/docs/



<br>

**DestinE Core Platform Insula Users**
<br>
Please perform the following and selecte my_env kernel when running the provided Notebooks<br>

Open a terminal window and run the following commands in sequence (File, New, Terminal)

Create a virtual environment: 
     
     python -m venv /home/jovyan/my_env

Activate it: 
     
     source /home/jovyan/my_env/bin/activate

Install required dependencies for this example Notebook:

     pip install destinelab
     pip install earthkit-data
     pip install earthkit-maps
     pip install earthkit-regrid  
     pip install cf-units         
     pip install --upgrade polytope-client
     pip install ecmwflibs
     pip install cfgrib
     pip install lxml
     pip install conflator==0.1.5
     pip install folium
     pip install pystac_client
     pip install geopandas
     pip install ipywidgets
     pip install ipykernel

Verify the installation. Open the terminal and run the command:
     
     python -m cfgrib selfcheck

This should give:

Found: ecCodes v2.35.0.
Your system is ready.

Install kernel my_env. Run the command:

     ipython kernel install --user --name=my_env

Select the kernel my_env from the top-right menu of this notebook
