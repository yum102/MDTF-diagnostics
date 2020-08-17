#!/usr/bin/env python

import sys
# do version check before importing other stuff
if sys.version_info[0] < 3 or sys.version_info[1] < 7:
    print(("ERROR: MDTF currently only supports python >= 3.7. Please check "
    "which version is on your $PATH (e.g. with `which python`.)"))
    print("Attempted to run with following python version:\n{}".format(sys.version))
    exit()
# passed; continue with imports
import os.path

from framework.framework import MDTFFramework

# get dir containing this script:
code_root = os.path.dirname(os.path.realpath(__file__)) 
fmwk_dir = os.path.join(code_root, 'framework')
cli_config_path = os.path.join(fmwk_dir, 'cli.jsonc')
if not os.path.exists(cli_config_path):
    # print('Warning: site-specific cli.jsonc not found, using template.')
    cli_config_path = os.path.join(fmwk_dir, 'cli_template.jsonc')
mdtf = MDTFFramework(code_root, cli_config_path)
mdtf.main_loop()
