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

"""
File that contains behavior for all supported client commands.
"""

from __future__ import annotations

import random
import re
import time
import typing

from typing import Any, Dict

from server import logger, clients
from server.constants import Constants
from server.exceptions import AreaError, ClientError, ServerError, PartyError, TsuserverException
# from server.evidence import EvidenceList

if typing.TYPE_CHECKING:
    # Avoid circular referencing
    from server.client_manager import ClientManager


def net_cmd_hi(client: ClientManager.Client, pargs: Dict[str, Any]):
    """ Handshake.

    HI#<hdid:string>#%

    :param args: a list containing all the arguments
    """

    if 'HI' in client.required_packets_received:
        # Prevent duplicate 'HI' packets
        client.disconnect()
        return
    client.required_packets_received.add('HI')  # One of two conditions to allow joining

    # Record new HDID and IPID if needed
    client.hdid = pargs['client_hdid']
    if client.hdid not in client.server.hdid_list:
        client.server.hdid_list[client.hdid] = []
    client.ipid = client.server.get_ipid(client.get_ipreal())
    if client.ipid not in client.server.hdid_list[client.hdid]:
        client.server.hdid_list[client.hdid].append(client.ipid)
        client.server.dump_hdids()

    # Check if the client is banned
    for ipid in client.server.hdid_list[client.hdid]:
        if client.server.ban_manager.is_banned(ipid):
            client.send_ooc_others(
                f'Banned client with HDID {client.hdid} and IPID {client.ipid} '
                f'attempted to join the server but was refused entrance.',
                is_officer=True)
            client.send_command_dict('BD', dict())
            client.disconnect()
            return

    logger.log_server(f'Connected. HDID: {client.hdid}.', client)
    client.send_command_dict('ID', {
        'client_id': client.id,
        'server_software': client.server.software,
        'server_software_version': client.server.get_version_string(),
        })
    client.send_command_dict('PN', {
        'player_count': client.server.get_player_count(),
        'player_limit': client.server.config['playerlimit'],
        })


def net_cmd_id(client: ClientManager.Client, pargs: Dict[str, Any]):
    """ Client version

    ID#<software:string>#<version:string>#%

    """

    if 'ID' in client.required_packets_received:
        # Prevent duplicate 'ID' packets
        client.disconnect()
        return
    client.required_packets_received.add('ID')  # One of two conditions to allow joining

    def check_client_version():
        raw_software, raw_version = pargs['client_software'], pargs['client_software_version']
        client.version = (raw_software, raw_version)

        software = raw_software
        version_list = raw_version.split('.')

        # Identify version number
        if len(version_list) >= 3:
            # Such versions include DRO and AO
            release = int(version_list[0])
            major = int(version_list[1])
            # Strip out any extra identifiers (like -b1) from minor
            match = re.match(r'(?P<minor>\d+)(?P<rest>.*)', version_list[2])
            if match:
                minor = int(match['minor'])
                rest = match['rest']
            else:
                minor = 0
                rest = version_list[2]
            if pargs['client_software'] not in ['DRO', 'AO2']:
                return False
        else:
            # Only such version recognized now is CC
            # CC has args[1] == 'CC - Update (\d+\.)*\d+'
            if pargs['client_software_version'].startswith('CC'):
                release = 'CC'
                major = float(raw_version.split(' ')[-1])
                minor = 0
                rest = ''
            else:
                return False

        # While we grab rest for the sake of the future-proofing, right now it is not used.
        # I added this useless if so my IDE wouldn't complain of an unused variable.
        if rest:
            pass

        if software == 'DRO':
            if major >= 2:
                client.packet_handler = clients.ClientDRO1d2d0()
            elif major >= 1:
                client.packet_handler = clients.ClientDRO1d1d0()
            else:
                client.packet_handler = clients.ClientDRO1d0d0()
        else:  # AO2 protocol
            if release == 2:
                if major >= 10:
                    client.packet_handler = clients.ClientAO2d10()
                elif major >= 9:
                    client.packet_handler = clients.ClientAO2d9d0()
                elif major >= 8 and minor >= 4:
                    client.packet_handler = clients.ClientAO2d8d4()
                elif major >= 8:  # KFO
                    client.packet_handler = clients.ClientKFO2d8()
                elif major == 7:  # AO 2.7
                    client.packet_handler = clients.ClientAO2d7()
                elif major == 6:  # AO 2.6
                    client.packet_handler = clients.ClientAO2d6()
                elif major == 4 and minor == 8:  # Older DRO
                    client.packet_handler = clients.ClientDROLegacy()
                else:
                    return False  # Unrecognized
            elif release == 'CC':
                if major >= 24:
                    client.packet_handler = clients.ClientCC24()
                elif major >= 22:
                    client.packet_handler = clients.ClientCC22()
                else:
                    return False  # Unrecognized
        # The only way to make it here is if we have not returned False
        # If that is the case, we have successfully found a version
        return True

    if not check_client_version():
        # Warn player they are using an unknown client.
        # Assume a legacy DRO client instruction set.
        client.packet_handler = clients.ClientDRO1d0d0()
        client.bad_version = True

    client.send_command_dict('FL', {
        'fl_ao2_list': ['yellowtext', 'customobjections', 'flipping', 'fastloading',
                        'noencryption', 'deskmod', 'evidence', 'cccc_ic_support', 'looping_sfx',
                        'additive', 'effects', 'y_offset',
                        # DRO exclusive stuff
                        'ackMS', 'showname', 'chrini', 'charscheck', 'v110',]
        })

    client.send_command_dict('client_version', {
        'dro_version_ao2_list': client.packet_handler.VERSION_TO_SEND
    })


