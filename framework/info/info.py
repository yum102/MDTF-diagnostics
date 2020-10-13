"""Functions to store contents of settings files for diagnostics (PODs) and 
query them from the command line via 'mdtf info'.
"""
import os
import collections
import logging
from framework import util

_log = logging.getLogger(__name__)

class PodSettings(util.Singleton):
    """:class:`~framework.util.Singleton` to store the contents of settings files
    for diagnostics (PODs), for queries by the user and by the framework.

    Attributes:
        - ``pods``: dict associating a POD's short name with the parsed contents
            of their settings.jsonc file.
        - ``realms``: :py:class:`~collections.defaultdict` associating a modeling
            realm with a list of PODs using data from that realm. PODs can 
            associate themselves with multiple realms by specifying this 
            information as a list in their settings file. Modeling realms follow 
            those on the table at `https://www.gfdl.noaa.gov/mdtf-diagnostics/`__.
        - ``pod_list``: list of alphabetically sorted POD names.
        - ``realm_list``: list of alphabetically sorted modeling realms.
    """
    _pod_dir = 'diagnostics'
    _pod_settings_file = 'settings.jsonc'

    def __init__(self, code_root=None):
        if code_root is not None:
            self.code_root = code_root
            self.pods = dict()
            self.realms = collections.defaultdict(list)
            self.pod_list = []
            self.realm_list = []

    def _read_settings(self, pod):
        """Wrapper to read the settings file for a given POD.
        """
        d = dict()
        path = os.path.join(
            self.code_root, self._pod_dir, pod, self._pod_settings_file
        )
        try:
            d = util.read_json(path)
            assert 'settings' in d
        except Exception:
            # log error, but continue anyway
            _log.error('Attempt to read POD settings file from %s failed.', path)
        return d

    def get_pod_list(self):
        """Return a sorted list of PODs by inspecting the ``/diagnostics``
        directory.

        .. note::
           Currently this doesn't check if the PODs' supporting data is present.
        """
        pod_list = os.listdir(os.path.join(self.code_root, self._pod_dir))
        pod_list = [s for s in pod_list if not s.startswith(('_','.'))]
        pod_list.sort(key=str.lower)
        return pod_list

    def load_pod_settings(self, pod=None):
        """Method to populate attributes with POD settings file data.

        Args:
            pod (optional): If given, returns the parsed settings file for that
                POD. If the POD can't be found, an error is logged but no 
                exception is raised. If not given, reads the settings files for 
                all accessible PODs and populates the class' attributes with the
                contents.
        """
        pod_list = self.get_pod_list()
        if pod is None:
            realm_list = set()
            bad_pods = []
            for p in pod_list:
                d = self._read_settings(p)
                if not d:
                    bad_pods.append(p)
                    continue
                self.pods[p] = d
                # PODs requiring data from multiple realms get stored in the dict
                # under a tuple of those realms; realms stored indivudally in realm_list
                _realm = util.to_iter(d['settings'].get('realm', None), tuple)
                if len(_realm) == 0:
                    continue
                elif len(_realm) == 1:
                    _realm = _realm[0]
                    realm_list.add(_realm)
                else:
                    realm_list.update(_realm)
                self.realms[_realm].append(p)
            for p in bad_pods:
                pod_list.remove(p)
            self.pod_list = pod_list
            self.realm_list = sorted(list(realm_list), key=str.lower)
        else:
            if pod not in pod_list:
                _log.error(
                    "Couldn't recognize POD %s out of the following diagnostics:\n%s",
                    pod, ', '.join(pod_list)
                )
                return dict()
            return self._read_settings(pod)

