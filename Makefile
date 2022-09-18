# -*- makefile -*-
.PHONY: main clean test pip supy docs

# OS-specific configurations
ifeq ($(OS),Windows_NT)
	PYTHON_exe = python.exe

else
	UNAME_S := $(shell uname -s)


	ifeq ($(UNAME_S),Linux) # Linux
		PYTHON_exe=python

	endif

	ifeq ($(UNAME_S),Darwin) # macOS
		PYTHON_exe=python

	endif

endif

src_dir = src
docs_dir = docs


PYTHON := $(if $(PYTHON_exe),$(PYTHON_exe),python)
# All the files which include modules used by other modules (these therefore
# need to be compiled first)

MODULE = supy

# default make options
main: test
	$(MAKE) -C $(src_dir) main
	$(MAKE) -C $(docs_dir) html

# build wheel
wheel:
	python -m build src --wheel --outdir wheelhouse -n

# house cleaning
clean:
	$(MAKE) -C $(src_dir) clean
	$(MAKE) -C $(docs_dir) clean

# make supy and run test cases
test:
	$(MAKE) -C $(src_dir) test

# make docs and open index
docs:
	$(MAKE) -C $(docs_dir) html
	open $(docs_dir)/build/html/index.html

# upload wheels to pypi using twine
upload:
	$(MAKE) -C $(src_dir) upload

# make live docs for testing
livehtml:
	$(MAKE) -C $(docs_dir) livehtml

# use cibuildwheel to build wheels for all platforms
cibuid:
	pipx run cibuildwheel==2.9.0 --platform macos