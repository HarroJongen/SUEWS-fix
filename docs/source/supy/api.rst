.. _api_ref:



API reference
=============


Top-level Functions
-------------------
.. currentmodule:: supy

.. autosummary::
    :toctree: api/supy

    init_supy
    load_forcing_grid
    run_supy
    save_supy
    load_SampleData
    show_version


Utility Functions
-------------------
.. currentmodule:: supy.util

ERA-5 Data Downloader
~~~~~~~~~~~~~~~~~~~~~
.. autosummary::
    :toctree: api/supy.util

    download_era5
    gen_forcing_era5

Typical Meteorological Year
~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. autosummary::
    :toctree: api/supy.util

    gen_epw
    read_epw

Gap Filling
~~~~~~~~~~~

.. autosummary::
    :toctree: api/supy.util

    fill_gap_all

OHM
~~~~~~~~~~~

.. autosummary::
    :toctree: api/supy.util

    derive_ohm_coef
    sim_ohm

Surface Conductance
~~~~~~~~~~~~~~~~~~~

.. autosummary::
    :toctree: api/supy.util

    cal_gs_suews
    cal_gs_obs
    calib_g

WRF-SUEWS
~~~~~~~~~

.. autosummary::
    :toctree: api/supy.util

    extract_reclassification
    plot_reclassification

Plotting
~~~~~~~~

.. autosummary::
    :toctree: api/supy.util

    plot_comp
    plot_day_clm
    plot_rsl

Roughness Calculation
~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
    :toctree: api/supy.util

    cal_z0zd
    cal_neutral


Command-Line Tools
-------------------
.. toctree::
  :maxdepth: 1

  api/supy.cmd/suews-run
  api/supy.cmd/suews-convert



Key Data Structures
-------------------

.. toctree::
  :maxdepth: 1

  data-structure/df_state
  data-structure/df_forcing
  data-structure/df_output