def net_cmd_ch(client: ClientManager.Client, pargs: Dict[str, Any]):
    """ Periodically checks the connection.

    CHECK#<char_id:int>%

    """

    client.send_command_dict('CHECK', dict())


def net_cmd_askchaa(client: ClientManager.Client, pargs: Dict[str, Any]):
    """ Ask for the counts of characters/evidence/music

    askchaa#%

    """

    # Check if client is ready to actually join, and did not do weird packet shenanigans before
    if client.required_packets_received != {'HI', 'ID'}:
        return
    # Check if client asked for this before but did not finish processing it
    if not client.can_askchaa:
        return

    client.can_askchaa = False  # Enforce the joining process happening atomically

    # Make sure there is enough room for the client
    char_cnt = len(client.server.char_list)
    evi_cnt = 0
    music_cnt = sum([len(item['songs']) + 1
                        for item in client.server.music_list])  # +1 for category
    area_cnt = len(client.server.area_manager.areas)
    client.send_command_dict('SI', {
        'char_count': char_cnt,
        'evidence_count': evi_cnt,
        'music_list_count': music_cnt+area_cnt,
        })


def net_cmd_ae(client: ClientManager.Client, pargs: Dict[str, Any]):
    """ Asks for specific pages of the evidence list.

    AE#<page:int>#%

    """

    # Check if client is ready to actually join, and did not do weird packet shenanigans before
    if client.required_packets_received != {'HI', 'ID'}:
        return
    # TODO evidence maybe later


def net_cmd_rc(client: ClientManager.Client, pargs: Dict[str, Any]):
    """ Asks for the whole character list(AO2)

    AC#%

    """

    # Check if client is ready to actually join, and did not do weird packet shenanigans before
    if client.required_packets_received != {'HI', 'ID'}:
        return
    client.send_command_dict('SC', {
        'chars_ao2_list': client.server.char_list,
        })


def net_cmd_rm(client: ClientManager.Client, pargs: Dict[str, Any]):
    """ Asks for the whole music list(AO2)

    AM#%

    """

    # Check if client is ready to actually join, and did not do weird packet shenanigans before
    if client.required_packets_received != {'HI', 'ID'}:
        return

    # Force the server to rebuild the music list, so that clients who just join get the correct
    # music list (as well as every time they request an updated music list directly).
    full_music_list = client.server.build_music_list(include_areas=True,
                                                    include_music=True)
    client.send_command_dict('SM', {
        'music_ao2_list': full_music_list,
        })


def net_cmd_rd(client: ClientManager.Client, pargs: Dict[str, Any]):
    """ Asks for server metadata(charscheck, motd etc.) and a DONE#% signal(also best packet)

    RD#%

    """

    # Check if client is ready to actually join, and did not do weird packet shenanigans before
    if client.required_packets_received != {'HI', 'ID'}:
        return

    client.send_done()
    if client.server.config['announce_areas']:
        if client.server.config['rp_mode_enabled']:
            client.send_limited_area_list()
        else:
            client.send_area_list()
    client.send_motd()
    client.reload_music_list()  # Reload the default area's music list
    # so that it only includes areas reachable from that default area.
    client.can_askchaa = True  # Allow rejoining if left to lobby but did not dc.


