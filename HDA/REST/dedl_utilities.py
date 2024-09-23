import requests
import json

import ipywidgets as widgets
from IPython.display import display, clear_output, HTML, JSON
from ipywidgets import Layout, Box
from rich.console import Console
import rich.table

# HDA Core API
HDA_API_URL = "https://hda.data.destination-earth.eu"

# STAC API
## Core
STAC_API_URL = f"{HDA_API_URL}/stac"

## Collections
COLLECTIONS_URL = f"{STAC_API_URL}/collections"

class DEDLUtilities:
    def __init__(self,collectionId):
        self.collectionId = collectionId
        self.queryablesByCollectionId = ''
        self.outputArea = widgets.Output()
        self.dropdown = widgets.Dropdown()

    def on_collection_change(self,change):
        with self.outputArea:
            clear_output()
            print(f'Selected: {change["new"]}')
            print('---------------------------------------------')
            delimiter=''
            if(delimiter.join(change["new"])):
                self.collectionId = delimiter.join(change["new"])
            self.queryablesByCollectionId = f"{COLLECTIONS_URL}/{self.collectionId}/queryables"

            product_types = requests.get(COLLECTIONS_URL).json()['collections'] 
            index = next((i for i, d in enumerate(product_types) if d.get('id') == self.collectionId), None)

            print("TITLE: "+product_types[index]['title'])
            print("DESCRIPTION: "+product_types[index]['description'])
            print("\nQUERYABLES ENDPOINT: \n"+self.queryablesByCollectionId)
        
        
    # Function to build (filtered or not) collections dropdowns to choose one collection
    def create_collections_dropdown(self, prefix='EO.', parameters=None):

        options_all = [product_type["id"] for product_type in requests.get(COLLECTIONS_URL).json()['collections']]
        options_filtered =  [s for s in options_all if s.startswith(prefix)]
        
        self.dropdown = widgets.Dropdown(
            options=options_filtered,
            value=options_filtered [0],
            description="Collections:",
            disabled=False,
        ) 
        self.dropdown.observe(self.on_collection_change, names='value')
        
class DEDLQueryablesUtilities:
    def __init__(self,collectionId):
        self.collectionId = collectionId
        self.hdaFilters = None
        self.dropdowns = {}
        self.dropdownContainer = widgets.VBox()
        self.outputArea = widgets.Output()
            
    # Function to display queryables in a table
    def create_queryables_table(self,filters,parameters=None):
        table = rich.table.Table(title="Applicable filters", expand=True, show_lines=True)
        table.add_column("Description", style="cyan", justify="right")
        table.add_column("Type", style="violet", justify="right", no_wrap=True)
        table.add_column("enum", style="violet", justify="right")
        table.add_column("value", style="violet", justify="right", no_wrap=True)
        for filtername in filters.keys():
            if ( bool(parameters) and filtername not in parameters.keys()):
                continue
            enum=''
            if 'enum' in filters[filtername]:
                enum=' , ' .join(map(str,filters[filtername]["enum"]))
            value=''
            if'value' in filters[filtername]:
                value=json.dumps(filters[filtername]["value"])
            if'type' in filters[filtername]:
                typeq=json.dumps(filters[filtername]["type"])
            else:
                typeq=''

            if (filters[filtername]["description"] not in ['ID','Geometry','Datetime - use parameters year, month, day, time instead if available']):
                table.add_row(filters[filtername]["description"],  typeq , enum, value)
        return table

    # Function to fetch queryable properties for the given collection (self.collectionId) with optional params
    def fetch_queryables(self, parameters= None, complete= False):
        url = f"{COLLECTIONS_URL}/{self.collectionId}/queryables"
        response = requests.get(url, parameters)
        if response.status_code == 200 and complete == False:
            return response.json().get('properties', {})
        elif response.status_code == 200 and complete == True:
            return response.json()
        else:
            return None

    # Function to build dropdowns to choose the available filters for the given collection (self.collectionId) and build the corresponding HDA filter
    def update_queryables_dropdowns(self, parameters=None):
        properties = self.fetch_queryables(parameters)
        with self.outputArea:
            clear_output()
            if properties:
                #print("Properties fetched successfully.")
                #print(json.dumps(properties, indent=2))
                print("\nThe table below contains the selected parameters or their the default values' Those are visible in the column 'value'. \nDefault values will be applied by default if no value has been chosen.")
                table=self.create_queryables_table(properties, parameters)
                console = Console()
                console.print(table)
                if (parameters!=None):
                    print("The parameters chosen can be translated in the following filters for the HDA query. \n" )
                    cleaned_params = {k: v for k, v in parameters.items() if v}
                    self.hdaFilters = {
                        key: {"eq": value}
                        for key, value in cleaned_params.items()
                    }
                    print(json.dumps(self.hdaFilters, indent=4))
            else:
                print("Failed to fetch properties.")
                return
            
        # Preserve existing selected values
        selected_values = {prop: dropdown.value for prop, dropdown in self.dropdowns.items()}

        # Clear existing dropdowns
        self.dropdownContainer.children = []
        self.dropdowns.clear()

        # Create new dropdowns for properties with enum values
        new_dropdowns = []
        for prop, details in properties.items():
            if details.get('type') == 'string' and 'enum' in details:
                options = details['enum']
                options = [''] + options  # Add empty option for 'param' property

                dropdown = widgets.Dropdown(
                    description=prop,
                    options=options,
                    value=selected_values.get(prop, options[0])  # Set previously selected value or default to the first option
                )
                dropdown.observe(self.on_value_change, names='value')
                self.dropdowns[prop] = dropdown
                new_dropdowns.append(dropdown)

        if new_dropdowns:
            self.dropdownContainer.children = new_dropdowns
        else:
            with self.outputArea:
                print("No properties with enum values found.")

    # Function to update the dropdowns containing the available filters for the given collection (self.collectionId) once a new value has been chosen            
    def on_value_change(self,change):
        parameters = {prop: dropdown.value for prop, dropdown in self.dropdowns.items() if dropdown.value is not None}

        if parameters:
            details = self.fetch_queryables(parameters, complete = True)

            with self.outputArea:
                clear_output()
                #print(json.dumps(details, indent=2))

        # Update dropdowns based on the new selection
        self.update_queryables_dropdowns( parameters) 
    
    



