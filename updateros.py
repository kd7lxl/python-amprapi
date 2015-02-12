#!/usr/bin/env python
#
# Copyright 2013, 2014 Tom Hayward <tom@tomh.us>
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

import amprapi
from datetime import date
import time
import paramiko
import socket
import sys

edge_router_ip = sys.argv[-1]
ssh_port = 22
username = None

# blacklist BGP-announced networks with direct-routing agreements
bgp_networks = [
    "44.24.240.0/20",   # HamWAN Puget Sound
    "44.34.128.0/21",   # HamWAN Memphis
    "44.103.0.0/19",    # W8CMN Mi6WAN
]


def get_encap():
    ampr = amprapi.AMPRAPI()
    return ampr.encap


def filter_encap(route):
    if route.network() in bgp_networks:
        return False
    return route


def parse_ros_route(line):
    dstaddress, gateway = None, None
    for field in line.split(" "):
        try:
            param, val = field.split("=")
        except ValueError:
            continue
        if param == "dst-address":
            dstaddress = val
        elif param == "gateway" and val.startswith("ampr-"):
            gateway = val

    if dstaddress and gateway:
        return (dstaddress, gateway)
    else:
        return None


def parse_ros_ipip(line):
    name, remoteaddr = None, None
    for field in line.split(" "):
        try:
            param, val = field.split("=")
        except ValueError:
            continue
        if param == "name" and val.startswith("ampr-"):
            name = val
        elif param == "remote-address":
            remoteaddr = val

    if name and remoteaddr:
        return name, remoteaddr
    else:
        return None


def export_ros(ssh, command):
    stdin, stdout, stderr = ssh.exec_command(command)
    export = stdout.read()
    export = export.replace("\\\r\n    ", "")  # collapse line breaks
    return export.splitlines()


def export_ros_routes(ssh):
    return filter(None, map(parse_ros_route,
                            export_ros(ssh, "/ip route export")))


def export_ros_ipip_interfaces(ssh):
    return filter(None, map(parse_ros_ipip,
                            export_ros(ssh, "/interface ipip export")))


def main():
    encap = filter(None, map(filter_encap, get_encap()))

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(edge_router_ip, ssh_port, username)
        ros_routes = export_ros_routes(ssh)
        ros_ipips = export_ros_ipip_interfaces(ssh)

        unchanged = 0
        routes_to_add = set(encap)
        routes_to_remove = set(ros_routes)
        ipips_to_remove = set(ros_ipips)
        for entry in encap:
            dstaddress = entry.network()
            gateway = entry['gatewayIP']
            interface = "ampr-%s" % gateway
            if (dstaddress, interface) in ros_routes and \
               (interface, gateway) in ros_ipips:
                routes_to_add.discard(entry)
                routes_to_remove.discard((dstaddress, interface))
                ipips_to_remove.discard((interface, gateway))
                unchanged += 1

        commands = []
        commands.append("# %d routes unchanged" % unchanged)

        if len(routes_to_remove) > len(routes_to_add) + 100 and "-f" not in sys.argv:
            raise UserWarning("Sanity check failed: removing too many routes (-%d +%d)" % (
                len(routes_to_remove), len(routes_to_add)))

        if routes_to_remove:
            commands.append("# removing old or modified routes")
        for route in routes_to_remove:
            commands.append("/ip route remove [find dst-address=\"%s\" gateway=\"%s\"]" % route)

        if ipips_to_remove:
            commands.append("# removing orphaned ipip interfaces")
        for interface, gateway in ipips_to_remove:
            commands.append("/interface ipip remove [find name=%s]" % interface)

        if routes_to_add:
            commands.append("# adding new and modified routes")
        for entry in routes_to_add:
            interface = "ampr-%s" % entry['gatewayIP']
            commands.append("/interface ipip add !keepalive clamp-tcp-mss=yes "
                "local-address=%s name=%s remote-address=%s comment=\"%s\"" % (
                    edge_router_ip, interface, entry['gatewayIP'],
                    "AMPR last updated %s, added %s" % (
                        entry['updated'].date(), date.today())))
            commands.append("/ip route add dst-address=%s gateway=%s distance=30" % (entry.network(), interface))
            commands.append("/ip neighbor discovery set %s discover=no" % (interface))

        if "-v" in sys.argv:
            print "\n".join(commands)
        if "-n" not in sys.argv:
            for command in commands:
                ssh.exec_command(command)
                time.sleep(0.1)
    except UserWarning, e:
        print e
    except socket.timeout:
        print "timeout"
    finally:
        ssh.close()


if __name__ == "__main__":
    main()
