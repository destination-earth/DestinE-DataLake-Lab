# DEFAIR

**DEFAIR** (Destination Earth Framework for Preparing AI-Ready Data) is a Python framework
for processing satellite data with streaming workflows. It is the tool used within the
Destination Earth Data Lake (DEDL) to turn raw Earth observation (EO) product formats into
"AI-ready" cloud-optimized datasets, ready to feed downstream machine learning pipelines.

## Why it matters

Raw satellite products arrive in a wide range of instrument- and mission-specific formats
(e.g. MSG SEVIRI native files, MTG FCI/LI NetCDF, METOP products, Sentinel-3, ERA5 GRIB).
These formats are rarely convenient for ML workloads: they're not chunked for cloud access,
often mix irrelevant variables/regions, and aren't guaranteed to be CF-metadata compliant.

DEFAIR bridges that gap. It reads these heterogeneous formats through a common `Dataset`
abstraction, lets you filter/subset/reproject/align the data, and writes the result out as
cloud-optimized Zarr (or NetCDF4), with CF-1.13 compliant metadata and automatic processing
history tracking. Because it's built on Dask, it can process datasets lazily and in
streaming batches, keeping peak memory bounded even for very large EO products. The
resulting datasets are designed to plug directly into ML tooling such as `anemoi-datasets`,
xarray-based training pipelines, SatPy, and Earthkit.

## Package layout

DEFAIR ships as three cooperating Python packages.

### `defair` — core / orchestration

- The `defair` CLI application (`defair run --config workflow.yaml [--dry-run]`), which
  parses a YAML workflow, prints a rich-table execution plan (input stage, transformation
  stage, output stage), and executes it.
- `defair.models.workflow.WorkflowConfig` — loads/validates workflow YAML
  (`WorkflowConfig.from_yaml("workflow.yaml")`) and exposes `get_execution_plan()`.
- `defair.execute.execute_workflow(workflow)` — runs a validated `WorkflowConfig`.
- `defair.plugin_manager` — discovers and loads readers, writers, and transformations
  registered via entry points; exposes `list_readers()`, `list_writers()`,
  `list_transformations()`, `load_reader()`, `load_writer()`, `load_transformation()`.
- `defair.logging` — `setup_logging(log_level=..., json_output=..., module_levels=...)` for
  human-readable or JSON-structured logs, with per-module log-level overrides, and
  `get_logger(__name__)` for module loggers.
- `defair.cf_metadata` / `defair.cf_history_mixin` — CF (Climate and Forecast) conventions
  support. `CF_VERSION = "CF-1.13"`. The `CFHistoryMixin` class provides a
  `@CFHistoryMixin.track_history(include_params=[...])` decorator that automatically appends
  a timestamped entry to a dataset's `history` attribute whenever a decorated method runs.
- `defair.kwargs_validation` — validates plugin/operation keyword arguments against expected
  schemas.
- S3 credentials support: `S3CredentialsPlugin` and `propagate_s3_credentials()` push S3
  credentials through to Dask workers for remote reads/writes.
- `defair.profiling` — lightweight execution profiling hooks.

### `defair_data` — I/O layer

- `defair_data.core.Dataset` — the central data object wrapping an xarray `Dataset` with
  DEFAIR-specific methods (`from_source`, `to_file`, `transform`, `reproject`, `isel`,
  `list_variables`, `validate_cf`, `select_grid`, `with_cdm`, `copy`). Backed by Dask arrays
  when `use_dask=True`/streaming is enabled.
- `defair_data.cdm` — the Common Data Model, used for multi-grid datasets (e.g. combining
  products defined on different spatial grids within one `Dataset`).
- `defair_data.dask_manager.DaskClientManager` — a singleton manager ensuring only one Dask
  client exists across all readers/writers/transformations in a process. Helper functions:
  `set_dask_client(client)` to register an externally created client (e.g. a
  multiprocessing `LocalCluster` or a Dask Gateway cluster), and `close_dask_client()` to
  tear it down.
- `defair_data.data_reader_plugin.DataReaderPlugin`, `data_writer_plugin.DataWriterPlugin`,
  `data_source_plugin` — base classes for the three plugin kinds.
