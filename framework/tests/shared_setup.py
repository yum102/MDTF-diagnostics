import os
import sys
import collections
from framework.util import read_json, NameSpace, to_iter
from framework import configs

def setUp_ConfigManager(config=None, paths=None, pods=None, unittest=True):
    PodDataTuple = collections.namedtuple(
        'PodDataTuple', 'sorted_lists pod_data realm_data'
    )

    cwd = os.path.dirname(os.path.realpath(__file__)) 
    code_root = os.path.dirname(os.path.split(cwd)[0])
    dummy_config = read_json(os.path.join(cwd, 'dummy_config.json'))
    if config:
        dummy_config.update(config)
    if paths:
        dummy_config.update(paths)
    if not pods:
        pods = dict()
    dummy_cli_obj = NameSpace.fromDict({
        'code_root': code_root,
        'config': dummy_config
    })
    dummy_pod_data = PodDataTuple(
        pod_data=pods, realm_data=dict(), sorted_lists=dict()
    )
    config = configs.ConfigManager(dummy_cli_obj, dummy_pod_data, unittest=unittest)
    if paths:
        config.paths.parse(paths, list(paths.keys()))

def tearDown_ConfigManager():
    # clear Singletons
    try:
        temp = configs.ConfigManager(unittest=True)
        temp._reset()
    except:
        pass
    try:
        temp = configs.VariableTranslator(unittest=True)
        temp._reset()
    except:
        pass
    try:
        temp = configs.TempDirManager()
        temp._reset()
    except:
        pass


