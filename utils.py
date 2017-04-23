#
#    Copyright 2017 Vitalii Kulanov
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
import yaml
import json


SUPPORTED_FILE_FORMATS = ('json', 'yaml')


def safe_load(data_format, stream):
    loaders = {'json': json.load,
               'yaml': yaml.safe_load}

    if data_format not in loaders:
        raise ValueError('Unsupported data format.')

    loader = loaders[data_format]
    return loader(stream)


def safe_dump(data_format, stream, data):
    yaml_dumper = lambda data, stream: yaml.safe_dump(data,
                                                      stream,
                                                      default_flow_style=False)
    json_dumper = lambda data, stream: json.dump(data, stream, indent=4)
    dumpers = {'json': json_dumper,
               'yaml': yaml_dumper}

    if data_format not in dumpers:
        raise ValueError('Unsupported data format.')

    dumper = dumpers[data_format]
    dumper(data, stream)


def read_from_file(file_path):
    data_format = os.path.splitext(file_path)[1].lstrip('.')
    with open(file_path, 'r') as stream:
        return safe_load(data_format, stream)


def write_to_file(file_path, data):
    data_format = os.path.splitext(file_path)[1].lstrip('.')

    if data_format not in SUPPORTED_FILE_FORMATS:
        raise ValueError('Unsupported data format. Supported file formats: '
                         '{formats}'.format(formats=SUPPORTED_FILE_FORMATS))

    with open(file_path, 'w') as stream:
        safe_dump(data_format, stream, data)
