# TsuserverDR, a Danganronpa Online server based on tsuserver3, an Attorney Online server
#
# Copyright (C) 2016 argoneus <argoneuscze@gmail.com> (original tsuserver3)
# Current project leader: 2018-22 Chrezm/Iuvee <thechrezm@gmail.com>
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
The class that manages incoming connections.
"""

from __future__ import annotations

import asyncio
import typing
from collections import namedtuple
from typing import List

from server import logger, clients
from server.network import client_commands
from server.constants import ArgType, Constants
from server.exceptions import AOProtocolError

if typing.TYPE_CHECKING:
    # Avoid circular referencing
    from server.tsuserver import TsuserverDR


class AOProtocol(asyncio.Protocol):
    """
    The main class that deals with the AO protocol.
    """

    _command = namedtuple('ClientCommand', ['function', 'needs_auth'])

    def __init__(self, server: TsuserverDR):
        super().__init__()
        self.server = server
        self.client = None
        self.buffer = ''
        self.ping_timeout = None
        logger.log_print = logger.log_print2 if self.server.in_test else logger.log_print

        # Determine whether /exec is active or not and warn server owner if so.
        if getattr(self.server.commands, "ooc_cmd_exec")(self.client, "is_exec_active") == 1:
            logger.log_print("""

                  WARNING

                  THE /exec COMMAND IN commands.py IS ACTIVE.

                  UNLESS YOU ABSOLUTELY MEANT IT AND KNOW WHAT YOU ARE DOING,
                  PLEASE STOP YOUR SERVER RIGHT NOW AND DEACTIVATE IT BY GOING TO THE
                  commands.py FILE AND FOLLOWING THE INSTRUCTIONS UNDER ooc_cmd_exec.\n
                  BAD THINGS CAN AND WILL HAPPEN OTHERWISE.

                  """)

    def connection_made(self, transport):
        """ Called upon a new client connecting

        :param transport: the transport object
        """

        self.client, valid = self.server.new_client(transport, protocol=self)
        self.ping_timeout = asyncio.get_event_loop().call_later(self.server.config['timeout'],
                                                                self.client.disconnect)
        if not valid:
            self.client.send_command_dict('PN', {
                'player_count': self.server.get_player_count(),
                'player_limit': self.server.config['playerlimit']
                })
            self.client.disconnect()
            return

        fantacrypt_key = 34  # just fantacrypt things
        self.client.send_command_dict('decryptor', {'key': fantacrypt_key})

    def connection_lost(self, exc):
        """ User disconnected

        :param exc: reason
        """
        self.client.disconnected = True
        self.server.remove_client(self.client)
        self.ping_timeout.cancel()

    def _get_messages(self):
        """ Parses out full messages from the buffer.

        :return: yields messages
        """
        while '#%' in self.buffer:
            spl = self.buffer.split('#%', 1)
            self.buffer = spl[1]
            yield spl[0]

    def _process_message(self, msg):
        if len(msg) < 2:
            # This immediatelly kills any client that does not even try to follow the proper
            # client protocol
            msg = self.buffer if len(self.buffer) < 512 else self.buffer[:512] + '...'
            logger.log_server(f'Terminated {self.client.get_ipreal()} (packet too short): '
                              f'sent {msg} ({len(self.buffer)} bytes)')
            self.client.disconnect()
            return False

        # general netcode structure is not great
        if msg[0] == '#':
            msg = msg[1:]
        raw_parameters = msg.split('#')
        msg = '#'.join(raw_parameters)

        logger.log_debug(f'[INC][RAW]{msg}', self.client)
        try:
            if self.server.print_packets:
                print(f'> {self.client.id}: {msg}')
            self.server.log_packet(self.client, msg, True)
            # Decode AO clients' encoding
            cmd, *args = Constants.decode_ao_packet(msg.split('#'))
            if cmd not in self.net_cmd_dispatcher:
                logger.log_pserver(f'Client {self.client.id} sent abnormal packet {msg} '
                                   f'(client version: {self.client.version}).')
                return False

            dispatched = self.net_cmd_dispatcher[cmd]
            pargs = self._process_arguments(cmd, args, needs_auth=dispatched.needs_auth,
                                            fallback_protocols=[clients.ClientDROLegacy])
            self.client.publish_inbound_command(cmd, pargs)

            dispatched.function(self.client, pargs)
            self.ping_timeout.cancel()
            self.ping_timeout = asyncio.get_event_loop().call_later(
                self.client.server.config['timeout'], self.client.disconnect)
        except AOProtocolError.InvalidInboundPacketArguments:
            pass
        except Exception as ex: # pylint: disable=broad-except
            self.server.send_error_report(self.client, cmd, args, ex)
        return True

    def data_received(self, data):
        """ Handles any data received from the network.

        Receives data, parses them into a command and passes it
        to the command handler.

        :param data: bytes of data
        """
        buf = data
        if buf is None:
            buf = b''

        # try to decode as utf-8, ignore any erroneous characters
        self.buffer += buf.decode('utf-8', 'ignore')
        self.buffer = self.buffer.translate({ord(c): None for c in '\0'})

        if len(self.buffer) > 8192:
            msg = self.buffer if len(self.buffer) < 512 else self.buffer[:512] + '...'
            logger.log_server(f'Terminated {self.client.get_ipreal()} (packet too long): '
                              f'sent {msg} ({len(self.buffer)} bytes)')
            self.client.disconnect()
            return

        found_message = False
        for msg in self._get_messages():
            found_message = True
            if not self._process_message(msg):
                return

        if not found_message:
            # This immediatelly kills any client that does not even try to follow the proper
            # client protocol
            msg = self.buffer if len(self.buffer) < 512 else self.buffer[:512] + '...'
            logger.log_server(f'Terminated {self.client.get_ipreal()} (packet syntax '
                              f'unrecognized): sent {msg} ({len(self.buffer)} bytes)')
            self.client.disconnect()

    def _validate_net_cmd(self, args, *types, needs_auth=True):
        """ Makes sure the net command's arguments match expectations.

        :param args: actual arguments to the net command
        :param types: what kind of data types are expected
        :param needs_auth: whether you need to have chosen a character and sent HI and ID
        :return: returns True if message was validated
        """
        if needs_auth:
            if self.client.char_id is None:
                return False
            if 'HI' not in self.client.required_packets_received:
                return False
            if 'ID' not in self.client.required_packets_received:
                return False

        if len(args) != len(types):
            return False
        for i, arg in enumerate(args):
            if len(arg) == 0 and types[i] != ArgType.STR_OR_EMPTY:
                return False
            if types[i] == ArgType.INT:
                try:
                    args[i] = int(arg)
                except ValueError:
                    return False
        return True

    def _process_arguments(self, identifier, args, needs_auth=True, fallback_protocols=None):
        """
        Process the parameters associated with an incoming client packet.
        """

        if fallback_protocols is None:
            fallback_protocols = list()

        packet_type = f'{identifier.upper()}_INBOUND'
        protocols = [self.client.packet_handler]+fallback_protocols
        for protocol in protocols:
            try:
                expected_pairs = getattr(protocol, packet_type)
            except KeyError:
                continue
            expected_argument_names = [x[0] for x in expected_pairs]
            expected_types = [x[1] for x in expected_pairs]
            if not self._validate_net_cmd(args, *expected_types, needs_auth=needs_auth):
                continue
            return dict(zip(expected_argument_names, args))
        raise AOProtocolError.InvalidInboundPacketArguments

    def data_send(self, command: str, *args: List):
        if args:
            if command == 'MS':
                for evi_num, evi_value in enumerate(self.client.evi_list):
                    if evi_value == args[11]:
                        lst = list(args)
                        lst[11] = evi_num
                        args = tuple(lst)
                        break

        command, *args = Constants.encode_ao_packet([command] + list(args))
        message = f'{command}#'
        for arg in args:
            message += f'{arg}#'
        message += '%'

        # Only send messages to players that are.. players who are still connected
        # This should only be relevant in the case there is a function that requests packets
        # be sent to multiple clients, but the function does not check if all targets are
        # still clients.
        if self.server.is_client(self.client):
            if self.server.print_packets:
                print(f'< {self.client.id}: {message}')
            self.server.log_packet(self.client, message, False)
            self.client.transport.write(message.encode('utf-8'))
        else:
            if self.server.print_packets:
                print(f'< {self.client.id}: {message} || FAILED: Socket closed')

    net_cmd_dispatcher = {
        'HI': _command(function=client_commands.net_cmd_hi,
                       needs_auth=False),  # handshake
        'ID': _command(function=client_commands.net_cmd_id,
                       needs_auth=False),  # client version
        'CH': _command(function=client_commands.net_cmd_ch,
                       needs_auth=False),  # keepalive
        'askchaa': _command(function=client_commands.net_cmd_askchaa,
                            needs_auth=False),  # ask for list lengths
        'AE': _command(function=client_commands.net_cmd_ae,
                       needs_auth=False),  # evidence list
        'RC': _command(function=client_commands.net_cmd_rc,
                       needs_auth=False),  # character list
        'RM': _command(function=client_commands.net_cmd_rm,
                       needs_auth=False),  # music list
        'RD': _command(function=client_commands.net_cmd_rd,
                       needs_auth=False),  # done request, charscheck etc.
        'CC': _command(function=client_commands.net_cmd_cc,
                       needs_auth=False),  # select character
        'MS': _command(function=client_commands.net_cmd_ms,
                       needs_auth=True),  # IC message
        'CT': _command(function=client_commands.net_cmd_ct,
                       needs_auth=True),  # OOC message
        'MC': _command(function=client_commands.net_cmd_mc,
                       needs_auth=True),  # play song
        'RT': _command(function=client_commands.net_cmd_rt,
                       needs_auth=True),  # WT/CE buttons
        'HP': _command(function=client_commands.net_cmd_hp,
                       needs_auth=True),  # penalties
        'PE': _command(function=client_commands.net_cmd_pe,
                       needs_auth=True),  # add evidence
        'DE': _command(function=client_commands.net_cmd_de,
                       needs_auth=True),  # delete evidence
        'EE': _command(function=client_commands.net_cmd_ee,
                       needs_auth=True),  # edit evidence
        'ZZ': _command(function=client_commands.net_cmd_zz,
                       needs_auth=True),  # call mod button
        'PW': _command(function=client_commands.net_cmd_pw,
                       needs_auth=True),  # character password (only on CC/KFO clients), deprecated
        'SP': _command(function=client_commands.net_cmd_sp,
                       needs_auth=True),  # set position
        'SN': _command(function=client_commands.net_cmd_sn,
                       needs_auth=True),  # set showname
        'chrini': _command(function=client_commands.net_cmd_chrini,
                           needs_auth=True),  # char.ini information
        'CharsCheck': _command(function=client_commands.net_cmd_charscheck,
                               needs_auth=True),  # character availability request
    }