- **Reader plugins** (`defair_data.readers`), one Python class per instrument/product,
  each declaring `SUPPORTED_EXTENSIONS` and a `PRIORITY`:
  - `msg15` — MSG SEVIRI native format (`msg15nat`)
  - `mtg_fci` — MTG FCI Level 1c (`mtg_fci_l1c_nc`) and Level 2 products: AMV, ASR
    (all-sky radiance), CLM (cloud mask), GII (global instability index), OCA (optimal
    cloud analysis), OLR (outgoing longwave radiation)
  - `mtg_li` — MTG Lightning Imager products: AF (accumulated flashes), AFA, AFR,
    LEF (lightning events filtered), LFL (lightning flashes), LGR (lightning groups)
  - `metop` — ~28 EUMETSAT METOP product readers, including AMSU-L1, ASCAT SZF/SZO/SZR
    (B and R02/1B variants), AVHRR L1 and AVHRR-derived AMV, EDLST (land surface
    temperature), GLBSST (global sea surface temperature), GOME L1 (and R03 variant),
    HIRS L1 and FDR, IASI L1C-ALL and IASI SND02, MHS L1, OSI SAF products (OSI104,
    OSI150A, OSI150B), and SOMO12/SOMO25 (soil moisture)
  - `sentinel3` — OLCI Level 1 (EFR, ERR) and Level 2 (WFR, WRR), SLSTR Level 1 (RBT),
    SLSTR-derived AOD and FRP, SRAL Level 1 (SRA, SRA-A, SRA-BS) and Level 2 (WAT), and
    WST (sea surface temperature)
  - `era5_grib` — ECMWF ERA5 reanalysis GRIB files (`era5grib`)
  - `planck` — Planck mission products
