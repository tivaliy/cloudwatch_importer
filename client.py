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

import json
import requests


class APIClient(object):
    """This class handles API requests."""

    def __init__(self, url, api_path="/api/v1/"):
        self.root = "{url}".format(url=url)
        self._session = None
        self.api_root = "{0}{1}".format(self.root, api_path)

    @staticmethod
    def _make_common_headers():
        """Returns a dict of HTTP headers common for all requests."""

        return {'Content-Type': 'application/json',
                'Accept': 'application/json'}

    def _make_session(self):
        """Initializes a HTTP session."""

        session = requests.Session()
        session.headers.update(self._make_common_headers())
        return session

    @property
    def session(self):
        """Lazy initialization of a session."""

        if self._session is None:
            self._session = self._make_session()
        return self._session

    def delete_request(self, api):
        """Make DELETE request to specific API with some data.

        :param api: API endpoint(path)
        """

        url = self.api_root + api
        resp = self.session.delete(url)
        self._raise_for_status_with_info(resp)

        return self._decode_content(resp)

    def put_request(self, api, data, **params):
        """Make PUT request to specific API with some data.

        :param api: API endpoint (path)
        :param data: Data send in request, will be serialized to JSON
        :param params: Params of query string
        """

        url = self.api_root + api
        data_json = json.dumps(data)
        resp = self.session.put(url, data=data_json, params=params)
        self._raise_for_status_with_info(resp)
        return self._decode_content(resp)

    def get_request_raw(self, api, params=None):
        """Make a GET request to specific API and return raw response.

        :param api: API endpoint (path)
        :param params: params passed to GET request
        """

        url = self.api_root + api
        return self.session.get(url, params=params)

    def get_request(self, api, params=None):
        """Make GET request to specific API."""

        params = params or {}
        resp = self.get_request_raw(api, params)
        self._raise_for_status_with_info(resp)
        return self._decode_content(resp)

    def post_request_raw(self, api, data=None):
        """Make a POST request to specific API and return raw response.

        :param api: API endpoint (path)
        :param data: data send in request, will be serialized to JSON
        """

        url = self.api_root + api
        data_json = None if data is None else json.dumps(data)

        return self.session.post(url, data=data_json)

    def post_request(self, api, data=None):
        """Make POST request to specific API with some data."""

        resp = self.post_request_raw(api, data)
        self._raise_for_status_with_info(resp)
        return self._decode_content(resp)

    @staticmethod
    def _decode_content(response):
        if response.status_code == 204:
            return {}
        return response.json()

    @staticmethod
    def _get_error_body(error):
        try:
            error_body = json.loads(error.response.text)['message']
        except (ValueError, TypeError, KeyError):
            error_body = error.response.text
        return error_body

    def _raise_for_status_with_info(self, response):
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            "{} ({})".format(e, self._get_error_body(e))
            raise
