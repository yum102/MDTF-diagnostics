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
import json
import logging
import logging.config
import logging.handlers

class MultiFlushMemoryHandler(logging.handlers.MemoryHandler):
    """Extend flush() method of logging.handlers.MemoryHandler to flush contents
    of log buffer to multiple targets. We do this to solve the chicken-and-egg
    problem of logging any events that happen before the log outputs are 
    configured: those events are captured by an instance of this handler and 
    then transfer()'ed to other handlers once they're set up.
    See `https://stackoverflow.com/a/12896092`__.
    """
    def transfer(self, target_handler):
        """Transfer contents of buffer to target_handler."""
        self.acquire()
        try:
            self.setTarget(target_handler)
            if self.target:
                for record in self.buffer:
                    self.target.handle(record)
                # self.buffer = [] # don't clear buffer!
        finally:
            self.release()

    def transfer_to_all(self, logger):
        """Transfer contents of buffer to all handlers attached to logger."""
        no_transfer_flag = True
        for handler in logger.handlers:
            if handler is not self:
                self.transfer(handler)
                no_transfer_flag = False
        if no_transfer_flag:
            logger.warning("No loggers configured.")
            self.transfer(logging.lastResort)

# get root logger and set up temporary log cache for catching pre-config errors
logging.captureWarnings(True)
_log = logging.getLogger()
_log.setLevel(logging.DEBUG)
temp_log_cache = MultiFlushMemoryHandler(1024*32, flushOnClose=False)
_log.addHandler(temp_log_cache)

# get dir containing this script:
code_root = os.path.dirname(os.path.realpath(__file__)) 
fmwk_dir = os.path.join(code_root, 'framework')

# now configure the real loggers from a file
try:
    with open(os.path.join(fmwk_dir, 'log_config.json')) as file_:
        log_config = json.load(file_)
    logging.config.dictConfig(log_config)
except Exception as exc:
    _log.exception("Logging config failed.")

# transfer cache contents to real loggers
temp_log_cache.transfer_to_all(_log)
temp_log_cache.close()
_log.removeHandler(temp_log_cache)

from framework.cli import FrameworkCLIHandler, InfoCLIHandler
from framework.framework import MDTFFramework

# find CLI configuration file
cli_config_path = os.path.join(fmwk_dir, 'cli.jsonc')
if not os.path.exists(cli_config_path):
    # print('Warning: site-specific cli.jsonc not found, using template.')
    cli_config_path = os.path.join(fmwk_dir, 'cli_template.jsonc')

# poor man's subparser: just dispatch on first argument
if len(sys.argv) == 1 or \
    len(sys.argv) == 2 and sys.argv[1].lower().endswith('help'):
    # build CLI, print its help and exit
    cli_obj = FrameworkCLIHandler(code_root, cli_config_path)
    cli_obj.parser.print_help()
    exit()
elif sys.argv[1].lower() == 'info': 
    # "subparser" for command-line info
    InfoCLIHandler(code_root, sys.argv[2:])
else:
    # not printing help or info, setup CLI normally and run framework
    mdtf = MDTFFramework(code_root, cli_config_path)
    mdtf.main_loop()

# believe this is registered with atexit in 3.7, so no need to handle abnormal
# exit
logging.shutdown()
