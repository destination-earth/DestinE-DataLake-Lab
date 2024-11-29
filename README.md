<img src="./img/DestinE-banner.jpg"
     alt="Destination Earth banner"
/>

# DestinE-DataLake-Lab

<img style="float:left; width:5%" src="./img/EUMETSAT-icon.png"/> **Author:** EUMETSAT

Destination Earth Data Lake Laboratory, which contains additional information for working with DestinE Data Lake services:
- [Harmonised Data Access](https://github.com/destination-earth/DestinE-DataLake-Lab/tree/main/HDA) (Juypter notebooks examples)


Further information available in DestinE Data Lake documentation: https://destine-data-lake-docs.data.destination-earth.eu/en/latest/index.html


>**Additional ressources:**
>- DestinE Data Portfolio: https://hda.data.destination-earth.eu/ui/catalog
>- DataLake Priority services: https://hda.data.destination-earth.eu/ui/services 
>- HDA SWAGGER UI: https://hda.data.destination-earth.eu/docs/
>

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

destinelab         0.11

Install kernel my_env. Run the command:

     python -m ipykernel install --name my_env --user

Select the kernel my_env from the top-right menu of these notebooks.

Users who already have a previous version of the 'my_env' environment installed, should delete the kernel before running the steps above. To delete the my_env kernel please run the following command: 'jupyter kernelspec uninstall my_env' from a terminal window.