- **Source plugins** (`defair_data.sources`) abstract *where* bytes come from, independent
  of the reader: `local` (filesystem), `s3` (object storage, with `endpoint_url` /
  credentials), and `hda` (Harmonized Data Access, DEDL's discovery/access API).
- **Writer plugins** (`defair_data.writers`): `zarrv2`, `zarrv3` (cloud-optimized, chunked,
  supports `consolidated` metadata and `auto_chunk`/`chunk_size_mb`), and `netcdf4`.

### `defair_ops` — transformation layer

- `defair_ops.core.TransformationPlugin` — base class; each plugin exposes a `name`
  property (the operation name used in workflow YAML/`.transform()` calls) and a
  `transform(dataset, target, **kwargs)` method.
- `defair_ops.handlers` — dispatches operations to the correct registered plugin.
- **Registered transformations** (`defair_ops.transformations`):
  - `content_filter` — keep/drop variables via `include_vars` / `exclude_vars`
  - `spatial_filter` — subset by `lat_min`/`lat_max`/`lon_min`/`lon_max` (or
    `min_lat`/`max_lat`/`min_lon`/`max_lon` depending on plugin version)
  - `temporal_filter` — subset by `start_time` / `end_time`
  - `temporal_aggregate` — resample/aggregate over time, e.g. `method="mean"`,
    `frequency="1h"`
  - `alignment` — regrid and merge multiple named inputs onto a common target grid/CRS
    (`target`, `target_resolution`, `spatial_method`, `temporal_method`, `time_bounds`,
    `conflict_resolution`)
  - `reprojection` — coordinate reference system transform and resampling (`target`,
    `resampling`, `resolution`, `bounds`), backed by geometry-validation utilities
- `defair_ops.dask_manager` — transformation-side access to the shared Dask client via
  `DaskClientManager` for operations that need distributed execution explicitly (most
  transformations rely on xarray's automatic Dask handling and don't need this).

## Core `Dataset` API

```python
from defair_data.core import Dataset

# Load: auto-detects reader from extension/content, or pass reader= explicitly
dataset = Dataset.from_source(
    "/path/to/MSG3-SEVIRI-file.nat",
    reader="",              # "" = auto-detect; or e.g. "msg15nat"
    source="",               # "" = auto-detect; or "local" / "s3" / "hda"
    source_kwargs=None,      # e.g. S3 endpoint_url / credentials
    concat_dim="time",
    streaming=None,           # or True / DEFAIR_STREAMING_MODE=on env var
    stream_batch_size=None,
    use_dask=True,
)

# Inspect
print(list(dataset.data.data_vars))
print(dataset.list_variables())
dataset.validate_cf(strict=False)   # CF-1.13 compliance check

# Transform (fluent chaining)
result = (
    dataset
    .transform("content_filter", include_vars=["ch1", "ch9"])
    .transform("spatial_filter", lat_min=35, lat_max=45, lon_min=5, lon_max=20)
    .transform("reprojection", target="EPSG:4326", resolution=0.05, resampling="bilinear")
)

# Write: auto-detects writer from extension, or pass writer= explicitly
result.to_file(
    "/path/to/output.zarr",
    writer="zarrv2",
    mode="w",
    consolidated=True,    # faster metadata reads
    auto_chunk=True,      # cloud-optimized chunking
    chunk_size_mb=10,
)
```

Other notable methods: `Dataset.reproject(target, resampling="bilinear", resolution=None,
bounds=None, backend=None, **kwargs)` (direct reprojection without the transform-plugin
indirection), `Dataset.isel(...)` for index-based subsetting, `Dataset.select_grid(grid_id)`
and `Dataset.with_cdm(cdm)` for Common Data Model / multi-grid datasets.

Loading from S3 and writing to S3 both go through `source_kwargs`/`storage_options`:

```python
dataset = Dataset.from_source(
    "s3://bucket/path/to/file.nat",
    source="s3",
    source_kwargs={
        "endpoint_url": "https://s3.example.com",
        "aws_access_key_id": "YOUR_KEY",
        "aws_secret_access_key": "YOUR_SECRET",
    },
)

dataset.to_file(
    "s3://bucket/path/to/output.zarr",
    writer="zarrv2",
    storage_options={
        "key": "YOUR_KEY",
        "secret": "YOUR_SECRET",
        "endpoint_url": "https://s3.example.com",
    },
)
```

Logging is configured separately:

```python
from defair.logging import setup_logging

setup_logging(log_level="INFO")                          # human-readable
setup_logging(log_level="DEBUG", json_output=True)        # JSON, for log aggregation
setup_logging(
    log_level="WARNING",
    module_levels={"defair_data": "DEBUG", "defair_ops": "INFO"},
)
```

## Two ways to run it

### 1. Python API

As shown above — used interactively or in notebooks. DEFAIR ships 54 demo Jupyter notebooks
covering end-to-end, per-instrument pipelines (MSG SEVIRI, MTG FCI/LI, ~30 METOP products,
Sentinel-3 OLCI/SLSTR/SRAL), plus cross-cutting demos for SatPy interop
(`09_msg_satpy_scene`), Earthkit/xarray interop (`41_earthkit_xarray_interop`), exporting to
`anemoi-datasets` format for ML training (`48_anemoi_zarr_export`), the HTTP API service
(`48_defair_api_service_demo`), and a multi-source Mediterranean datacube
(`d27_increment_a_demo`).

### 2. Declarative YAML workflows (CLI)

Workflows are reproducible, version-controlled pipeline definitions with three sections —
`inputs`, `transformations`, `outputs` — executed via `defair run`.

**Simple filtering example** — read MSG SEVIRI, filter by time, write NetCDF4:

```yaml
name: "MSG Temporal Filtering"
description: "Filter MSG SEVIRI data by time range"

inputs:
  - id: msg
    reader:
      name: "msg15nat"
    source:
      fs_type: local
      path: test-data/MSG2-SEVI-MSG15-0100-NA-20251008074241.503000000Z-NA.nat

transformations:
  - operation: "temporal_filter"
    apply_to: msg
    start_time: "2025-10-08T00:00:00"
    end_time: "2025-10-08T12:00:00"

outputs:
  - writer: "netcdf4"
    path: output/filtered.nc
```

**Multi-step pipeline** — Dask-chunked read, temporal + spatial + content filtering, then
hourly aggregation, written to cloud-optimized Zarr:

```yaml
name: "MSG Multi-Step Processing"

inputs:
  - id: msg
    reader:
      name: "msg15nat"
      chunks: { time: 1, y: 1024, x: 1024 }
    source:
      fs_type: local
      path: test-data/MSG2-SEVI-MSG15-0100-NA-20251008074241.503000000Z-NA.nat

transformations:
  - operation: "temporal_filter"
    apply_to: msg
    start_time: "2025-10-08T00:00:00"
    end_time: "2025-10-08T23:59:59"
  - operation: "spatial_filter"
    apply_to: msg
    min_lat: 30.0
    max_lat: 50.0
    min_lon: -10.0
    max_lon: 20.0
  - operation: "content_filter"
    apply_to: msg
    variables: ["ir_10.8", "vis_0.6"]
  - operation: "temporal_aggregate"
    apply_to: msg
    method: "mean"
    frequency: "1h"

outputs:
  - writer: "zarrv2"
    path: output/processed.zarr
```

**Multi-source datacube** — fuses MSG SEVIRI imagery, ERA5 reanalysis, and MTG GII fire
products onto one aligned grid. Each input has a unique `id`; transformations route to
inputs via `apply_to` (independent per-input) or `base_input`/`align_inputs` (multi-source
merge):

```yaml
name: d27_multi_source_cube

inputs:
  - id: msg
    reader: { name: msg15nat, use_channel_names: true, channels: [ir_10.8, vis_0.6, ir_3.9] }
    source: { fs_type: local, path: "test-data/demo/msg/MSG3-SEVI-MSG15*.nat" }
  - id: era5
    reader: { name: era5grib }
    source: { fs_type: local, path: "test-data/demo/era5/era5sl_20251016_2m_temperature.grib" }
  - id: mtg_gii
    reader: { name: mtg_l2_gii }
    source: { fs_type: local, path: "test-data/demo/mtg_gii/gii_*.nc" }

transformations:
  - operation: spatial_filter
    apply_to: [msg, mtg_gii]
    lat_min: 30.0
    lat_max: 46.0
    lon_min: -6.0
    lon_max: 36.0
  - operation: alignment
    base_input: msg
    align_inputs: [era5, mtg_gii]
    target: "EPSG:4326"
    target_resolution: 0.05
    spatial_method: bilinear
    temporal_method: nearest
    time_bounds: base
    conflict_resolution: prefix   # merged vars become era5_t2m, mtg_gii_frp, ...

outputs:
  - writer: zarrv2
    path: output/med_datacube.zarr
```

Routing-field rules: every transformation needs either `apply_to` (single id or list, run
independently per input) or `base_input` (not both); `align_inputs` requires `base_input`;
after `alignment` runs, the secondary inputs are consumed and only the merged base dataset
remains.

Run it:

```bash
defair run --config workflow.yaml               # execute
defair run --config workflow.yaml --dry-run      # preview the plan without processing data
```

`--dry-run` prints a table for each stage (inputs with reader/source, transformations with
parameters, outputs with writer/destination) so you can sanity-check a pipeline before it
touches data.

## Dask execution modes

DEFAIR is lazy by default: operations build a task graph and nothing computes until you
call `.to_file()` (or `.compute()`). When `use_dask=True`, DEFAIR auto-creates a Dask
`LocalCluster` unless a client is already registered; a single `DaskClientManager` singleton
ensures only one client exists across all readers/writers/transformations in a process.

- **Local threads (default)** — single process, multiple threads
  (`dask_client_kwargs={"n_workers": 4, "memory_limit": "2GB"}` to tune). Minimal overhead,
  efficient memory sharing, no serialization cost. Best for development, I/O-bound work
  (filtering/subsetting/content selection), and datasets that fit in memory.
- **Local processes** — multiple Python processes on one machine
  (`LocalCluster(n_workers=4, threads_per_worker=2, memory_limit="4GB", processes=True)`,
  then `set_dask_client(client)`). Bypasses the GIL for true parallelism on CPU-bound work
  like reprojection; higher memory/serialization overhead. Recommended for datasets in the
  5–50GB range or CPU-intensive transforms.
- **Remote cluster (Dask Gateway)** — connect via `dask_gateway.Gateway()`, create/scale a
  cluster, then `set_dask_client(cluster.get_client())`. Scales beyond one machine; adds
  setup and network overhead. Recommended for datasets larger than local memory, production
  pipelines, and shared/multi-user environments.

Always call `close_dask_client()` when finished with Dask operations to release the client.

## Extensibility (plugin system)

Readers, writers, and transformations are all discovered via Python **entry points**
declared in a package's `pyproject.toml`:

```toml
[project.entry-points."defair_data.readers"]
my_custom_reader = "my_package.readers.my_custom_reader:MyCustomReaderPlugin"

[project.entry-points."defair_data.writers"]
my_custom_writer = "my_package.writers.my_custom_writer:MyCustomWriterPlugin"

[project.entry-points."defair_ops.transformations"]
my_transformation = "my_package.transformations.my_transformation:MyTransformationPlugin"
```

After adding an entry point, run `uv sync` (or `make update`) so it's picked up.

- **Reader plugins** subclass `DataReaderPlugin`, declare `SUPPORTED_EXTENSIONS` and a
  `PRIORITY` (0–100, default 50; built-ins use 10–30, custom readers 50–80, overrides
  90–100 — higher wins when multiple readers claim the same extension), implement
  `can_handle(path)` and `read(path, source=None, source_kwargs=None, **kwargs) -> Dataset`.
  They should use `self.open_file(...)` (works transparently across local/S3/other sources)
  and open data with `chunks=...` so results stay Dask-backed — never call `.compute()`/
  `.load()` inside a reader.
- **Writer plugins** subclass `DataWriterPlugin`, declare `SUPPORTED_EXTENSIONS`/`PRIORITY`,
  and implement `write(dataset, path)`. They should use streaming-capable formats/engines
  (NetCDF4 via `h5netcdf` with `zlib`/`complevel` encoding, or Zarr with `numcodecs`
  compressors) and avoid forcing `.compute()` before writing.
- **Transformation plugins** subclass `TransformationPlugin`, expose a `name` property (the
  operation name used in workflow YAML) and implement
  `transform(dataset, target, **kwargs) -> Dataset`, preserving Dask laziness throughout
  (no `.compute()`/`.load()`/`.values` unless unavoidable).
- All three plugin kinds are unit-tested by: confirming `PluginManager` discovery
  (`load_reader("name")` / `load_writer("name")` / `load_transformation("name")`), verifying
  `can_handle()` correctly matches file paths, verifying the operation itself, and verifying
  outputs remain Dask-backed (`isinstance(x.data, dask.array.Array)`).

### CF metadata & history tracking

DEFAIR follows Climate and Forecast (CF) metadata conventions and expects plugins to
preserve/extend them. The `CFHistoryMixin` (from the core `defair` package) provides a
decorator that auto-appends a history entry:

```python
from defair.cf_history_mixin import CFHistoryMixin

class MyWriterPlugin(CFHistoryMixin, DataWriterPlugin):
    @CFHistoryMixin.track_history(include_params=["compression_level", "format"])
    def write(self, dataset, path):
        dataset.data.to_netcdf(path)
```

This produces entries such as:
`2025-11-16T10:30:00Z - Written to NetCDF4 format (compression_level=4, format=NETCDF4)`.
History can also be updated manually by appending timestamped strings to
`ds.attrs["history"]`.

## API service

Alongside the CLI, a proof-of-concept HTTP service exposes DEFAIR YAML workflows as
[OGC API - Processes](https://ogcapi.ogc.org/processes/) resources, executed on the same
Dask-backed runtime as the CLI. Flow: a workflow (identical YAML syntax to `defair run`) is
registered as a process; a client submits an execution request; DEFAIR runs it and writes
output via the configured writer (e.g. to S3 Zarr). It includes a small browser UI at `/ui`
for creating/running workflows and inspecting jobs, plus full OpenAPI docs at `/docs`.

Main endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /` | Landing page with service links |
| `GET /conformance` | OGC conformance declaration |
| `GET /openapi.json` | OpenAPI description |
| `GET /processes` | List registered workflows as OGC processes |
| `POST /processes` | Register a workflow from DEFAIR YAML |
| `GET /processes/{processId}` | Describe one registered workflow |
| `POST /processes/{processId}/execution` | Execute a workflow |
| `GET /jobs` | List jobs |
| `GET /jobs/{jobId}` | Poll job status |
| `GET /jobs/{jobId}/results` | Fetch completed job outputs |
| `DELETE /jobs/{jobId}` | Dismiss a job |
| `GET /ui` | Browser UI |

Asynchronous execution is requested with header `Prefer: respond-async`; the response
includes a job URL to poll until it succeeds or fails. Deployment notes: Dask Gateway is
configured via `DEFAIR_DASK_*` environment variables; S3 credentials are supplied as
environment variables or Kubernetes secrets and propagated to Dask workers; example
workflows can be bundled into the API image and seeded at startup.

