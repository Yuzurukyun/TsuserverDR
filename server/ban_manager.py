# TsuserverDR, server software for Danganronpa Online based on tsuserver3,
# which is server software for Attorney Online.
#
# Copyright (C) 2016 argoneus <argoneuscze@gmail.com> (original tsuserver3)
#           (C) 2018-22 Chrezm/Iuvee <thechrezm@gmail.com> (further additions)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import annotations

import ipaddress
import json
import typing

from server import logger
from server.constants import Constants
from server.exceptions import ServerError

if typing.TYPE_CHECKING:
    from server.tsuserver import TsuserverDR

class BanManager:
    def __init__(self, server: TsuserverDR):
        self.bans = []
        self.server = server

        self.load_banlist()
        self.write_banlist()  # TODO: Remove this after next major update

    def load_banlist(self):
        try:
            with Constants.fopen('storage/banlist.json', 'r', encoding='utf-8') as banlist_file:
                self.bans = json.load(banlist_file)
        except ServerError.FileNotFoundError:
            message = 'WARNING: File not found: storage/banlist.json. Creating a new one...'
            logger.log_pdebug(message)
            self.write_banlist()
        except Exception as ex:
            message = 'WARNING: Error loading storage/banlist.json. Will assume empty values.\n'
            message += '{}: {}'.format(type(ex).__name__, ex)
            logger.log_pdebug(message)

    def write_banlist(self):
        with open('storage/banlist.json', 'w', encoding='utf-8') as banlist_file:
            json.dump(self.bans, banlist_file, indent=4)

    def add_ban(self, ip):
        try:
            try:
                int(ip)
            except ValueError:
                ipaddress.ip_address(ip)
                ip = self.server.get_ipid(ip)
        except ValueError:
            raise ServerError('Argument must be an IP address or IPID.')
        if ip not in self.bans:
            self.bans.append(ip)
        else:
            raise ServerError('User is already banned.')
        self.write_banlist()

    def remove_ban(self, ip):
        try:
            try:
                int(ip)
            except ValueError:
                ipaddress.ip_address(ip)
                ip = self.server.get_ipid(ip)
        except ValueError:
            raise ServerError('Argument must be an IP address or IPID.')
        if ip in self.bans:
            self.bans.remove(ip)
        else:
            raise ServerError('User is already not banned.')
        self.write_banlist()

    def is_banned(self, ipid):
        return ipid in self.bans
