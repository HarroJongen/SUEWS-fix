#!/usr/bin/env python3

import sys
from pathlib import Path
from shutil import copyfile, copytree, make_archive, move, rmtree

import f90nml

# locate base path
path_base = Path('.').resolve()

# locate exe
path_bin = path_base / 'bin'
if not path_bin.exists():
    print(f'{path_bin} not existing! Packing stopped!')
    sys.exit()

# load version
path_sys = list(path_bin.glob('*'))[0]
# system: macOS, Windows, or Linux
name_sys = path_sys.stem
# SUEWS release:
path_exe = list(path_sys.glob('SUEWS*'))[0]
name_exe = path_exe.stem
name_ver = name_exe.split('_V')[-1]

# create path for archive
path_archive = path_base / ('_'.join(['SUEWS', name_ver, name_sys]))
print(f'creating {path_archive}.zip')

# copy input tables
path_input_tables = path_base / 'InputTables' / name_ver
if path_input_tables.exists():
    if path_archive.exists():
        rmtree(path_archive)
    copytree(path_input_tables, path_archive)
else:
    print(f'{path_input_tables} not existing! Packing stopped!')
    sys.exit()


# load path info for input and output
dict_runcontrol = f90nml.read(path_archive / 'RunControl.nml')['runcontrol']

# make input dir
path_input = dict_runcontrol['fileinputpath']
path_input = path_archive / path_input
if not path_input.exists():
    path_input.mkdir()

# move input files
list_input_files = [
    file for file in path_archive.glob('*.*')
    if 'RunControl' not in str(file)]
for file in list_input_files:
    move(str(file), str(path_input))

# make output dir
path_output = dict_runcontrol['fileoutputpath']
path_output = path_archive / path_output
if not path_output.exists():
    path_output.mkdir()

# # remove test run files
# # SUEWS binary or symlink
# Path(path_archive / path_exe.name).unlink()
# # runtime warning or error files
# for x in path_archive.glob('*.txt'):
#     x.unlink()
# # hidden files
# for x in path_archive.glob('.*'):
#     x.unlink()

# copy SUEWS exe
path_exe_target = copyfile(path_exe, path_archive / path_exe.name)
path_exe_target.chmod(0o775)


# archive folder as zip
make_archive(path_archive, 'zip', path_archive)

# clean workspace
rmtree(path_archive)