def net_cmd_cc(client: ClientManager.Client, pargs: Dict[str, Any]):
    """ Character selection.

    CC#<client_id:int>#<char_id:int>#<client_hdid:string>#%

    """

    # Check if client is ready to actually join, and did not do weird packet shenanigans before
    if client.required_packets_received != {'HI', 'ID'}:
        return

    char_id = pargs['char_id']

    ever_chose_character_before = client.ever_chose_character  # Store for later
    try:
        client.change_character(char_id)
    except ClientError:
        return
    client.last_active = Constants.get_time()

    if not ever_chose_character_before:
        client.send_command_dict('GM', {
            'name': ''
            })
        client.send_command_dict('TOD', {
            'name': ''
            })
        try:
            client.area.play_current_track(only_for={client}, force_same_restart=1)
        except AreaError:
            # Only if there is no current music in the area
            pass


def net_cmd_ms(client: ClientManager.Client, pargs: Dict[str, Any]):
    """ IC message.

    Refer to the implementation for details.

    """

    if client.is_muted:  # Checks to see if the client has been muted by a mod
        client.send_ooc("You have been muted by a moderator.")
        return
    if (client.area.ic_lock and not client.is_staff()
        and not client.can_bypass_iclock):
        client.send_ooc('The IC chat in this area is currently locked.')
        return
    if not client.area.can_send_message():
        return

    # Trim out any leading/trailing whitespace characters up to a chain of spaces
    pargs['text'] = Constants.trim_extra_whitespace(pargs['text'])
    # Check if after all of this, the message is empty. If so, ignore
    if not pargs['text']:
        return

    # First, check if the player just sent the same message with the same character and did
    # not receive any other messages in the meantime.
    # This helps prevent record these messages and retransmit it to clients who may want to
    # filter these out
    if (pargs['text'] == client.last_ic_raw_message
        and client.last_received_ic[0] == client
        and client.get_char_name() == client.last_ic_char):
        return

    if not client.area.iniswap_allowed:
        if client.area.is_iniswap(client, pargs['pre'], pargs['anim'],
                                        pargs['folder']):
            client.send_ooc("Iniswap is blocked in this area.")
            return
    if pargs['folder'] in client.area.restricted_chars and not client.is_staff():
        client.send_ooc('Your character is restricted in this area.')
        return
    if pargs['msg_type'] not in ('chat', '0', '1'):
        return
    if pargs['anim_type'] not in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10):
        return
    if pargs['char_id'] != client.char_id:
        return
    if Constants.includes_relative_directories(pargs['sfx']):
        client.send_ooc(f'Sound effects and voicelines may not not reference parent or '
                                f'current directories: {pargs["sfx"]}')
        return
    if pargs['sfx_delay'] < 0:
        return
    if pargs['button'] not in (0, 1, 2, 3, 4, 5, 6, 7, 8):  # Shouts
        return
    if pargs['button'] > 0 and not client.area.bullet and not client.is_staff():
        client.send_ooc('Bullets are disabled in this area.')
        return
    if pargs['evidence'] < 0:
        return
    if pargs['ding'] not in (0, 1, 2, 3, 4, 5, 6, 7):  # Effects
        return
    if pargs['color'] not in (0, 1, 2, 3, 4, 5, 6, 7, 8):
        return
    if pargs['color'] == 5 and not client.is_officer():
        pargs['color'] = 0
    if client.pos:
        pargs['pos'] = client.pos
    else:
        if pargs['pos'] not in ('def', 'pro', 'hld', 'hlp', 'jud', 'wit'):
            return

    if 'showname' in pargs:
        try:
            client.command_change_showname(pargs['showname'], False)
        except ClientError as exc:
            client.send_ooc(exc)
            return

    # Make sure the areas are ok with this
    try:
        client.area.publisher.publish('area_client_inbound_ms_check', {
            'client': client,
            'contents': pargs,
            })
    except TsuserverException as ex:
        client.send_ooc(ex)
        return

    # Make sure the clients are ok with this
    try:
        client.publisher.publish('client_inbound_ms_check', {
            'contents': pargs,
            })
    except TsuserverException as ex:
        client.send_ooc(ex)
        return

    # At this point, the message is guaranteed to be sent
    if client.packet_handler.HAS_ACKMS:
        client.send_command_dict('ackMS', dict())
    client.pos = pargs['pos']

    # First, update last raw message sent *before* any transformations. That is so that the
    # server can accurately ignore client sending the same message over and over again
    client.last_ic_raw_message = pargs['text']
    client.last_ic_char = client.get_char_name()

    # Truncate and alter message if message effect is in place
    raw_msg = pargs['text'][:256]
    msg = raw_msg
    if client.gimp:  # If you are gimped, gimp message.
        msg = random.choice(client.server.gimp_list)
    if client.disemvowel:  # If you are disemvoweled, replace string.
        msg = Constants.disemvowel_message(msg)
    if client.disemconsonant:  # If you are disemconsonanted, replace string.
        msg = Constants.disemconsonant_message(msg)
    if client.remove_h:  # If h is removed, replace string.
        msg = Constants.remove_h_message(msg)

    gag_replaced = False
    if client.is_gagged:
        allowed_starters = ('(', '*', '[')
        if msg != ' ' and not msg.startswith(allowed_starters):
            gag_replaced = True
            msg = Constants.gagged_message()
        if msg != raw_msg:
            client.send_ooc_others(f'(X) {client.displayname} [{client.id}] tried to say '
                                   f'`{raw_msg}` but is currently gagged.',
                                   is_zstaff_flex=True, in_area=True)

    # Censor passwords if login command accidentally typed in IC
    for password in client.server.all_passwords:
        for login in ['login ', 'logincm ', 'loginrp ', 'logingm ']:
            if login + password in msg:
                msg = msg.replace(password, '[CENSORED]')

    if pargs['evidence'] and pargs['evidence'] in client.evi_list:
        evidence_position = client.evi_list[pargs['evidence']] - 1
        if client.area.evi_list.evidences[evidence_position].pos != 'all':
            client.area.evi_list.evidences[evidence_position].pos = 'all'
            client.area.broadcast_evidence_list()
        pargs['evidence'] = client.evi_list[pargs['evidence']]
    else:
        pargs['evidence'] = 0

    # If client has GlobalIC enabled, set area range target to intended range and remove
    # GlobalIC prefix if needed.
    if client.multi_ic is None or not msg.startswith(client.multi_ic_pre):
        area_range = range(client.area.id, client.area.id + 1)
    else:
        # As msg.startswith('') is True, this also accounts for having no required prefix.
        start, end = client.multi_ic[0].id, client.multi_ic[1].id + 1
        start_area = client.server.area_manager.get_area_by_id(start)
        end_area = client.server.area_manager.get_area_by_id(end-1)
        area_range = range(start, end)

        truncated_msg = msg.replace(client.multi_ic_pre, '', 1)
        if start != end-1:
            client.send_ooc(f'Sent global IC message "{truncated_msg}" to areas '
                            f'{start_area.name} through {end_area.name}.')
        else:
            client.send_ooc(f'Sent global IC message "{truncated_msg}" to area {start_area.name}.')

    pargs['msg'] = msg
    # Try to change our showname if showname packet exists, and doesn't match our current showname
    if 'showname' in pargs and client.showname != pargs['showname']:
        client.net_cmd_sn([pargs['showname']])

    # Compute pairs
    # Based on tsuserver3.3 code
    # Only do this if character is paired, which would only happen for AO 2.6+ clients

    # Handle AO 2.8 logic
    # AO 2.8 sends their charid_pair in slightly longer format (\d+\^\d+)
    # The first bit corresponds to the proper charid_pair, the latter one to whether
    # the character should appear in front or behind the pair. We still want to extract
    # charid_pair so pre-AO 2.8 still see the pair; but make it so that AO 2.6 can send pair
    # messages. Thus, we 'invent' the missing arguments based on available info.
    if 'charid_pair_pair_order' in pargs:
        # AO 2.8 sender
        pargs['charid_pair'] = int(pargs['charid_pair_pair_order'].split('^')[0])
    elif 'charid_pair' in pargs:
        # AO 2.6 sender
        pargs['charid_pair_pair_order'] = f'{pargs["charid_pair"]}^0'
    else:
        # E.g. DRO
        pargs['charid_pair'] = -1
        pargs['charid_pair_pair_order'] = -1

    client.charid_pair = pargs['charid_pair'] if 'charid_pair' in pargs else -1
    client.offset_pair = pargs['offset_pair'] if 'offset_pair' in pargs else 0
    client.flip = pargs['flip']
    if not client.char_folder:
        client.char_folder = pargs['folder']

    if pargs['anim_type'] not in (5, 6):
        client.last_sprite = pargs['anim']

    pargs['other_offset'] = 0
    pargs['other_emote'] = 0
    pargs['other_flip'] = 0
    pargs['other_folder'] = ''
    if 'charid_pair' not in pargs or pargs['charid_pair'] < -1:
        pargs['charid_pair'] = -1
        pargs['charid_pair_pair_order'] = -1

    if pargs['charid_pair'] > -1:
        for target in client.area.clients:
            if target == client:
                continue
            # Check pair has accepted pair
            if target.char_id != client.charid_pair:
                continue
            if target.charid_pair != client.char_id:
                continue
            # Check pair is in same position
            if target.pos != client.pos:
                continue

            pargs['other_offset'] = target.offset_pair
            pargs['other_emote'] = target.last_sprite
            pargs['other_flip'] = target.flip
            pargs['other_folder'] = target.char_folder
            break
        else:
            # There are no clients who want to pair with this client
            pargs['charid_pair'] = -1
            pargs['offset_pair'] = 0
            pargs['charid_pair_pair_order'] = -1

    client.publish_inbound_command('MS_final', pargs)

    for area_id in area_range:
        target_area = client.server.area_manager.get_area_by_id(area_id)
        for target in target_area.clients:
            target.send_ic(params=pargs, sender=client, gag_replaced=gag_replaced)

        target_area.set_next_msg_delay(len(msg))

        # Deal with shoutlog
        if pargs['button'] > 0:
            info = f'used shout {pargs["button"]} with the message: {msg}'
            target_area.add_to_shoutlog(client, info)

    client.area.set_next_msg_delay(len(msg))
    logger.log_server(f'[IC][{client.area.id}][{client.get_char_name()}]{msg}', client)

    # Sending IC messages reveals sneaked players
    if not client.is_staff() and not client.is_visible:
        client.change_visibility(True)
        client.send_ooc_others(f'(X) {client.displayname} [{client.id}] revealed themselves by '
                               f'talking ({client.area.id}).', is_zstaff=True)

    # Restart AFK kick timer and lurk callout timers, if needed
    client.server.tasker.create_task(client,
                                    ['as_afk_kick', client.area.afk_delay, client.area.afk_sendto])
    client.check_lurk()

    client.last_ic_message = msg
    client.last_active = Constants.get_time()

