#!/usr/bin/env python
import os
import sys
import argparse
import textwrap
import json
from . import checksum_shared as shared


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('config_file', nargs='?', type=str, 
                        default='', help="Configuration file.")
    args = parser.parse_args()

    header = """
        # This file was produced by make_file_checksums.py and is used by the
        # test_*_checksums.py unit tests. Don't modify it by hand!
        #
        """

    config = shared.get_configuration(args.config_file, check_input=True, check_output=True)
    md5_path = config['paths']['md5_path']
    obs_path = config['paths']['OBS_ROOT_DIR']
    model_path = config['paths']['MODEL_ROOT_DIR']
    out_path = config['paths']['OUTPUT_DIR']

    case_list = shared.get_test_data_configuration()

    print('Hashing input observational data')
    checksum_dict = shared.checksum_in_subtree_1(obs_path, case_list['pods'])
    with open(os.path.join(md5_path, 'checksum_obs_data.json'), 'w') as file_obj:
        file_obj.write(textwrap.dedent(header))
        json.dump(checksum_dict, file_obj)

    print('Hashing input model data')
    checksum_dict = shared.checksum_in_subtree_1(model_path, case_list['models'])
    with open(os.path.join(md5_path, 'checksum_model_data.json'), 'w') as file_obj:
        file_obj.write(textwrap.dedent(header))
        json.dump(checksum_dict, file_obj)

    print('Hashing output data')
    checksum_dict = shared.make_output_data_dict(out_path, case_list['case_list'],
        ['.tar','.tar_old','.log','.json'])
    with open(os.path.join(md5_path, 'checksum_output.json'), 'w') as file_obj:
        file_obj.write(textwrap.dedent(header))
        json.dump(checksum_dict, file_obj)