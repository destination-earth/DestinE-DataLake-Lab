# EUMETSAT Data Notebooks - Installation Guide

This folder contains Jupyter notebooks for accessing and processing EUMETSAT data from the DestinE Data Lake using the Harmonized Data Access (HDA) API.

## Notebooks Overview

- **DEDL-HDA-EO.EUM.DAT.METOP.AVHRRL1.ipynb**: Access and visualize AVHRR Level 1B Metop data
- **DEDL-HDA-EO.EUM.DAT.MSG-1.5.ipynb**: Access and visualize High Rate SEVIRI Level 1.5 MSG data
- **DEDL-HDA-EO.EUM.DAT.MTG.ipynb**: Access and visualize MTG FCI data
- **DEDL-HDA-EO.EUM.DAT.SENTINEL-3.OL_1_ERR___.ipynb**: Access and visualize OLCI Level 1B Sentinel-3 data

## Prerequisites

- Python 3.8 or higher
- A [DestinE user account](https://platform.destine.eu/)
- Internet connection to access the DestinE Data Lake

## Installation Instructions

### Option 1: Using pip

#### Step 1: Create a Virtual Environment (Recommended)

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

#### Step 2: Install Required Dependencies

```bash
pip install -r requirements.txt
```

### Option 2: Using uv (Fast Alternative)

[uv](https://github.com/astral-sh/uv) is a modern, fast Python package installer and resolver.

#### Step 1: Install uv

```bash
# On macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows:
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or using pip:
pip install uv
```

#### Step 2: Create a Virtual Environment and Install Dependencies

```bash
# Create a virtual environment
uv venv

# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt
```

## Required Packages

All required packages are listed in [requirements.txt](requirements.txt), including:

- **destinelab**: Authentication for DestinE services
- **requests**: HTTP library for API calls
- **tqdm**: Progress bar for downloads
- **satpy**: Satellite data processing library
- **pyspectral**: Spectral calculations for satellite data
- **xarray**: N-dimensional labeled arrays and datasets
- **numpy**: Numerical computing library
- **matplotlib**: Plotting and visualization library
- **pyresample**: Resampling of satellite data
- **jupyter/jupyterlab**: For running notebooks locally (optional)

## Running the Notebooks

After installing the dependencies, you can run the notebooks:

1. **Launch Jupyter Notebook or JupyterLab**:
   ```bash
   jupyter lab
   ```
   
   Note: Jupyter is included in requirements.txt. If not installed, run:
   ```bash
   pip install jupyter jupyterlab
   # Or with uv:
   uv pip install jupyter jupyterlab
   ```

2. **Navigate** to the notebook you want to run

3. **Provide your DestinE credentials** when prompted in the first cell

## Troubleshooting

### Import Errors

If you encounter import errors, ensure all packages are installed in the active environment:

```bash
# Verify installed packages
pip list

# Or with uv
uv pip list
```

### Authentication Issues

- Ensure you have a valid [DestinE account](https://platform.destine.eu/)
- Check that your credentials are correct
- Verify your internet connection

### Data Download Issues

- Ensure you have sufficient disk space for downloads
- Check your network connection stability
- Verify that you're authenticated properly before attempting downloads

## Additional Resources

- [DestinE Data Lake Documentation](https://destine-data-lake-docs.data.destination-earth.eu/)
- [Satpy Documentation](https://satpy.readthedocs.io/)
- [EUMETSAT Navigator](https://navigator.eumetsat.int/)
