# TsuserverDR, server software for Danganronpa Online based on tsuserver3,
# which is server software for Attorney Online.
#
# Copyright (C) 2016 argoneus <argoneuscze@gmail.com> (original tsuserver3)
# Current project leader: 2018-21 Chrezm/Iuvee <thechrezm@gmail.com>
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

"""
Class that contains the master server client, which is a worker that advertises the server's
presence to the AO master server.
"""

from __future__ import annotations

import asyncio
import typing

import aiohttp

from server import logger

if typing.TYPE_CHECKING:
    from server.tsuserver import TsuserverDR

class MasterServerClient():
    """
    Worker that advertises the server's presence to the AO master server.
    """

    def __init__(self, server: TsuserverDR):
        """
        Create a new master server client.

        Parameters
        ----------
        server : TsuserverDR
            Instance of the server that is meant to be advertised.
        """

        self.server = server
        self._period_length = 20
        self._announced_success = False
        self._session: aiohttp.ClientSession = None

        self._ms_ip: str = self.server.config['masterserver_ip']
        self._own_port: int = self.server.config['port']
        self._own_name: str = self.server.config['masterserver_name']
        self._own_description: str = self.server.config['masterserver_description']

    def _get_server_content(self) -> typing.Dict[str, typing.Any]:
        """
        Prepare contents of the server's status that the master server expects in an advertisement.

        Returns
        -------
        typing.Dict[str, typing.Any]
            Contents of the server's status
        """

        port = self._own_port
        players = self.server.get_player_count()
        name = self._own_name
        description = self._own_description

        content = {
            "port": port,
            "players": players,
            "name": name,
            "description": description
        }
        return content

    async def _post_json(self,
                         content: typing.Dict[str, typing.Any]) -> typing.Tuple[bool, typing.Dict]:
        """
        Send content that can be coerced into JSON format to the master server, and return the
        response it returns.

        Parameters
        ----------
        content : typing.Dict[str, typing.Any]
            Content to send.

        Returns
        -------
        typing.Tuple[bool, typing.Dict]
            - If the master server accepted the advertisement, this will be `(True, dict())`.
            - If instead the master server rejected the advertisement, this will be
              `(False, reason)`, where `reason` is why the master server rejected.
            - If instead some error was raised, this will be `(False, {"local": ex})`, where `ex`
              is what the error was.
        """

        try:
            async with self._session.post(self._ms_ip, json=content) as response:
                j = await response.json(content_type=None)
                return response.ok, j
        except Exception as ex:  # pylint: disable=broad-except
            return False, {"local": ex}

    async def _advertise(self) -> typing.Tuple[bool, typing.Dict]:
        """
        Attempt to advertise to the master server the current server status, and return the
        response it returns.

        Returns
        -------
        typing.Tuple[bool, typing.Dict]
            - If the master server accepted the advertisement, this will be `(True, dict())`.
            - If instead the master server rejected the advertisement, this will be
              `(False, reason)`, where `reason` is why the master server rejected.
            - If instead some error was raised, this will be `(False, {"local": ex})`, where `ex`
              is what the error was.
        """

        async with aiohttp.ClientSession() as self._session:
            if not self._announced_success:
                logger.log_pdebug('Establishing connection with the master server...')
            content = self._get_server_content()
            task = asyncio.create_task(self._post_json(content))
            val = await asyncio.gather(*[task], return_exceptions=True)
            return val[0]

    async def connect(self):
        """
        Make the worker start trying to open sessions to the master server client to advertise
        the server's existence. Sessions are refreshed every 20 seconds.

        Logging to console about the attempt are made if any of these are true:
        1. Worker failed to reach the master server, or
        2. Worker reached the master server, but the master server rejected the advertisement, or.
        3. Worker reached the master server, the master server accepted the advertisement, and
        logging such a message would not be an immediate duplicate of a message logged because of
        this case.
        """

        while True:
            try:
                ad_ok, ad_content = await self._advertise()
            except asyncio.exceptions.TimeoutError:
                logger.log_pdebug(f"Unable to connect to the master server, retrying in "
                                  f"{self._period_length} seconds.")
                self._announced_success = False
            else:
                if ad_ok:
                    if not self._announced_success:
                        self._announced_success = True
                        logger.log_pdebug("Advertised to the master server.")
                else:
                    logger.log_pdebug(f"Failed to advertise to the master server: {ad_content}.")
                    self._announced_success = False
            await asyncio.sleep(self._period_length)

    async def shutdown(self):
        """
        Explicitly shut down the connection to the master server if one is active.
        """

        if self._session:
            await self._session.close()
