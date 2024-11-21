from typing import Dict, List, Optional, Union, Literal, Tuple
from pydantic import (
    BaseModel,
    Field,
    model_validator,
    field_validator,
    PrivateAttr,
)
import numpy as np
from enum import Enum
import pandas as pd
import scipy as sp
import yaml
import pdb
import math


class SurfaceType(str, Enum):
    PAVED = "paved"
    BLDGS = "bldgs"
    DECTR = "dectr"
    EVETR = "evetr"
    GRASS = "grass"
    BSOIL = "bsoil"
    WATER = "water"


class SnowAlb(BaseModel):
    snowalb: float = Field(ge=0, le=1, description="Snow albedo")


class WaterUse(BaseModel):
    wu_total: float = Field(ge=0, description="Total water use")
    wu_auto: float = Field(ge=0, description="Automatic water use")
    wu_manual: float = Field(ge=0, description="Manual water use")


class SurfaceInitialState(BaseModel):
    """Initial state parameters for a surface type"""

    state: float = Field(ge=0, description="Initial state of the surface", default=0.0)
    soilstore: float = Field(ge=0, description="Initial soil store", default=0.0)
    snowfrac: Optional[float] = Field(
        ge=0, le=1, description="Snow fraction", default=0.0
    )
    snowpack: Optional[float] = Field(ge=0, description="Snow pack", default=0.0)
    icefrac: Optional[float] = Field(
        ge=0, le=1, description="Ice fraction", default=0.0
    )
    snowwater: Optional[float] = Field(ge=0, description="Snow water", default=0.0)
    snowdens: Optional[float] = Field(ge=0, description="Snow density", default=0.0)
    alb_id: Optional[float] = Field(
        description="Initial albedo for vegetated surfaces", default=None
    )
    porosity_id: Optional[float] = Field(
        description="Initial porosity for deciduous trees", default=None
    )
    decidcap_id: Optional[float] = Field(
        description="Initial deciduous capacity for deciduous trees", default=None
    )
    lai_id: Optional[float] = Field(
        description="Initial leaf area index for vegetated surfaces", default=None
    )
    gdd_id: Optional[float] = Field(
        description="Growing degree days ID for vegetated surfaces", default=None
    )
    sdd_id: Optional[float] = Field(
        description="Senescence degree days ID for vegetated surfaces", default=None
    )
    temperature: List[float] = Field(
        min_items=5,
        max_items=5,
        description="Initial temperature for each thermal layer",
        default=[15.0, 15.0, 15.0, 15.0, 15.0],
    )
    tsfc: Optional[float] = Field(
        description="Initial exterior surface temperature", default=15.0
    )
    tin: Optional[float] = Field(
        description="Initial interior surface temperature", default=20.0
    )
    wu: Optional[WaterUse] = (
        None  # TODO: add validation - only needed for vegetated surfaces
    )
    _surface_type: Optional[SurfaceType] = PrivateAttr(default=None)

    def set_surface_type(self, surface_type: SurfaceType):
        """Set and validate surface type specific parameters"""
        self._surface_type = surface_type

    @model_validator(mode="after")
    def validate_surface_state(self) -> "SurfaceInitialState":
        """Validate state based on surface type if set"""
        if self._surface_type is not None:
            # Re-run validation with current surface type
            self.set_surface_type(self._surface_type)
        # Validate vegetation-specific parameters
        veg_types = [SurfaceType.DECTR, SurfaceType.EVETR, SurfaceType.GRASS]
        if self._surface_type in veg_types:
            if self.alb_id is None:
                raise ValueError(f"alb_id is required for {self._surface_type.value}")
            if self.lai_id is None:
                raise ValueError(f"lai_id is required for {self._surface_type.value}")
            if self.wu is None:
                raise ValueError(f"wu is required for {self._surface_type.value}")

        # Validate deciduous-specific parameters
        if self._surface_type == SurfaceType.DECTR:
            if self.decidcap_id is None:
                raise ValueError("decidcap_id is required for deciduous trees")
            if self.porosity_id is None:
                raise ValueError("porosity_id is required for deciduous trees")

        # Validate non-vegetation parameters
        non_veg_types = [
            SurfaceType.PAVED,
            SurfaceType.BLDGS,
            SurfaceType.BSOIL,
            SurfaceType.WATER,
        ]
        if self._surface_type in non_veg_types:
            if any(
                param is not None
                for param in [
                    self.alb_id,
                    self.lai_id,
                    self.decidcap_id,
                    self.porosity_id,
                ]
            ):
                raise ValueError(
                    f"Vegetation parameters should not be set for {self._surface_type.value}"
                )
        return self


class InitialStates(BaseModel):
    """Initial conditions for the SUEWS model"""

    snowalb: float = Field(ge=0, le=1, description="Initial snow albedo", default=0.5)
    paved: SurfaceInitialState = Field(default_factory=SurfaceInitialState)
    bldgs: SurfaceInitialState = Field(default_factory=SurfaceInitialState)
    dectr: SurfaceInitialState = Field(default_factory=SurfaceInitialState)
    evetr: SurfaceInitialState = Field(default_factory=SurfaceInitialState)
    grass: SurfaceInitialState = Field(default_factory=SurfaceInitialState)
    bsoil: SurfaceInitialState = Field(default_factory=SurfaceInitialState)
    water: SurfaceInitialState = Field(default_factory=SurfaceInitialState)
    roofs: Optional[List[SurfaceInitialState]] = Field(
        default=[
            SurfaceInitialState(),
            SurfaceInitialState(),
        ],
        description="Initial states for roof layers",
    )
    walls: Optional[List[SurfaceInitialState]] = Field(
        default=[
            SurfaceInitialState(),
            SurfaceInitialState(),
        ],
        description="Initial states for wall layers",
    )

    def __init__(self, **data):
        super().__init__(**data)
        # Set surface types for each surface
        self.paved.set_surface_type(SurfaceType.PAVED)
        self.bldgs.set_surface_type(SurfaceType.BLDGS)
        self.dectr.set_surface_type(SurfaceType.DECTR)
        self.evetr.set_surface_type(SurfaceType.EVETR)
        self.grass.set_surface_type(SurfaceType.GRASS)
        self.bsoil.set_surface_type(SurfaceType.BSOIL)
        self.water.set_surface_type(SurfaceType.WATER)


class ThermalLayer(BaseModel):
    dz: List[float] = Field([0.1, 0.2, 0.3, 0.4, 0.5], min_items=5, max_items=5)
    k: List[float] = Field([1.0, 1.0, 1.0, 1.0, 1.0], min_items=5, max_items=5)
    cp: List[float] = Field([1000, 1000, 1000, 1000, 1000], min_items=5, max_items=5)


class VegetationParams(BaseModel):
    porosity_id: int
    gdd_id: int = Field(description="Growing degree days ID")
    sdd_id: int = Field(description="Senescence degree days ID")
    lai: Dict[str, Union[float, List[float]]] = Field(
        description="Leaf area index parameters"
    )
    ie_a: float = Field(description="Irrigation efficiency coefficient a")
    ie_m: float = Field(description="Irrigation efficiency coefficient m")


class WaterDistribution(BaseModel):
    # Optional fields for all possible distributions
    to_paved: Optional[float] = Field(None, ge=0, le=1)
    to_bldgs: Optional[float] = Field(None, ge=0, le=1)
    to_dectr: Optional[float] = Field(None, ge=0, le=1)
    to_evetr: Optional[float] = Field(None, ge=0, le=1)
    to_grass: Optional[float] = Field(None, ge=0, le=1)
    to_bsoil: Optional[float] = Field(None, ge=0, le=1)
    to_water: Optional[float] = Field(None, ge=0, le=1)
    to_runoff: Optional[float] = Field(None, ge=0, le=1)  # For paved/bldgs
    to_soilstore: Optional[float] = Field(None, ge=0, le=1)  # For vegetated surfaces

    def validate_distribution(self, surface_type: SurfaceType) -> None:
        """Validate water distribution based on surface type"""
        # Define required fields for each surface type
        required_fields = {
            SurfaceType.PAVED: [
                "to_bldgs",
                "to_dectr",
                "to_evetr",
                "to_grass",
                "to_bsoil",
                "to_water",
                "to_runoff",
            ],
            SurfaceType.BLDGS: [
                "to_paved",
                "to_dectr",
                "to_evetr",
                "to_grass",
                "to_bsoil",
                "to_water",
                "to_runoff",
            ],
            SurfaceType.DECTR: [
                "to_paved",
                "to_bldgs",
                "to_evetr",
                "to_grass",
                "to_bsoil",
                "to_water",
                "to_soilstore",
            ],
            SurfaceType.EVETR: [
                "to_paved",
                "to_bldgs",
                "to_dectr",
                "to_grass",
                "to_bsoil",
                "to_water",
                "to_soilstore",
            ],
            SurfaceType.GRASS: [
                "to_paved",
                "to_bldgs",
                "to_dectr",
                "to_evetr",
                "to_bsoil",
                "to_water",
                "to_soilstore",
            ],
            SurfaceType.BSOIL: [
                "to_paved",
                "to_bldgs",
                "to_dectr",
                "to_evetr",
                "to_grass",
                "to_water",
                "to_soilstore",
            ],
            SurfaceType.WATER: None,  # Water surface doesn't have water distribution
        }

        if surface_type == SurfaceType.WATER:
            raise ValueError("Water surface should not have water distribution")

        fields = required_fields[surface_type]
        values = []

        # Check required fields are present and collect values
        for field in fields:
            value = getattr(self, field)
            if value is None:
                raise ValueError(
                    f"Missing required field {field} for {surface_type.value}"
                )
            values.append(value)

        # Validate sum
        total = sum(values)
        if not np.isclose(total, 1.0, rtol=1e-5):
            raise ValueError(f"Water distribution sum must be 1.0, got {total}")


class StorageDrainParams(BaseModel):
    store_min: float = Field(ge=0, default=0.0)
    store_max: float = Field(ge=0, default=10.0)
    store_cap: float = Field(ge=0, default=10.0)
    drain_eq: int = Field(default=0)
    drain_coef_1: float = Field(default=0.013)
    drain_coef_2: float = Field(default=1.71)


class OHMCoefficients(BaseModel):
    a1: Dict[str, float]
    a2: Dict[str, float]
    a3: Dict[str, float]


class SurfaceProperties(BaseModel):
    """Base properties for all surface types"""

    sfr: float = Field(ge=0, le=1, description="Surface fraction", default=1.0 / 7)
    emis: float = Field(ge=0, le=1, description="Surface emissivity", default=0.95)
    chanohm: Optional[float] = Field(default=0.0)
    cpanohm: Optional[float] = Field(default=1200.0)
    kkanohm: Optional[float] = Field(default=0.4)
    ohm_threshsw: Optional[float] = Field(default=0.0)
    ohm_threshwd: Optional[float] = Field(default=0.0)
    ohm_coef: Optional[OHMCoefficients] = None
    soildepth: float = Field(default=0.15)
    soilstorecap: float = Field(default=150.0)
    statelimit: float = Field(default=10.0)
    wetthresh: float = Field(default=0.5)
    sathydraulicconduct: float = Field(default=0.0001)
    waterdist: Optional[WaterDistribution] = Field(
        default=None, description="Water distribution parameters"
    )
    storedrainprm: StorageDrainParams = Field(
        default_factory=StorageDrainParams, description="Storage and drain parameters"
    )
    snowpacklimit: Optional[float] = Field(default=10.0)
    thermal_layers: ThermalLayer = Field(
        default_factory=ThermalLayer, description="Thermal layers for the surface"
    )
    irrfrac: Optional[float] = Field(default=0.0)
    _surface_type: Optional[SurfaceType] = PrivateAttr(default=None)

    def set_surface_type(self, surface_type: SurfaceType):
        self._surface_type = surface_type
        if self._surface_type == SurfaceType.WATER:
            if self.waterdist is not None:
                raise ValueError("Water surface should not have water distribution")
        else:
            if self.waterdist is None:
                raise ValueError(
                    f"Water distribution required for {self._surface_type.value}"
                )
            self.waterdist.validate_distribution(self._surface_type)


