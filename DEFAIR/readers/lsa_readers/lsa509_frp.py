import re
from os import PathLike
from typing import Any, ClassVar, Literal

import numpy as np
import xarray as xr

from defair_data.cdm import CommonDataModel, GeostationaryParams, GriddedModel, build_point_cdm
from defair_data.core import Dataset
from defair_data.data_reader_plugin import DataReaderPlugin

FCI_CENTRE = 5567.5
FCI_STEP = 1000.0
GEOS_ATTRS = {
    "grid_mapping_name": "geostationary",
    "longitude_of_projection_origin": 0.0,
    "latitude_of_projection_origin": 0.0,
    "perspective_point_height": 35786400.0,
    "sweep_angle_axis": "y",
    "semi_major_axis": 6378137.0,
    "semi_minor_axis": 6356752.31414,
    "false_easting": 0.0,
    "false_northing": 0.0,
}


class LSA509FRPReaderPlugin(DataReaderPlugin):
    """Reader for the daily Iberian cut of the LSA SAF MTG FRP-Pixel product (LSA-509)."""

    PRIORITY: ClassVar[int] = 60
    FILENAME_PATTERN: ClassVar[re.Pattern] = re.compile(r"LSA509_iberia_(\d{8})\.nc$")

    @classmethod
    def can_handle(cls, path: str | PathLike) -> bool:
        return bool(cls.FILENAME_PATTERN.search(str(path)))

    def read(
        self,
        path: str | PathLike,
        source: str | None = None,
        source_kwargs: dict[str, Any] | None = None,
        product: Literal["fires", "quality"] = "fires",
    ) -> Dataset:
        f = self.open_file(path, source, source_kwargs)
        if product == "fires":
            date = int(self.FILENAME_PATTERN.search(str(path)).group(1))
            return self._read_fires(f, date)
        return self._read_quality(f)

    @staticmethod
    def _read_fires(f, date: int) -> Dataset:
        ds = xr.open_dataset(f, engine="h5netcdf", group="ListProduct", chunks={})
        ds = ds.assign_coords(fire=date * 100_000 + ds.fire.values)
        ds = ds.set_coords(["LATITUDE_PARALLAX", "LONGITUDE_PARALLAX", "LATITUDE", "LONGITUDE", "ACQTIME"])
        ds["LATITUDE_PARALLAX"].attrs.update(standard_name="latitude", units="degrees_north")
        ds["LONGITUDE_PARALLAX"].attrs.update(standard_name="longitude", units="degrees_east")
        ds["LATITUDE"].attrs.pop("standard_name", None)
        ds["LONGITUDE"].attrs.pop("standard_name", None)
        cdm = build_point_cdm(
            reader="lsa509_frp",
            product_family="lsa_saf",
            ds=ds,
            sample_dim="fire",
            latitude="LATITUDE_PARALLAX",
            longitude="LONGITUDE_PARALLAX",
            time_coord="ACQTIME",
            time_representation="per_sample_observation",
        )
        return Dataset(ds, cdm=cdm)

    @staticmethod
    def _read_quality(f) -> Dataset:
        ds = xr.open_dataset(f, engine="h5netcdf", group="QualityProduct", chunks={"time": 1}, mask_and_scale=False)
        ds = ds.assign_coords(
            x=("samp", (ds.samp.values - FCI_CENTRE) * FCI_STEP, {"standard_name": "projection_x_coordinate", "units": "m", "axis": "X"}),
            y=("line", (FCI_CENTRE - ds.line.values) * FCI_STEP, {"standard_name": "projection_y_coordinate", "units": "m", "axis": "Y"}),
        ).swap_dims(samp="x", line="y")
        ds["qualityflag"].attrs["grid_mapping"] = "geostationary"
        ds["geostationary"] = xr.DataArray(np.int32(0), attrs=GEOS_ATTRS)
        grid = GriddedModel(
            id="lsa509_quality_grid",
            variables=("qualityflag",),
            crs="GEOS",
            dims=("y", "x"),
            x_dim="x",
            y_dim="y",
            x_coord="x",
            y_coord="y",
            grid_mapping="geostationary",
            geostationary=GeostationaryParams(
                satellite_longitude=0.0,
                perspective_point_height=35786400.0,
                sweep_axis="y",
                grid_mapping="geostationary",
            ),
        )
        cdm = CommonDataModel(reader="lsa509_frp", product_family="lsa_saf", spatial_groups=(grid,), temporal_groups=())
        return Dataset(ds, cdm=cdm)