def _process_ooc_command(cmd, client):
    called_function = f'ooc_cmd_{cmd}'
    if hasattr(client.server.commands, called_function):
        function = getattr(client.server.commands, called_function)
        return function

    get_command_alias = getattr(client.server.commands_alt, 'get_command_alias')
    command_alias = get_command_alias(cmd)
    if command_alias:
        called_function = f'ooc_cmd_{command_alias}'
        function = getattr(client.server.commands, called_function)
        return function

    get_command_deprecated = getattr(client.server.commands_alt, 'get_command_deprecated')
    command_deprecated = get_command_deprecated(cmd)
    if command_deprecated:
        called_function = f'ooc_cmd_{command_deprecated}'
        function = getattr(client.server.commands, called_function)

        client.send_ooc(f'This command is deprecated and pending removal in 4.4. '
                        f'Please use /{command_deprecated} next time.')
        return function

    return None


def net_cmd_ct(client: ClientManager.Client, pargs: Dict[str, Any]):
    """ OOC Message

    CT#<name:string>#<message:string>#%

    """

    username, message = pargs['username'], pargs['message']

    # Trim out any leading/trailing whitespace characters up to a chain of spaces
    username = Constants.trim_extra_whitespace(username)
    message = Constants.trim_extra_whitespace(message)

    if client.is_ooc_muted:  # Checks to see if the client has been muted by a mod
        client.send_ooc("You have been muted by a moderator.")
        return
    if username == '' or not client.is_valid_name(username):
        client.send_ooc('You must insert a name with at least one letter.')
        return
    if username.startswith(' '):
        client.send_ooc('You must insert a name that starts with a letter.')
        return
    if Constants.contains_illegal_characters(username):
        client.send_ooc('Your name contains an illegal character.')
        return
    if (Constants.decode_ao_packet([client.server.config['hostname']])[0] in username
        or '$G' in username):
        client.send_ooc('That name is reserved.')
        return

    # After this the name is validated
    client.name = username

    if message.startswith('/'):
        spl = message[1:].split(' ', 1)
        cmd = spl[0]
        arg = ''
        if len(spl) == 2:
            arg = spl[1][:1024]
        arg = Constants.trim_extra_whitespace(arg)  # Do it again because args may be weird

        function = _process_ooc_command(cmd, client)
        if function:
            try:
                function(client, arg)
            except TsuserverException as ex:
                if ex.message:
                    client.send_ooc(ex)
                else:
                    client.send_ooc(type(ex).__name__)
        else:
            client.send_ooc(f'Invalid command `{cmd}`.')
    else:
        # Censor passwords if accidentally said without a slash in OOC
        for password in client.server.all_passwords:
            for login in ['login ', 'logincm ', 'loginrp ', 'logingm ']:
                if login + password in pargs['message']:
                    message = message.replace(password, '[CENSORED]')
        if client.disemvowel:  # If you are disemvoweled, replace string.
            message = Constants.disemvowel_message(message)
        if client.disemconsonant:  # If you are disemconsonanted, replace string.
            message = Constants.disemconsonant_message(message)
        if client.remove_h:  # If h is removed, replace string.
            message = Constants.remove_h_message(message)

        for target in client.area.clients:
            target.send_ooc(message, username=client.name)
        client.last_ooc_message = pargs['message']
        logger.log_server(f'[OOC][{client.area.id}][{client.get_char_name()}]'
                            f'[{client.name}]{message}', client)
    client.last_active = Constants.get_time()


