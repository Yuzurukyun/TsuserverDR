# TsuserverDR, a Danganronpa Online server based on tsuserver3, an Attorney Online server
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

from __future__ import annotations

import aiohttp
import asyncio
import typing

from server import logger

if typing.TYPE_CHECKING:
    from server.tsuserver import TsuserverDR

class MasterServerClient():
    def __init__(self, server: TsuserverDR):
        self._server = server
        self._session: aiohttp.ClientSession = None
        self._period_length: int = 20

        self._ms_ip: str = self._server.config['masterserver_ip']
        self._own_port: int = self._server.config['port']
        self._own_name: str = self._server.config['masterserver_name']
        self._own_description: str = self._server.config['masterserver_description']

    def _get_server_content(self) -> typing.Dict[str, typing.Any]:
        port = self._own_port
        ws_port = 0
        players = self._server.get_player_count()
        name = self._own_name
        description = self._own_description

        content = {
            "port": port,
            "ws_port": ws_port,
            "players": players,
            "name": name,
            "description": description
        }
        return content

    async def _post_json(self, content: typing.Dict) -> typing.Tuple[bool, typing.Dict]:
        try:
            async with self._session.post(self._ms_ip, json=content) as response:
                ok = response.ok
                j = await response.json(content_type=None)
                return ok, j
        except Exception as ex:
            return False, {"local": ex}

    async def _advertise(self) -> typing.Tuple[bool, typing.Dict]:
        async with aiohttp.ClientSession() as self._session:
            logger.log_pdebug('Established connection with the master server.')
            content = self._get_server_content()
            task = asyncio.create_task(self._post_json(content))
            val = await asyncio.gather(*[task], return_exceptions=True)
            ok, j = val[0]
            return ok, j

    async def connect(self):
        while True:
            try:
                ok, j = await self._advertise()
            except asyncio.exceptions.TimeoutError:
                logger.log_pdebug(f"Unable to connect to the master server, retrying in "
                                  f"{self._period_length} seconds.")
            else:
                if ok:
                    logger.log_pdebug(f"Advertised in master server.")
                else:
                    logger.log_pdebug(f"Failed to advertise: {j}.")
            await asyncio.sleep(self._period_length)

    async def shutdown(self):
        """
        Explicitly shut down the connection to the master server if one is active.
        """

        if self._session:
            await self._session.close()
