# TsuserverDR, server software for Danganronpa Online based on tsuserver3,
# which is server software for Attorney Online.
#
# Copyright (C) 2016 argoneus <argoneuscze@gmail.com> (original tsuserver3)
#           (C) 2018-22 Chrezm/Iuvee <thechrezm@gmail.com> (further additions)
#           (C) 2022 Tricky Leifa (further additions)
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
Module that contains the AreaManager class, which itself contains the Area subclass.

As Attorney Online clients have no concept of areas, it is the task of the server to perform
all necessary actions in order to simulate different rooms.
"""

from __future__ import annotations

import asyncio
import json
import random
import time
import typing

from typing import Any, Callable, Dict, List, Set, Tuple, Union

from server import logger
from server.asset_manager import AssetManager
from server.constants import Constants, FadeOption
from server.evidence import EvidenceList
from server.exceptions import AreaError, MusicError, ServerError, TaskError
from server.subscriber import Publisher
from server.validate.areas import ValidateAreas

if typing.TYPE_CHECKING:
    # Avoid circular referencing
    from server.hub_manager import _Hub
    from server.client_manager import ClientManager
    from server.party_manager import PartyManager
    from server.tsuserver import TsuserverDR
    from server.zone_manager import ZoneManager


class AreaManager(AssetManager):
    """
    A manager for areas. Area managers store a list of areas either from a
    loaded file or an adequate Python representation.
    It also contains the Area object definition.
    """

    class Area:
        """
        Create a new area for the hub.
        """

        def __init__(
            self,
            server: TsuserverDR,
            hub: _Hub,
            area_id: int,
            parameters: Dict[str, Any]
        ):
            """
            Parameters
            ----------
            server : TsuserverDR
                The server this area belongs to.
            hub: _Hub
                The hub this area belongs to.
            area_id: int
                The area ID.
            parameters: dict
                Area parameters as specified in the loaded area list.
            """

            self.server = server
            self.hub = hub
            self.id = area_id
            self.publisher = Publisher(self)

            self._clients = set()
            self.invite_list = {}
            self.music_looper = None
            self.music_looper_pargs = {}
            self.next_message_time = 0
            self.hp_def = 10
            self.hp_pro = 10
            self.doc = 'No document.'
            self.judgelog = []
            self.shoutlog = []
            self.current_music = ''
            self.current_music_player = ''
            self.current_music_source = ''
            self.legacy_jukebox = False
            self.evi_list = EvidenceList()
            self.recorded_messages = []
            self.ic_lock = False
            self.is_locked = False
            self.is_modlocked = False
            self.bleeds_to = set()
            self.blood_smeared = False
            self.lights = True
            self.last_ic_messages = list()
            self.parties = set()
            self.dicelog = list()
            self.lurk_length = 0
            self._in_zone = None
            self.noteworthy = False
            self.default_noteworthy_text = '[Something catches your attention]'
            self.noteworthy_text = self.default_noteworthy_text
            self.ambient = ''

            self.name = parameters['area']
            self.background = parameters['background']
            self.background_tod = parameters['background_tod']
            self.bg_lock = parameters['bglock']
            self.evidence_mod = parameters['evidence_mod']
            self.locking_allowed = parameters['locking_allowed']
            self.iniswap_allowed = parameters['iniswap_allowed']
            self.rp_getarea_allowed = parameters['rp_getarea_allowed']
            self.rp_getareas_allowed = parameters['rp_getareas_allowed']
            self.rollp_allowed = parameters['rollp_allowed']
            self.reachable_areas = parameters['reachable_areas']
            self.change_reachability_allowed = parameters['change_reachability_allowed']
            self.default_change_reachability_allowed = parameters['change_reachability_allowed']
            self.gm_iclock_allowed = parameters['gm_iclock_allowed']
            self.afk_delay = parameters['afk_delay']
            self.afk_sendto = parameters['afk_sendto']
            self.global_allowed = parameters['global_allowed']
            self.lobby_area = parameters['lobby_area']
            self.private_area = parameters['private_area']
            self.scream_range = parameters['scream_range']
            self.restricted_chars = parameters['restricted_chars']
            self.default_description = parameters['default_description']
            self.has_lights = parameters['has_lights']
            self.cbg_allowed = parameters['cbg_allowed']
            self.song_switch_allowed = parameters['song_switch_allowed']
            self.bullet = parameters['bullet']
            self.visible_areas = parameters['visible_areas']

            # Store the current description separately from the default description
            self.description = self.default_description

            self.default_reachable_areas = self.reachable_areas.copy()

            self.reachable_areas.add(self.name)  # Area can always reach itself

        @property
        def clients(self) -> Set[ClientManager.Client]:
            """
            Declarator for a public clients attribute.
            """

            return self._clients

        @clients.setter
        def clients(self, new_clients: Set[ClientManager.Client]):
            """
            Set the clients parameter to a copy of the given one.

            Parameters
            ----------
            new_clients: Set[ClientManager.Client]
                New set of clients.
            """

            self._clients = new_clients

        def new_client(self, client: ClientManager.Client):
            """
            Add a client to the client list of the current area.

            Parameters
            ----------
            client: ClientManager.Client
                Client to add.
            """

            self.clients.add(client)

        def remove_client(self, client: ClientManager.Client):
            """
            Remove a client of the client list of the current area.

            Parameters
            ----------
            client: server.ClientManager.Client
                Client to remove.

            Raises
            ------
            KeyError
                If the client is not in the area list.
            """

            try:
                self.clients.remove(client)
            except KeyError:
                if client.id != -1:  # Ignore pre-clients (before getting playercount)
                    info = 'Area {} does not contain client {}'.format(self, client)
                    raise KeyError(info)

            if not self.clients:
                self.unlock()

        def send_command(self, cmd: str, *args: List):
            """
            Send a network packet to all clients in the area.

            Parameters
            ----------
            cmd: str
                ID of the packet.
            *args
                Packet arguments.
            """

            for c in self.clients:
                c.send_command(cmd, *args)

        def send_command_dict(self, cmd: str, dargs: Dict[str, Any]):
            """
            Send a network packet to all clients in the area.

            Parameters
            ----------
            cmd: str
                ID of the packet.
            dargs : dict of str to Any
                Packet argument as a map of argument name to argument value.
            """

            for client in self.clients:
                client.send_command_dict(cmd, dargs)

        def broadcast_player_list(self):
            """
            Send the player list packet to everyone in the area.
            """
            return_data = {}
            return_data['packet'] = 'player_list'


            for target_client in self.clients:
                player_data_to_send = list()
                player_stuff = list()
                if self.rp_getarea_allowed and self.lights:
                    for c in self.clients: 
                        
                        if(c != target_client and c.is_visible and c.char_id is not None and c.char_id != -1):
                            chara_client_info = {}
                            player_stuff.append(str(c.id))
                            chara_client_info["id"] = str(c.id)

                            #Append the Showname
                            ## 1.5
                            player_stuff.append(str(c.showname_else_char_showname))
                            chara_client_info["showname"] = str(c.showname_else_char_showname)

                            ## 1.5.1
                            

                            #Append the Character Name
                            ## 1.5
                            if(c.icon_visible):
                                player_stuff.append(str(c.char_folder))
                                chara_client_info["character"] = str(c.char_folder)
                            else:
                                player_stuff.append("")
                                chara_client_info["character"] = "NO_CHARA"

                            if(target_client.is_mod):
                                chara_client_info["HDID"] = str(c.hdid)
                                chara_client_info["IPID"] = str(c.ipid)

                            if(c.files):
                                chara_client_info["url"] = c.files[1]    

                            if(c.char_outfit):
                                chara_client_info["outfit"] = c.char_outfit 

                            if(c.status):
                                chara_client_info["status"] = c.status 
                            player_data_to_send.append(chara_client_info)
                            

                return_data['data'] = player_data_to_send
                
                json_data = json.dumps(return_data)
                target_client.send_command_dict('JSN', {
                    'json_data': json_data
                })
                
                target_client.send_command_dict('LP', {
                    'player_data_ao2_list': player_stuff
                })
        def broadcast_player_list_prompt(self):
            """
            Send the player list prompt packet to everyone in the area.
            """
            for target_client in self.clients:
                target_client.broadcast_player_list_reason_auto()

        def broadcast_ooc(self, msg: str):
            """
            Send an OOC server message to the clients in the area.

            Parameters
            ----------
            msg: str
                Message to be sent.
            """

            for client in self.clients:
                client.send_ooc(msg)

        def broadcast_ic_attention(self, cond: Callable[[ClientManager.Client], bool] = None,
                                   ding: bool = True):
            """
            Send an IC message with a ding to everyone in the area indicating something catches
            their attention, *except* if the player is blind or deaf, or if the area is a lobby
            area.

            Parameters
            ----------
            cond : types.LambdaType: ClientManager.Client -> bool, optional
                Custom condition each player in the area must also satisfy to receive the
                attention message.
            ding : bool, optional
                If the accompanying IC message should also include the "ding" effect.

            Returns
            -------
            None.

            """

            if self.lobby_area:
                return

            if cond is None:
                def cond(_): return True
            for player in self.clients:
                if player.is_deaf and player.is_blind:
                    continue

                if cond(player):
                    player.send_ic_attention(ding=ding)

        def get_background_tod(self) -> Dict[str, str]:
            if not self.lights:
                return dict()

            return self.background_tod.copy()

        def change_background(self, bg: str, validate: bool = True, override_blind: bool = False):
            """
            Change the background of the current area.

            Parameters
            ----------
            bg: str
                New background name.
            validate: bool, optional
                Whether to first determine if background name is listed as a server background
                before changing. Defaults to True.
            override_blind: bool, optional
                Whether to send the intended background to blind people as opposed to the server
                blackout one. Defaults to False (send blackout).

            Raises
            ------
            AreaError
                If the hub attempted to validate the background name and failed.
            """

            if validate and not self.hub.background_manager.is_background(bg):
                raise AreaError('Invalid background name.')

            self.background = bg
            for c in self.clients:
                if c.is_blind and not override_blind:
                    c.send_background(name=self.server.config['blackout_background'])
                elif not c.area.lights:
                    c.send_background(name=self.server.config['blackout_background'])
                else:
                    c.send_background(name=self.background,
                                      tod_backgrounds=self.get_background_tod())

        def change_background_tod(self, bg: str, tod: str, validate: bool = True,
                                  override_blind: bool = False):
            """
            If `bg` is non-empty, change the background of the given period of the current area.
            Otherwise, remove the background associated with the given period.

            Parameters
            ----------
            bg: str
                New background name.
            tod: str
                Time of day.
            validate: bool, optional
                Whether to first determine if background name is listed as a server background
                before changing. Defaults to True.
            override_blind: bool, optional
                Whether to send the intended background to blind people as opposed to the hub
                blackout one. Defaults to False (send blackout).

            Raises
            ------
            AreaError
                If the background name is non-empty and the hub attempted to validate the
                background name and failed, or if the background name is empty and the area already
                has no backgroudn associated with the given period.
            """

            if validate and not self.hub.background_manager.is_background(bg):
                raise AreaError('Invalid background name.')

            if tod not in self.background_tod and not bg:
                raise AreaError(f'There already is no background associated with the period '
                                f'`{tod}`.')
            if bg:
                self.background_tod[tod] = bg
            else:
                self.background_tod.pop(tod)

            for c in self.clients:
                if c.is_blind and not override_blind:
                    c.send_background(name=self.server.config['blackout_background'])
                elif not c.area.lights:
                    c.send_background(name=self.server.config['blackout_background'])
                else:
                    c.send_background(name=self.background,
                                      tod_backgrounds=self.get_background_tod())

        def get_chars_unusable(self, allow_restricted: bool = False,
                               more_unavail_chars: Set[int] = None) -> Set[int]:
            """
            Obtain all characters that a player in the current area may NOT change to.

            Parameters
            ----------
            allow_restricted: bool, optional
                Whether to include characters whose usage has been manually restricted in the area.
                Defaults to False.
            more_unavail_chars: set of int, optional
                Additional characters to mark as taken (and thus unusuable) in the area. Defaults
                to None.

            Returns
            -------
            unavailable: set of int
                Character IDs of all unavailable characters in the area.
            """

            if more_unavail_chars is None:
                more_unavail_chars = set()

            unavailable = {x.char_id for x in self.clients if x.has_participant_character()}
            unavailable |= more_unavail_chars
            restricted = {self.hub.character_manager.get_character_id_by_name(name)
                          for name in self.restricted_chars}

            if not allow_restricted:
                unavailable |= restricted

            return unavailable

        def get_rand_avail_char_id(self, allow_restricted: bool = False,
                                   more_unavail_chars: Set[int] = None) -> int:
            """
            Obtain a random available character in the area.

            Parameters
            ----------
            allow_restricted: bool, optional
                Whether to include characters whose usage has been manually restricted in the area.
                Defaults to false.
            more_unavail_chars: set of int, optional
                Additional characters to mark as taken (and thus unsuable) in the area. Defaults to
                None.

            Returns
            -------
            int
                ID of randomly chosen available character in the area.

            Raises
            -------
            AreaError
                If there are no available characters in the area.
            """

            unusable = self.get_chars_unusable(allow_restricted=allow_restricted,
                                               more_unavail_chars=more_unavail_chars)
            available = {i for i in range(len(self.hub.character_manager.get_characters()))
                         if i not in unusable}

            if not available:
                raise AreaError('No available characters.')

            return random.choice(tuple(available))

        def is_char_available(self, char_id: Union[int, None], allow_restricted: bool = False,
                              more_unavail_chars: Set[int] = None) -> bool:
            """
            Decide whether a character can be selected in the current area.

            Parameters
            ----------
            char_id: Union[int, None]
                ID of the character to test.
            allow_restricted: bool, optional
                Whether to include characters whose usage has been manually restricted in the area.
                Defaults to False.
            more_unavail_chars: set, optional
                Additional characters to mark as taken in the area. Defaults to None.

            Returns
            -------
            bool
                True if tested character ID is the spectator ID (which is always available) or None
                (the ID that is given when on the lobby but before getting to the character select
                screen), or is not found to be among the area's unusable characters.
            """

            if not self.hub.character_manager.is_char_id_participant(char_id):
                return True

            unusable = self.get_chars_unusable(allow_restricted=allow_restricted,
                                               more_unavail_chars=more_unavail_chars)
            return char_id not in unusable

        def add_to_dicelog(self, client: ClientManager.Client, msg: str):
            """
            Add a dice roll to the dice log of the area.

            Parameters
            ----------
            client: server.ClientManager.Client
                Client to record.
            msg: str
                Dice log to record.
            """

            if len(self.dicelog) >= 20:
                self.dicelog = self.dicelog[1:]

            info = '{} | [{}] {} ({}) {}'.format(Constants.get_time(), client.id,
                                                 client.displayname, client.get_ip(), msg)
            self.dicelog.append(info)

        def get_dicelog(self) -> str:
            """
            Return the dice log of the area.
            """

            info = '== Dice log of area {} ({}) =='.format(self.name, self.id)

            if not self.dicelog:
                info += '\r\nNo dice have been rolled since the area was loaded.'
            else:
                for log in self.dicelog:
                    info += '\r\n*{}'.format(log)
            return info

        def change_doc(self, doc: str = 'No document.'):
            """
            Changes the RP document of the area, usually a URL.

            Parameters
            ----------
            doc: str, optional
                New RP document of the area. Defaults to 'No document.'
            """

            self.doc = doc

        def get_evidence_list(self, client: ClientManager.Client):
            """
            Obtain the evidence list for a client.

            Parameters
            ----------
            client: server.ClientManager.Client
                Client to target.
            """

            client.evi_list, evi_list = self.evi_list.create_evi_list(client)
            return evi_list

        def broadcast_evidence_list(self):
            """
            Resend all clients in the area their evidence list.

            Packet format: LE#<name>&<desc>&<img>#<name>
            """

            for client in self.clients:
                client.send_evidence_list()

        def change_hp(self, side: int, health: int):
            """
            Change a penalty healthbar.

            Parameters
            ----------
            side: int
                Penalty bar to change (1 for def, 2 for pro).
            health: int
                New health value of the penalty bar.

            Raises
            ------
            AreaError
                If an invalid penalty bar or health value was given.

            """

            if not 1 <= side <= 2:
                raise AreaError('Invalid penalty side.')
            if not 0 <= health <= 10:
                raise AreaError('Invalid penalty value.')

            if side == 1:
                self.hp_def = health
            elif side == 2:
                self.hp_pro = health

            for client in self.clients:
                client.send_health(side=side, health=health)

        def is_iniswap(self, client: ClientManager.Client, anim1: str, anim2: str,
                       char: str) -> bool:
            """
            Decide if a client is iniswapping or using files outside their claimed character folder.

            Assumes that server permitted iniswaps do not count as iniswaps.

            Parameters
            ----------
            client: ClientManager.Client
                Client to test.
            anim1: str
                Location of the preanimation the client used.
            anim2: str
                Location of the main animation the client used.
            char: str
                Name of the folder the client claims their files are.

            Returns
            -------
            bool
                True if either anim1 or anim2 point to an external location through '../../' or
                their claimed character folder does not match the expected server name.
            """

            if char == client.get_char_name():
                return False

            if '..' in anim1 or '..' in anim2:
                return True
            return True

        def add_to_judgelog(self, client: ClientManager.Client, msg: str):
            """
            Add a judge action to the judge log of the area.

            Parameters
            ----------
            client: ClientManager.Client
                Client to record.
            msg: str
                Judge action to record.
            """

            if len(self.judgelog) >= 20:
                self.judgelog = self.judgelog[1:]

            info = '{} | [{}] {} ({}) {}'.format(Constants.get_time(), client.id,
                                                 client.displayname, client.get_ip(), msg)
            self.judgelog.append(info)

        def get_judgelog(self) -> str:
            """
            Return the judge log of the area.
            """

            info = '== Judge log of {} ({}) =='.format(self.name, self.id)

            if not self.judgelog:
                info += '\r\nNo judge actions have been performed since the area was loaded.'
            else:
                for log in self.judgelog:
                    info += '\r\n*{}'.format(log)
            return info

        def change_lights(self, new_lights: bool, initiator: ClientManager.Client = None,
                          area: AreaManager.Area = None):
            """
            Change the light status of the area and send related announcements.

            This also updates the light status for parties.

            Parameters
            ----------
            new_lights: bool
                New light status
            initiator: server.ClientManager.Client, optional
                Client who triggered the light status change.
            area: server.AreaManager.Area, optional
                Broadcasts light change messages to chosen area. Used if
                the initiator is elsewhere, such as in /zone_lights.
                If not None, the initiator will receive no notifications of
                light status changes.

            Raises
            ------
            AreaError
                If the new light status matches the current one.
            """

            status = {True: 'on', False: 'off'}
            if self.lights == new_lights:
                raise AreaError('The lights are already turned {}.'.format(status[new_lights]))

            self.lights = new_lights
            self.change_background(self.background, validate=False)  # Allow restoring custom bg.

            # Announce light status change
            if initiator:  # If a player initiated the change light sequence, send targeted messages
                if area is None:
                    if not initiator.is_blind:
                        initiator.send_ooc('You turned the lights {}.'.format(status[new_lights]))
                    elif not initiator.is_deaf:
                        initiator.send_ooc('You hear a flicker.')
                    else:
                        initiator.send_ooc('You feel a light switch was flipped.')

                initiator.send_ooc_others('The lights were turned {}.'.format(status[new_lights]),
                                          is_zstaff_flex=False, to_blind=False,
                                          in_area=area if area else True)
                initiator.send_ooc_others('You hear a flicker.',
                                          is_zstaff_flex=False, to_blind=True, to_deaf=False,
                                          in_area=area if area else True)
                initiator.send_ooc_others('(X) {} [{}] turned the lights {}.'
                                          .format(initiator.displayname, initiator.id,
                                                  status[new_lights]),
                                          is_zstaff_flex=True, in_area=area if area else True)
            else:  # Otherwise, send generic message
                self.broadcast_ooc('The lights were turned {}.'.format(status[new_lights]))

            self.broadcast_player_list_prompt()
            
            self.broadcast_player_list()

            # Notify the parties in the area that the lights have changed
            for party in self.parties:
                party.check_lights()

            for c in self.clients:
                found_something, ding_something = c.area_changer.notify_me_rp(
                    self, changed_visibility=True, changed_hearing=False)
                if found_something and new_lights:
                    c.send_ic_attention(ding=ding_something)

        def set_next_msg_delay(self, msg_length: int):
            """
            Set a message delay for the next IC message in the area based on the length of the
            current message, so new messages sent before this delay expires are discarded.

            Parameters
            ----------
            msg_length: int
                Length of the current message.
            """

            delay = min(3000, 100 + 60 * msg_length)
            self.next_message_time = round(time.time() * 1000.0 + delay)

        def can_send_message(self) -> bool:
            """
            Decide if an incoming IC message does not violate the area's established delay for
            the previously received IC message.

            Returns
            -------
            bool
                True if the message was sent after the delay was over.
            """

            return (time.time() * 1000.0 - self.next_message_time) > 0

        def play_track(self, name: str, client: ClientManager.Client,
                       raise_if_not_found: bool = False, reveal_sneaked: bool = False,
                       force_same_restart: int = 1, fade_option: FadeOption = FadeOption.NO_FADE,
                       pargs: Dict[str, Any] = None):
            """
            Play a music track in an area.

            Parameters
            ----------
            name : str
                Name of the track to play
            client : ClientManager.Client
                Client who initiated the track change request.
            effect : int, optional
                Accompanying effect to the track (only used by AO 2.8.4+). Defaults to 0.
            raise_if_not_found : bool, optional
                If True, it will raise ServerError if the track name is not in the hub's music
                list nor the client's music list. If False, it will not care about it. Defaults to
                False.
            reveal_sneaked : bool, optional
                If True, it will change the visibility status of the sender client to True (reveal
                them). If False, it will keep their visibility as it was. Defaults to False.
            force_same_restart : int, optional
                If 0, the server allows a player's client to not restart their music if it happens
                to be the case the client is already playing it. If 1, no such permission is given
                and a track must always be restarted from the beginning. Defaults to 1.
            fade_option: FadeOption, optional
                See enum FadeOption
            pargs : dict of str to Any
                If given, they are arguments to an MC packet that was given when the track was
                requested, and will override any other arguments given. If not, this is ignored.
                Defaults to None (and converted to an empty dictionary).

            Raises
            ------
            ServerError.FileInvalidNameError:
                If `name` references parent or current directories (e.g. "../hi.opus")
            MusicError.MusicNotFoundError:
                If `name` is not a music track in the hub's music list and
                `raise_if_not_found` is True.
            """

            if not pargs:
                pargs = dict()
            if Constants.includes_relative_directories(name):
                info = f'Music names may not reference parent or current directories: {name}'
                raise ServerError.FileInvalidNameError(info)

            try:
                name, length, source = client.music_manager.get_music_data(
                    name)
            except MusicError.MusicNotFoundError:
                try:
                    name, length, source = client.hub.music_manager.get_music_data(
                        name)
                except MusicError.MusicNotFoundError:
                    if raise_if_not_found:
                        raise
                    length, source = -1, ''

            if 'name' not in pargs:
                pargs['name'] = name
            if 'char_id' not in pargs:
                pargs['char_id'] = client.char_id
            if 'fade_option' not in pargs:
                pargs['fade_option'] = fade_option.value
            pargs['showname'] = client.showname  # Ignore AO shownames
            if 'loop' not in pargs:
                pargs['loop'] = -1
            if 'channel' not in pargs:
                pargs['channel'] = 0
            if 'effects' not in pargs:
                pargs['effects'] = 0

            loop_pargs = pargs.copy()
            loop_pargs['force_same_restart'] = force_same_restart

            def loop(zeroth_loop):
                for player in self.clients:
                    if zeroth_loop or self.legacy_jukebox or not player.packet_handler.HAS_CLIENTSIDE_MUSIC_LOOPING:
                        player.send_music(**loop_pargs)

                if self.music_looper:
                    self.music_looper.cancel()
                if length > 0:
                    def f(): return loop(False)
                    self.music_looper = asyncio.get_event_loop().call_later(length, f)

                # Overwrite in case char_id changed (e.g., server looping)
                loop_pargs['char_id'] = -1
                loop_pargs['force_same_restart'] = 0
                self.music_looper_pargs = loop_pargs

            loop(True)

            # Record the character name and the track they played.
            self.current_music_player = client.displayname
            self.current_music = name
            self.current_music_source = source

            logger.log_server('[{}][{}]Changed music to {}.'
                              .format(self.id, client.get_char_name(), name), client)

            # Changing music reveals sneaked players, so do that if requested
            if not client.is_staff() and not client.is_visible and reveal_sneaked:
                client.change_visibility(True)
                client.send_ooc_others('(X) {} [{}] revealed themselves by playing music ({}).'
                                       .format(client.displayname, client.id, client.area.id),
                                       is_zstaff_flex=True)

        def play_current_track(self, only_for: Set[ClientManager.Client] = None,
                               force_same_restart: int = -1):
            if not self.current_music:
                raise AreaError('No music is currently playing.')
            if only_for is None:
                only_for = self.clients

            for player in only_for:
                if player not in self.clients:
                    raise AreaError(f'{player.displayname} [{player.id}] is not part of the area.')

            pargs = self.music_looper_pargs.copy()
            if force_same_restart >= 0:
                pargs['force_same_restart'] = force_same_restart

            for player in only_for:
                if player.packet_handler.HAS_CLIENTSIDE_MUSIC_LOOPING:
                    player.send_music(**pargs)

        def add_to_shoutlog(self, client: ClientManager.Client, msg: str):
            """
            Add a shout message to the shout log of the area.

            Parameters
            ----------
            client: ClientManager.Client
                Client to record.
            msg: str
                Shout message to record.
            """

            if len(self.shoutlog) >= 20:
                self.shoutlog = self.shoutlog[1:]

            info = '{} | [{}] {} ({}) {}'.format(Constants.get_time(), client.id,
                                                 client.displayname, client.get_ip(), msg)
            self.shoutlog.append(info)

        def add_party(self, party: PartyManager.Party):
            """
            Adds a party to the area's party list.

            Parameters
            ----------
            party: PartyManager.Party
                Party to record.

            Raises
            ------
            AreaError:
                If the party is already a part of the party list.
            """

            if party in self.parties:
                raise AreaError('Party {} is already part of the party list of this area.'
                                .format(party.get_id()))
            self.parties.add(party)

        def remove_party(self, party: PartyManager.Party):
            """
            Removes a party from the area's party list.

            Parameters
            ----------
            party: server.PartyManager.Party
                Party to record.

            Raises
            ------
            AreaError:
                If the party is not part of the party list.
            """

            if party not in self.parties:
                raise AreaError('Party {} is not part of the party list of this area.'
                                .format(party.get_id()))
            self.parties.remove(party)

        def get_shoutlog(self) -> str:
            """
            Get the shout log of the area.
            """
            info = '== Shout log of {} ({}) =='.format(self.name, self.id)

            if not self.shoutlog:
                info += '\r\nNo shouts have been performed since the area was loaded.'
            else:
                for log in self.shoutlog:
                    info += '\r\n*{}'.format(log)
            return info

        def get_clock_creator(self) -> ClientManager.Client:
            """
            Return a client that has an active day cycle involving the current area.
            If multiple clients satisfy this condition, it returns the client with the smallest ID.
            If no clients satisfy the condition, it raises AreaError.ClientNotFound.

            Returns
            -------
            ClientManager.Client
                Client that has an active day cycle involving the current area.

            Raises
            ------
            AreaError.ClientNotFound
                If no client has an active day cycle involving the current area.
            """

            for client in self.hub.get_players():
                try:
                    task = self.server.task_manager.get_task(client, 'as_day_cycle')
                except TaskError.TaskNotFoundError:
                    pass
                else:
                    area_1, area_2 = task.parameters['area_1'], task.parameters['area_2']
                    if area_1 <= self.id <= area_2:
                        return client
            raise AreaError.ClientNotFound

        def get_clock_period(self) -> str:
            """
            Return the period of a clock initiated by the user with the smallest ID that involves
            the current area.
            If no such users exists, return an empty string.

            Returns
            -------
            str
                Period name.
            """

            try:
                client = self.get_clock_creator()
            except AreaError.ClientNotFound:
                return ''
            else:
                task = self.server.task_manager.get_task(client, 'as_day_cycle')
                period = task.parameters['period']
                return period

        def get_look_output_for(self,
                                client: ClientManager.Client) -> Tuple[bool, bool, str, bool, str]:
            """
            Return information about the visual aspect of the current area in accordance to
            a particular player's perspective.

            Parameters
            ----------
            client : ClientManager.Client
                Player whose perspective will be used.

            Returns
            -------
            Tuple[bool, bool, str, bool, str]
                - First argument is True if information that only GM+ could have obtained is
                  included in the return, False otherwise.
                - Second argument is whether a non-default description is stated in the next
                  argument.
                - Third argument is a description of the current area (ignoring whether `client` is
                  blind or lights are off).
                - Fourth argument is whether a non-default description is stated in the next
                  argument and the player does not see another player in the target area.
                - Fifth argument is a description of the players in the current area that `client`
                  is entitled to see.
            """

            elevated = False

            if self.description == self.server.config['default_area_description']:
                has_area_description = False
                area_description = 'Nothing particularly interesting.'
            else:
                has_area_description = True
                area_description = self.description

            players = client.get_visible_clients(self)
            player_list = list()
            player_description = ''
            for player in players:
                if player.showname:
                    name = player.showname
                elif player.char_showname:
                    name = player.char_showname
                elif player.char_folder != player.get_char_name():
                    name = player.char_folder
                else:
                    name = player.get_char_name()

                priority = 0
                if player.status:
                    priority -= 2**2
                if player.party and player.party == client.party:
                    priority -= 2**1

                player_list.append([priority, name, player.id, player])
                # We add player.id as a tiebreaker if both priority and name are the same
                # This can be the case if, say, two SPECTATOR are in the same area.
                # player.id is unique, so it helps break ties
                # player instances do not have order, so they are a bad way to sort ties.

            player_list.sort()
            for (_, name, _, player) in player_list:
                player_description += f'\r\n[{player.id}] {name}'
                if player.status:
                    player_description += ' (!)'
                if player.party and player.party == client.party:
                    player_description += ' (P)'
                if client.is_staff() and len(client.get_multiclients()) > 1:
                    # If client is multiclienting add (MC) for officers
                    elevated = True
                    player_description += ' (MC)'
                if not player.is_visible:
                    elevated = True
                    player_description += ' (S)'

            if player_description and (players-{player}):
                has_other_players = True
            else:
                # This could happen for example, when a player peeks into an area where they cannot
                # see any player.
                has_other_players = False
                player_description = 'no one'
            return (elevated, has_area_description, area_description,
                    has_other_players, player_description)

        def unlock(self):
            """
            Unlock the area so that non-authorized players may now join.
            """

            self.is_locked = False
            if not self.is_modlocked:
                self.invite_list = {}

        def modunlock(self):
            """
            Unlock the area if it had a mod lock so that non-authorized players may now join.
            """

            self.is_modlocked = False
            self.is_locked = False
            self.invite_list = {}

        @property
        def in_zone(self):
            """
            Declarator for a public in_zone attribute.
            """

            return self._in_zone

        @in_zone.setter
        def in_zone(self, new_zone_value: ZoneManager.Zone):
            """
            Set the in_zone parameter to the given one

            Parameters
            ----------
            new_zone_value: ZoneManager.Zone or None
                New zone the area belongs to.

            Raises
            ------
            AreaError:
                If the area was not part of a zone and new_zone_value is None or,
                if the area was part of a zone and new_zone_value is not None.
            """

            if new_zone_value is None and self._in_zone is None:
                raise AreaError('This area is already not part of a zone.')
            if new_zone_value is not None and self._in_zone is not None:
                raise AreaError('This area is already part of a zone.')

            self._in_zone = new_zone_value

        def destroy(self):
            """
            Emit destruction signal.

            Returns
            -------
            None.

            """

            self.publisher.publish('area_destroyed', dict())

        def __repr__(self):
            """
            Return a string representation of the area.

            The string follows the convention 'A::AreaID:AreaName:ClientsInArea'
            """

            return 'A::{}:{}:{}:{}'.format(self.id, self.name, len(self.clients),
                                           self.hub.get_numerical_id())

    def __init__(self, server: TsuserverDR, hub: Union[_Hub, None] = None):
        """
        Create an area manager object.

        Parameters
        ----------
        server: TsuserverDR
            The server this area manager belongs to.
        hub : _Hub, optional
            The hub this area manager belongs to. Defaults to None.
        """

        super().__init__(server, hub=hub)
        self._areas = []
        self._source_file = None
        self._previous_source_file = None
        self.area_names = set()

        self._default_area_id = 0

    def get_type_name(self) -> str:
        """
        Return `'area list'`.

        Returns
        -------
        str
            `'area list'`.
        """

        return 'area list'

    def get_default_file(self) -> str:
        """
        Return `'config/areas.yaml'`.

        Returns
        -------
        str
            `'config/areas.yaml'`.
        """

        return 'config/areas.yaml'

    def get_loader(self) -> Callable[[str, ], str]:
        """
        Return `self.hub.load_areas`.

        Returns
        -------
        Callable[[str, ], str]
            `self.hub.load_areas`.
        """

        return self.hub.load_areas

    def get_source_file(self) -> Union[str, None]:
        """
        Return the source file of the last area list the manager successfully loaded relative to
        the root directory of the server, or None if the latest loaded area list was loaded raw.

        Returns
        -------
        Union[str, None]
            Source file or None.
        """

        return self._source_file

    def get_previous_source_file(self) -> Union[str, None]:
        """
        Return the output that self.get_source_file() would have returned *before* the last
        successful time an area list was successfully loaded.
        If no such call was ever made, return None.

        Returns
        -------
        Union[str, None]
            Previous source file or None.
        """

        return self._previous_source_file

    def get_custom_folder(self) -> str:
        """
        Return `'config/area_lists'`.

        Returns
        -------
        str
            `'config/area_lists'`.
        """

        return 'config/area_lists'

    def get_areas(self) -> List[Area]:
        """
        Return a copy of the areas managed by this manager.

        Returns
        -------
        List[Area]
            Areas managed.
        """

        return self._areas.copy()

    def load_file(self, source_file: str) -> List:
        """
        Load an area list from a file.

        Parameters
        ----------
        source_file: str
            Location of the area list to load.

        Returns
        -------
        List[AreaManager.Area]
            Areas.

        Raises
        ------
        ServerError.FileNotFoundError
            If the file was not found.
        ServerError.FileOSError
            If there was an operating system error when opening the file.
        ServerError.YAMLInvalidError
            If the file was empty, had a YAML syntax error, or could not be decoded using UTF-8.
        ServerError.FileSyntaxError
            If the file failed verification for areas.
        """

        areas = ValidateAreas().validate(source_file, extra_parameters={
            'server_character_list': self.hub.character_manager.get_characters(),
            'server_default_area_description': self.server.config['default_area_description']
        })
        areas = self._load_areas(areas, source_file)
        self._check_structure()

        return areas

    def load_raw(self, yaml_contents: Dict) -> List[Area]:
        """
        Load an area list from a YAML representation.

        Parameters
        ----------
        yaml_contents: Dict
            YAML representation.

        Returns
        -------
        List[AreaManager.Area]
            Areas.

        Raises
        ------
        ServerError.FileNotFoundError
            If the file was not found.
        ServerError.FileOSError
            If there was an operating system error when opening the file.
        ServerError.YAMLInvalidError
            If the file was empty, had a YAML syntax error, or could not be decoded using UTF-8.
        ServerError.FileSyntaxError
            If the file failed verification for its asset type.
        """

        areas = ValidateAreas().validate_contents(yaml_contents, extra_parameters={
            'server_character_list': self.hub.character_manager.get_characters(),
            'server_default_area_description': self.server.config['default_area_description']
        })
        areas = self._load_areas(areas, None)
        self._check_structure()

        return areas

    def _load_areas(self, areas: List[Area], source_file: Union[str, None]) -> List[Area]:
        self._previous_source_file = self._source_file

        # Now we are ready to create the areas
        self._source_file = source_file

        temp_areas = list()
        for (i, area_item) in enumerate(areas):
            temp_areas.append(self.Area(self.server, self.hub, i, area_item))

        old_areas = self.get_areas()
        self._areas = temp_areas
        self.area_names = [area.name for area in self._areas]

        # Only once all areas have been created, actually set the corresponding values
        # Helps avoiding junk area lists if there was an error
        # But first, remove all zones
        backup_zones = self.hub.zone_manager.get_zones()
        for (zone_id, zone) in backup_zones.items():
            self.hub.zone_manager.delete_zone(zone_id)
            for client in zone.get_watchers():
                client.send_ooc('Your zone has been automatically deleted due to an area list '
                                'load.')

        # And end all existing day cycles
        clients_with_clocks: Set[ClientManager.Client] = set()
        for area in old_areas:
            try:
                clock_creator = area.get_clock_creator()
            except AreaError.ClientNotFound:
                continue
            else:
                clients_with_clocks.add(clock_creator)

        for client in clients_with_clocks:
            try:
                client.server.task_manager.delete_task(client, 'as_day_cycle')
            except TaskError.TaskNotFoundError:
                pass

        # And remove all global IC and global IC prefixes
        for client in self.hub.get_players():
            if client.multi_ic:
                client.send_ooc('Due to an area list reload, your global IC was turned off. You '
                                'may turn it on again manually.')
                client.multi_ic = None
            if client.multi_ic_pre:
                client.send_ooc('Due to an area list reload, your global IC prefix was removed. '
                                'You may set it again manually.')
                client.multi_ic_pre = ''

        # If the default area ID is now past the number of available areas, reset it back to zero
        if self._default_area_id >= len(self._areas):
            self._default_area_id = 0

        # And do other tasks associated with areas reloading
        self.publisher.publish('areas_loaded', dict())

        # Add new areas to hub
        for area in self._areas:
            self.hub.add_area(area)

        for area in old_areas:
            # Decide whether the area still exists or not
            try:
                new_area = self.get_area_by_name(area.name)
                remains = True
            except AreaError:
                new_area = self.default_area()
                remains = False

            # Move existing clients to new corresponding area (or to default area if their previous
            # area no longer exists).
            for client in area.clients.copy():
                # Check if current char is available
                if new_area.is_char_available(client.char_id):
                    new_char_id = client.char_id
                else:
                    try:
                        new_char_id = new_area.get_rand_avail_char_id()
                    except AreaError:
                        new_char_id = -1

                if remains:
                    message = 'Area list reload. Moving you to the new {}.'
                else:
                    message = ('Area list reload. Your previous area no longer exists. Moving you '
                               'to the hub default area {}.')

                client.send_ooc(message.format(new_area.name))
                client.change_area(new_area, ignore_checks=True, change_to=new_char_id,
                                   ignore_notifications=True)

            # Move parties (independently)
            for party in area.parties.copy():
                party.area = new_area
                new_area.add_party(party)

        # Once that is done, indicate old areas to emit destruction signals
        # This is done separately
        for area in old_areas:
            area.destroy()

        return self._areas.copy()

    def default_area(self) -> AreaManager.Area:
        """
        Return the Area object corresponding to the hub's default area.
        """

        return self._areas[self._default_area_id]

    def set_default_area(self, area: Area):
        """
        Set the default area of the area manager.

        Parameters
        ----------
        area : Area
            New area.

        Raises
        ------
        AreaError
            If the manager does not recognize the area as an area it manages.
        """

        if area not in self._areas:
            raise AreaError
        self._default_area_id = area.id

    def get_area_by_name(self, name: str) -> AreaManager.Area:
        """
        Return the Area object corresponding to the area that has the given name.

        Parameters
        ----------
        name: str
            Area name to look for.

        Returns
        -------
        AreaManager.Area
            Area.

        Raises
        ------
        AreaError
            If no area has the given name.
        """

        for area in self._areas:
            if area.name == name:
                return area
        raise AreaError('Area not found.')

    def get_area_by_id(self, area_id: int) -> AreaManager.Area:
        """
        Return the Area object corresponding to the area that has the given ID.

        Parameters
        ----------
        area_id: int
            Area ID to look for.

        Returns
        -------
        AreaManager.Area
            Area.

        Raises
        ------
        AreaError
            If no area has the given ID.
        """

        for area in self._areas:
            if area.id == area_id:
                return area
        raise AreaError('Area not found.')

    def get_areas_in_range(self, area1: AreaManager.Area,
                           area2: AreaManager.Area) -> Set[AreaManager.Area]:
        """
        Return all areas whose ID is at least area1's and at most area2's (both inclusive).
        If both areas have the same ID, return just the given area.
        If area2's ID is smaller than area1's, return the empty set.

        Parameters
        ----------
        area1: self.Area
            Area whose ID will be the lower bound.
        area2: self.Area
            Area whose ID will be the upper bound

        Returns
        ------
        set of self.Area
            All areas in `self.get_areas()` that satisfy area1.id <= area.id <= area2.id
        """

        return {self.get_area_by_id(i) for i in range(area1.id, area2.id+1)}

    def get_client_view(self, client: ClientManager.Client, from_area: Area) -> List[str]:
        # Determine whether to filter the areas in the results
        need_to_check = from_area is None or client.is_staff() or client.is_transient

        # Now add areas
        if from_area is None:
            from_area = client.area

        prepared_list = list()
        prepared_list.append(Constants.get_first_area_list_item('HUB', from_area.hub, from_area))
        for area in self.get_areas():
            if need_to_check or area.name in from_area.visible_areas:
                prepared_list.append(f'{area.id}-{area.name}')

        return prepared_list

    def change_passage_lock(self, client: ClientManager.Client,
                            areas: List[AreaManager.Area],
                            bilock: bool = False,
                            change_passage_visibility: bool = False):
        now_reachable = []
        num_areas = 2 if bilock else 1

        # First check if the player should be able to change the passage at all
        for i in range(num_areas):
            # First check if it is the case a non-authorized use is trying to change passages to
            # areas that do not allow their passages to be modified
            if not areas[i].change_reachability_allowed and not client.is_staff():
                raise AreaError('You must be authorized to change passages in area {}.'
                                .format(areas[i].name))

            # And make sure that non-authorized users cannot create passages they cannot see
            if ((not areas[1-i].name in areas[i].reachable_areas) and
                    not (client.is_staff() or areas[1-i].name in areas[i].visible_areas)):
                raise AreaError('You must be authorized to create a new passage from {} to '
                                '{}.'.format(areas[i].name, areas[1-i].name))

        # If we are at this point, we are committed to changing the passage locks
        for i in range(num_areas):
            if areas[1-i].name in areas[i].reachable_areas:  # Case removing a passage
                now_reachable.append(False)
                areas[i].reachable_areas -= {areas[1-i].name}
                if change_passage_visibility:
                    areas[i].visible_areas -= {areas[1-i].name}
            else:  # Case creating a passage
                now_reachable.append(True)
                areas[i].reachable_areas.add(areas[1-i].name)
                if change_passage_visibility:
                    areas[i].visible_areas.add(areas[1-i].name)

            for client in areas[i].clients:
                client.send_music_list_view()

        return now_reachable

    def _check_structure(self):
        """
        Assert that all invariants specified in the class description are maintained.

        Raises
        ------
        AssertionError
            If any of the invariants are not maintained.

        """

        # 1. At least one area.
        assert self._areas