def net_cmd_mc(client: ClientManager.Client, pargs: Dict[str, Any]):
    """ Play music.

    MC#<song_name:int>#<char_id:int>#%

    """

    # First attempt to switch area,
    # because music lists typically include area names for quick access
    try:
        delimiter = pargs['name'].find('-')
        area = client.server.area_manager.get_area_by_name(pargs["name"][delimiter+1:])
        client.change_area(area, from_party=True if client.party else False)

    # Otherwise, attempt to play music.
    except (AreaError, ValueError):
        if client.is_muted:  # Checks to see if the client has been muted by a mod
            client.send_ooc("You have been muted by a moderator.")
            return
        if not client.is_dj:
            client.send_ooc('You were blockdj\'d by a moderator.')
            return

        if int(pargs['char_id']) != client.char_id:
            return

        delay = client.change_music_cd()
        if delay:
            client.send_ooc(f'You changed song too many times recently. Please try again '
                            f'after {Constants.time_format(delay)}.')
            return

        try:
            client.area.play_track(pargs['name'], client, raise_if_not_found=True,
                                   reveal_sneaked=True, pargs=pargs)
        except ServerError.MusicNotFoundError:
            client.send_ooc(f'Unrecognized area or music `{pargs["name"]}`.')
        except ServerError:
            return
    except (ClientError, PartyError) as ex:
        client.send_ooc(ex)

    client.last_active = Constants.get_time()


