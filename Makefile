# SUEWS Makefile - read the README file before editing

.PHONY: main clean test pip supy docs

# OS-specific configurations
ifeq ($(OS),Windows_NT)
	PYTHON_exe = python.exe
	# F2PY_PY= /c/Users/sunt05/Anaconda2/Scripts/f2py.py
	# F2PY_EXE = $(PYTHON) $(F2PY_PY)
	TARGET=$(MODULE).pyd
else
	UNAME_S := $(shell uname -s)
	TARGET=$(MODULE).so

	ifeq ($(UNAME_S),Linux) # Linux
		PYTHON_exe=python
		# F2PY_EXE = f2py
	endif

	ifeq ($(UNAME_S),Darwin) # macOS
		PYTHON_exe=python
		# F2PY_EXE = f2py
	endif

endif

MODULE=SUEWS_driver

SUEWS_dir = SUEWS-SourceCode

docs_dir = docs

test_dir= test

release_dir = Release

makefile = Makefile.gfortran

SuPy_dir = supy-driver

PYTHON := $(if $(PYTHON_exe),$(PYTHON_exe),python)

all: driver

# make fortran exe
suews:
	$(MAKE) -C $(SUEWS_dir) suews; # make SUEWS with the `main` recipe
	# -rm -rf *.o *.mod *.f95 *.a *.dSYM

# make fortran exe and run test cases
test:
	$(MAKE) -C $(test_dir) test

# make fortran exe and pack release archive
release: pip
	$(MAKE) -C $(release_dir) clean; # clean release directory
	$(MAKE) suews # build SUEWS binary
	$(MAKE) -C $(release_dir) pack # pack binary and input files

# make supy dist
driver: suews
	$(MAKE) -C $(SuPy_dir) test; # make and test supy_driver

pip:
	pip install pipreqs
	pipreqs $(test_dir) --savepath requirements.txt
	pip install -r requirements.txt
	rm -rf requirements.txt

# documentation
docs:
	$(MAKE) -B -C $(docs_dir) html

# live html documentation
livehtml:
	$(MAKE) -B -C $(docs_dir) livehtml

# If wanted, clean all *.o files after build
clean:
	$(MAKE) -C $(SUEWS_dir) clean
	$(MAKE) -C $(SuPy_dir) clean
	$(MAKE) -C $(release_dir) clean
	$(MAKE) -C $(docs_dir) clean
