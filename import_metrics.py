#!/usr/bin/env python
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

import argparse
import os

import boto3

import client
import utils


def config_file(file_path):
    if not os.path.lexists(file_path):
        raise argparse.ArgumentTypeError(
            "File '{0}' does not exist".format(file_path))
    return file_path


def get_settings(file_path):
    """Gets settings data from configuration file.

    :param file_path: path to configuration file
    :type file_path: str
    """

    return utils.read_from_file(file_path)


def get_metrics_data(client_api, metrics):
    """Gets all data for specific metrics.

    :param client_api: API client, that handles API requests
    :type client_api: client.APIClient
    :param metrics: list of metrics to retrieve data
    :type metrics: list
    :return: list of metrics data
    :rtype: list[dict]
    """

    metrics_data_list = []
    for metric in metrics:
        params = {'query': metric}
        data = client_api.get_request('/query', params)
        metrics_data_list.append(data)
    return metrics_data_list


def create_metric_dimensions(data):
    """Creates metric dimensions based on retrieved unique data.

    :param data: extra information about metric
    :type data: dict
    :return: metric dimensions as a list of dimension dict
            [{'Name': 'string', 'Value': 'string'}, {...}, {...}] 
    :rtype: list[dict]
    """

    ignored = ('__name__',)
    return [{'Name': k, 'Value': v} for k, v in data.items()
            if k not in ignored]


def convert_value(value):
    """Converts metric value to float."""

    try:
        return float(value)
    except ValueError:
        return value


def prepare_single_metric(name, value, dimensions, timestamp, unit='None'):
    """Creates CloudWatch valid metric data format."""

    return {
            'MetricName': name,
            'Dimensions': dimensions,
            'Timestamp': timestamp,
            'Value': convert_value(value),
            'Unit': unit
        }


def prepare_metrics(data):
    """Converts Prometheus metric data format to CloudWatch one.

    :param data: list of metrics data in Prometheus-like format
    :type data: list[dict]
    :return: list of metrics data in CloudWatch-like format 
    :rtype: list[dict]
    """

    metrics = []
    for item in data:
        for i in item['data']['result']:
            single_metric_data = prepare_single_metric(
                name=i['metric']['__name__'],
                value=i['value'][1],
                dimensions=create_metric_dimensions(i['metric']),
                timestamp=i['value'][0],
                unit='Count'
            )
            metrics.append(single_metric_data)
    return metrics


def main():
    parser = argparse.ArgumentParser(description='CloudWatch metrics importer')
    parser.add_argument('-c',
                        '--config',
                        metavar='CONFIG_FILE',
                        required=True,
                        type=config_file,
                        help='Configuration file.')
    args = parser.parse_args()
    settings = get_settings(args.config)
    url = settings.get('url')
    metrics = settings.get('metrics')
    namespace = settings.get('namespace')
    aws_region = settings.get('aws-region')

    # APIClient to fetch data from Prometheus
    client_api = client.APIClient(url=url)
    metrics_data = get_metrics_data(client_api, metrics)
    cw_metrics_data = prepare_metrics(metrics_data)

    cw_client = boto3.client('cloudwatch', region_name=aws_region)
    cw_client.put_metric_data(Namespace=namespace, MetricData=cw_metrics_data)


if __name__ == "__main__":
    main()