class NonVegetatedSurfaceProperties(SurfaceProperties):
    alb: float = Field(ge=0, le=1, description="Surface albedo", default=0.1)


class PavedProperties(NonVegetatedSurfaceProperties):
    surface_type: Literal[SurfaceType.PAVED] = SurfaceType.PAVED


class BuildingLayer(BaseModel):
    alb: float = Field(ge=0, le=1, description="Surface albedo", default=0.1)
    emis: float = Field(ge=0, le=1, description="Surface emissivity", default=0.95)
    thermal_layers: ThermalLayer = Field(
        default_factory=ThermalLayer, description="Thermal layers for the surface"
    )
    statelimit: float = Field(default=10.0)
    soilstorecap: float = Field(default=150.0)
    wetthresh: float = Field(default=0.5)
    roof_albedo_dir_mult_fact: Optional[float] = Field(default=0.1)
    wall_specular_frac: Optional[float] = Field(default=0.1)


class VerticalLayers(BaseModel):
    nlayer: int
    height: List[float]
    veg_frac: List[float]
    veg_scale: List[float]
    building_frac: List[float]
    building_scale: List[float]
    roofs: List[BuildingLayer]
    walls: List[BuildingLayer]

    @model_validator(mode="after")
    def validate_building(self) -> "VerticalLayers":
        # Validate building heights
        if len(self.height) != self.nlayer + 1:
            raise ValueError(
                f"Number of building heights ({len(self.height)}) must match nlayer+1 = ({self.nlayer+1})"
            )

        # Validate building fractions
        if len(self.building_frac) != self.nlayer:
            raise ValueError(
                f"Number of building fractions ({len(self.building_frac)}) must match nlayer ({self.nlayer})"
            )
        if not math.isclose(sum(self.building_frac), 1.0, rel_tol=1e-9):
            raise ValueError(
                f"Building fractions must sum to 1.0, got {sum(self.building_frac)}"
            )

        # Validate building scales
        if len(self.building_scale) != self.nlayer:
            raise ValueError(
                f"Number of building scales ({len(self.building_scale)}) must match nlayer ({self.nlayer})"
            )

        # Validate number of roof layers matches nlayer
        if len(self.roofs) != self.nlayer:
            raise ValueError(
                f"Number of roof layers ({len(self.roof)}) must match nlayer ({self.nlayer})"
            )

        # Validate number of wall layers matches nlayer
        if len(self.walls) != self.nlayer:
            raise ValueError(
                f"Number of wall layers ({len(self.wall)}) must match nlayer ({self.nlayer})"
            )

        return self


class BuildingProperties(NonVegetatedSurfaceProperties):
    surface_type: Literal[SurfaceType.BLDGS] = SurfaceType.BLDGS
    faibldg: float = Field(
        ge=0, default=0.3, description="Frontal area index of buildings"
    )
    bldgh: float = Field(ge=0, default=10.0, description="Building height")

    @model_validator(mode="after")
    def validate_rsl_zd_range(self) -> "BuildingProperties":
        # Existing validation
        sfr_bldg_lower_limit = 0.18
        if self.sfr < sfr_bldg_lower_limit:
            if self.faibldg < 0.25 * (1 - self.sfr):
                error_message = ValueError(
                    "The Frontal Area Index (FAI) is falling below the lower limit of: 0.25 * (1 - PAI), which is likely causing issues regarding negative displacement height (zd) in the RSL.\n"
                    f"\tYou have entered a building FAI of {self.faibldg} and a building PAI of {self.sfr}.\n"
                    "\tFor more details, please refer to: https://github.com/UMEP-dev/SUEWS/issues/302"
                )
                exceptions.append(error_message)
        return self


class BaresoilProperties(NonVegetatedSurfaceProperties):
    surface_type: Literal[SurfaceType.BSOIL] = SurfaceType.BSOIL


class WaterProperties(NonVegetatedSurfaceProperties):
    surface_type: Literal[SurfaceType.WATER] = SurfaceType.WATER
    flowchange: float = Field(default=0.0)


class ModelControl(BaseModel):
    tstep: int = Field(description="Time step in seconds")
    forcing_file: str
    output_file: str
    # daylightsaving_method: int
    diagnose: int


class ModelPhysics(BaseModel):
    netradiationmethod: int
    emissionsmethod: int
    storageheatmethod: int
    ohmincqf: int
    roughlenmommethod: int
    roughlenheatmethod: int
    stabilitymethod: int
    smdmethod: int
    waterusemethod: int
    diagmethod: int
    faimethod: int
    localclimatemethod: int
    snowuse: int


class LUMPSParams(BaseModel):
    raincover: float = Field(ge=0, le=1)
    rainmaxres: float = Field(ge=0, le=1)
    drainrt: float = Field(ge=0, le=1)
    veg_type: int


class SPARTACUSParams(BaseModel):
    air_ext_lw: float
    air_ext_sw: float
    air_ssa_lw: float
    air_ssa_sw: float
    ground_albedo_dir_mult_fact: float
    n_stream_lw_urban: int
    n_stream_sw_urban: int
    n_vegetation_region_urban: int
    sw_dn_direct_frac: float
    use_sw_direct_albedo: float
    veg_contact_fraction_const: float
    veg_fsd_const: float
    veg_ssa_lw: float
    veg_ssa_sw: float


class DayProfile(BaseModel):
    working_day: float
    holiday: float


class WeeklyProfile(BaseModel):
    monday: float
    tuesday: float
    wednesday: float
    thursday: float
    friday: float
    saturday: float
    sunday: float


class HourlyProfile(BaseModel):
    working_day: Dict[str, float]
    holiday: Dict[str, float]

    @field_validator("working_day", "holiday", mode="before")
    def convert_keys_to_str(cls, v: Dict) -> Dict[str, float]:
        if isinstance(v, dict):
            return {str(k): float(v) for k, v in v.items()}
        return v

    @model_validator(mode="after")
    def validate_hours(self) -> "HourlyProfile":
        for profile in [self.working_day, self.holiday]:
            hours = [int(h) for h in profile.keys()]
            if not all(1 <= h <= 24 for h in hours):
                error_message = ValueError("Hour values must be between 1 and 24")
                exceptions.append(error_message)
                # raise ValueError("Hour values must be between 1 and 24")
            if sorted(hours) != list(range(1, 25)):
                error_message = ValueError("Must have all hours from 1 to 24")
                exceptions.append(error_message)
                # raise ValueError("Must have all hours from 1 to 24")
        return self


class IrrigationParams(BaseModel):
    h_maintain: float
    faut: float
    ie_start: float
    ie_end: float
    internalwateruse_h: float
    daywatper: WeeklyProfile
    daywat: WeeklyProfile
    wuprofa_24hr: HourlyProfile
    wuprofm_24hr: HourlyProfile


class AnthropogenicHeat(BaseModel):
    qf0_beu: DayProfile
    qf_a: DayProfile
    qf_b: DayProfile
    qf_c: DayProfile
    baset_cooling: DayProfile
    baset_heating: DayProfile
    ah_min: DayProfile
    ah_slope_cooling: DayProfile
    ah_slope_heating: DayProfile
    ahprof_24hr: HourlyProfile
    popdensdaytime: DayProfile
    popdensnighttime: float
    popprof_24hr: HourlyProfile


class CO2Params(BaseModel):
    co2pointsource: float
    ef_umolco2perj: float
    enef_v_jkm: float
    fcef_v_kgkm: DayProfile
    frfossilfuel_heat: float
    frfossilfuel_nonheat: float
    maxfcmetab: float
    maxqfmetab: float
    minfcmetab: float
    minqfmetab: float
    trafficrate: DayProfile
    trafficunits: float
    traffprof_24hr: HourlyProfile
    humactivity_24hr: HourlyProfile


class AnthropogenicEmissions(BaseModel):
    startdls: float
    enddls: float
    heat: AnthropogenicHeat
    co2: CO2Params


class Conductance(BaseModel):
    g_max: float = Field(description="Maximum conductance")
    g_k: float = Field(
        description="Conductance parameter related to incoming solar radiation"
    )
    g_q_base: float = Field(
        description="Base value for conductance parameter related to vapor pressure deficit"
    )
    g_q_shape: float = Field(
        description="Shape parameter for conductance related to vapor pressure deficit"
    )
    g_t: float = Field(description="Conductance parameter related to air temperature")
    g_sm: float = Field(description="Conductance parameter related to soil moisture")
    kmax: float = Field(description="Maximum incoming shortwave radiation")
    gsmodel: int = Field(description="Stomatal conductance model selection")
    s1: float = Field(description="Soil moisture threshold parameter")
    s2: float = Field(description="Soil moisture threshold parameter")
    tl: float = Field(description="Air temperature threshold parameter")
    th: float = Field(description="Air temperature threshold parameter")


class LAIPowerCoefficients(BaseModel):
    growth_lai: float = Field(
        default=0.1,
        description="Power coefficient for LAI in growth equation (LAIPower[1])",
    )
    growth_gdd: float = Field(
        default=0.1,
        description="Power coefficient for GDD in growth equation (LAIPower[2])",
    )
    senescence_lai: float = Field(
        default=0.1,
        description="Power coefficient for LAI in senescence equation (LAIPower[3])",
    )
    senescence_sdd: float = Field(
        default=0.1,
        description="Power coefficient for SDD in senescence equation (LAIPower[4])",
    )

    def to_list(self) -> List[float]:
        """Convert to list format for Fortran interface"""
        return [
            self.growth_lai,
            self.growth_gdd,
            self.senescence_lai,
            self.senescence_sdd,
        ]


class LAIParams(BaseModel):
    baset: float = Field(
        default=10.0,
        description="Base Temperature for initiating growing degree days (GDD) for leaf growth [degC]",
    )
    gddfull: float = Field(
        default=100.0,
        description="Growing degree days (GDD) needed for full capacity of LAI [degC]",
    )
    basete: float = Field(
        default=10.0,
        description="Base temperature for initiating senescence degree days (SDD) for leaf off [degC]",
    )
    sddfull: float = Field(
        default=100.0,
        description="Senescence degree days (SDD) needed to initiate leaf off [degC]",
    )
    laimin: float = Field(default=0.1, description="Leaf-off wintertime value [m2 m-2]")
    laimax: float = Field(
        default=10.0, description="Full leaf-on summertime value [m2 m-2]"
    )
    laipower: LAIPowerCoefficients = Field(
        default_factory=LAIPowerCoefficients,
        description="LAI calculation power parameters for growth and senescence",
    )
    laitype: int = Field(
        default=0,
        description="LAI calculation choice (0: original, 1: new high latitude)",
    )

    @model_validator(mode="after")
    def validate_lai_ranges(self) -> "LAIParams":
        if self.laimin > self.laimax:
            error_message = ValueError(
                f"laimin ({self.laimin}) must be less than or equal to laimax ({self.laimax})."
            )
            exceptions.append(error_message)
            # raise ValueError(f"laimin ({self.laimin})must be less than or equal to laimax ({self.laimax}).")
        if self.baset > self.gddfull:
            error_message = ValueError(
                f"baset ({self.baset}) must be less than gddfull ({self.gddfull})."
            )
            exceptions.append(error_message)
            # raise ValueError(f"baset {self.baset} must be less than gddfull ({self.gddfull}).")
        return self


