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

**Python script**
- [Authentification package](https://github.com/destination-earth/DestinE-DataLake-Lab/blob/main/HDA/dedl_authentication.py)

Further information available in DestinE Data Lake documentation: https://destine-data-lake-docs.data.destination-earth.eu/en/latest/index.html


>**Additional ressources:**
>- DestinE Data Portfolio: https://hda.data.destination-earth.eu/ui/catalog
>- DataLake Priority services: https://hda.data.destination-earth.eu/ui/services 
>- HDA SWAGGER UI: https://hda.data.destination-earth.eu/docs/

<br>

**DestinE Core Platform Insula Users**
<br>
Please perform the following and selecte my_env kernel when running the provided Notebooks<br>
If you have done already for ECMWF notebooks, make sure to add ipywidgets

Open a terminal window and run the following commands in sequence (File, New, Terminal)

Create a virtual environment: 
     
     python -m venv /home/jovyan/my_env

Activate it: 
     
     source /home/jovyan/my_env/bin/activate

Install required dependencies for this example Notebook:

     pip install earthkit-data
     pip install earthkit-maps
     pip install earthkit-regrid  
     pip install cf-units         
     pip install --upgrade polytope-client
     pip install ecmwflibs
     pip install cfgrib
     pip install lxml
     pip install conflator==0.1.5
     pip install ipykernel
     pip install ipywidgets

Verify the installation. Open the terminal and run the command:
     
     python -m cfgrib selfcheck

This should give:

Found: ecCodes v2.34.1.
Your system is ready.

Install kernel my_env. Run the command:

     ipython kernel install --user --name=my_env

Select the kernel my_env from the top-right menu of this notebook
