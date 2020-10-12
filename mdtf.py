#!/usr/bin/env python3
"""Top-level script for running all MDTF diagnostics functions.
"""

import sys
# do version check before importing other stuff
if sys.version_info[0] < 3 or sys.version_info[1] < 7:
    sys.exit((
        "ERROR: MDTF currently only supports python >= 3.7. Please check "
        "which version is on your $PATH (e.g. with `which python`.)"
        f"Attempted to run with following python version:\n{sys.version}"
    ))
# passed; continue with imports
import os
import argparse
import logging
import glob
import importlib
import warnings
from framework import cli
from framework.util import logs
from framework.util.file_io import read_json


class MDTFSubcommandDispatch(object):
    """Class for constructing the command-line interface, parsing the options,
    and handing off execution to the selected subcommand.
    """
    def __init__(self, code_root):
        self.code_root = code_root
        self.fmwk_dir = os.path.join(code_root, 'framework')
        self.sites_dir = os.path.join(code_root, 'sites')
        self.installed = False
        self.site = None
        self.sites = []
        self.default_site = "local"
        self.sub_cmds = dict()
        self.p = None

    def read_config_file(self, config_type, site=""):
        """Load a configuration file. Check in the site-specific installation
        directory if specified; if that fails, search for defaults listed in the
        framework directory.
        """
        # search site directory
        site_dir = os.path.join(self.sites_dir, site)
        paths = glob.glob(
            os.path.join(site_dir, '**', config_type+'_cli.jsonc'),
            recursive=True
        )
        if len(paths) == 1 and os.path.isfile(paths[0]):
            return read_json(paths[0])
        # warnings.warn((
        #     f"Site-specific {config_type} config not found in {} %s; using defaults.",
        #     config_type, paths
        # )
        # fallback: search framework directory for "_cli.jsonc" or "_template.jsonc"
        paths = glob.glob(
            os.path.join(self.fmwk_dir, '**', config_type+'_template.jsonc'),
            recursive=True
        ) + glob.glob(
            os.path.join(self.fmwk_dir, '**', config_type+'_cli.jsonc'),
            recursive=True
        )
        if len(paths) == 1 and os.path.isfile(paths[0]):
            return read_json(paths[0])
        sys.exit((
            f"Error: Couldn't find {config_type}.jsonc configuration file in"
            f" {site_dir} or defaults in {self.fmwk_dir}."
        ))

    def get_subcommands(self):
        """Subcommands are configured through an external file (this is done 
        mainly done to let the installer configure a default ``--site`` argument.) 
        This method finds and reads that file.
        """
        d = self.read_config_file("subcommands", site="")
        if "default_site" in d and "{{" not in d["default_site"]:
            self.default_site = d["default_site"]
            self.installed = True
        self.sub_cmds = d.get("subcommands", dict())

    def get_site(self):
        """We allow site-specific installations to customize the CLI, so before 
        we construct the CLI parser we need to determine what site to use. We do
        this by running a parser that only looks for the ``--site`` flag.
        """
        self.sites = [d for d in os.listdir(self.sites_dir) \
            if os.path.isdir(d) and not d.startswith('.')]
        if 'local' in self.sites:
            self.installed = True

        site_p = argparse.ArgumentParser(add_help=False)
        site_p.add_argument('--site', '-s', default=self.default_site)
        self.site = getattr(site_p.parse_known_args()[0], 'site', self.default_site)
        if not os.path.isdir(os.path.join(self.sites_dir, self.site)) \
            and not (self.site == 'local' and not self.installed):
            sys.exit(
                f"Error: requested site {self.site} not found in directory {self.sites_dir}."
            )

    def make_subcommand_parser(self):
        """Method that assembles the top-level CLI parser. Options specific to 
        the script are hard-coded here; CLI options for each subcommand are 
        given in jsonc configuration files for each command which are read in 
        here. See associated documentation for :class:`~framework.cli.MDTFArgParser`
        for information on the configuration file mechanism.
        """
        self.p = cli.MDTFArgParser(
            prog="mdtf",
            usage="%(prog)s [flags] <command> [command-specific options]",
            description=cli.dedent("""
                Driver script for the NOAA Model Diagnostics Task Force (MDTF)
                package, which runs process-oriented diagnostics (PODs) on
                climate model data. See documentation at
                https://mdtf-diagnostics.rtfd.io.
                """)
        )
        self.p.add_argument(
            '--version', action="version", version="%(prog)s 3.0 beta 3"
        )
        self.p.add_argument(
            '--site', '-s', 
            metavar="<site>",
            default=self.default_site,
            choices=self.sites,
            help=cli.dedent("""
                Site-specific functionality to use. 
            """)
        )
        self.p._optionals.title = 'GENERAL OPTIONS'
        if not self.installed:
            self.p.epilog=cli.dedent("""
                Warning: User-customized configuration files not found. Consider
                running 'mdtf install' to configure your installation.
            """)
        sub_ps = self.p.add_subparsers(
            title='COMMANDS', 
            description=cli.dedent("""
                Subcommand functionality. Use '%(prog)s <command> --help' to get
                help on options specific to each command.
            """),
            help=None, metavar="<command> is one of:",
            required=True, dest='subcommand',
            parser_class=cli.MDTFArgParser
        )
        _ = sub_ps.add_parser("help", help="Show this help message and exit.")

        for sub_cmd in self.sub_cmds:
            d = self.sub_cmds[sub_cmd]
            d["parser"] = sub_ps.add_parser(sub_cmd, help=d.get("help", ""))
            # read the command's CLI config file, if it exists. 
            cli_config = self.read_config_file(d['cli_file'], site=self.site)
            d["parser"].configure(cli_config)

    def logging_init(self):
        """If we're running the framework on data ('mdtf run'), initialize the
        logging interface (which would be overkill for other subcommands). 
        Loggers are configured from a file which may be customized for each site; 
        see documentation for :module:`~framework.util.logs`.
        """
        logging.captureWarnings(True)
        _log = logging.getLogger()
        _log.setLevel(logging.NOTSET)
        # MultiFlushMemoryHandler not strictly necessary any more, since we set 
        # up real loggers immediately afterward now
        temp_log_cache = logs.MultiFlushMemoryHandler(1024*16, flushOnClose=False)
        _log.addHandler(temp_log_cache)

        # now configure the real loggers from a file
        log_config = self.read_config_file("logging", site=self.site)
        logs.mdtf_log_config(log_config, temp_log_cache, _log)

    def main(self):
        """Main method of this class. Constructs CLI parser from config files
        for subcommands, parses it and calls subcommand with its arguments.
        """
        # set up CLI parser
        self.get_subcommands()
        self.get_site()
        self.make_subcommand_parser()

        # parse the arguments.
        parsed_args = self.p.parse_args()
        if parsed_args.subcommand == 'help':
            self.p.print_help()
            exit(0)
        d = self.sub_cmds[parsed_args.subcommand]
        mod_ = importlib.import_module(d['module'])
        func_ = getattr(mod_, d['entry_point'])
        if parsed_args.subcommand == 'run':
            self.logging_init()
        # parsed_args attribute of MDTFArgParser contains parsed values
        func_(code_root, self.p)

if __name__ == '__main__':
    # get dir containing this script:
    code_root = os.path.dirname(os.path.realpath(__file__)) 
    dispatch = MDTFSubcommandDispatch(code_root)
    dispatch.main()

    # Call logging cleanup, in case we started it for "mdtf run". Believe this 
    # is registered with atexit in 3.7, so no need to handle situations where we
    # exit the script abnormally.
    logging.shutdown()