class VegetatedSurfaceProperties(SurfaceProperties):
    alb_min: float = Field(ge=0, le=1, description="Minimum albedo", default=0.2)
    alb_max: float = Field(ge=0, le=1, description="Maximum albedo", default=0.3)
    beta_bioco2: float = Field(
        default=0.6, description="Biogenic CO2 exchange coefficient"
    )
    beta_enh_bioco2: float = Field(
        default=0.7, description="Enhanced biogenic CO2 exchange coefficient"
    )
    alpha_bioco2: float = Field(
        default=0.8, description="Biogenic CO2 exchange coefficient"
    )
    alpha_enh_bioco2: float = Field(
        default=0.9, description="Enhanced biogenic CO2 exchange coefficient"
    )
    resp_a: float = Field(default=1.0, description="Respiration coefficient")
    resp_b: float = Field(default=1.1, description="Respiration coefficient")
    theta_bioco2: float = Field(
        default=1.2, description="Biogenic CO2 exchange coefficient"
    )
    maxconductance: float = Field(
        default=0.5, description="Maximum surface conductance"
    )
    min_res_bioco2: float = Field(
        default=0.1, description="Minimum respiratory biogenic CO2"
    )
    lai: LAIParams = Field(
        default_factory=LAIParams, description="Leaf area index parameters"
    )
    ie_a: float = Field(
        default=0.5, description="Irrigation efficiency coefficient-automatic"
    )
    ie_m: float = Field(
        default=0.6, description="Irrigation efficiency coefficient-manual"
    )

    @model_validator(mode="after")
    def validate_albedo_range(self) -> "VegetatedSurfaceProperties":
        if self.alb_min > self.alb_max:
            error_message = ValueError(
                f"alb_min (input {self.alb_min}) must be less than or equal to alb_max (entered {self.alb_max})."
            )
            exceptions.append(error_message)
            # raise ValueError(f"alb_min (input {self.alb_min}) must be less than or equal to alb_max (entered {self.alb_max}).")
        return self


class DectrProperties(VegetatedSurfaceProperties):
    faidectree: float = Field(
        default=0.1, description="Frontal area index of deciduous trees"
    )
    dectreeh: float = Field(default=10.0, description="Height of deciduous trees [m]")
    pormin_dec: float = Field(
        default=0.1,
        ge=0.1,
        le=0.9,
        description="Minimum porosity of deciduous trees in winter when leaves are off",
    )
    pormax_dec: float = Field(
        default=0.9,
        ge=0.1,
        le=0.9,
        description="Maximum porosity of deciduous trees in summer when leaves are fully on",
    )
    capmax_dec: float = Field(
        default=100.0,
        description="Maximum storage capacity of deciduous trees in summer when leaves are fully on [mm]",
    )
    capmin_dec: float = Field(
        default=10.0,
        description="Minimum storage capacity of deciduous trees in winter when leaves are off [mm]",
    )

    @model_validator(mode="after")
    def validate_porosity_range(self) -> "DectrProperties":
        if self.pormin_dec >= self.pormax_dec:
            error_message = ValueError(
                f"pormin_dec ({self.pormin_dec}) must be less than pormax_dec ({self.pormax_dec})."
            )
            exceptions.append(error_message)
            # raise ValueError(f"pormin_dec ({self.pormin_dec}) must be less than pormax_dec ({self.pormax_dec}).")
        return self

    @model_validator(mode="after")
    def validate_cap_range(self) -> "DectrProperties":
        if self.capmin_dec >= self.capmax_dec:
            error_message = ValueError(
                f"capmin_dec ({self.capmin_dec}) must be less than capmax_dec ({self.capmax_dec})."
            )
            exceptions.append(error_message)
            # raise ValueError(f"capmin_dec ({self.capmin_dec}) must be less than capmax_dec ({self.capmax_dec}).")
        return self


class EvetrProperties(VegetatedSurfaceProperties):
    faievetree: float = Field(
        default=0.1, description="Frontal area index of evergreen trees"
    )
    evetreeh: float = Field(default=10.0, description="Height of evergreen trees [m]")


class SnowParams(BaseModel):
    crwmax: float
    crwmin: float
    narp_emis_snow: float
    preciplimit: float
    preciplimitalb: float
    snowalbmax: float
    snowalbmin: float
    snowdensmin: float
    snowdensmax: float
    snowlimbldg: float
    snowlimpaved: float
    snowprof_24hr: HourlyProfile
    tau_a: float
    tau_f: float
    tau_r: float
    tempmeltfact: float
    radmeltfact: float

    @model_validator(mode="after")
    def validate_crw_range(self) -> "SnowParams":
        if self.crwmin >= self.crwmax:
            error_message = ValueError(
                f"crwmin ({self.crwmin}) must be less than crwmax ({self.crwmax})."
            )
            exceptions.append(error_message)
            # raise ValueError(f"crwmin ({self.crwmin}) must be less than crwmax ({self.crwmax}).")
        return self

    @model_validator(mode="after")
    def validate_snowalb_range(self) -> "SnowParams":
        if self.snowalbmin >= self.snowalbmax:
            error_message = ValueError(
                f"snowalbmin ({self.snowalbmin}) must be less than snowalbmax ({self.snowalbmax})."
            )
            exceptions.append(error_message)
            # raise ValueError(f"snowalbmin ({self.snowalbmin}) must be less than snowalbmax ({self.snowalbmax}).")
        return self


class LandCover(BaseModel):
    paved: PavedProperties
    bldgs: BuildingProperties
    dectr: DectrProperties
    evetr: EvetrProperties
    grass: VegetatedSurfaceProperties
    bsoil: BaresoilProperties
    water: WaterProperties

    @model_validator(mode="after")
    def set_surface_types(self) -> "LandCover":
        # Set surface types and validate
        surface_map = {
            "paved": (self.paved, SurfaceType.PAVED),
            "bldgs": (self.bldgs, SurfaceType.BLDGS),
            "dectr": (self.dectr, SurfaceType.DECTR),
            "evetr": (self.evetr, SurfaceType.EVETR),
            "grass": (self.grass, SurfaceType.GRASS),
            "bsoil": (self.bsoil, SurfaceType.BSOIL),
            "water": (self.water, SurfaceType.WATER),
        }

        for prop, surface_type in surface_map.values():
            prop.set_surface_type(surface_type)

        return self


