import gzip
import io
import re
from os import PathLike
from typing import Any, ClassVar

import numpy as np
import pandas as pd
import xarray as xr

from defair_data.cdm import CommonDataModel, GeostationaryParams, GriddedModel
from defair_data.core import Dataset
from defair_data.data_reader_plugin import DataReaderPlugin

DISK_EXTENT = (-5570248.686685662, -5567248.28340708, 5567248.28340708, 5570248.686685662)
DISK_SIZE = 3712
GEOS_ATTRS = {
    "grid_mapping_name": "geostationary",
    "longitude_of_projection_origin": 0.0,
    "latitude_of_projection_origin": 0.0,
    "perspective_point_height": 35785831.0,
    "sweep_angle_axis": "y",
    "semi_major_axis": 6378169.0,
    "semi_minor_axis": 6356583.8,
    "false_easting": 0.0,
    "false_northing": 0.0,
}


class HSAFH61ReaderPlugin(DataReaderPlugin):
    """Reader for H SAF H61B daily accumulated precipitation, MSG SEVIRI full disc, gzipped NetCDF."""

    PRIORITY: ClassVar[int] = 60
    FILENAME_PATTERN: ClassVar[re.Pattern] = re.compile(r"h61_(\d{8})_0000_24_fdk\.nc\.gz$")

    @classmethod
    def can_handle(cls, path: str | PathLike) -> bool:
        return bool(cls.FILENAME_PATTERN.search(str(path)))

    def read(
        self,
        path: str | PathLike,
        source: str | None = None,
        source_kwargs: dict[str, Any] | None = None,
    ) -> Dataset:
        sealed = pd.to_datetime(self.FILENAME_PATTERN.search(str(path)).group(1))
        with self.open_file(path, source, source_kwargs) as f:
            raw = gzip.decompress(f.read())
        engine = "h5netcdf" if raw[:4] == b"\x89HDF" else "scipy"
        ds = xr.open_dataset(io.BytesIO(raw), engine=engine)[["acc_rr"]].load()
        ds = ds.rename(dict(zip(ds.acc_rr.dims, ("y", "x"))))

        dx = (DISK_EXTENT[2] - DISK_EXTENT[0]) / DISK_SIZE
        centres = np.arange(DISK_SIZE) + 0.5
        ds = ds.assign_coords(
            x=("x", DISK_EXTENT[0] + centres * dx, {"standard_name": "projection_x_coordinate", "units": "m", "axis": "X"}),
            y=("y", DISK_EXTENT[3] - centres * dx, {"standard_name": "projection_y_coordinate", "units": "m", "axis": "Y"}),
        )
        ds["acc_rr"].attrs["grid_mapping"] = "geostationary"
        ds = ds.expand_dims(time=[sealed - pd.Timedelta(days=1)])
        ds = ds.assign_coords(geostationary=xr.DataArray(np.int32(0), attrs=GEOS_ATTRS))
        ds.attrs = {"Conventions": "CF-1.8", "source": "H SAF H61B daily accumulated precipitation, MSG SEVIRI full disc"}
        return Dataset(ds.chunk(), cdm=self._build_cdm())

    @staticmethod
    def _build_cdm() -> CommonDataModel:
        grid = GriddedModel(
            id="hsaf_h61_grid",
            variables=("acc_rr",),
            crs="GEOS",
            dims=("y", "x"),
            x_dim="x",
            y_dim="y",
            x_coord="x",
            y_coord="y",
            grid_mapping="geostationary",
            geostationary=GeostationaryParams(
                satellite_longitude=0.0,
                perspective_point_height=35785831.0,
                sweep_axis="y",
                grid_mapping="geostationary",
            ),
        )
        return CommonDataModel(reader="hsaf_h61", product_family="hsaf", spatial_groups=(grid,), temporal_groups=())