def net_cmd_rt(client: ClientManager.Client, pargs: Dict[str, Any]):
    """ Plays the Testimony/CE animation.

    RT#<type:string>#%

    """

    if client.is_muted:  # Checks to see if the client has been muted by a mod
        client.send_ooc('You have been muted by a moderator.')
        return
    if not client.is_staff() and client.area.lobby_area:
        client.send_ooc('Judge buttons are disabled in this area.')
        return

    name = pargs['name']

    for target in client.area.clients:
        target.send_splash(name=name)
    client.area.add_to_judgelog(client, f'used judge button {name}.')
    logger.log_server(f'[{client.area.id}][{client.get_char_name()}] used judge '
                      f'button {name}.', client)
    client.last_active = Constants.get_time()


def net_cmd_hp(client: ClientManager.Client, pargs: Dict[str, Any]):
    """ Sets the penalty bar.

    HP#<type:int>#<new_value:int>#%

    """

    if client.is_muted:  # Checks to see if the client has been muted by a mod
        client.send_ooc("You have been muted by a moderator")
        return

    try:
        side, health = pargs['side'], pargs['health']
        client.area.change_hp(side, health)
        info = f'changed penalty bar {side} to {health}.'
        client.area.add_to_judgelog(client, info)
        logger.log_server(f'[{client.area.id}]{client.get_char_name()} changed HP '
                          f'({side}) to {health}.', client)
    except AreaError:
        pass
    client.last_active = Constants.get_time()