class SiteProperties(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    alt: float
    timezone: int = Field(ge=-12, le=12)
    surfacearea: float = Field(gt=0)
    z: float = Field(gt=0)
    z0m_in: float = Field(gt=0)
    zdm_in: float = Field(gt=0)
    pipecapacity: float = Field(gt=0)
    runofftowater: float = Field(ge=0, le=1)
    narp_trans_site: float
    lumps: LUMPSParams
    spartacus: SPARTACUSParams
    conductance: Conductance
    irrigation: IrrigationParams
    anthropogenic_emissions: AnthropogenicEmissions
    snow: SnowParams
    land_cover: LandCover
    vertical_layers: VerticalLayers


class Site(BaseModel):
    name: str
    gridiv: int
    properties: SiteProperties
    initial_states: InitialStates


class Model(BaseModel):
    control: ModelControl
    physics: ModelPhysics


class SUEWSConfig(BaseModel):
    name: str
    description: str
    model: Model
    site: List[Site]

    class Config:
        extra = "allow"

    def create_multi_index_columns(self, columns_file: str) -> pd.MultiIndex:
        """Create MultiIndex from df_state_columns.txt"""
        with open(columns_file, "r") as f:
            lines = f.readlines()

        tuples = []
        for line in lines:
            col_name, indices = line.strip().split(",", 1)
            str_indices = f"{indices}" if indices != "0" else "0"
            tuples.append((col_name, str_indices))

        return pd.MultiIndex.from_tuples(tuples)

    def to_df_state(self) -> pd.DataFrame:
        """Convert config to DataFrame state format"""
        # Initialize empty DataFrame with correct structure
        columns = self.create_multi_index_columns("df_state_columns.txt")
        columns.set_names(["var", "ind_dim"], inplace=True)
        index = pd.Index([0], name="grid")
        df = pd.DataFrame(index=index, columns=columns)

        # Process each site (assuming single site for now)
        site = self.site[0]
        props = site.properties
        gridiv = site.gridiv
        # update index using gridiv
        df.index = pd.Index([gridiv], name="grid")

        # Helper function to set values in DataFrame
        def set_df_value(col_name: str, indices: Union[int, Tuple], value: float):
            if isinstance(indices, int):
                if indices == 0:
                    str_indices = str(indices)
                else:
                    str_indices = f"({indices},)"
            else:
                # Tuples should maintain their string representation
                str_indices = str(indices)
            df.loc[gridiv, (col_name, str_indices)] = value

        # Model control
        set_df_value("tstep", 0, self.model.control.tstep)
        set_df_value("diagnose", 0, self.model.control.diagnose)
        # Model physics
        set_df_value("netradiationmethod", 0, self.model.physics.netradiationmethod)
        set_df_value("emissionsmethod", 0, self.model.physics.emissionsmethod)
        set_df_value("storageheatmethod", 0, self.model.physics.storageheatmethod)
        set_df_value("ohmincqf", 0, self.model.physics.ohmincqf)
        set_df_value("roughlenmommethod", 0, self.model.physics.roughlenmommethod)
        set_df_value("roughlenheatmethod", 0, self.model.physics.roughlenheatmethod)
        set_df_value("stabilitymethod", 0, self.model.physics.stabilitymethod)
        set_df_value("smdmethod", 0, self.model.physics.smdmethod)
        set_df_value("waterusemethod", 0, self.model.physics.waterusemethod)
        set_df_value("diagmethod", 0, self.model.physics.diagmethod)
        set_df_value("faimethod", 0, self.model.physics.faimethod)
        set_df_value("localclimatemethod", 0, self.model.physics.localclimatemethod)
        set_df_value("snowuse", 0, self.model.physics.snowuse)

        # Basic site properties
        set_df_value("gridiv", 0, gridiv)
        set_df_value("lat", 0, props.lat)
        set_df_value("lng", 0, props.lng)
        set_df_value("alt", 0, props.alt)
        set_df_value("timezone", 0, props.timezone)
        set_df_value("surfacearea", 0, props.surfacearea)
        set_df_value("z", 0, props.z)
        set_df_value("z0m_in", 0, props.z0m_in)
        set_df_value("zdm_in", 0, props.zdm_in)
        set_df_value("pipecapacity", 0, props.pipecapacity)
        set_df_value("runofftowater", 0, props.runofftowater)
        set_df_value("narp_trans_site", 0, props.narp_trans_site)

        # LUMPS parameters
        lumps = props.lumps
        set_df_value("raincover", 0, lumps.raincover)
        set_df_value("rainmaxres", 0, lumps.rainmaxres)
        set_df_value("drainrt", 0, lumps.drainrt)
        set_df_value("veg_type", 0, lumps.veg_type)

        # SPARTACUS parameters
        spartacus = props.spartacus
        set_df_value("air_ext_lw", 0, spartacus.air_ext_lw)
        set_df_value("air_ext_sw", 0, spartacus.air_ext_sw)
        set_df_value("air_ssa_lw", 0, spartacus.air_ssa_lw)
        set_df_value("air_ssa_sw", 0, spartacus.air_ssa_sw)
        set_df_value(
            "ground_albedo_dir_mult_fact", 0, spartacus.ground_albedo_dir_mult_fact
        )
        set_df_value("n_stream_lw_urban", 0, spartacus.n_stream_lw_urban)
        set_df_value("n_stream_sw_urban", 0, spartacus.n_stream_sw_urban)
        set_df_value(
            "n_vegetation_region_urban", 0, spartacus.n_vegetation_region_urban
        )
        set_df_value("sw_dn_direct_frac", 0, spartacus.sw_dn_direct_frac)
        set_df_value("use_sw_direct_albedo", 0, spartacus.use_sw_direct_albedo)
        set_df_value(
            "veg_contact_fraction_const", 0, spartacus.veg_contact_fraction_const
        )
        set_df_value("veg_fsd_const", 0, spartacus.veg_fsd_const)
        set_df_value("veg_ssa_lw", 0, spartacus.veg_ssa_lw)
        set_df_value("veg_ssa_sw", 0, spartacus.veg_ssa_sw)

        # Conductance parameters
        cond = props.conductance
        set_df_value("g_max", 0, cond.g_max)
        set_df_value("g_k", 0, cond.g_k)
        set_df_value("g_q_base", 0, cond.g_q_base)
        set_df_value("g_q_shape", 0, cond.g_q_shape)
        set_df_value("g_t", 0, cond.g_t)
        set_df_value("g_sm", 0, cond.g_sm)
        set_df_value("kmax", 0, cond.kmax)
        set_df_value("gsmodel", 0, cond.gsmodel)
        set_df_value("s1", 0, cond.s1)
        set_df_value("s2", 0, cond.s2)

        # Irrigation parameters
        irr = props.irrigation
        set_df_value("h_maintain", 0, irr.h_maintain)
        set_df_value("faut", 0, irr.faut)
        set_df_value("ie_start", 0, irr.ie_start)
        set_df_value("ie_end", 0, irr.ie_end)
        set_df_value("internalwateruse_h", 0, irr.internalwateruse_h)

        # Daily water parameters
        set_df_value("daywatper", (0,), irr.daywatper.monday)
        set_df_value("daywatper", (1,), irr.daywatper.tuesday)
        set_df_value("daywatper", (2,), irr.daywatper.wednesday)
        set_df_value("daywatper", (3,), irr.daywatper.thursday)
        set_df_value("daywatper", (4,), irr.daywatper.friday)
        set_df_value("daywatper", (5,), irr.daywatper.saturday)
        set_df_value("daywatper", (6,), irr.daywatper.sunday)

        set_df_value("daywat", (0,), irr.daywat.monday)
        set_df_value("daywat", (1,), irr.daywat.tuesday)
        set_df_value("daywat", (2,), irr.daywat.wednesday)
        set_df_value("daywat", (3,), irr.daywat.thursday)
        set_df_value("daywat", (4,), irr.daywat.friday)
        set_df_value("daywat", (5,), irr.daywat.saturday)
        set_df_value("daywat", (6,), irr.daywat.sunday)

        # Water use profile
        for hour in range(24):
            hour_str = str(hour + 1)
            set_df_value(
                "wuprofa_24hr", (hour, 0), irr.wuprofa_24hr.working_day[hour_str]
            )
            set_df_value("wuprofa_24hr", (hour, 1), irr.wuprofa_24hr.holiday[hour_str])

        # SPARTACUS parameters
        spartacus = props.spartacus
        set_df_value("air_ext_lw", 0, spartacus.air_ext_lw)
        set_df_value("air_ext_sw", 0, spartacus.air_ext_sw)
        set_df_value("air_ssa_lw", 0, spartacus.air_ssa_lw)
        set_df_value("air_ssa_sw", 0, spartacus.air_ssa_sw)
        set_df_value(
            "ground_albedo_dir_mult_fact", 0, spartacus.ground_albedo_dir_mult_fact
        )
        set_df_value("n_stream_lw_urban", 0, spartacus.n_stream_lw_urban)
        set_df_value("n_stream_sw_urban", 0, spartacus.n_stream_sw_urban)
        set_df_value(
            "n_vegetation_region_urban", 0, spartacus.n_vegetation_region_urban
        )
        set_df_value("sw_dn_direct_frac", 0, spartacus.sw_dn_direct_frac)
        set_df_value("use_sw_direct_albedo", 0, spartacus.use_sw_direct_albedo)
        set_df_value(
            "veg_contact_fraction_const", 0, spartacus.veg_contact_fraction_const
        )
        set_df_value("veg_fsd_const", 0, spartacus.veg_fsd_const)
        set_df_value("veg_ssa_lw", 0, spartacus.veg_ssa_lw)
        set_df_value("veg_ssa_sw", 0, spartacus.veg_ssa_sw)

        # Conductance properties
        conductance = props.conductance
        set_df_value("g_max", 0, conductance.g_max)
        set_df_value("g_k", 0, conductance.g_k)
        set_df_value("g_q_base", 0, conductance.g_q_base)
        set_df_value("g_q_shape", 0, conductance.g_q_shape)
        set_df_value("g_t", 0, conductance.g_t)
        set_df_value("g_sm", 0, conductance.g_sm)
        set_df_value("kmax", 0, conductance.kmax)
        set_df_value("gsmodel", 0, conductance.gsmodel)
        set_df_value("s1", 0, conductance.s1)
        set_df_value("s2", 0, conductance.s2)
        set_df_value("tl", 0, conductance.tl)
        set_df_value("th", 0, conductance.th)

        # Irrigation parameters
        irrigation = props.irrigation
        set_df_value("h_maintain", 0, irrigation.h_maintain)
        set_df_value("faut", 0, irrigation.faut)
        set_df_value("ie_start", 0, irrigation.ie_start)
        set_df_value("ie_end", 0, irrigation.ie_end)
        set_df_value("internalwateruse_h", 0, irrigation.internalwateruse_h)
        # weekly profile
        for i, day in enumerate(
            [
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            ]
        ):
            set_df_value(f"daywatper", (i,), getattr(irrigation.daywatper, day))
            set_df_value(f"daywat", (i,), getattr(irrigation.daywat, day))
        # 24-hour profile
        for hour in range(24):
            for i, day in enumerate(["working_day", "holiday"]):
                prop_day = getattr(irrigation.wuprofa_24hr, day)
                set_df_value(f"wuprofa_24hr", (hour, i), prop_day[f"{hour+1}"])
                prop_day = getattr(irrigation.wuprofm_24hr, day)
                set_df_value(f"wuprofm_24hr", (hour, i), prop_day[f"{hour+1}"])

        # Process anthropogenic emissions
        anthro = props.anthropogenic_emissions
        set_df_value("startdls", 0, anthro.startdls)
        set_df_value("enddls", 0, anthro.enddls)
        # heat
        for i, day in enumerate(["working_day", "holiday"]):
            set_df_value("qf0_beu", (i,), getattr(anthro.heat.qf0_beu, day))
            set_df_value("qf_a", (i,), getattr(anthro.heat.qf_a, day))
            set_df_value("qf_b", (i,), getattr(anthro.heat.qf_b, day))
            set_df_value("qf_c", (i,), getattr(anthro.heat.qf_c, day))
            set_df_value("baset_cooling", (i,), getattr(anthro.heat.baset_cooling, day))
            set_df_value("baset_heating", (i,), getattr(anthro.heat.baset_heating, day))
            set_df_value("ah_min", (i,), getattr(anthro.heat.ah_min, day))
            set_df_value(
                "ah_slope_cooling", (i,), getattr(anthro.heat.ah_slope_cooling, day)
            )
            set_df_value(
                "ah_slope_heating", (i,), getattr(anthro.heat.ah_slope_heating, day)
            )
            # Hourly profiles
            for hour in range(24):
                set_df_value(
                    "ahprof_24hr",
                    (hour, i),
                    getattr(anthro.heat.ahprof_24hr, day)[f"{hour+1}"],
                )

        # CO2 parameters
        set_df_value("co2pointsource", 0, anthro.co2.co2pointsource)
        set_df_value("ef_umolco2perj", 0, anthro.co2.ef_umolco2perj)
        set_df_value("enef_v_jkm", 0, anthro.co2.enef_v_jkm)

        # Traffic and emission factors for weekday/weekend
        for i, day in enumerate(["working_day", "holiday"]):
            # Traffic rate and emission factors
            set_df_value("trafficrate", (i,), getattr(anthro.co2.trafficrate, day))
            set_df_value("fcef_v_kgkm", (i,), getattr(anthro.co2.fcef_v_kgkm, day))

            # 24-hour profiles
            for hour in range(24):
                set_df_value(
                    "traffprof_24hr",
                    (hour, i),
                    getattr(anthro.co2.traffprof_24hr, day)[f"{hour+1}"],
                )
                set_df_value(
                    "humactivity_24hr",
                    (hour, i),
                    getattr(anthro.co2.humactivity_24hr, day)[f"{hour+1}"],
                )

        # Traffic units setting
        set_df_value("trafficunits", 0, anthro.co2.trafficunits)

        # Additional emission-related parameters
        set_df_value("frfossilfuel_heat", 0, anthro.co2.frfossilfuel_heat)
        set_df_value("frfossilfuel_nonheat", 0, anthro.co2.frfossilfuel_nonheat)
        set_df_value("maxfcmetab", 0, anthro.co2.maxfcmetab)
        set_df_value("maxqfmetab", 0, anthro.co2.maxqfmetab)
        set_df_value("minfcmetab", 0, anthro.co2.minfcmetab)
        set_df_value("minqfmetab", 0, anthro.co2.minqfmetab)

        # Snow parameters
        snow = props.snow
        set_df_value("crwmax", 0, snow.crwmax)
        set_df_value("crwmin", 0, snow.crwmin)
        set_df_value("narp_emis_snow", 0, snow.narp_emis_snow)
        set_df_value("preciplimit", 0, snow.preciplimit)
        set_df_value("preciplimitalb", 0, snow.preciplimitalb)
        set_df_value("snowalbmax", 0, snow.snowalbmax)
        set_df_value("snowalbmin", 0, snow.snowalbmin)
        set_df_value("snowdensmin", 0, snow.snowdensmin)
        set_df_value("snowdensmax", 0, snow.snowdensmax)
        set_df_value("snowlimbldg", 0, snow.snowlimbldg)
        set_df_value("snowlimpaved", 0, snow.snowlimpaved)
        set_df_value("tau_a", 0, snow.tau_a)
        set_df_value("tau_r", 0, snow.tau_r)
        set_df_value("tau_f", 0, snow.tau_f)
        set_df_value("tempmeltfact", 0, snow.tempmeltfact)
        set_df_value("radmeltfact", 0, snow.radmeltfact)

        # Missing height parameters for vegetation and buildings
        set_df_value("bldgh", 0, props.land_cover.bldgs.bldgh)  # Building height
        set_df_value(
            "evetreeh", 0, props.land_cover.evetr.evetreeh
        )  # Evergreen tree height
        set_df_value(
            "dectreeh", 0, props.land_cover.dectr.dectreeh
        )  # Deciduous tree height
        # Add to to_df_state where vegetation parameters are handled

        # Missing FAI parameters
        set_df_value("faibldg", 0, props.land_cover.bldgs.faibldg)
        set_df_value("faievetree", 0, props.land_cover.evetr.faievetree)
        set_df_value("faidectree", 0, props.land_cover.dectr.faidectree)

        # LUMPS parameters
        lumps = props.lumps
        set_df_value("raincover", 0, lumps.raincover)
        set_df_value("rainmaxres", 0, lumps.rainmaxres)
        set_df_value("drainrt", 0, lumps.drainrt)
        set_df_value("veg_type", 0, lumps.veg_type)

        # Population profile parameters
        set_df_value("popdensnighttime", 0, anthro.heat.popdensnighttime)
        for i, day in enumerate(["working_day", "holiday"]):
            set_df_value(
                "popdensdaytime", (i,), getattr(anthro.heat.popdensdaytime, day)
            )
            # 24-hour population profile
            for hour in range(24):
                set_df_value(
                    "popprof_24hr",
                    (hour, i),
                    getattr(anthro.heat.popprof_24hr, day)[f"{hour+1}"],
                )

        # Additional CO2 parameters
        set_df_value("frfossilfuel_heat", 0, anthro.co2.frfossilfuel_heat)
        set_df_value("frfossilfuel_nonheat", 0, anthro.co2.frfossilfuel_nonheat)
        set_df_value("maxfcmetab", 0, anthro.co2.maxfcmetab)
        set_df_value("maxqfmetab", 0, anthro.co2.maxqfmetab)
        set_df_value("minfcmetab", 0, anthro.co2.minfcmetab)
        set_df_value("minqfmetab", 0, anthro.co2.minqfmetab)
        set_df_value("trafficrate", (0,), anthro.co2.trafficrate.working_day)
        set_df_value("trafficrate", (1,), anthro.co2.trafficrate.holiday)
        set_df_value("trafficunits", 0, anthro.co2.trafficunits)

        # Snow profile
        for i, day in enumerate(["working_day", "holiday"]):
            for hour in range(24):
                set_df_value(
                    "snowprof_24hr",
                    (hour, i),
                    getattr(snow.snowprof_24hr, day)[f"{hour+1}"],
                )
        # Surface properties
        surface_map = {
            "paved": 0,
            "bldgs": 1,
            "evetr": 2,
            "dectr": 3,
            "grass": 4,
            "bsoil": 5,
            "water": 6,
        }

        # Process each surface type
        for surf_name, surf_idx in surface_map.items():
            surface = getattr(props.land_cover, surf_name)

            # Basic surface properties
            set_df_value("sfr_surf", (surf_idx,), surface.sfr)
            set_df_value("emis", (surf_idx,), surface.emis)

            # Add water distribution parameters
            if surface.waterdist is not None:
                # Map of possible distribution targets based on (8,6) dimensionality
                # 8 rows: Paved(0), Bldgs(1), EveTr(2), DecTr(3), Grass(4), BSoil(5), Water(6), Extra(7)
                # 6 cols: Paved(0), Bldgs(1), EveTr(2), DecTr(3), Grass(4), BSoil(5)
                dist_targets = {
                    "to_paved": 0,
                    "to_bldgs": 1,
                    "to_evetr": 2,
                    "to_dectr": 3,
                    "to_grass": 4,
                    "to_bsoil": 5,
                    "to_water": 6,
                }

                # Set water distribution values
                for target, value in surface.waterdist.__dict__.items():
                    try:
                        target_idx = dist_targets[target]
                        # print(surf_idx, target_idx, value)
                    except KeyError:
                        print(f"Target {target} not found in dist_targets")
                        continue
                    if value is not None:
                        if target == "to_runoff":
                            # Special case for runoff (separate column)
                            # set_df_value("waterdist_runoff", (surf_idx,), value)
                            pass
                        elif target == "to_soilstore":
                            # Special case for soil store (separate column)
                            # set_df_value("waterdist_soilstore", (surf_idx,), value)
                            pass
                        elif target == "to_water":
                            # Special case for water (row 6)
                            set_df_value("waterdist", (6, surf_idx), value)
                        elif target in dist_targets:
                            # Regular surface-to-surface distributions
                            target_idx = dist_targets[target]
                            # Note: in the DataFrame, first index is FROM surface, second is TO surface
                            set_df_value("waterdist", (target_idx, surf_idx), value)

                # Set unused row (7) to 0
                for col_idx in range(6):
                    set_df_value("waterdist", (7, col_idx), 0.0)
                # Set diagonal elements (targets to themselves) to 0
                for row_idx in range(6):
                    set_df_value("waterdist", (row_idx, row_idx), 0.0)

            # Handle albedo
            if hasattr(surface, "alb"):
                set_df_value("alb", (surf_idx,), surface.alb)
            elif hasattr(surface, "alb_min") and hasattr(surface, "alb_max"):
                set_df_value("alb", (surf_idx,), surface.alb_min)  # Use min as default
                if surf_name == "dectr":
                    set_df_value("albmax_dectr", 0, surface.alb_max)
                    set_df_value("albmin_dectr", 0, surface.alb_min)
                elif surf_name == "evetr":
                    set_df_value("albmax_evetr", 0, surface.alb_max)
                    set_df_value("albmin_evetr", 0, surface.alb_min)
                elif surf_name == "grass":
                    set_df_value("albmax_grass", 0, surface.alb_max)
                    set_df_value("albmin_grass", 0, surface.alb_min)
            # Add to OHM section
            if hasattr(surface, "ohm_threshsw"):
                set_df_value("ohm_threshsw", (surf_idx,), surface.ohm_threshsw)
                set_df_value("ohm_threshsw", (7,), surface.ohm_threshsw)

            if hasattr(surface, "ohm_threshwd"):
                set_df_value("ohm_threshwd", (surf_idx,), surface.ohm_threshwd)
                set_df_value("ohm_threshwd", (7,), surface.ohm_threshwd)
            if hasattr(surface, "chanohm"):
                set_df_value("chanohm", (surf_idx,), surface.chanohm)
            if hasattr(surface, "cpanohm"):
                set_df_value("cpanohm", (surf_idx,), surface.cpanohm)
            if hasattr(surface, "kkanohm"):
                set_df_value("kkanohm", (surf_idx,), surface.kkanohm)

            # Add to surface properties section
            if hasattr(surface, "soildepth"):
                set_df_value("soildepth", (surf_idx,), surface.soildepth)
            if hasattr(surface, "soilstorecap"):
                set_df_value("soilstorecap_surf", (surf_idx,), surface.soilstorecap)
            if hasattr(surface, "statelimit"):
                set_df_value("statelimit_surf", (surf_idx,), surface.statelimit)

            if hasattr(surface, "wetthresh"):
                set_df_value("wetthresh_surf", (surf_idx,), surface.wetthresh)

            # porosity parameters for deciduous trees
            if hasattr(surface, "pormin_dec"):
                set_df_value("pormin_dec", 0, surface.pormin_dec)
            if hasattr(surface, "pormax_dec"):
                set_df_value("pormax_dec", 0, surface.pormax_dec)

            # capacity parameters for deciduous trees
            if hasattr(surface, "capmin_dec"):
                set_df_value("capmin_dec", 0, surface.capmin_dec)
            if hasattr(surface, "capmax_dec"):
                set_df_value("capmax_dec", 0, surface.capmax_dec)
            if hasattr(surface, "min_res_bioco2"):
                set_df_value("min_res_bioco2", (surf_idx - 2,), surface.min_res_bioco2)

            # OHM coefficients
            if surface.ohm_coef:
                for i, (a1, a2, a3) in enumerate(
                    zip(
                        surface.ohm_coef.a1.values(),
                        surface.ohm_coef.a2.values(),
                        surface.ohm_coef.a3.values(),
                    )
                ):
                    set_df_value("ohm_coef", (surf_idx, i, 0), a1)
                    set_df_value("ohm_coef", (surf_idx, i, 1), a2)
                    set_df_value("ohm_coef", (surf_idx, i, 2), a3)
                    # dummy row for extra surface
                    set_df_value("ohm_coef", (7, i, 0), a1)
                    set_df_value("ohm_coef", (7, i, 1), a2)
                    set_df_value("ohm_coef", (7, i, 2), a3)

            # Storage and drain parameters
            if hasattr(surface, "storedrainprm"):
                for i, var in enumerate(
                    [
                        "store_min",
                        "store_max",
                        "store_cap",
                        "drain_eq",
                        "drain_coef_1",
                        "drain_coef_2",
                    ]
                ):
                    set_df_value(
                        "storedrainprm",
                        (i, surf_idx),
                        getattr(surface.storedrainprm, var),
                    )
            # Irrigation coefficients
            if hasattr(surface, "ie_a"):
                set_df_value("ie_a", (surf_idx - 2,), surface.ie_a)
            if hasattr(surface, "ie_m"):
                set_df_value("ie_m", (surf_idx - 2,), surface.ie_m)

            # Maximum conductance
            if hasattr(surface, "maxconductance"):
                idx = surf_idx - 2
                set_df_value("maxconductance", (idx,), surface.maxconductance)

            # Snow pack limit
            if hasattr(surface, "snowpacklimit"):
                set_df_value("snowpacklimit", (surf_idx,), surface.snowpacklimit)

            # LAI parameters
            if hasattr(surface, "lai"):
                lai = surface.lai
                idx = surf_idx - 2
                set_df_value("baset", (idx,), lai.baset)
                set_df_value("gddfull", (idx,), lai.gddfull)
                set_df_value("basete", (idx,), lai.basete)
                set_df_value("sddfull", (idx,), lai.sddfull)
                set_df_value("laimin", (idx,), lai.laimin)
                set_df_value("laimax", (idx,), lai.laimax)
                set_df_value("laitype", (idx,), lai.laitype)
                for i, var in enumerate(
                    [
                        "growth_lai",
                        "growth_gdd",
                        "senescence_lai",
                        "senescence_sdd",
                    ]
                ):
                    set_df_value("laipower", (i, idx), getattr(lai.laipower, var))

            # CO2 parameters for vegetated surfaces
            if hasattr(surface, "beta_bioco2"):
                idx = surf_idx - 2
                set_df_value("beta_bioco2", (idx,), surface.beta_bioco2)
                set_df_value("beta_enh_bioco2", (idx,), surface.beta_enh_bioco2)
                set_df_value("alpha_bioco2", (idx,), surface.alpha_bioco2)
                set_df_value("alpha_enh_bioco2", (idx,), surface.alpha_enh_bioco2)

            # Add to surface properties section
            if hasattr(surface, "sathydraulicconduct"):
                set_df_value(
                    "sathydraulicconduct", (surf_idx,), surface.sathydraulicconduct
                )

            # Water specific parameters
            if hasattr(surface, "flowchange"):
                set_df_value("flowchange", 0, surface.flowchange)

            # Add to CO2 parameters section for vegetated surfaces
            if hasattr(surface, "resp_a"):
                set_df_value("resp_a", (surf_idx - 2,), surface.resp_a)
            if hasattr(surface, "resp_b"):
                set_df_value("resp_b", (surf_idx - 2,), surface.resp_b)
            if hasattr(surface, "theta_bioco2"):
                set_df_value("theta_bioco2", (surf_idx - 2,), surface.theta_bioco2)

            # Snowpack limit
            if hasattr(surface, "snowpacklimit"):
                set_df_value("snowpacklimit", (surf_idx,), surface.snowpacklimit)

            # irrigation fraction
            if hasattr(surface, "irrfrac"):
                set_df_value(f"irrfrac{surf_name}", 0, surface.irrfrac)

            # Thermal layers
            if hasattr(surface, "thermal_layers"):
                # Get the lists from thermal_layers
                dz_list = surface.thermal_layers.dz
                k_list = surface.thermal_layers.k
                cp_list = surface.thermal_layers.cp

                # Set each value in the lists
                for i in range(5):  # We know there are exactly 5 values
                    set_df_value("dz_surf", (surf_idx, i), dz_list[i])
                    set_df_value("k_surf", (surf_idx, i), k_list[i])
                    set_df_value("cp_surf", (surf_idx, i), cp_list[i])

            # Initial states
            init_state = getattr(site.initial_states, surf_name)
            if init_state:
                # Basic state parameters
                set_df_value("state_surf", (surf_idx,), init_state.state)
                set_df_value("soilstore_surf", (surf_idx,), init_state.soilstore)

                # fill in dummy values for variables that are not needed for users
                for i in range(12):
                    set_df_value("hdd_id", (i,), 0)
                set_df_value("dqndt", 0, 1)
                set_df_value("dqnsdt", 0, 10)
                set_df_value("qn_av", 0, 10)
                set_df_value("qn_s_av", 0, 10)
                set_df_value("dt_since_start", 0, 0)
                set_df_value("lenday_id", 0, 0)
                set_df_value("tmax_id", 0, 0)
                set_df_value("tmin_id", 0, 0)
                set_df_value("tstep_prev", 0, 300)
                set_df_value("tair_av", 0, 0)
                set_df_value("snowfallcum", 0, 0)

                # Snow-related parameters
                if init_state.snowfrac is not None:
                    set_df_value("snowfrac", (surf_idx,), init_state.snowfrac)
                if init_state.snowpack is not None:
                    set_df_value("snowpack", (surf_idx,), init_state.snowpack)
                if init_state.snowwater is not None:
                    set_df_value("snowwater", (surf_idx,), init_state.snowwater)
                if init_state.snowdens is not None:
                    set_df_value("snowdens", (surf_idx,), init_state.snowdens)
                if init_state.icefrac is not None:
                    set_df_value("icefrac", (surf_idx,), init_state.icefrac)

                # Vegetation-specific parameters
                if surf_name in ["dectr", "evetr", "grass"]:
                    # albedo
                    if init_state.alb_id is not None:
                        set_df_value(f"alb{surf_name}_id", 0, init_state.alb_id)
                    # LAI
                    if init_state.lai_id is not None:
                        set_df_value(f"lai_id", (surf_idx - 2,), init_state.lai_id)
                    # GDD
                    if init_state.gdd_id is not None:
                        set_df_value(f"gdd_id", (surf_idx - 2,), init_state.gdd_id)
                    # SDD
                    if init_state.sdd_id is not None:
                        set_df_value(f"sdd_id", (surf_idx - 2,), init_state.sdd_id)
                    # water use
                    if init_state.wu is not None:
                        set_df_value(
                            f"wuday_id",
                            ((surf_idx - 2) * 3 + 0,),
                            init_state.wu.wu_total,
                        )
                        set_df_value(
                            f"wuday_id",
                            ((surf_idx - 2) * 3 + 1,),
                            init_state.wu.wu_auto,
                        )
                        set_df_value(
                            f"wuday_id",
                            ((surf_idx - 2) * 3 + 2,),
                            init_state.wu.wu_manual,
                        )
                    # Additional parameters for deciduous trees
                    if surf_name == "dectr":
                        if init_state.decidcap_id is not None:
                            set_df_value("decidcap_id", 0, init_state.decidcap_id)
                        if init_state.porosity_id is not None:
                            set_df_value("porosity_id", 0, init_state.porosity_id)
                # temperature
                for k, var in enumerate(["temperature", "tsfc", "tin"]):
                    if var == "tsfc":
                        set_df_value(f"tsfc_surf", (surf_idx,), init_state.tsfc)
                    elif var == "temperature":
                        for k in range(5):
                            set_df_value(
                                f"temp_surf", (surf_idx, k), getattr(init_state, var)[k]
                            )
                    elif var == "tin":
                        set_df_value(f"tin_surf", (surf_idx,), init_state.tin)
            # Set initial snow albedo
            set_df_value("snowalb", 0, site.initial_states.snowalb)

        # Vertical layers
        if hasattr(props, "vertical_layers"):
            print("vertical_layers here")
            vertical_layers = props.vertical_layers
            set_df_value("nlayer", 0, vertical_layers.nlayer)
            for i in range(vertical_layers.nlayer + 1):
                set_df_value("height", (i,), vertical_layers.height[i])
            for i in range(vertical_layers.nlayer):
                set_df_value("building_scale", (i,), vertical_layers.building_scale[i])
                set_df_value("building_frac", (i,), vertical_layers.building_frac[i])
                set_df_value("veg_scale", (i,), vertical_layers.veg_scale[i])
                set_df_value("veg_frac", (i,), vertical_layers.veg_frac[i])
            for i, layer in enumerate(vertical_layers.roofs):
                set_df_value(
                    f"roof_albedo_dir_mult_fact",
                    (0, i),
                    layer.roof_albedo_dir_mult_fact,
                )
                set_df_value(f"alb_roof", (i,), layer.alb)
                set_df_value(f"emis_roof", (i,), layer.emis)
                set_df_value(f"statelimit_roof", (i,), layer.statelimit)
                set_df_value(f"soilstorecap_roof", (i,), layer.soilstorecap)
                set_df_value(f"wetthresh_roof", (i,), layer.wetthresh)
                thermal_layers = layer.thermal_layers
                for j, var in enumerate(["dz", "k", "cp"]):
                    for k in range(5):
                        set_df_value(
                            f"{var}_roof", (i, k), getattr(thermal_layers, var)[k]
                        )
            for i, layer in enumerate(vertical_layers.walls):
                set_df_value(f"wall_specular_frac", (0, i), layer.wall_specular_frac)
                set_df_value(f"alb_wall", (i,), layer.alb)
                set_df_value(f"emis_wall", (i,), layer.emis)
                set_df_value(f"statelimit_wall", (i,), layer.statelimit)
                set_df_value(f"soilstorecap_wall", (i,), layer.soilstorecap)
                set_df_value(f"wetthresh_wall", (i,), layer.wetthresh)
                thermal_layers = layer.thermal_layers
                for j, var in enumerate(["dz", "k", "cp"]):
                    for k in range(5):
                        set_df_value(
                            f"{var}_wall", (i, k), getattr(thermal_layers, var)[k]
                        )
        for building_facet in ["roofs", "walls"]:
            facet = building_facet[:-1]
            if hasattr(site.initial_states, building_facet):
                for j, layer in enumerate(getattr(site.initial_states, building_facet)):
                    set_df_value(f"state_{facet}", (j,), layer.state)
                    set_df_value(f"soilstore_{facet}", (j,), layer.soilstore)
                    # set_df_value(f"snowwater_{facet}", (j,), layer.snowwater)
                    # set_df_value(f"snowdens_{facet}", (j,), layer.snowdens)
                    # set_df_value(f"snowfrac_{facet}", (j,), layer.snowfrac)
                    # set_df_value(f"snowpack_{facet}", (j,), layer.snowpack)
                    for k, var in enumerate(["temperature", "tsfc", "tin"]):
                        if var == "tsfc":
                            set_df_value(f"tsfc_{facet}", (j,), layer.tsfc)
                        elif var == "temperature":
                            for k in range(5):
                                set_df_value(
                                    f"temp_{facet}", (j, k), getattr(layer, var)[k]
                                )
                        elif var == "tin":
                            set_df_value(f"tin_{facet}", (j,), layer.tin)
        return df

    def to_df_state_new(self) -> pd.DataFrame:
        """Convert config to DataFrame state format"""
        # Initialize empty DataFrame with correct structure
        columns = self.create_multi_index_columns("df_state_columns.txt")
        columns.set_names(["var", "ind_dim"], inplace=True)
        index = pd.Index([0], name="grid")
        df = pd.DataFrame(index=index, columns=columns)

        # Process each site (assuming single site for now)
        site = self.site[0]
        props = site.properties
        gridiv = site.gridiv
        # update index using gridiv
        df.index = pd.Index([gridiv], name="grid")

        # Helper function to set values in DataFrame
        def set_df_value(col_name: str, indices: Union[int, Tuple], value: float):
            if isinstance(indices, int):
                if indices == 0:
                    str_indices = str(indices)
                else:
                    str_indices = f"({indices},)"
            else:
                # Tuples should maintain their string representation
                str_indices = str(indices)
            df.loc[gridiv, (col_name, str_indices)] = value

        # Model control
        # Create mappings for cleaner code
        model_control = self.model.control
        model_physics = self.model.physics
        lumps = props.lumps
        spartacus = props.spartacus
        conductance = props.conductance
        irrigation = props.irrigation
        map_model_control = {
            "tstep": model_control.tstep,
            "diagnose": model_control.diagnose,
        }

        map_model_physics = {
            "netradiationmethod": model_physics.netradiationmethod,
            "emissionsmethod": model_physics.emissionsmethod,
            "storageheatmethod": model_physics.storageheatmethod,
            "ohmincqf": model_physics.ohmincqf,
            "roughlenmommethod": model_physics.roughlenmommethod,
            "roughlenheatmethod": model_physics.roughlenheatmethod,
            "stabilitymethod": model_physics.stabilitymethod,
            "smdmethod": model_physics.smdmethod,
            "waterusemethod": model_physics.waterusemethod,
            "diagmethod": model_physics.diagmethod,
            "faimethod": model_physics.faimethod,
            "localclimatemethod": model_physics.localclimatemethod,
            "snowuse": model_physics.snowuse,
        }

        map_site_props = {
            "gridiv": gridiv,
            "lat": props.lat,
            "lng": props.lng,
            "alt": props.alt,
            "timezone": props.timezone,
            "surfacearea": props.surfacearea,
            "z": props.z,
            "z0m_in": props.z0m_in,
            "zdm_in": props.zdm_in,
            "pipecapacity": props.pipecapacity,
            "runofftowater": props.runofftowater,
            "narp_trans_site": props.narp_trans_site,
        }

        map_lumps = {
            "raincover": lumps.raincover,
            "rainmaxres": lumps.rainmaxres,
            "drainrt": lumps.drainrt,
            "veg_type": lumps.veg_type,
        }

        map_spartacus = {
            "air_ext_lw": spartacus.air_ext_lw,
            "air_ext_sw": spartacus.air_ext_sw,
            "air_ssa_lw": spartacus.air_ssa_lw,
            "air_ssa_sw": spartacus.air_ssa_sw,
            "ground_albedo_dir_mult_fact": spartacus.ground_albedo_dir_mult_fact,
            "n_stream_lw_urban": spartacus.n_stream_lw_urban,
            "n_stream_sw_urban": spartacus.n_stream_sw_urban,
            "n_vegetation_region_urban": spartacus.n_vegetation_region_urban,
            "sw_dn_direct_frac": spartacus.sw_dn_direct_frac,
            "use_sw_direct_albedo": spartacus.use_sw_direct_albedo,
            "veg_contact_fraction_const": spartacus.veg_contact_fraction_const,
            "veg_fsd_const": spartacus.veg_fsd_const,
            "veg_ssa_lw": spartacus.veg_ssa_lw,
            "veg_ssa_sw": spartacus.veg_ssa_sw,
        }

        map_conductance = {
            "g_max": conductance.g_max,
            "g_k": conductance.g_k,
            "g_q_base": conductance.g_q_base,
            "g_q_shape": conductance.g_q_shape,
            "g_t": conductance.g_t,
            "g_sm": conductance.g_sm,
            "kmax": conductance.kmax,
            "gsmodel": conductance.gsmodel,
            "s1": conductance.s1,
            "s2": conductance.s2,
            "tl": conductance.tl,
            "th": conductance.th,
        }

        map_irrigation = {
            "h_maintain": irrigation.h_maintain,
            "faut": irrigation.faut,
            "ie_start": irrigation.ie_start,
            "ie_end": irrigation.ie_end,
            "internalwateruse_h": irrigation.internalwateruse_h,
        }

        # Set values using mappings
        for group in [
            map_model_control,
            map_model_physics,
            map_site_props,
            map_lumps,
            map_spartacus,
            map_conductance,
            map_irrigation,
        ]:
            for name, value in group.items():
                set_df_value(name, 0, value)

        # weekly profile
        for i, day in enumerate(
            [
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            ]
        ):
            for var in ["daywatper", "daywat"]:
                val = getattr(getattr(irrigation, var), day)
                set_df_value(var, (i,), val)
        # 24-hour profile
        for hour in range(24):
            for i, day in enumerate(["working_day", "holiday"]):
                for var in ["wuprofa_24hr", "wuprofm_24hr"]:
                    val = getattr(getattr(irrigation, var), day)[f"{hour+1}"]
                    set_df_value(var, (hour, i), val)

        # Process anthropogenic emissions
        anthro = props.anthropogenic_emissions
        for var in ["startdls", "enddls"]:
            set_df_value(var, 0, getattr(anthro, var))

        # heat
        anthro_heat = anthro.heat
        # day-specific mappings for anthro_heat
        daymap_anthro_heat = {
            "qf0_beu": anthro_heat.qf0_beu,
            "qf_a": anthro_heat.qf_a,
            "qf_b": anthro_heat.qf_b,
            "qf_c": anthro_heat.qf_c,
            "baset_cooling": anthro_heat.baset_cooling,
            "baset_heating": anthro_heat.baset_heating,
            "ah_min": anthro_heat.ah_min,
            "ah_slope_cooling": anthro_heat.ah_slope_cooling,
            "ah_slope_heating": anthro_heat.ah_slope_heating,
            "popdensdaytime": anthro_heat.popdensdaytime,
        }

        # Set values for working day and holiday
        for i, day in enumerate(["working_day", "holiday"]):
            for name, value in daymap_anthro_heat.items():
                set_df_value(name, (i,), getattr(value, day))

            # Hourly profiles
            for hour in range(24):
                set_df_value(
                    "ahprof_24hr",
                    (hour, i),
                    getattr(anthro_heat.ahprof_24hr, day)[f"{hour+1}"],
                )

        # CO2 parameters
        anthro_co2 = anthro.co2
        # invariant parameters
        map_anthro_co2 = {
            "co2pointsource": anthro_co2.co2pointsource,
            "ef_umolco2perj": anthro_co2.ef_umolco2perj,
            "enef_v_jkm": anthro_co2.enef_v_jkm,
            "trafficunits": anthro_co2.trafficunits,
            "frfossilfuel_heat": anthro_co2.frfossilfuel_heat,
            "frfossilfuel_nonheat": anthro_co2.frfossilfuel_nonheat,
            "maxfcmetab": anthro_co2.maxfcmetab,
            "maxqfmetab": anthro_co2.maxqfmetab,
            "minfcmetab": anthro_co2.minfcmetab,
            "minqfmetab": anthro_co2.minqfmetab,
        }
        for name, value in map_anthro_co2.items():
            set_df_value(name, 0, value)

        # Traffic and emission factors for weekday/weekend
        daymap_anthro_co2_traffic = {
            "trafficrate": anthro_co2.trafficrate,
            "fcef_v_kgkm": anthro_co2.fcef_v_kgkm,
        }
        for i, day in enumerate(["working_day", "holiday"]):
            for name, value in daymap_anthro_co2_traffic.items():
                set_df_value(name, (i,), getattr(value, day))

        # 24-hour profiles dependent on day type
        dayhourmap_anthro_co2_traffic = {
            "traffprof_24hr": anthro_co2.traffprof_24hr,
            "humactivity_24hr": anthro_co2.humactivity_24hr,
        }
        for i, day in enumerate(["working_day", "holiday"]):
            for hour in range(24):
                for name, value in dayhourmap_anthro_co2_traffic.items():
                    set_df_value(name, (hour, i), getattr(value, day)[f"{hour+1}"])

        # Snow parameters
        snow = props.snow
        map_snow = {
            "crwmax": snow.crwmax,
            "crwmin": snow.crwmin,
            "narp_emis_snow": snow.narp_emis_snow,
            "preciplimit": snow.preciplimit,
            "preciplimitalb": snow.preciplimitalb,
            "snowalbmax": snow.snowalbmax,
            "snowalbmin": snow.snowalbmin,
            "snowdensmin": snow.snowdensmin,
            "snowdensmax": snow.snowdensmax,
            "snowlimbldg": snow.snowlimbldg,
            "snowlimpaved": snow.snowlimpaved,
            "tau_a": snow.tau_a,
            "tau_r": snow.tau_r,
            "tau_f": snow.tau_f,
            "tempmeltfact": snow.tempmeltfact,
            "radmeltfact": snow.radmeltfact,
        }
        for name, value in map_snow.items():
            set_df_value(name, 0, value)

        # Missing height parameters for vegetation and buildings
        map_veg_height = {
            "bldgh": props.land_cover.bldgs.bldgh,  # Building height
            "evetreeh": props.land_cover.evetr.evetreeh,  # Evergreen tree height
            "dectreeh": props.land_cover.dectr.dectreeh,  # Deciduous tree height
        }
        for name, value in map_veg_height.items():
            set_df_value(name, 0, value)

        # Missing FAI parameters
        map_faibldg = {
            "faibldg": props.land_cover.bldgs.faibldg,
            "faievetree": props.land_cover.evetr.faievetree,
            "faidectree": props.land_cover.dectr.faidectree,
        }
        for name, value in map_faibldg.items():
            set_df_value(name, 0, value)

        # Population profile parameters
        set_df_value("popdensnighttime", 0, anthro_heat.popdensnighttime)
        for i, day in enumerate(["working_day", "holiday"]):
            # set_df_value(
            #     "popdensdaytime", (i,), getattr(anthro_heat.popdensdaytime, day)
            # )
            # 24-hour population profile
            for hour in range(24):
                set_df_value(
                    "popprof_24hr",
                    (hour, i),
                    getattr(anthro_heat.popprof_24hr, day)[f"{hour+1}"],
                )

        dayhourmap_snow = {
            "snowprof_24hr": snow.snowprof_24hr,
        }
        for i, day in enumerate(["working_day", "holiday"]):
            for hour in range(24):
                for name, value in dayhourmap_snow.items():
                    set_df_value(name, (hour, i), getattr(value, day)[f"{hour+1}"])


        # Surface properties
        surface_map = {
            "paved": 0,
            "bldgs": 1,
            "evetr": 2,
            "dectr": 3,
            "grass": 4,
            "bsoil": 5,
            "water": 6,
        }

        # Process each surface type
        for surf_name, surf_idx in surface_map.items():
            surface = getattr(props.land_cover, surf_name)

            # Basic surface properties
            set_df_value("sfr_surf", (surf_idx,), surface.sfr)
            set_df_value("emis", (surf_idx,), surface.emis)

            # Add water distribution parameters
            if surface.waterdist is not None:
                # Map of possible distribution targets based on (8,6) dimensionality
                # 8 rows: Paved(0), Bldgs(1), EveTr(2), DecTr(3), Grass(4), BSoil(5), Water(6), Extra(7)
                # 6 cols: Paved(0), Bldgs(1), EveTr(2), DecTr(3), Grass(4), BSoil(5)
                dist_targets = {
                    "to_paved": 0,
                    "to_bldgs": 1,
                    "to_evetr": 2,
                    "to_dectr": 3,
                    "to_grass": 4,
                    "to_bsoil": 5,
                    "to_water": 6,
                }

                # Set water distribution values
                for target, value in surface.waterdist.__dict__.items():
                    try:
                        target_idx = dist_targets[target]
                        # print(surf_idx, target_idx, value)
                    except KeyError:
                        print(f"Target {target} not found in dist_targets")
                        continue
                    if value is not None:
                        if target == "to_runoff":
                            # Special case for runoff (separate column)
                            # set_df_value("waterdist_runoff", (surf_idx,), value)
                            pass
                        elif target == "to_soilstore":
                            # Special case for soil store (separate column)
                            # set_df_value("waterdist_soilstore", (surf_idx,), value)
                            pass
                        elif target == "to_water":
                            # Special case for water (row 6)
                            set_df_value("waterdist", (6, surf_idx), value)
                        elif target in dist_targets:
                            # Regular surface-to-surface distributions
                            target_idx = dist_targets[target]
                            # Note: in the DataFrame, first index is FROM surface, second is TO surface
                            set_df_value("waterdist", (target_idx, surf_idx), value)

                # Set unused row (7) to 0
                for col_idx in range(6):
                    set_df_value("waterdist", (7, col_idx), 0.0)
                # Set diagonal elements (targets to themselves) to 0
                for row_idx in range(6):
                    set_df_value("waterdist", (row_idx, row_idx), 0.0)

            # Handle albedo
            if hasattr(surface, "alb"):
                set_df_value("alb", (surf_idx,), surface.alb)
            elif hasattr(surface, "alb_min") and hasattr(surface, "alb_max"):
                set_df_value("alb", (surf_idx,), surface.alb_min)  # Use min as default
                if surf_name == "dectr":
                    set_df_value("albmax_dectr", 0, surface.alb_max)
                    set_df_value("albmin_dectr", 0, surface.alb_min)
                elif surf_name == "evetr":
                    set_df_value("albmax_evetr", 0, surface.alb_max)
                    set_df_value("albmin_evetr", 0, surface.alb_min)
                elif surf_name == "grass":
                    set_df_value("albmax_grass", 0, surface.alb_max)
                    set_df_value("albmin_grass", 0, surface.alb_min)
            # Add to OHM section
            if hasattr(surface, "ohm_threshsw"):
                set_df_value("ohm_threshsw", (surf_idx,), surface.ohm_threshsw)
                set_df_value("ohm_threshsw", (7,), surface.ohm_threshsw)

            if hasattr(surface, "ohm_threshwd"):
                set_df_value("ohm_threshwd", (surf_idx,), surface.ohm_threshwd)
                set_df_value("ohm_threshwd", (7,), surface.ohm_threshwd)
            if hasattr(surface, "chanohm"):
                set_df_value("chanohm", (surf_idx,), surface.chanohm)
            if hasattr(surface, "cpanohm"):
                set_df_value("cpanohm", (surf_idx,), surface.cpanohm)
            if hasattr(surface, "kkanohm"):
                set_df_value("kkanohm", (surf_idx,), surface.kkanohm)

            # Add to surface properties section
            if hasattr(surface, "soildepth"):
                set_df_value("soildepth", (surf_idx,), surface.soildepth)
            if hasattr(surface, "soilstorecap"):
                set_df_value("soilstorecap_surf", (surf_idx,), surface.soilstorecap)
            if hasattr(surface, "statelimit"):
                set_df_value("statelimit_surf", (surf_idx,), surface.statelimit)

            if hasattr(surface, "wetthresh"):
                set_df_value("wetthresh_surf", (surf_idx,), surface.wetthresh)

            # porosity parameters for deciduous trees
            if hasattr(surface, "pormin_dec"):
                set_df_value("pormin_dec", 0, surface.pormin_dec)
            if hasattr(surface, "pormax_dec"):
                set_df_value("pormax_dec", 0, surface.pormax_dec)

            # capacity parameters for deciduous trees
            if hasattr(surface, "capmin_dec"):
                set_df_value("capmin_dec", 0, surface.capmin_dec)
            if hasattr(surface, "capmax_dec"):
                set_df_value("capmax_dec", 0, surface.capmax_dec)
            if hasattr(surface, "min_res_bioco2"):
                set_df_value("min_res_bioco2", (surf_idx - 2,), surface.min_res_bioco2)

            # OHM coefficients
            if surface.ohm_coef:
                for i, (a1, a2, a3) in enumerate(
                    zip(
                        surface.ohm_coef.a1.values(),
                        surface.ohm_coef.a2.values(),
                        surface.ohm_coef.a3.values(),
                    )
                ):
                    set_df_value("ohm_coef", (surf_idx, i, 0), a1)
                    set_df_value("ohm_coef", (surf_idx, i, 1), a2)
                    set_df_value("ohm_coef", (surf_idx, i, 2), a3)
                    # dummy row for extra surface
                    set_df_value("ohm_coef", (7, i, 0), a1)
                    set_df_value("ohm_coef", (7, i, 1), a2)
                    set_df_value("ohm_coef", (7, i, 2), a3)

            # Storage and drain parameters
            if hasattr(surface, "storedrainprm"):
                for i, var in enumerate(
                    [
                        "store_min",
                        "store_max",
                        "store_cap",
                        "drain_eq",
                        "drain_coef_1",
                        "drain_coef_2",
                    ]
                ):
                    set_df_value(
                        "storedrainprm",
                        (i, surf_idx),
                        getattr(surface.storedrainprm, var),
                    )
            # Irrigation coefficients
            if hasattr(surface, "ie_a"):
                set_df_value("ie_a", (surf_idx - 2,), surface.ie_a)
            if hasattr(surface, "ie_m"):
                set_df_value("ie_m", (surf_idx - 2,), surface.ie_m)

            # Maximum conductance
            if hasattr(surface, "maxconductance"):
                idx = surf_idx - 2
                set_df_value("maxconductance", (idx,), surface.maxconductance)

            # Snow pack limit
            if hasattr(surface, "snowpacklimit"):
                set_df_value("snowpacklimit", (surf_idx,), surface.snowpacklimit)

            # LAI parameters
            if hasattr(surface, "lai"):
                lai = surface.lai
                idx = surf_idx - 2
                set_df_value("baset", (idx,), lai.baset)
                set_df_value("gddfull", (idx,), lai.gddfull)
                set_df_value("basete", (idx,), lai.basete)
                set_df_value("sddfull", (idx,), lai.sddfull)
                set_df_value("laimin", (idx,), lai.laimin)
                set_df_value("laimax", (idx,), lai.laimax)
                set_df_value("laitype", (idx,), lai.laitype)
                for i, var in enumerate(
                    [
                        "growth_lai",
                        "growth_gdd",
                        "senescence_lai",
                        "senescence_sdd",
                    ]
                ):
                    set_df_value("laipower", (i, idx), getattr(lai.laipower, var))

            # CO2 parameters for vegetated surfaces
            if hasattr(surface, "beta_bioco2"):
                idx = surf_idx - 2
                set_df_value("beta_bioco2", (idx,), surface.beta_bioco2)
                set_df_value("beta_enh_bioco2", (idx,), surface.beta_enh_bioco2)
                set_df_value("alpha_bioco2", (idx,), surface.alpha_bioco2)
                set_df_value("alpha_enh_bioco2", (idx,), surface.alpha_enh_bioco2)

            # Add to surface properties section
            if hasattr(surface, "sathydraulicconduct"):
                set_df_value(
                    "sathydraulicconduct", (surf_idx,), surface.sathydraulicconduct
                )

            # Water specific parameters
            if hasattr(surface, "flowchange"):
                set_df_value("flowchange", 0, surface.flowchange)

            # Add to CO2 parameters section for vegetated surfaces
            if hasattr(surface, "resp_a"):
                set_df_value("resp_a", (surf_idx - 2,), surface.resp_a)
            if hasattr(surface, "resp_b"):
                set_df_value("resp_b", (surf_idx - 2,), surface.resp_b)
            if hasattr(surface, "theta_bioco2"):
                set_df_value("theta_bioco2", (surf_idx - 2,), surface.theta_bioco2)

            # Snowpack limit
            if hasattr(surface, "snowpacklimit"):
                set_df_value("snowpacklimit", (surf_idx,), surface.snowpacklimit)

            # irrigation fraction
            if hasattr(surface, "irrfrac"):
                set_df_value(f"irrfrac{surf_name}", 0, surface.irrfrac)

            # Thermal layers
            if hasattr(surface, "thermal_layers"):
                # Get the lists from thermal_layers
                dz_list = surface.thermal_layers.dz
                k_list = surface.thermal_layers.k
                cp_list = surface.thermal_layers.cp

                # Set each value in the lists
                for i in range(5):  # We know there are exactly 5 values
                    set_df_value("dz_surf", (surf_idx, i), dz_list[i])
                    set_df_value("k_surf", (surf_idx, i), k_list[i])
                    set_df_value("cp_surf", (surf_idx, i), cp_list[i])

            # Initial states
            init_state = getattr(site.initial_states, surf_name)
            if init_state:
                # Basic state parameters
                set_df_value("state_surf", (surf_idx,), init_state.state)
                set_df_value("soilstore_surf", (surf_idx,), init_state.soilstore)

                # fill in dummy values for variables that are not needed for users
                for i in range(12):
                    set_df_value("hdd_id", (i,), 0)
                set_df_value("dqndt", 0, 1)
                set_df_value("dqnsdt", 0, 10)
                set_df_value("qn_av", 0, 10)
                set_df_value("qn_s_av", 0, 10)
                set_df_value("dt_since_start", 0, 0)
                set_df_value("lenday_id", 0, 0)
                set_df_value("tmax_id", 0, 0)
                set_df_value("tmin_id", 0, 0)
                set_df_value("tstep_prev", 0, 300)
                set_df_value("tair_av", 0, 0)
                set_df_value("snowfallcum", 0, 0)

                # Snow-related parameters
                if init_state.snowfrac is not None:
                    set_df_value("snowfrac", (surf_idx,), init_state.snowfrac)
                if init_state.snowpack is not None:
                    set_df_value("snowpack", (surf_idx,), init_state.snowpack)
                if init_state.snowwater is not None:
                    set_df_value("snowwater", (surf_idx,), init_state.snowwater)
                if init_state.snowdens is not None:
                    set_df_value("snowdens", (surf_idx,), init_state.snowdens)
                if init_state.icefrac is not None:
                    set_df_value("icefrac", (surf_idx,), init_state.icefrac)

                # Vegetation-specific parameters
                if surf_name in ["dectr", "evetr", "grass"]:
                    # albedo
                    if init_state.alb_id is not None:
                        set_df_value(f"alb{surf_name}_id", 0, init_state.alb_id)
                    # LAI
                    if init_state.lai_id is not None:
                        set_df_value(f"lai_id", (surf_idx - 2,), init_state.lai_id)
                    # GDD
                    if init_state.gdd_id is not None:
                        set_df_value(f"gdd_id", (surf_idx - 2,), init_state.gdd_id)
                    # SDD
                    if init_state.sdd_id is not None:
                        set_df_value(f"sdd_id", (surf_idx - 2,), init_state.sdd_id)
                    # water use
                    if init_state.wu is not None:
                        set_df_value(
                            f"wuday_id",
                            ((surf_idx - 2) * 3 + 0,),
                            init_state.wu.wu_total,
                        )
                        set_df_value(
                            f"wuday_id",
                            ((surf_idx - 2) * 3 + 1,),
                            init_state.wu.wu_auto,
                        )
                        set_df_value(
                            f"wuday_id",
                            ((surf_idx - 2) * 3 + 2,),
                            init_state.wu.wu_manual,
                        )
                    # Additional parameters for deciduous trees
                    if surf_name == "dectr":
                        if init_state.decidcap_id is not None:
                            set_df_value("decidcap_id", 0, init_state.decidcap_id)
                        if init_state.porosity_id is not None:
                            set_df_value("porosity_id", 0, init_state.porosity_id)
                # temperature
                for k, var in enumerate(["temperature", "tsfc", "tin"]):
                    if var == "tsfc":
                        set_df_value(f"tsfc_surf", (surf_idx,), init_state.tsfc)
                    elif var == "temperature":
                        for k in range(5):
                            set_df_value(
                                f"temp_surf", (surf_idx, k), getattr(init_state, var)[k]
                            )
                    elif var == "tin":
                        set_df_value(f"tin_surf", (surf_idx,), init_state.tin)
            # Set initial snow albedo
            set_df_value("snowalb", 0, site.initial_states.snowalb)

        # Vertical layers
        if hasattr(props, "vertical_layers"):
            print("vertical_layers here")
            vertical_layers = props.vertical_layers
            set_df_value("nlayer", 0, vertical_layers.nlayer)
            for i in range(vertical_layers.nlayer + 1):
                set_df_value("height", (i,), vertical_layers.height[i])
            for i in range(vertical_layers.nlayer):
                set_df_value("building_scale", (i,), vertical_layers.building_scale[i])
                set_df_value("building_frac", (i,), vertical_layers.building_frac[i])
                set_df_value("veg_scale", (i,), vertical_layers.veg_scale[i])
                set_df_value("veg_frac", (i,), vertical_layers.veg_frac[i])
            for i, layer in enumerate(vertical_layers.roofs):
                set_df_value(
                    f"roof_albedo_dir_mult_fact",
                    (0, i),
                    layer.roof_albedo_dir_mult_fact,
                )
                set_df_value(f"alb_roof", (i,), layer.alb)
                set_df_value(f"emis_roof", (i,), layer.emis)
                set_df_value(f"statelimit_roof", (i,), layer.statelimit)
                set_df_value(f"soilstorecap_roof", (i,), layer.soilstorecap)
                set_df_value(f"wetthresh_roof", (i,), layer.wetthresh)
                thermal_layers = layer.thermal_layers
                for j, var in enumerate(["dz", "k", "cp"]):
                    for k in range(5):
                        set_df_value(
                            f"{var}_roof", (i, k), getattr(thermal_layers, var)[k]
                        )
            for i, layer in enumerate(vertical_layers.walls):
                set_df_value(f"wall_specular_frac", (0, i), layer.wall_specular_frac)
                set_df_value(f"alb_wall", (i,), layer.alb)
                set_df_value(f"emis_wall", (i,), layer.emis)
                set_df_value(f"statelimit_wall", (i,), layer.statelimit)
                set_df_value(f"soilstorecap_wall", (i,), layer.soilstorecap)
                set_df_value(f"wetthresh_wall", (i,), layer.wetthresh)
                thermal_layers = layer.thermal_layers
                for j, var in enumerate(["dz", "k", "cp"]):
                    for k in range(5):
                        set_df_value(
                            f"{var}_wall", (i, k), getattr(thermal_layers, var)[k]
                        )
        for building_facet in ["roofs", "walls"]:
            facet = building_facet[:-1]
            if hasattr(site.initial_states, building_facet):
                for j, layer in enumerate(getattr(site.initial_states, building_facet)):
                    set_df_value(f"state_{facet}", (j,), layer.state)
                    set_df_value(f"soilstore_{facet}", (j,), layer.soilstore)
                    # set_df_value(f"snowwater_{facet}", (j,), layer.snowwater)
                    # set_df_value(f"snowdens_{facet}", (j,), layer.snowdens)
                    # set_df_value(f"snowfrac_{facet}", (j,), layer.snowfrac)
                    # set_df_value(f"snowpack_{facet}", (j,), layer.snowpack)
                    for k, var in enumerate(["temperature", "tsfc", "tin"]):
                        if var == "tsfc":
                            set_df_value(f"tsfc_{facet}", (j,), layer.tsfc)
                        elif var == "temperature":
                            for k in range(5):
                                set_df_value(
                                    f"temp_{facet}", (j, k), getattr(layer, var)[k]
                                )
                        elif var == "tin":
                            set_df_value(f"tin_{facet}", (j,), layer.tin)
        return df

    @classmethod
    def from_df_state(cls, df: pd.DataFrame) -> "SUEWSConfig":
        """Create config from DataFrame state"""
        # TODO: add from_df_state
        pass


if __name__ == "__main__":
    # Create list for collecting all exceptions
    exceptions = []

    # test the sample config
    # Load YAML config
    with open("./config-suews.yml", "r") as file:
        yaml_config = yaml.safe_load(file)

    # Create SUEWSConfig object
    suews_config = SUEWSConfig(**yaml_config[0])

    if exceptions:
        raise ExceptionGroup("Validation errors occurred", exceptions)

    print(r"testing suews_config done!")

    # pdb.set_trace()

    # Convert to DataFrame
    df_state_test = suews_config.to_df_state()
    df_state_test.to_pickle("./df_state_test.pkl")
    print("testing df_state done!")

    # checking if all properties are properly converted
    # Get the column differences
    df_state = pd.read_pickle("./df_state.pkl")
    df_state_cols = set(df_state.columns)
    df_test_cols = set(df_state_test.columns)

    print("Columns only in df_state:")
    print(sorted(df_state_cols - df_test_cols))

    print("\nColumns only in df_state_test:")
    print(sorted(df_test_cols - df_state_cols))

    print("\nTotal columns in df_state:", len(df_state_cols))
    print("Total columns in df_state_test:", len(df_test_cols))

    # Get columns with any NA values
    na_cols = df_state_test.columns[df_state_test.isna().any()].tolist()

    # Sort and print the column names
    print(f"{len(na_cols)} Columns containing NA values:")
    for col in sorted(na_cols):
        print(col)

    # test running supy
    import supy as sp

    df_state, df_forcing = sp.load_SampleData()
    df_state_test = pd.read_pickle("./df_state_test.pkl")
    sp.run_supy(df_forcing.iloc[0 : 288 * 10], df_state_test)


# # Convert back to config
# suews_config_back = SUEWSConfig.from_df_state(df_state)
# print("testing from_df_state done!")
