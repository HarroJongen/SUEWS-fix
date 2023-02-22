.. _index_page:

SuPy: SUEWS that speaks Python
------------------------------

.. image:: https://img.shields.io/pypi/pyversions/supy.svg
    :target: https://pypi.org/project/supy
    :alt: Python Version Support Status

.. image:: https://img.shields.io/pypi/v/supy.svg
    :target: https://pypi.org/project/supy
    :alt: Latest Version Status

.. image:: https://pepy.tech/badge/supy
    :target: https://pepy.tech/project/supy
    :alt: Downloads

.. image:: https://mybinder.org/badge_logo.svg
    :target: https://mybinder.org/v2/gh/UMEP-dev/SuPy/main
    :alt: Binder Status

.. image:: https://readthedocs.org/projects/supy/badge/?version=latest
    :target: https://supy.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.2574404.svg
   :target: https://doi.org/10.5281/zenodo.2574404
   :alt: DOI



- **What is SuPy?**

    SuPy is a Python-enhanced urban climate model
    with `SUEWS <https://suews-docs.readthedocs.io/en/latest/>`_ as its computation core.

    The scientific rigour in SuPy results is thus gurranteed by SUEWS
    (see :ref:`SUEWS publications <Recent_publications>` and
    :ref:`Parameterisations and sub-models within SUEWS`).

    Meanwhile, the data analysis ability of SuPy is greatly enhanced
    by `the Python-based SciPy Stack <https://scipy.org>`_,
    notably `numpy <https://www.numpy.org>`_ and
    `pandas <http://pandas.pydata.org/>`_.
    More details are described in `our SuPy paper <https://doi.org/10.5194/gmd-12-2781-2019>`_.



- **How to get SuPy?**

  SuPy is available on all major platforms (macOS, Windows, Linux) for Python 3.7+ (64-bit only)
  via `PyPI <https://pypi.org/project/supy/>`_:

  .. code-block:: shell

    python3 -m pip install supy --upgrade

- **How to use SuPy?**

    * Please follow :ref:`Quickstart of SuPy` and :ref:`other tutorials <tutorial_index>`.

    * Please see `api` for details.

    * Please see `faq` if any issue.

- **How to contribute to SuPy?**

    * Add your development via `Pull Request <https://github.com/UMEP-dev/SuPy/compare>`_
    * Report issues via the `GitHub page <https://github.com/UMEP-dev/SuPy/issues/new?template=issue-report.md>`_.
    * Cite `our SuPy paper <https://doi.org/10.5194/gmd-12-2781-2019>`_.
    * Provide `suggestions and feedback <https://github.com/UMEP-dev/UMEP/discussions/>`_.

.. toctree::
  :hidden:
  :maxdepth: 2

  tutorial/tutorial
  data-structure/supy-io
  api
  faq
  version-history

