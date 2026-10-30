import re
from os import PathLike
from typing import Any, ClassVar

import numpy as np
import pandas as pd
import xarray as xr

from defair_data.cdm import CommonDataModel, GeostationaryParams, GriddedModel
from defair_data.core import Dataset
from defair_data.data_reader_plugin import DataReaderPlugin

# The disc: the standard SEVIRI full disc at 3 km (satpy area msg_seviri_fes_3km)
DISK_SIZE = 3712
DISK_EXTENT = (-5570248.686685662, -5567248.28340708, 5567248.28340708, 5570248.686685662)
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


class LSAFRMReaderPlugin(DataReaderPlugin):
    """Reader for the LSA SAF MSG Fire Risk Map (FRM), Euro window, HDF5."""

    PRIORITY: ClassVar[int] = 60
    FILENAME_PATTERN: ClassVar[re.Pattern] = re.compile(r"LSASAF_MSG_FRM-F\d{3}_Euro_\d{12}$")
    DEFAULT_VARIABLES: ClassVar[list[str]] = ["FWI", "FFMC", "DMC", "DC", "Risk"]

    @classmethod
    def can_handle(cls, path: str | PathLike) -> bool:
        return bool(cls.FILENAME_PATTERN.search(str(path)))

    def read(
        self,
        path: str | PathLike,
        source: str | None = None,
        source_kwargs: dict[str, Any] | None = None,
        variables: list[str] | None = None,
    ) -> Dataset:
        variables = variables or self.DEFAULT_VARIABLES
        with self.open_file(path, source, source_kwargs) as f:
            raw = xr.open_dataset(f, engine="h5netcdf", phony_dims="sort", mask_and_scale=False)
            ds = raw[variables].load()

        ds = ds.rename({"phony_dim_0": "y", "phony_dim_1": "x"})
        for v in variables:
            a = ds[v].attrs
            ds[v].attrs = {
                "scale_factor": np.float32(1 / a["SCALING_FACTOR"]),
                "add_offset": np.float32(a["OFFSET"]),
                "_FillValue": np.int16(a["MISSING_VALUE"]),
                "long_name": a["PRODUCT"],
                "units": "1",
                "grid_mapping": "geostationary",
            }
        ds = xr.decode_cf(ds)

        # The window: where this file starts within the disc, from its CGMS attributes
        coff, loff = int(raw.attrs["COFF"]), int(raw.attrs["LOFF"])   # window column and row of the disc centre, counted from 1
        centre = DISK_SIZE // 2                                        # the same disc centre in the full disc, counted from 0
        col0, row0 = centre - (coff - 1), centre - (loff - 1)

        # The coordinates: the centre of every column and row, in metres, in the view of the satellite
        dx = (DISK_EXTENT[2] - DISK_EXTENT[0]) / DISK_SIZE
        x = DISK_EXTENT[0] + (col0 + np.arange(ds.sizes["x"]) + 0.5) * dx
        y = DISK_EXTENT[3] - (row0 + np.arange(ds.sizes["y"]) + 0.5) * dx
        ds = ds.assign_coords(
            x=("x", x, {"standard_name": "projection_x_coordinate", "units": "m", "axis": "X"}),
            y=("y", y, {"standard_name": "projection_y_coordinate", "units": "m", "axis": "Y"}),
        )

        time = pd.to_datetime(str(raw.attrs["IMAGE_ACQUISITION_TIME"]), format="%Y%m%d%H%M%S")
        ds = ds.expand_dims(time=[time])
        ds = ds.assign_coords(geostationary=xr.DataArray(np.int32(0), attrs=GEOS_ATTRS))
        ds.attrs = {
            "Conventions": "CF-1.8",
            "source": "LSA SAF Fire Risk Map, MSG SEVIRI Euro window",
            "time_range": raw.attrs["TIME_RANGE"],
            "nominal_product_time": str(raw.attrs["NOMINAL_PRODUCT_TIME"]),
        }
        return Dataset(ds.chunk(), cdm=self._build_cdm(variables))

    @staticmethod
    def _build_cdm(variables: list[str]) -> CommonDataModel:
        grid = GriddedModel(
            id="lsa_frm_grid",
            variables=tuple(variables),
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
        return CommonDataModel(reader="lsa_frm", product_family="lsa_saf", spatial_groups=(grid,), temporal_groups=())