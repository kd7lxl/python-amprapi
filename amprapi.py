#!/usr/bin/env python
#
# Copyright 2014 Tom Hayward <tom@tomh.us>
#
# This file is part of python-amprapi.
#
# python-amprapi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# python-amprapi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with python-amprapi.  If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime
import json
import requests
import UserDict

import settings


class EncapEntry(UserDict.UserDict):
    def __init__(self, initial_data):
        UserDict.UserDict.__init__(self, initial_data)
        self.data['updated'] = datetime.strptime(
            self.data['updated'], "%Y-%m-%d %H:%M:%S")

    def __hash__(self):
        return id(self)

    def network(self):
        return "%(network)s/%(maskLength)s" % self.data


class AMPRAPI:
    """Python bindings for the AMPR Portal API.

    Usage:
    ampr = AMPRAPI()
    result = ampr.endpoint

    Example (with "encap" endpoint):
    >>> import amprapi
    >>> ampr = amprapi.AMPRAPI()
    >>> for entry in ampr.encap:
    ...     print "%(network)s/%(netmask)s via %(gatewayIP)s" % entry
    ...
    44.151.22.22/32 via 2.10.28.74
    44.182.69.0/24 via 5.15.186.251
    44.133.30.64/32 via 5.57.28.49
    ...
    """
    _map = {
        'encap': EncapEntry,
    }
    _api_version = 'v1'
    _api_version_minor = "1.04"

    def __init__(self, url=settings.API_URL, user=settings.API_USER,
                 api_key=settings.API_KEY):
        self.url = url
        self.user = user
        self.api_key = api_key

        if settings.CHECK_VERSION:
            self.enforce_version()

    def check_version(self):
        return self._api_version_minor == self.get('version')['version']

    def enforce_version(self):
        if not self.check_version():
            version = self.get('version')['version']
            raise ValueError('Unknown API version: %s: %s' % (
                version, self.get('changeLog')[version]))

    def get(self, endpoint):
        r = requests.get(self.url + self._api_version + '/' + endpoint,
                         auth=(self.user, self.api_key))
        if r.status_code == 200:
            return json.loads(r.json())
        elif r.status_code == 404:
            raise NotImplementedError(r.json())
        else:
            raise Exception(r.text)

    def __getattr__(self, name):
        return map(self._map.get(name), self.get(name))


if __name__ == "__main__":
    ampr = AMPRAPI()
    for entry in ampr.encap:
        print "%(network)s/%(netmask)s via %(gatewayIP)s" % entry
