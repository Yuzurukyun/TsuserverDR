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

# WARNING!
# This class will suffer major reworkings for 4.3

from __future__ import annotations
from typing import Any, Callable, Dict, List, Tuple

import asyncio
import errno
import importlib
import json
import random
import socket
import ssl
import sys
import traceback
import urllib.request, urllib.error

from server import logger
from server.ban_manager import BanManager
from server.constants import Constants
from server.client_manager import ClientManager
from server.exceptions import ServerError
from server.hub_manager import HubManager
from server.network.ao_protocol import AOProtocol
from server.network.ms3_protocol import MasterServerClient
from server.party_manager import PartyManager
from server.task_manager import TaskManager
from server.timer_manager import TimerManager

from server.validate.config import ValidateConfig
from server.validate.gimp import ValidateGimp


class TsuserverDR:
    def __init__(self, protocol: AOProtocol = None,
                 client_manager: ClientManager = None, in_test: bool = False):
        self.logged_packet_limit = 100  # Arbitrary
        self.logged_packets = []
        self.print_packets = False  # For debugging purposes
        self._server = None  # Internal server object, changed to proper object later

        self.release = 4
        self.major_version = 4
        self.minor_version = 0
        self.segment_version = 'a6'
        self.internal_version = 'M220920b'
        version_string = self.get_version_string()
        self.software = 'TsuserverDR {}'.format(version_string)
        self.version = 'TsuserverDR {} ({})'.format(version_string, self.internal_version)
        self.in_test = in_test

        self.protocol = AOProtocol if protocol is None else protocol
        client_manager = ClientManager if client_manager is None else client_manager
        logger.log_print = logger.log_print2 if self.in_test else logger.log_print
        logger.log_server = logger.log_server2 if self.in_test else logger.log_server
        self.random = importlib.reload(random)

        logger.log_print('Launching {}...'.format(self.version))
        logger.log_print('Loading server configurations...')

        self.config = None
        self.local_connection = None
        self.masterserver_connection = None
        self.shutting_down = False
        self.loop = None
        self.last_error = None
        self.all_passwords = list()
        self.global_allowed = True
        self.server_select_name = 'SERVER_SELECT'

        self.load_config()

        self.ban_manager = BanManager(self)
        self.timer_manager = TimerManager(self)
        self.party_manager = PartyManager(self)

        self.client_manager: ClientManager = client_manager(self)
        self.hub_manager = HubManager(self)
        self.hub_manager.new_managee(
            autoadd_on_client_enter=True,
        )

        self.ipid_list = {}
        self.hdid_list = {}
        self.gimp_list = list()
        self.load_commandhelp()
        self.load_ids()
        self.load_gimp()

        self.ms_client = None
        self.user_auth_req = False
        self.showname_freeze = False
        self.commands = importlib.import_module('server.commands')
        self.commands_alt = importlib.import_module('server.commands_alt')
        self.logger_handlers = logger.setup_logger(debug=self.config['debug'])

        logger.log_print('Server configurations loaded successfully!')

        self.error_queue = None

    async def start(self):
        self.loop = asyncio.get_event_loop()
        self.error_queue = asyncio.Queue()

        self.task_manager = TaskManager(self)
        if self.config['local']:
            bound_ip = '127.0.0.1'
            logger.log_print('Starting a local server...')
        else:
            bound_ip = '0.0.0.0'
            logger.log_print('Starting a nonlocal server...')

        # Check if port is available
        port = self.config['port']
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((bound_ip, port))
            except socket.error as exc:
                if exc.errno == errno.EADDRINUSE:
                    msg = (f'Port {port} is in use by another application. Make sure to close any '
                           f'conflicting applications (even another instance of this server) and '
                           f'try again.')
                    raise ServerError(msg)
                raise exc
            except OverflowError as exc:
                msg = str(exc).replace('bind(): ', '').capitalize()
                msg += ' Make sure to set your port number to an appropriate value and try again.'
                raise ServerError(msg)

        # Yes there is a race condition here (between checking if port is available, and actually
        # using it). The only side effect of a race condition is a slightly less nice error
        # message, so it's not that big of a deal.
        self._server = await self.loop.create_server(lambda: self.protocol(self),
                                                     bound_ip, port,
                                                     start_serving=False)
        asyncio.create_task(self._server.serve_forever())
        logger.log_pserver('Server started successfully!')

        if self.config['local']:
            host_ip = '127.0.0.1'
        else:
            try:
                host_ip = (urllib.request.urlopen('https://api.ipify.org',
                                                  context=ssl.SSLContext())
                           .read().decode('utf8'))
            except urllib.error.URLError as ex:
                host_ip = None
                logger.log_pdebug('Unable to obtain personal IP from https://api.ipify.org\n'
                                  '{}: {}\n'
                                  'Players may be unable to join.'
                                  .format(type(ex).__name__, ex.reason))
        if host_ip is not None:
            logger.log_pdebug(f'Server should be now accessible from address {host_ip} and port '
                              f'{self.config["port"]}.')
        if not self.config['local']:
            logger.log_pdebug(f'If you want to join your server from this device, you may need to '
                              f'join instead from address 127.0.0.1 and port '
                              f'{self.config["port"]}.')

        if self.config['local']:
            self.local_connection = asyncio.create_task(Constants.do_nothing())

        if self.config['use_masterserver']:
            self.ms_client = MasterServerClient(self)
            self.masterserver_connection = asyncio.create_task(self.ms_client.connect())
            print(' ')
            logger.log_print('Attempting to connect to the master server at {} with the '
                             'following details:'.format(self.config['masterserver_ip']))
            logger.log_print('*Server name: {}'.format(self.config['masterserver_name']))
            logger.log_print('*Server description: {}'
                             .format(self.config['masterserver_description']))

        raise await self.error_queue.get()

    async def normal_shutdown(self):
        # Cleanup operations
        self.shutting_down = True

        # Cancel further polling for master server
        if self.local_connection:
            self.local_connection.cancel()
            await Constants.await_cancellation(self.local_connection)

        if self.masterserver_connection:
            self.masterserver_connection.cancel()
            await Constants.await_cancellation(self.masterserver_connection)
            await Constants.await_cancellation(self.ms_client.shutdown())

        # Cancel pending client tasks and cleanly remove them from the areas
        players = self.get_player_count()
        logger.log_print('Kicking {} remaining client{}.'
                         .format(players, 's' if players != 1 else ''))

        for client in self.get_clients():
            client.disconnect()

        if self._server:
            self._server.close()
            await self._server.wait_closed()

    def get_version_string(self):
        mes = '{}.{}.{}'.format(self.release, self.major_version, self.minor_version)
        if self.segment_version:
            mes = '{}-{}'.format(mes, self.segment_version)
        return mes

    def reload(self):
        default_hub = self.hub_manager.get_default_managee()
        try:
            default_hub.background_manager.validate_file()
            default_hub.character_manager.validate_file()
            default_hub.music_manager.validate_file()
        except ServerError.YAMLInvalidError as exc:
            # The YAML exception already provides a full description. Just add the fact the
            # reload was undone to ease the person who ran the command's nerves.
            msg = (f'{exc} Reload was undone.')
            raise ServerError.YAMLInvalidError(msg)
        except ServerError.FileSyntaxError as exc:
            msg = f'{exc} Reload was undone.'
            raise ServerError(msg)

        # Only on success reload
        default_hub.load_backgrounds()
        default_hub.load_characters()
        default_hub.load_music()

    def reload_commands(self):
        try:
            self.commands = importlib.reload(self.commands)
            self.commands_alt = importlib.reload(self.commands_alt)
        except Exception as error:
            return error

    def log_packet(self, client: ClientManager.Client, packet: str, incoming: bool):
        while len(self.logged_packets) > self.logged_packet_limit:
            self.logged_packets.pop(0)
        entry = ('R:' if incoming else 'S:', Constants.get_time_iso(), str(client.id), packet)
        self.logged_packets.append(entry)

    def new_client(self, transport, protocol=None) -> Tuple[ClientManager.Client, bool]:
        c, valid = self.client_manager.new_client(
            self.hub_manager.get_default_managee(),
            transport,
            protocol=protocol
            )
        c.server = self
        c.area = self.hub_manager.get_default_managee().area_manager.default_area()
        c.area.new_client(c)
        return c, valid

    def remove_client(self, client: ClientManager.Client):
        client.area.remove_client(client)
        self.client_manager.remove_client(client)

    def is_client(self, client: ClientManager.Client):
        # This should only be False for clients that have been disconnected.
        return not client.disconnected and self.client_manager.is_client(client)

    def get_clients(self) -> List[ClientManager.Client]:
        """
        Return a copy of all the clients connected to the server, sorted in ascending order by
        client ID.

        Returns
        -------
        list of ClientManager.Client
            Clients connected to the server.

        """
        return sorted(self.client_manager.clients)

    def get_player_count(self) -> int:
        # Ignore players in the server selection screen.
        return len([client for client in self.get_clients() if client.char_id is not None])

    def load_config(self) -> Dict[str, Any]:
        self.config = ValidateConfig().validate('config/config.yaml')

        self.config['motd'] = self.config['motd'].replace('\\n', ' \n')
        self.all_passwords = list()
        passwords = [
            'modpass',
            'cmpass',
            'gmpass',
            'gmpass1',
            'gmpass2',
            'gmpass3',
            'gmpass4',
            'gmpass5',
            'gmpass6',
            'gmpass7',
            ]

        self.all_passwords = [self.config[password]
                              for password in passwords if self.config[password]]

        # Default values to fill in config.yaml if not present
        defaults_for_tags = {
            'discord_link': None,
            'utc_offset': 'local',

            'max_numdice': 20,
            'max_numfaces': 11037,
            'max_modifier_length': 12,
            'max_acceptable_term': 22074,
            'def_numdice': 1,
            'def_numfaces': 6,
            'def_modifier': '',

            'blackout_background': 'Blackout_HD',
            'default_area_description': 'No description.',
            'party_lights_timeout': 10,
            'showname_max_length': 30,
            'sneak_handicap': 5,
            'spectator_name': 'SPECTATOR',

            'music_change_floodguard': {'times_per_interval': 1,
                                        'interval_length': 0,
                                        'mute_length': 0}
            }

        for (tag, value) in defaults_for_tags.items():
            if tag not in self.config:
                self.config[tag] = value

        return self.config

    def load_commandhelp(self):
        with Constants.fopen('README.md', 'r', encoding='utf-8') as readme:
            lines = [x.rstrip() for x in readme.readlines()]

        self.linetorank = {
            '### User Commands': 'normie',
            '### GM Commands': 'gm',
            '### Community Manager Commands': 'cm',
            '### Moderator Commands': 'mod'}

        self.commandhelp = {
            'normie': dict(),
            'gm': dict(),
            'cm': dict(),
            'mod': dict()}

        # Look for the start of the command list
        try:
            start_index = lines.index('## Commands')
            end_index = lines.index('### Debug commands')
        except ValueError as error:
            error_mes = ", ".join([str(s) for s in error.args])
            message = ('Unable to generate help based on README.md: {}. Are you sure you have the '
                       'latest README.md?'.format(error_mes))
            raise ServerError(message)

        rank = None
        current_command = None

        for line in lines[start_index:end_index]:
            # Check if empty line
            if not line:
                continue

            # Check if this line defines the rank we are taking a look at right now
            if line in self.linetorank.keys():
                rank = self.linetorank[line]
                current_command = None
                continue

            # Otherwise, check if we do not have a rank yet
            if rank is None:
                continue

            # Otherwise, check if this is the start of a command
            if line[0] == '*':
                # Get the command name
                command_split = line[4:].split('** ')
                if len(command_split) == 1:
                    # Case: * **version**
                    current_command = command_split[0][:-2]
                else:
                    # Case: * **uninvite** "ID/IPID"
                    current_command = command_split[0]

                formatted_line = '/{}'.format(line[2:])
                formatted_line = formatted_line.replace('**', '')
                self.commandhelp[rank][current_command] = [formatted_line]
                continue

            # Otherwise, line is part of command description, so add it to its current command desc
            #     - Unlocks your area, provided the lock came as a result of /lock.
            # ... assuming we have a command
            if current_command:
                self.commandhelp[rank][current_command].append(line[4:])
                continue

            # Otherwise, we have a line that is a description of the rank
            # Do nothing about them
            continue  # Not really needed, but made explicit

    def load_ids(self):
        self.ipid_list = dict()
        self.hdid_list = dict()

        # load ipids
        try:
            with Constants.fopen('storage/ip_ids.json', 'r', encoding='utf-8') as whole_list:
                self.ipid_list = json.load(whole_list)
        except ServerError.FileNotFoundError:
            with Constants.fopen('storage/ip_ids.json', 'w', encoding='utf-8') as whole_list:
                json.dump(dict(), whole_list)
            message = 'WARNING: File not found: storage/ip_ids.json. Creating a new one...'
            logger.log_pdebug(message)
        except Exception as ex:
            message = 'WARNING: Error loading storage/ip_ids.json. Will assume empty values.\n'
            message += '{}: {}'.format(type(ex).__name__, ex)
            logger.log_pdebug(message)

        # If the IPID list is not a dict, fix the file
        # Why on earth is it called an IPID list if it is a Python dict is beyond me.
        if not isinstance(self.ipid_list, dict):
            message = (f'WARNING: File storage/ip_ids.json had a structure of the wrong type: '
                       f'{self.ipid_list}. Replacing it with a proper type.')
            logger.log_pdebug(message)
            self.ipid_list = dict()
            self.dump_ipids()

        # load hdids
        try:
            with Constants.fopen('storage/hd_ids.json', 'r', encoding='utf-8') as whole_list:
                self.hdid_list = json.loads(whole_list.read())
        except ServerError.FileNotFoundError:
            with Constants.fopen('storage/hd_ids.json', 'w', encoding='utf-8') as whole_list:
                json.dump(dict(), whole_list)
            message = 'WARNING: File not found: storage/hd_ids.json. Creating a new one...'
            logger.log_pdebug(message)
        except Exception as ex:
            message = 'WARNING: Error loading storage/hd_ids.json. Will assume empty values.\n'
            message += '{}: {}'.format(type(ex).__name__, ex)
            logger.log_pdebug(message)

        # If the HDID list is not a dict, fix the file
        # Why on earth is it called an HDID list if it is a Python dict is beyond me.
        if not isinstance(self.hdid_list, dict):
            message = (f'WARNING: File storage/hd_ids.json had a structure of the wrong type: '
                       f'{self.hdid_list}. Replacing it with a proper type.')
            logger.log_pdebug(message)
            self.hdid_list = dict()
            self.dump_hdids()

    def load_gimp(self):
        try:
            gimp_list = ValidateGimp().validate('config/gimp.yaml')
        except ServerError.FileNotFoundError:
            gimp_list = [
                'ERP IS BAN',
                'HELP ME',
                '(((((case????)))))',
                'Anyone else a fan of MLP?',
                'does this server have sans from undertale?',
                'what does call mod do',
                'Join my discord server please',
                'can I have mod pls?',
                'why is everyone a missingo?',
                'how 2 change areas?',
                '19 years of perfection, i don\'t play games to fucking lose',
                ('nah... your taunts are fucking useless... only defeat angers me... by trying '
                 'to taunt just earns you my pitty'),
                'When do we remove dangits',
                'MODS STOP GIMPING ME',
                'PLAY NORMIES PLS',
                'share if you not afraid of herobrine',
                'New Killer Choosen! Hold On!!',
                'The cake killed Nether.',
                'How you win Class Trials is simple, call your opposition cucks.',
                ]
            with Constants.fopen('config/gimp.yaml', 'w') as gimp:
                Constants.yaml_dump(gimp_list, gimp)
            message = 'WARNING: File not found: config/gimp.yaml. Creating a new one...'
            logger.log_pdebug(message)

        self.gimp_list = gimp_list
        return gimp_list.copy()

    def dump_ipids(self):
        with Constants.fopen('storage/ip_ids.json', 'w', encoding='utf-8') as whole_list:
            json.dump(self.ipid_list, whole_list)

    def dump_hdids(self):
        with Constants.fopen('storage/hd_ids.json', 'w', encoding='utf-8') as whole_list:
            json.dump(self.hdid_list, whole_list)

    def get_ipid(self, ip: str) -> int:
        if ip not in self.ipid_list:
            while True:
                ipid = random.randint(0, 10**10-1)
                if ipid not in self.ipid_list.values():
                    break
            self.ipid_list[ip] = ipid
            self.dump_ipids()
        return self.ipid_list[ip]

    def make_all_clients_do(self, function: str, *args: List[str],
                            pred: Callable[[ClientManager.Client], bool] = lambda x: True,
                            **kwargs):
        for client in self.get_clients():
            if pred(client):
                getattr(client, function)(*args, **kwargs)

    def send_error_report(self, client: ClientManager.Client, cmd: str, args: List[str],
                          ex: Exception):
        """
        In case of an error caused by a client packet, send error report to user, notify moderators
        and have full traceback available on console and through /lasterror
        """

        # Send basic logging information to user
        info = ('=========\nThe server ran into a Python issue. Please contact the server owner '
                'and send them the following logging information:')
        etype, evalue, etraceback = sys.exc_info()
        tb = traceback.extract_tb(tb=etraceback)
        current_time = Constants.get_time()
        file, line_num, module, func = tb[-1]
        file = file[file.rfind('\\')+1:]  # Remove unnecessary directories
        version = self.version
        info += '\r\n*Server version: {}'.format(version)
        info += '\r\n*Server time: {}'.format(current_time)
        info += '\r\n*Packet details: {} {}'.format(cmd, args)
        info += '\r\n*Client version: {}'.format(client.version)
        info += '\r\n*Client status: {}'.format(client)
        info += '\r\n*Area status: {}'.format(client.area)
        info += '\r\n*File: {}'.format(file)
        info += '\r\n*Line number: {}'.format(line_num)
        info += '\r\n*Module: {}'.format(module)
        info += '\r\n*Function: {}'.format(func)
        info += '\r\n*Error: {}: {}'.format(type(ex).__name__, ex)
        info += '\r\nYour help would be much appreciated.'
        info += '\r\n========='
        client.send_ooc(info)
        client.send_ooc_others('Client {} triggered a Python error through a client packet. '
                               'Do /lasterror to take a look at it.'.format(client.id),
                               pred=lambda c: c.is_mod)

        # Print complete traceback to console
        info = 'TSUSERVERDR HAS ENCOUNTERED AN ERROR HANDLING A CLIENT PACKET'
        info += '\r\n*Server version: {}'.format(version)
        info += '\r\n*Server time: {}'.format(current_time)
        info += '\r\n*Packet details: {} {}'.format(cmd, args)
        info += '\r\n*Client version: {}'.format(client.version)
        info += '\r\n*Client status: {}'.format(client)
        info += '\r\n*Area status: {}'.format(client.area)
        info += '\r\n\r\n{}'.format("".join(traceback.format_exception(etype, evalue, etraceback)))
        logger.log_print(info)
        self.last_error = [info, etype, evalue, etraceback]

        # Log error to file
        logger.log_error(info, server=self, errortype='C')

        if self.in_test:
            raise ex

    def broadcast_global(self, client: ClientManager.Client, msg: str, as_mod: bool = False,
                         mtype: str = "<dollar>G",
                         condition: Constants.ClientBool = lambda x: not x.muted_global):
        username = client.name
        ooc_name = '{}[{}][{}]'.format(mtype, client.area.id, username)
        if as_mod:
            ooc_name += '[M]'
        ooc_name_ipid = f'{ooc_name}[{client.ipid}]'
        targets = [c for c in self.get_clients() if condition(c)]
        for c in targets:
            if c.is_officer():
                c.send_ooc(msg, username=ooc_name_ipid)
            else:
                c.send_ooc(msg, username=ooc_name)

    def broadcast_need(self, client: ClientManager.Client, msg: str):
        char_name = client.displayname
        area_name = client.area.name
        area_id = client.area.id

        targets = [c for c in self.get_clients() if not c.muted_adverts]
        msg = ('=== Advert ===\r\n{} in {} [{}] needs {}\r\n==============='
               .format(char_name, area_name, area_id, msg))
        for c in targets:
            c.send_ooc(msg)