def net_cmd_pe(client: ClientManager.Client, pargs: Dict[str, Any]):
    """ Adds a piece of evidence.

    PE#<name: string>#<description: string>#<image: string>#%

    """

    # evi = Evidence(args[0], args[1], args[2], client.pos)
    client.area.evi_list.add_evidence(client, pargs['name'], pargs['description'], pargs['image'],
                                      'all')
    client.area.broadcast_evidence_list()
    client.last_active = Constants.get_time()


def net_cmd_de(client: ClientManager.Client, pargs: Dict[str, Any]):
    """ Deletes a piece of evidence.

    DE#<id: int>#%

    """

    client.area.evi_list.del_evidence(client, client.evi_list[int(pargs['evi_id'])])
    client.area.broadcast_evidence_list()
    client.last_active = Constants.get_time()


def net_cmd_ee(client: ClientManager.Client, pargs: Dict[str, Any]):
    """ Edits a piece of evidence.

    EE#<id: int>#<name: string>#<description: string>#<image: string>#%

    """

    evi = (pargs['name'], pargs['description'], pargs['image'], 'all')

    client.area.evi_list.edit_evidence(client, client.evi_list[int(pargs['evi_id'])], evi)
    client.area.broadcast_evidence_list()
    client.last_active = Constants.get_time()


def net_cmd_zz(client: ClientManager.Client, pargs: Dict[str, Any]):
    """ Sent on mod call.

    """

    if client.is_muted:  # Checks to see if the client has been muted by a mod
        client.send_ooc('You have been muted by a moderator.')
        return
    if not client.can_call_mod():
        client.send_ooc('You must wait 30 seconds between mod calls.')
        return

    client.send_ooc('You have called for a moderator.')
    current_time = time.strftime("%H:%M", time.localtime())
    message = (f'[{current_time}] {client.get_char_name()} ({client.get_ip()}) '
               f'called for a moderator in {client.area.name} ({client.area.id}).')

    for target in client.server.get_clients():
        if target.is_officer():
            target.send_command_dict('ZZ', {
                'message': message
                })

    client.set_mod_call_delay()
    logger.log_server(f'[{client.get_ip()}][{client.area.id}]'
                        f'{client.get_char_name()} called a moderator.')


def net_cmd_sp(client: ClientManager.Client, pargs: Dict[str, Any]):
    """
    Set position packet.
    """

    client.change_position(pargs['position'])


def net_cmd_sn(client: ClientManager.Client, pargs: Dict[str, Any]):
    """
    Set showname packet.
    """

    if client.showname == pargs['showname']:
        return

    try:
        client.command_change_showname(pargs['showname'], False)
    except ClientError as exc:
        client.send_ooc(exc)


def net_cmd_chrini(client: ClientManager.Client, pargs: Dict[str, Any]):
    """
    Char.ini information
    """

    client.change_character_ini_details(pargs['actual_folder_name'],
                                        pargs['actual_character_showname'])


def net_cmd_re(self, _):
    # Ignore packet
    return


def net_cmd_charscheck(client: ClientManager.Client, pargs: Dict[str, Any]):
    """
    Character availability request.
    """

    client.refresh_visible_char_list()

def net_cmd_fs(client: ClientManager.Client, pargs: Dict[str, Any]):
    """
    Files set.
    """

    client.change_files(pargs['url'])


def net_cmd_pw(self, _):
    # Ignore packet
    # For now, TsuserverDR will not implement a character password system
    # However, so that it stops raising errors for clients, an empty method is implemented
    # Well, not empty, there are these comments which makes it not empty
    # but not code is run.
    return
