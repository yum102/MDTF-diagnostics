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
import logging
from framework.util import logs

def _find_config_file(site_dir, fmwk_dir, config_type):
    """Check for a site-specific configuration file. If that's not found, look
    for the framework's defaults.
    """
    path = os.path.join(site_dir, config_type+'.jsonc')
    if os.path.exists(path):
        return path
    _log.warning(
        "Site-specific '%s' config not found at %s; using defaults.",
        config_type, path
    )
    path = os.path.join(fmwk_dir, config_type+'_template.jsonc')
    if os.path.exists(path):
        return path
    _log.error(
        "Default '%s' config not found at %s.",
        config_type, path
    )
    exit()

# get root logger and set up temporary log cache for catching pre-config errors
logging.captureWarnings(True)
_log = logging.getLogger()
_log.setLevel(logging.NOTSET)
temp_log_cache = logs.MultiFlushMemoryHandler(1024*16, flushOnClose=False)
_log.addHandler(temp_log_cache)

# get dir containing this script:
code_root = os.path.dirname(os.path.realpath(__file__)) 
fmwk_dir = os.path.join(code_root, 'framework')
site_dir = fmwk_dir # temporarily

# now configure the real loggers from a file
config_path = _find_config_file(site_dir, fmwk_dir, 'logging')
logs.mdtf_log_config(config_path, temp_log_cache, _log)

from framework.cli import FrameworkCLIHandler, InfoCLIHandler
from framework.framework import MDTFFramework

config_path = _find_config_file(site_dir, fmwk_dir, 'cli')

# poor man's subparser: just dispatch on first argument
if len(sys.argv) == 1 or \
    len(sys.argv) == 2 and sys.argv[1].lower().endswith('help'):
    # build CLI, print its help and exit
    cli_obj = FrameworkCLIHandler(code_root, config_path)
    cli_obj.parser.print_help()
    exit()
elif sys.argv[1].lower() == 'info': 
    # "subparser" for command-line info
    InfoCLIHandler(code_root, sys.argv[2:])
else:
    # not printing help or info, setup CLI normally and run framework
    mdtf = MDTFFramework(code_root, config_path)
    mdtf.main_loop()

# believe this is registered with atexit in 3.7, so no need to handle abnormal
# exit
logging.shutdown()
