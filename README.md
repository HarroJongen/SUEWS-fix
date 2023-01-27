# SUEWS


This is a public repo for SUEWS source code and documentation.

---

- [SUEWS](#suews)
  - [Documentation](#documentation)
  - [Developer Note](#developer-note)
    - [Branch](#branch)
      - [Central curated branches](#central-curated-branches)
    - [Manual](#manual)
    - [Test](#test)
      - [Tests and purposes](#tests-and-purposes)
      - [Workflow](#workflow)
      - [Preparation of tests](#preparation-of-tests)
    - [Debugging with GDB](#debugging-with-gdb)
      - [GDB on macOS](#gdb-on-macos)
      - [debugging with GDB](#debugging-with-gdb-1)
    - [Questions](#questions)


## Documentation

* Documentation site: <https://suews-docs.readthedocs.io/>

* Documentation source: `docs` folder in this repo

## Developer Note

### Branch

#### Central curated branches
These branches are regularly curated by admin members with specific purposes and set with triggers for automatic deployment (via MS Azure Pipeline) in the [*releases* page](https://github.com/Urban-Meteorology-Reading/SUEWS/releases) named **Latest Release Test**:

* `master`:
  * the main branch that keeps milestone and stable features.
  * `push` is restricted to admin members.
* `develop`:
  * used for core developments.
  * `push` is restricted to admin members.


### Manual

* Please keep the development changes documented in the [Documentation repo](https://github.com/Urban-Meteorology-Reading/SUEWS-Docs).
* The SUEWS docs are mainly written in [RST](http://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html) but [Markdown](https://guides.github.com/features/mastering-markdown/) is also acceptable.
* Your changes to docs will be reviewed and merged into public release if appropriate.

### Test

Whenever changes are made, please run `make test` in the repo root to check if your changes are working or not.
If any error, please resolve it or justify that the test is giving false alarm.

#### Tests and purposes
`make test` will perform the following checks:

- if single-grid-multi-year run could be successful: to check if multi-year run is functional;
- if multi-grid-multi-year run could be successful: to check if multi-grid run is functional;
- if test run results could match those from the standard run (runs under `BaseRun`): to check if any non-functional changes would break the current code;
- if all physics schemes are working: to check possible invalid physics schemes.

#### Workflow
The test workflow is as follows (details refer to the Makefile `test` recipe and related python code):

1. clean existing build and rebuild the code;
2. create a temporary directory as working directory to perform checks;
3. copy the rebuilt `SUEWS_{version}` binary to the temporary folder;
4. copy the version specific input files under `Release/InputTables/{version}` to the temporary folder (see below for its preparation);
5. run python code to perform the above checks and write out test results to the console:
   1. if all tests are successful, the code is generally good to go;
   2. if any test failed, we NEED to look into the reasons for the failure and resolve them before any further feature-added operations.

#### Preparation of tests

1. Prepare a base run:
   - under `Test/BaseRun`, create a folder named with version/feature info (e.g., `2019a`);
   - perform a simulation to produce example output files, which will later be used as standard run to verify the correct code functionalities.

   *Note: all the above input files will be automatically copied under `Release/InputTables` with explicit version/feature (e.g., `Release/InputTables/2019a`) and later archived in public releases for users; so carefully construct test data to include in the input files.*
2. Configure test namelist file `Test/code/BTS_config.nml`:

   - `name_exe`: the SUEWS binary name that will be used for testing.
   - `dir_exe`: the directory to copy `name_exe`.
   - `dir_input`: the directory to copy input files; suggested to be `Release/InputTables/{version}`.
   - `dir_baserun`: the base run against which to test identity in results.

### Debugging with GDB

GDB is a generic debugging tool used along with gfortran.
Here are some tips to debug SUEWS code:

#### GDB on macOS

Recent macOS (since High Sierra) introduces extra security procedures for system level operations that makes installation GDB more tedious than before.
The best practice, in TS's option, to avoid hacking your macOS, is to use Linux docker images with gfortran&gdb installations: e.g., [alpine-gfortran](https://github.com/cmplopes/alpine-gfortran).

Once the docker image is installed, simply run this from the SUEWS root folder for debugging:

```bash
 docker run --rm -it -v $(pwd):/source cmplopes/alpine-gfortran /bin/bash

```
 which will mount the current `SUEWS` directory to docker's path `/source` and enter the interactive mode for debugging.


#### debugging with GDB

1. enable the debugging related flags in `Makefile` under `SUEWS-SourceCode` by removing the `#` after the equal sign `=`:

```makefile
FCNOOPT = -O0
FFLAGS = -O3 $(STATIC) $(FCDEBUG) -Wall -Wtabs -fbounds-check -cpp \
					-Wno-unused-dummy-argument -Wno-unused-variable
```

2. fully clean and recompile `SUEWS`:
```
make clean; make
```

3. copy the recompiled `SUEWS` binary into your SUEWS testing folder (e.g., `Test/BaseRun/2019a`) and load it into GDB:

```
gdb SUEWS

run

```
then you should have stack info printed out by GDB if any runtime error occurs.

More detailed GDB tutorial can be found [here](https://github.com/jackrosenthal/gdb-tutorial/blob/master/notes.pdf).



### Questions

* Please [raise issues](https://github.com/Urban-Meteorology-Reading/SUEWS/issues/new) for questions in the development so our progress can be well managed.
