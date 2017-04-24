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

import jsonschema
import six

import utils


CONFIG_SCHEMA = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "properties": {
            "url": {
                "type": "string"
            },
            "aws-region": {
                "type": "string"
            },
            "namespace": {
                "type": "string"
            },
            "metrics": {
                "items": {
                    "type": "string"
                },
                "type": "array"
            }
        },
        "required": ["url", "aws-region", "namespace", "metrics"]
    }


def validate_schema(data, schema, file_path, value_path=None):
    try:
        jsonschema.validate(data, schema)
    except jsonschema.exceptions.ValidationError as exc:
        print(_make_error_message(exc, file_path, value_path))
        raise


def validate_file_by_schema(schema, file_path):
    data = utils.read_from_file(file_path)
    if data is not None:
        validate_schema(data, schema, file_path)
    else:
        raise ValueError('File {0} is empty'.format(file_path))
    return data


def _make_error_message(exc, file_path, value_path):
    if value_path is None:
        value_path = []

    if exc.absolute_path:
        value_path.extend(exc.absolute_path)

    if exc.context:
        sub_exceptions = sorted(
            exc.context, key=lambda e: len(e.schema_path), reverse=True)
        sub_message = sub_exceptions[0]
        value_path.extend(list(sub_message.absolute_path)[2:])
        message = sub_message.message
    else:
        message = exc.message

    error_msg = "File '{0}', {1}".format(file_path, message)

    if value_path:
        value_path = ' -> '.join(map(six.text_type, value_path))
        error_msg = '{0}, {1}'.format(
            error_msg, "value path '{0}'".format(value_path))

    return error_msg
