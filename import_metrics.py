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
import logging
import logging.handlers
import sys

import boto3
import requests

from botocore.exceptions import ClientError
from botocore.exceptions import BotoCoreError

import client
import validator
import utils

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
CONSOLE_LOG_FORMAT = '%(levelname)s: %(message)s'
FILE_LOG_FORMAT = ('%(asctime)s.%(msecs)03d %(levelname)s '
                   '(%(module)s) %(message)s')
LOG_FILE_SIZE = 10485760  #  10MB
ROTATE_LOG_FILE_COUNT = 5


def get_settings(file_path):
    """Gets settings data from configuration file.

    :param file_path: path to configuration file
    :type file_path: str
    :return: data settings from configuration file
    :rtype: dict
    """

    try:
        data = validator.validate_file_by_schema(validator.CONFIG_SCHEMA,
                                                 file_path)
    except (ValueError, OSError, IOError) as e:
        logging.error("Received error: {}".format(e), exc_info=True)
        raise
    return data


def get_metrics_data(client_api, metrics):
    """Gets all data for specific metrics.

    :param client_api: API client, that handles API requests
    :type client_api: client.APIClient
    :param metrics: list of metrics to retrieve data
    :type metrics: list
    :return: list of metrics data
    :rtype: list[dict]
    """

    logging.info("Start fetching metrics from Prometheus.")
    metrics_data_list = []
    for metric in metrics:
        params = {'query': metric}
        try:
            data = client_api.get_request('query', params)
        except requests.exceptions.RequestException as e:
            logging.error("Received error: {}".format(e), exc_info=True)
            raise
        # Prometheus returns false-positive result for non-existent metrics.
        # We have to skip non-existent metrics, i.e. those with empty data
        if not data['data']['result']:
            logging.warning("Metric '{0}' not found.".format(metric))
            continue
        metrics_data_list.append(data)
    logging.info("{0} out of {1} metrics were successfully fetched from "
                 "Prometheus.".format(len(metrics_data_list), len(metrics)))
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

    logging.info("Start converting metrics to CloudWatch format.")
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
    logging.info("{0} metrics are ready to be pushed to "
                 "CloudWatch.".format(len(metrics)))
    return metrics


def chunks(data, n):
    """Yield successive n-sized chunks from metrics data list."""

    for i in range(0, len(data), n):
        yield data[i:i + n]


def configure_logging(level=logging.INFO, file_path=None):
    logging.basicConfig(level=level, format=CONSOLE_LOG_FORMAT)

    if file_path:
        fh = logging.handlers.RotatingFileHandler(
            filename=file_path,
            maxBytes=LOG_FILE_SIZE,
            backupCount=ROTATE_LOG_FILE_COUNT
        )
        fh.setLevel(level=level)
        formatter = logging.Formatter(fmt=FILE_LOG_FORMAT, datefmt=DATE_FORMAT)
        fh.setFormatter(formatter)
        logging.getLogger('').addHandler(fh)


def main():
    parser = argparse.ArgumentParser(description='CloudWatch metrics importer')
    parser.add_argument('-c',
                        '--config',
                        metavar='CONFIG_FILE',
                        required=True,
                        help='Configuration file.')
    parser.add_argument('-d',
                        '--dump',
                        choices=['prometheus', 'cloudwatch'],
                        help='Dump metrics to file and exit.')
    parser.add_argument('-f',
                        '--format',
                        choices=utils.SUPPORTED_FILE_FORMATS,
                        default='json',
                        help='Format of metrics file dump. Defaults to json.')
    parser.add_argument('-v',
                        '--verbose',
                        action='store_true',
                        help='Increase output verbosity.')
    parser.add_argument('--log-file',
                        help='Log file to store logs.')
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    log_file = args.log_file if args.log_file else None
    configure_logging(level=level, file_path=log_file)

    logging.info("Start reading configuration from "
                 "file '{0}'.".format(args.config))
    settings = get_settings(args.config)
    url = settings.get('url')
    metrics = settings.get('metrics')
    namespace = settings.get('namespace')
    aws_region = settings.get('aws-region')

    # APIClient to fetch data from Prometheus
    client_api = client.APIClient(url=url)
    metrics_data = get_metrics_data(client_api, metrics)
    cw_metrics_data = prepare_metrics(metrics_data)
    dump_type = {'prometheus': metrics_data, 'cloudwatch': cw_metrics_data}
    if args.dump:
        file_name = "{0}.{1}".format(args.dump, args.format)
        utils.write_to_file(file_name, dump_type[args.dump])
        logging.info("Dump file '{0}' successfully created".format(file_name))
        sys.exit()

    logging.info("Start pushing metrics to CloudWatch.")
    try:
        cw_client = boto3.client('cloudwatch', region_name=aws_region)
        # Split imported metrics list in chunks,
        # since only 20/PutMetricData per request is allowed
        for chunk in chunks(cw_metrics_data, 20):
            cw_client.put_metric_data(Namespace=namespace, MetricData=chunk)
    except (BotoCoreError, ClientError) as e:
        logging.error("Received error: {}".format(e), exc_info=True)
        raise
    logging.info("Metrics were successfully pushed to CloudWatch.")


if __name__ == "__main__":
    main()