class PodInfoQueryHandler(object):
    """Class providing the user interface to the 'mdtf info' command, used for
    querying information stored in the POD settings files.
    """
    def __init__(self, code_root):
        def _add_topic_handler(keywords, function):
            # keep cmd_list ordered
            keywords = util.to_iter(keywords)
            self.cmd_list.extend(keywords)
            for k in keywords:
                self.cmds[k] = function

        # initialize PodSettings, load data from POD settings files
        pod_settings = PodSettings(code_root)
        pod_settings.load_pod_settings()

        # build list of recognized topics
        self.cmds = dict()
        self.cmd_list = []
        _add_topic_handler('topics', self.info_topics)
        _add_topic_handler(['diagnostics', 'pods'], self.info_pods_all)
        _add_topic_handler('realms', self.info_realms_all)
        _add_topic_handler(pod_settings.realm_list, self.info_realm)
        _add_topic_handler(pod_settings.pod_list, self.info_pod)
        # ...

    def info_topics(self, *args):
        """Topic handler that lists all recognized topics.
        """
        print('Recognized topics for `mdtf info`:')
        print(', '.join(self.cmd_list))

    def _print_pod_info(self, pod, verbose):
        """Subroutine used by the topic handlers which handles the printing of 
        POD information at various verbosity levels.
        """
        pod_settings = PodSettings()
        ds = pod_settings.pods[pod]['settings']
        dv = pod_settings.pods[pod]['varlist']
        if verbose == 1:
            print('  {}: {}.'.format(pod, ds['long_name']))
        elif verbose == 2:
            print('  {}: {}.'.format(pod, ds['long_name']))
            print('    {}'.format(ds['description']))
            print('    Model data used: {}'.format(
                ', '.join([v['var_name'].replace('_var','') for v in dv])
            ))
        elif verbose == 3:
            print('{}: {}.'.format(pod, ds['long_name']))
            print('  Realm: {}.'.format(' and '.join(util.to_iter(ds['realm']))))
            print('  {}'.format(ds['description']))
            print('  Model data used:')
            for var in dv:
                var_str = '    {} ({}) @ {} frequency'.format(
                    var['var_name'].replace('_var',''), 
                    var.get('requirement',''), 
                    var['freq'] 
                )
                if 'alternates' in var:
                    var_str = var_str + '; alternates: {}'.format(
                        ', '.join([s.replace('_var','') for s in var['alternates']])
                    )
                print(var_str)

    def info_pods_all(self, *args):
        """Topic handler that lists all PODs.
        """
        print((
            'Do `mdtf info <diagnostic>` for more info on a specific diagnostic '
            'or check documentation at '
            'https://mdtf-diagnostics.rtfd.io/en/latest/sphinx/pod_toc.html.'
        ))
        print('List of installed diagnostics:')
        pod_settings = PodSettings()
        for pod in pod_settings.pod_list:
            self._print_pod_info(pod, verbose=1)

    def info_pod(self, pod):
        """Topic handler that prints all info for a specific POD.
        """
        self._print_pod_info(pod, verbose=3)

    def info_realms_all(self, *args):
        """Topic handler that prints each modeling realm and the PODs that are
        associated with it.
        """
        print('List of installed diagnostics by realm:')
        pod_settings = PodSettings()
        for realm in pod_settings.realms:
            if isinstance(realm, str):
                print('{}:'.format(realm))
            else:
                # tuple of multiple realms
                print('{}:'.format(' and '.join(realm)))
            for pod in pod_settings.realms[realm]:
                self._print_pod_info(pod, verbose=1)

    def info_realm(self, realm):
        """Topic handler that prints which PODs are associated with one specific
        modeling realm.
        """
        print('List of installed diagnostics for {}:'.format(realm))
        pod_settings = PodSettings()
        for pod in pod_settings.realms[realm]:
            self._print_pod_info(pod, verbose=2)

    def dispatch(self, arg_list):
        """Dispatch to the correct topic handler, based on command-line input.
        """
        if arg_list[0] in self.cmd_list:
            self.cmds[arg_list[0]](arg_list[0])
        else:
            print("ERROR: '{}' not a recognized topic.".format(' '.join(arg_list)))
            self.info_topics()
            exit(1)
        # displayed info, now exit
        exit(0)

# --------------------------------------------------------------

def main(code_root, cli_parser):
    """Entry point for script when called as a subcommand from mdtf.py.

    Args:
        code_root: MDTF-diagnostics repo directory (not used, but passed by
            mdtf.py)
        cli_parser: :class:`framework.cli.MDTFArgParser` instance containing
            parsed command-line arguments.
    """
    info = PodInfoQueryHandler(code_root)
    info.dispatch(cli_parser.parsed_args.topic)
