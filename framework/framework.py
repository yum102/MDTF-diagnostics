import os
import sys
import signal
import shutil
import logging
from framework import util
from framework import (
    cli, configs, data_manager, environment_manager, diagnostic, netcdf_helper
)

_log = logging.getLogger(__name__)

class MDTFFramework(object):
    def __init__(self, code_root, defaults_rel_path):
        """Initial dispatch of CLI args: are we printing help info or running
        framework. 
        """
        self.code_root = code_root
        # delete temp files if we're killed
        signal.signal(signal.SIGTERM, self.cleanup_tempdirs)
        signal.signal(signal.SIGINT, self.cleanup_tempdirs)

        # set up CLI and parse arguments
        # print('\tDEBUG: argv = {}'.format(sys.argv[1:]))
        cli_obj = cli.FrameworkCLIHandler(code_root, defaults_rel_path)
        self._cli_pre_parse_hook(cli_obj)
        cli_obj.parse_cli()
        self._cli_post_parse_hook(cli_obj)
        # load pod data
        pod_info_tuple = cli.load_pod_settings(code_root)
        # do nontrivial parsing
        config = configs.ConfigManager(cli_obj, pod_info_tuple)
        print(util.pretty_print_json(config.paths))
        self.parse_mdtf_args(cli_obj, config)
        # config should be read-only from here on
        self._post_parse_hook(cli_obj, config)
        self._print_config(cli_obj, config)

    def cleanup_tempdirs(self, signum=None, frame=None):
        # delete temp files
        util.signal_logger(self.__class__.__name__, signum, frame)
        config = configs.ConfigManager()
        tmpdirs = configs.TempDirManager()
        if not config.config.get('keep_temp', False):
            tmpdirs.cleanup()

    def _cli_pre_parse_hook(self, cli_obj):
        # gives subclasses the ability to customize CLI handler before parsing
        # although most of the work done by parse_mdtf_args
        pass

    def _cli_post_parse_hook(self, cli_obj):
        # gives subclasses the ability to customize CLI handler after parsing
        # although most of the work done by parse_mdtf_args
        if cli_obj.config.get('dry_run', False):
            cli_obj.config['test_mode'] = True

    @staticmethod
    def _populate_from_cli(cli_obj, group_nm, target_d=None):
        if target_d is None:
            target_d = dict()
        for key, val in cli_obj.iteritems_cli(group_nm):
            if val: # assign nonempty items only
                target_d[key] = val
        return target_d

    def parse_mdtf_args(self, cli_obj, config):
        """Parse script options returned by the CLI. For greater customizability,
        most of the functionality is spun out into sub-methods.
        """
        self.parse_env_vars(cli_obj, config)
        self.parse_pod_list(cli_obj, config)
        self.parse_case_list(cli_obj, config)
        self.parse_paths(cli_obj, config)

    def parse_env_vars(self, cli_obj, config):
        # don't think PODs use global env vars?
        # self.envvars = self._populate_from_cli(cli_obj, 'PATHS', self.envvars)
        config.global_envvars['RGB'] = os.path.join(self.code_root,'shared','rgb')
        # globally enforce non-interactive matplotlib backend
        # see https://matplotlib.org/3.2.2/tutorials/introductory/usage.html#what-is-a-backend
        config.global_envvars['MPLBACKEND'] = "Agg"

    def parse_pod_list(self, cli_obj, config):
        self.pod_list = []
        args = util.coerce_to_iter(config.config.pop('pods', []), set)
        if 'example' in args or 'examples' in args:
            self.pod_list = [pod for pod in config.pods \
                if pod.startswith('example')]
        elif 'all' in args:
            self.pod_list = [pod for pod in config.pods \
                if not pod.startswith('example')]
        else:
            # specify pods by realm
            realms = args.intersection(set(config.all_realms))
            args = args.difference(set(config.all_realms)) # remainder
            for key in config.pod_realms:
                if util.coerce_to_iter(key, set).issubset(realms):
                    self.pod_list.extend(config.pod_realms[key])
            # specify pods by name
            pods = args.intersection(set(config.pods))
            self.pod_list.extend(list(pods))
            for arg in args.difference(set(config.pods)): # remainder:
                _log.warning("Didn't recognize POD %s, ignoring", arg)
            # exclude examples
            self.pod_list = [pod for pod in self.pod_list \
                if not pod.startswith('example')]
        if not self.pod_list:
            print(("WARNING: no PODs selected to be run. Do `./mdtf info pods`"
            " for a list of available PODs, and check your -p/--pods argument."))
            print('Received --pods = {}'.format(list(args)))
            exit(1)

    def parse_case_list(self, cli_obj, config):
        case_list_in = util.coerce_to_iter(cli_obj.case_list)
        cli_d = self._populate_from_cli(cli_obj, 'MODEL')
        if 'CASE_ROOT_DIR' not in cli_d and cli_obj.config.get('root_dir', None): 
            # CASE_ROOT was set positionally
            cli_d['CASE_ROOT_DIR'] = cli_obj.config['root_dir']
        if not case_list_in:
            case_list_in = [cli_d]
        case_list = []
        for case_tup in enumerate(case_list_in):
            case_list.append(self.parse_case(case_tup, cli_d, cli_obj, config))
        self.case_list = [case for case in case_list if case is not None]
        if not self.case_list:
            print("ERROR: no valid entries in case_list. Please specify model run information.")
            print('Received:')
            print(util.pretty_print_json(case_list_in))
            exit(1)

    def parse_case(self, case_tup, cli_d, cli_obj, config):
        n, d = case_tup
        if 'CASE_ROOT_DIR' not in d and 'root_dir' in d:
            d['CASE_ROOT_DIR'] = d.pop('root_dir')
        case_convention = d.get('convention', '')
        d.update(cli_d)
        if case_convention:
            d['convention'] = case_convention

        if not ('CASENAME' in d or ('model' in d and 'experiment' in d)):
            _log.warning(("Need to specify either CASENAME or model/experiment "
                "in caselist entry %s, skipping."), n+1)
            return None
        _ = d.setdefault('model', d.get('convention', ''))
        _ = d.setdefault('experiment', '')
        _ = d.setdefault('CASENAME', '{}_{}'.format(d['model'], d['experiment']))

        for field in ['FIRSTYR', 'LASTYR', 'convention']:
            if not d.get(field, None):
                _log.warning(("WARNING: No value set for %s in caselist entry %s, "
                    "skipping."), field, n+1)
                return None
        # if pods set from CLI, overwrite pods in case list
        d['pod_list'] = self.set_case_pod_list(d, cli_obj, config)
        return d

    def set_case_pod_list(self, case, cli_obj, config):
        # if pods set from CLI, overwrite pods in case list
        # already finalized self.pod-list by the time we get here
        if not cli_obj.is_default['pods'] or not case.get('pod_list', None):
            return self.pod_list
        else:
            return case['pod_list']

    def parse_paths(self, cli_obj, config):
        config.paths.parse(cli_obj.config, cli_obj.custom_types.get('path', []))

    def _post_parse_hook(self, cli_obj, config):
        # init other services
        _ = configs.TempDirManager()
        _ = configs.VariableTranslator()
        self.verify_paths(config)

    def verify_paths(self, config):
        # clean out WORKING_DIR if we're not keeping temp files
        if os.path.exists(config.paths.WORKING_DIR) and not \
            (config.config.get('keep_temp', False) \
            or config.paths.WORKING_DIR == config.paths.OUTPUT_DIR):
            shutil.rmtree(config.paths.WORKING_DIR)
        util.check_required_dirs(
            already_exist = [
                config.paths.CODE_ROOT, config.paths.OBS_DATA_ROOT
            ], 
            create_if_nec = [
                config.paths.MODEL_DATA_ROOT, 
                config.paths.WORKING_DIR, 
                config.paths.OUTPUT_DIR
        ])

    def _print_config(self, cli_obj, config):
        # make config nested dict for backwards compatibility
        # this is all temporary
        d = dict()
        for n, case in enumerate(self.case_list):
            key = 'case_list({})'.format(n)
            d[key] = case
        d['pod_list'] = self.pod_list
        d['paths'] = config.paths
        d['paths'].pop('_unittest', None)
        d['settings'] = dict()
        settings_gps = set(cli_obj.parser_groups).difference(
            set(['parser','PATHS','MODEL','DIAGNOSTICS'])
        )
        for group in settings_gps:
            d['settings'] = self._populate_from_cli(cli_obj, group, d['settings'])
        d['settings'] = {k:v for k,v in iter(d['settings'].items()) \
            if k not in d['paths']}
        d['envvars'] = config.global_envvars
        print('DEBUG: SETTINGS:')
        print(util.pretty_print_json(d))

    _dispatch_search = [
        data_manager, environment_manager, diagnostic, netcdf_helper
    ]
    def manual_dispatch(self, config):
        def _dispatch(setting, class_suffix):
            class_prefix = config.config.get(setting, '')
            class_prefix = util.coerce_from_iter(class_prefix)
            # drop '_' and title-case class name
            class_prefix = ''.join(class_prefix.split('_')).title()
            for mod in self._dispatch_search:
                try:
                    return getattr(mod, class_prefix+class_suffix)
                except:
                    continue
            _log.error("No class named %s.", class_prefix+class_suffix)
            raise Exception('no_class')

        self.DataManager = _dispatch('data_manager', 'DataManager')
        self.EnvironmentManager = _dispatch('environment_manager', 'EnvironmentManager')
        self.Diagnostic = _dispatch('diagnostic', 'Diagnostic')
        self.NetCDFHelper = _dispatch('netcdf_helper', 'NetcdfHelper')

    def main_loop(self):
        _log.info("Starting MDTF run")
        config = configs.ConfigManager()
        self.manual_dispatch(config)
        caselist = []
        # only run first case in list until dependence on env vars cleaned up
        for case_dict in self.case_list[0:1]: 
            case = self.DataManager(case_dict)
            for pod_name in case.pod_list:
                try:
                    pod = self.Diagnostic(pod_name)
                except AssertionError as error:  
                    _log.error(str(error))
                case.pods.append(pod)
            case.setUp()
            case.fetch_data()
            caselist.append(case)

        for case in caselist:
            env_mgr = self.EnvironmentManager()
            env_mgr.pods = case.pods # best way to do this?
            # nc_helper = self.NetCDFHelper()

            # case.preprocess_local_data(
            #     netcdf_mixin=nc_helper, environment_manager=env_mgr
            # )
            env_mgr.setUp()
            env_mgr.run()
            env_mgr.tearDown()

        for case in caselist:
            case.tearDown()
        self.cleanup_tempdirs()
        _log.info("Exiting normally from MDTF run")
        _log.info("Output written to %s", config.paths.OUTPUT_DIR)
