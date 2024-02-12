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

# possible keys: ip, OOC, id, cname, ipid, hdid

import collections
import datetime
import random
import hashlib
import string
import time

from server import logger
from server.constants import Constants, FadeOption, TargetType
from server.exceptions import ArgumentError, AreaError, ClientError, HubError, MusicError, ServerError, TaskError
from server.exceptions import PartyError, ZoneError, TrialError, NonStopDebateError
from server.client_manager import ClientManager
from server.yaml_downloader import Downloader

from typing import Union


# <parameter_name>: required parameter
# {parameter_name}: optional parameter

# (STAFF ONLY): need to be logged in as GM, CM or mod
# (OFFICER ONLY): need to be logged in as CM or mod


def ooc_cmd_download_yaml(client: ClientManager.Client, arg: str):
    Constants.assert_command(client, arg, is_mod=True, parameters='=3')
    args = arg.split()
    yaml_downloader = Downloader(args[0].strip(), args[1].lower().strip(), args[2].strip())

    if not yaml_downloader.validate():
        client.send_ooc("Download Failed. Check your dir_type and link again."
                        "\n- It must be either (area, bg, char, music)."
                        "\n- It must be a YAML file.")

    else:
        client.send_ooc("Downloading YAML...")
        if yaml_downloader.download():
            client.send_ooc("[!] YAML Downloaded.")

        else:
            client.send_ooc("Download Failed. Check your dir_type and link again."
                            "\n- It must be either (area, bg, char, music)."
                            "\n- It must be a YAML file.")


def ooc_cmd_summon_all(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY+VARYING REQUIREMENTS)
    Summons EVERYONE except Staff to an area within the hub by using the
    /summon command and moving them to a specific given area ID.
    Area ID is the mandatory argument and this command requires only one.
    All rules of /summon applies here, read ooc_cmd_summon for more details.

    Note, again, this summons EVERYONE BUT the Staff, so be wary of this command.

    SYNTAX
    /summon_all {target_area}

    PARAMETERS
    {target_area}: Intended area to summon the user(s) to, by area ID or name

    EXAMPLES
    Assuming you want them to move to area 5...
    /summon_all 5
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')
    areas = client.hub.area_manager.get_areas()
    move_clients = list()
    for area in areas:
        for area_client in area.clients:
            if not area_client.is_staff():
                move_clients.append(area_client.id)

    for moving_client_id in move_clients:
        ooc_cmd_summon(client=client, arg=f"{moving_client_id} {arg}")

    client.send_ooc("Summoned User(s) to Area " + arg)


def ooc_cmd_summon_rpers(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY+VARYING REQUIREMENTS)
    Summons EVERYONE with the is_rping attribute to an area within the hub by using the
    /summon command and moving them to a specific given area ID.
    Area ID is the mandatory argument and this command requires only one.
    All rules of /summon applies here, read ooc_cmd_summon for more details.

    Note, again, this summons EVERYONE BUT the Staff, so be wary of this command.

    SYNTAX
    /summon_all {target_area}

    PARAMETERS
    {target_area}: Intended area to summon the user(s) to, by area ID or name

    EXAMPLES
    Assuming you want them to move to area 5...
    /summon_all 5
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')
    areas = client.hub.area_manager.get_areas()
    move_clients = list()
    for area in areas:
        for area_client in area.clients:
            if area_client.is_rping:
                move_clients.append(area_client.id)

    for moving_client_id in move_clients:
        ooc_cmd_summon(client=client, arg=f"{moving_client_id} {arg}")

    client.send_ooc("Summoned User(s) to Area " + arg)


def ooc_cmd_get_rpers(client: ClientManager.Client, arg: str):
    """For GMs to look for players on the fly."""
    Constants.assert_command(client, arg, is_staff=True, parameters='=0')
    areas = client.hub.area_manager.get_areas()
    _clients = list()
    for area in areas:
        for area_client in area.clients:
            if area_client.is_rping:
                _clients.append(area_client)

    data_string = f"== Player Data =="
    if not _clients:
        _str = "\n-> No one is roleplaying..."
        data_string += _str

    else:
        for player_data in _clients:
            _str = f"\n[{player_data.id}] {player_data.displayname} ({player_data.name})\n" \
                   f"-> Area {player_data.area.id}: {player_data.area.name}"
            data_string += _str

    client.send_ooc(data_string)


def ooc_cmd_rping(client: ClientManager.Client, arg: str):
    """Marks you as a roleplayer for various features for GMing."""

    Constants.assert_command(client, arg, parameters='=0')
    client.is_rping = not client.is_rping
    status = {False: 'off', True: 'on'}

    client.send_ooc(f'You turned Roleplay Mode {status[client.is_rping]}.')


def ooc_cmd_getmusic(client: ClientManager.Client, arg: str):
    Constants.assert_command(client, arg, parameters='=0')
    client.area.play_current_track(only_for=[client], force_same_restart=-1, has_clientside_music_looping=True)
    client.send_ooc(f'Now Playing Current Area Music: {client.area.current_music}')


def ooc_cmd_v20r(client: ClientManager.Client, arg: str):
    Constants.assert_command(client, arg, parameters='=2', split_commas=True)
    import random

    successes = 0
    dice, difficulty_value = arg.split(",")
    try:
        dice_value, dice_sides = dice.split("d")
        dice_value, dice_sides = int(dice_value.strip()), int(dice_sides.strip())
        difficulty_value = int(difficulty_value.strip())
    except ValueError:
        raise ClientError("Please input valid arguments. \nExample: /v20r 2d10, 6")

    roll = [random.randint(1, dice_sides) for _ in range(dice_value)]
    for number in roll:
        if number >= difficulty_value:
            successes += 1

    roll_message = f"rolled {roll} out of {dice_sides}. Your successes are: {successes}"
    client.send_ooc('You {}.'.format(roll_message))
    client.send_ooc_others('{} {}.'.format(
        client.displayname, roll_message), in_area=True)
    client.send_ooc_others('(X) {} [{}] {} in {} ({}).'
                           .format(client.displayname, client.id, roll_message,
                                   client.area.name, client.area.id),
                           is_zstaff_flex=client.area, in_area=False,
                           pred=lambda c: c.get_foreign_rolls)
    client.add_to_dicelog(roll_message + '.')
    client.area.add_to_dicelog(client, roll_message + '.')
    logger.log_server('[{}][{}]Used /roll and got {} out of {}.'
                      .format(client.area.id, client.get_char_name(), roll, dice_sides),
                      client)


def ooc_cmd_v20rp(client: ClientManager.Client, arg: str):
    if not client.area.rollp_allowed and not client.is_staff():
        raise ClientError(
            'This command has been restricted to authorized users only in this area.')

    import random
    Constants.assert_command(client, arg, parameters='=2', split_commas=True)

    successes = 0
    dice, difficulty_value = arg.split(",")
    try:
        dice_value, dice_sides = dice.split("d")
        dice_value, dice_sides = int(dice_value.strip()), int(dice_sides.strip())
        difficulty_value = int(difficulty_value.strip())
    except ValueError:
        raise ClientError("Please input valid arguments. \nExample: /v20r 2d10, 6")

    roll = [random.randint(1, dice_sides) for _ in range(dice_value)]
    for number in roll:
        if number >= difficulty_value:
            successes += 1

    roll_message = f"privately rolled {roll} out of {dice_sides}. Your successes are: {successes}"

    client.send_ooc('You {}.'.format(roll_message))
    client.send_ooc_others(
        'Someone rolled.', is_zstaff_flex=False, in_area=True)
    client.send_ooc_others('(X) {} [{}] {}.'.format(client.displayname, client.id, roll_message),
                           is_zstaff_flex=True, in_area=True)
    client.send_ooc_others('(X) {} [{}] {} in {} ({}).'
                           .format(client.displayname, client.id, roll_message, client.area.name,
                                   client.area.id),
                           is_zstaff_flex=client.area, in_area=False,
                           pred=lambda c: c.get_foreign_rolls)

    client.add_to_dicelog(roll_message + '.')
    client.area.add_to_dicelog(client, roll_message + '.')

    salt = ''.join(random.choices(
        string.ascii_uppercase + string.digits, k=16))
    encoding = hashlib.sha1(
        (str(roll) + salt).encode('utf-8')).hexdigest() + '|' + salt
    logger.log_server('[{}][{}]Used /rollp and got {} out of {}.'
                      .format(client.area.id, client.get_char_name(), encoding, dice_sides), client)


def ooc_cmd_ambient(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sets up the ambient sound effect of the current area. Players in the current area, and players
    that later join the area, will be ordered to play the area ambient sound effect.

    SYNTAX
    /ambient <ambient_name>

    PARAMETERS
    <ambient_name>: Name of the ambient sound effect

    EXAMPLES
    >>> /ambient wind.wav
    Sets the ambient sound effect of the area to `wind.wav`.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='>0')

    client.area.ambient = arg

    for target in client.area.clients:
        target.send_area_ambient(name=arg)

    client.send_ooc(
        f'You have set the ambient sound effect of your area to `{arg}`.')
    client.send_ooc_others(f'The ambient sound effect of your area was set to `{arg}`.',
                           in_area=True, is_zstaff_flex=False)
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] set the ambient sound effect '
                           f'of their area to `{arg}` ({client.area.id}).', is_zstaff_flex=True)


def ooc_cmd_ambient_end(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Clears the ambient sound effect of the current area. Players in the current area will be ordered
    to stop playing the former area ambient sound effect, and players that later join the area will
    not play the former area ambient sound effect.
    Returns an error if no ambient sound effect is playing in the area.

    SYNTAX
    /ambient

    PARAMETERS
    None

    EXAMPLES
    >>> /ambient_end
    Clears the ambient sound effect of the area.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    if not client.area.ambient:
        raise ClientError(
            'There already is no ambient sound effect in your area.')

    client.area.ambient = ''

    for target in client.area.clients:
        target.send_area_ambient(name='')

    client.send_ooc('You have cleared the ambient sound effect of your area.')
    client.send_ooc_others('The ambient sound effect of your area was cleared.', in_area=True,
                           is_zstaff_flex=False)
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] cleared the ambient sound '
                           f'effect of their area ({client.area.id}).', is_zstaff_flex=True)


def ooc_cmd_ambient_info(client: ClientManager.Client, arg: str):
    """
    Displays the current area ambient sound effect.
    Returns an error if no area ambient sound effect is playing.

    SYNTAX
    /ambient_info

    PARAMETERS
    None

    EXAMPLES
    Assuming the ambient sound effect of the current area is `wind.wav`...
    >>> /ambient_info
    Returns 'The current ambient sound effect of your area is `wind.wav`'.
    """
    Constants.assert_command(client, arg, parameters='=0')

    if not client.area.ambient:
        raise ClientError(
            'There already is no ambient sound effect in your area.')

    client.send_ooc(
        f'The current ambient sound effect of your area is `{client.area.ambient}`.')


def ooc_cmd_announce(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Sends an "announcement" to all users in the server, regardless of whether they have global chat
    turned on or off.
    Returns an error if you send an empty message.

    SYNTAX
    /announce <message>

    PARAMETERS
    <message>: Message to be sent

    EXAMPLE
    >>> /announce Hello World
    Sends Hello World to all users in the server.
    """

    try:
        Constants.assert_command(client, arg, is_mod=True, parameters='>0')
    except ArgumentError:
        raise ArgumentError('You cannot send an empty announcement.')

    for c in client.server.get_clients():
        c.send_ooc('=== Announcement ===\r\n{}\r\n=================='.format(arg))
    logger.log_server('[{}][{}][ANNOUNCEMENT]{}.'
                      .format(client.area.id, client.get_char_name(), arg), client)


def ooc_cmd_area(client: ClientManager.Client, arg: str):
    """
    Either lists all areas in the hub or changes your area to a new given area.
    Returns an error if you are unathorized to list all areas, already in the new area, or
    unable to move to the intended new area.

    SYNTAX
    /area
    /area <new_area_id>

    PARAMETERS
    None

    PARAMETERS
    <new_area_id>: ID of the area

    EXAMPLES
    >>> /area
    Lists all areas in the hub.
    >>> /area 1
    Moves you to area 1.
    """

    try:
        Constants.assert_command(client, arg, parameters='<2')
    except ArgumentError:
        raise ArgumentError('Too many arguments. Use /area <id>.')

    args = arg.split()
    # List all areas
    if not args:
        if not client.server.config['announce_areas'] and not client.is_staff():
            raise ClientError('You must be authorized to use the no-parameter version of this '
                              'command.')
        client.send_limited_area_list()

    # Switch to new area
    else:
        try:
            area = client.hub.area_manager.get_area_by_id(int(args[0]))
        except ValueError:
            raise ArgumentError('Area ID must be a number.')
        client.change_area(area, from_party=(client.party is not None))


def ooc_cmd_area_list(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sets the area list of your current hub (what areas exist at any given time).
    If given no arguments, it will return the area list to its original value
    (in config/areas.yaml).
    Clients that do not process 'SM' packets can be in servers that
    use this command without crashing, but they will continue to only see the areas they could see
    when joining.
    Returns an error if the given area list was not found.

    SYNTAX
    /area_list <area_list>

    PARAMETERS
    <area_list>: Name of the intended area list

    EXAMPLES
    >>> /area_list dr1dr2
    Load the "dr1dr2" area list.
    >>> /area_list
    Reset the area list to its original value.
    """

    Constants.assert_command(client, arg, is_staff=True)

    # lists which areas are locked before the reload
    old_locked_areas = [area.name for area in client.hub.area_manager.get_areas()
                        if area.is_locked]

    client.hub.area_manager.command_list_load(client, arg)

    # Every area that was locked before the reload gets warned that their areas were unlocked.
    for area_name in old_locked_areas:
        try:
            area = client.hub.area_manager.get_area_by_name(area_name)
            area.broadcast_ooc('This area became unlocked after the area reload. Relock it using '
                               '/lock.')
        # if no area is found with that name, then an old locked area does not exist anymore, so
        # we do not need to do anything.
        except AreaError:
            pass

    # Every area that was locked before the reload gets warned that their areas were unlocked.
    for area_name in old_locked_areas:
        try:
            area = client.hub.area_manager.get_area_by_name(area_name)
            area.broadcast_ooc('This area became unlocked after the area reload. Relock it using '
                               '/lock.')
        # if no area is found with that name, then an old locked area does not exist anymore, so
        # we do not need to do anything.
        except AreaError:
            pass


def ooc_cmd_area_list_info(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Returns the area list of your current hub.

    SYNTAX
    /area_list_info

    PARAMETERS
    None

    EXAMPLES
    >>> /area_list_info
    May return something like this:
    | $H: The current area list is the custom list `beach`.
    """

    Constants.assert_command(client, arg, is_officer=True, parameters='=0')

    client.hub.area_manager.command_list_info(client)


def ooc_cmd_autoglance(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    Toggles look messages being activated automatically or not to whenever you move,
    or (STAFF ONLY) when a target by client ID moves.

    SYNTAX
    /autoglance
    /autoglance <client_id>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)

    EXAMPLES
    Assuming /autoglance for you and for client 1 is off...
    >>> /autoglance
    Turns autoglance on.
    >>> /autoglance
    Turns autoglance off.
    >>> /autoglance 1
    Turns autoglance for client 1 on.
    >>> /autoglance 1
    Turns autoglance for client 1 off.
    """

    Constants.assert_command(client, arg, parameters='<2')
    if arg and not client.is_staff():
        raise ClientError.UnauthorizedError('You must be authorized to use the one-parameter '
                                            'version of this command.')
    if arg:
        target = Constants.parse_id(client, arg)
    else:
        target = client

    target.autoglance = not target.autoglance
    status = {False: 'off', True: 'on'}

    if client == target:
        client.send_ooc(
            f'You turned {status[client.autoglance]} your autoglance.')
    else:
        client.send_ooc(f'You turned {status[target.autoglance]} the autoglance for '
                        f'{target.displayname} [{target.id}].')
        target.send_ooc(
            f'Your autoglance was turned {status[target.autoglance]}.')
        client.send_ooc_others(f'(X) {client.displayname} [{client.id}] turned '
                               f'{status[target.autoglance]} the autoglance for '
                               f'{target.displayname} [{target.id}] ({client.area.id}).',
                               is_zstaff_flex=True, not_to={target})


def ooc_cmd_autopass(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    Toggles enter/leave messages being sent automatically or not to users in the current area
    whenever you move, or (STAFF ONLY) when a target by client ID moves.
    It will not send those messages if the target is a spectator or sneaking. Altered messages
    will be sent if the area's lights are turned off.

    SYNTAX
    /autopass
    /autopass <client_id>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)

    EXAMPLES
    Assuming /autopass for you and for client 1 is off...
    >>> /autopass
    Turns autopass on.
    >>> /autopass
    Turns autopass off.
    >>> /autopass 1
    Turns autopass for client 1 on.
    >>> /autopass 1
    Turns autopass for client 1 off.
    """

    Constants.assert_command(client, arg, parameters='<2')
    if arg and not client.is_staff():
        raise ClientError.UnauthorizedError('You must be authorized to use the one-parameter '
                                            'version of this command.')
    if arg:
        target = Constants.parse_id(client, arg)
    else:
        target = client

    target.autopass = not target.autopass
    status = {False: 'off', True: 'on'}

    if client == target:
        client.send_ooc(f'You turned {status[client.autopass]} your autopass.')
    else:
        client.send_ooc(f'You turned {status[target.autopass]} the autopass for '
                        f'{target.displayname} [{target.id}].')
        target.send_ooc(f'Your autopass was turned {status[target.autopass]}.')
        client.send_ooc_others(f'(X) {client.displayname} [{client.id}] turned '
                               f'{status[target.autopass]} the autopass for '
                               f'{target.displayname} [{target.id}] ({client.area.id}).',
                               is_zstaff_flex=True, not_to={target})


def ooc_cmd_ban(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Kicks given user by IPID or IP from the server and prevents them from rejoining. Requires
    /unban to undo.
    Returns an error if given identifier does not correspond to a user.

    SYNTAX
    /ban <client_ipid>
    /ban <client_ip>

    PARAMETERS
    <client_ipid>: IPID for the client (number in parentheses in /getarea)
    <client_ip>: user IP

    EXAMPLES
    >>> /ban 1234567890
    Bans the user with IPID 1234567890.
    >>> /ban 127.0.0.1
    Bans the user with IP 127.0.0.1.
    """

    arg = arg.strip()
    Constants.assert_command(client, arg, is_mod=True, parameters='>0')

    # Guesses that any number is an IPID
    # and that any non-numerical entry is an IP address.
    if arg.isdigit():
        # IPID
        idnt = int(arg)
        targets = client.server.client_manager.get_targets(
            client, TargetType.IPID, idnt, False)
    else:
        # IP Address
        idnt = arg
        targets = client.server.client_manager.get_targets(
            client, TargetType.IP, idnt, False)

    # Try and add the user to the ban list based on the given identifier
    client.server.ban_manager.add_ban(idnt)

    # Kick+ban all clients opened by the targeted user.
    if targets:
        for c in targets:
            client.send_ooc(
                'You banned {} [{}/{}].'.format(c.displayname, c.ipid, c.hdid))
            client.send_ooc_others('{} was banned.'.format(c.displayname),
                                   is_officer=False, in_area=True, in_hub=True)
            client.send_ooc_others('{} [{}] banned {} [{}/{}].'
                                   .format(client.name, client.id, c.displayname, c.ipid, c.hdid),
                                   is_officer=True, in_hub=None)
            c.disconnect()

    plural = 's were' if len(targets) != 1 else ' was'
    client.send_ooc('You banned `{}`. As a result, {} client{} kicked as well.'
                    .format(idnt, len(targets), plural))
    client.send_ooc_others('{} banned `{}`. As a result, {} client{} kicked as well.'
                           .format(client.name, idnt, len(targets), plural),
                           is_officer=True, in_hub=None)
    logger.log_server('Banned {}.'.format(idnt), client)


def ooc_cmd_banhdid(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Similar to /ban (kicks given user from the server if they are there and prevents them from
    rejoining), but the identifier must be an HDID. It does not require the user to be online.
    Requires /unbanhdid to undo.
    Returns an error if given identifier does not correspond to a user, or if the target is already
    banned.

    SYNTAX
    /banhdid <client_hdid>

    PARAMETERS
    <client_hdid>: User HDID (available in server logs and through a mod /whois)

    EXAMPLES
    >>> /banhdid abcd1234
    Bans the user with HDID abcd1234.
    """

    Constants.assert_command(client, arg, is_mod=True, parameters='=1')

    if arg not in client.server.hdid_list:
        raise ClientError('Unrecognized HDID {}.'.format(arg))

    # This works by banning one of the IPIDs the user is associated with. The way ban handling
    # works is that the server keeps track of all the IPIDs a user has logged in with their HDID
    # and checks on joining if any of those IPIDs was banned in the past. If that is the case,
    # then the server assumes that player is banned, even if they have changed IPIDs in the meantime

    # Thus, banning one IPID is sufficient, so check if any associated IPID is already banned.
    for ipid in client.server.hdid_list[arg]:
        if client.server.ban_manager.is_banned(ipid):
            raise ClientError(f'User is already banned (banned IPID: {ipid}).')

    identifier = random.choice(client.server.hdid_list[arg])
    # Try and add the user to the ban list based on the given identifier
    client.server.ban_manager.add_ban(identifier)

    # Try and kick the user from the server, as well as announce their ban.
    targets = client.server.client_manager.get_targets(
        client, TargetType.HDID, arg, False)

    # Kick+ban all clients opened by the targeted user.
    if targets:
        for c in targets:
            client.send_ooc(
                'You HDID banned {} [{}/{}].'.format(c.displayname, c.ipid, c.hdid))
            client.send_ooc_others('{} was banned.'.format(c.displayname), is_officer=False,
                                   in_area=True, in_hub=True)
            client.send_ooc_others('{} [{}] HDID banned {} [{}/{}].'
                                   .format(client.name, client.id, c.displayname, c.ipid, c.hdid),
                                   is_officer=True, in_hub=None)
            c.disconnect()

    plural = 's were' if len(targets) != 1 else ' was'
    client.send_ooc('You banned HDID `{}`. As a result, {} client{} kicked as well.'
                    .format(arg, len(targets), plural))
    client.send_ooc_others('{} [{}] banned HDID `{}`. As a result, {} client{} kicked as well.'
                           .format(client.name, client.id, arg, len(targets), plural),
                           is_officer=True, in_hub=None)
    logger.log_server('HDID-banned {}.'.format(identifier), client)


def ooc_cmd_bg(client: ClientManager.Client, arg: str):
    """
    Changes the background of the current area.
    Returns an error if area background is locked and you are unathorized or if the sought
    background does not exist.

    SYNTAX
    /bg <background_name>

    PARAMETERS
    <background_name>: New background name, possibly with spaces (e.g. Principal's Room)

    EXAMPLES
    >>> /bg Principal's Room
    Changes background to Principal's Room
    """

    try:
        Constants.assert_command(client, arg, parameters='>0')
    except ArgumentError:
        raise ArgumentError('You must specify a name. Use /bg <background>.')
    if not client.is_mod and client.area.bg_lock:
        raise AreaError("This area's background is locked.")

    client.area.change_background(arg, validate=not (
            client.is_staff() or client.area.cbg_allowed))
    client.area.broadcast_ooc('{} changed the background to {}.'
                              .format(client.displayname, arg))
    logger.log_server('[{}][{}]Changed background to {}'
                      .format(client.area.id, client.get_char_name(), arg), client)


def ooc_cmd_bg_list(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sets the background list of your current hub (what backgrounds areas may normally use at any
    given time).
    If given no arguments, it will return the background list to its original value
    (in config/backgrounds.yaml).
    Returns an error if the given background list name included relative directories,
    was not found, caused an OS error when loading, or raised a YAML or asset syntax error when
    loading.

    SYNTAX
    /bg_list <bg_list>

    PARAMETERS
    <bg_list>: Name of the intended background list

    EXAMPLES
    >>> /bg_list beach
    Load the "beach" background list.
    >>> /bg_list
    Reset the background list to its original value.
    """

    Constants.assert_command(client, arg, is_staff=True)

    client.hub.background_manager.command_list_load(client, arg)


def ooc_cmd_bg_list_info(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Returns the background list of your current hub.

    SYNTAX
    /bg_list_info

    PARAMETERS
    None

    EXAMPLES
    >>> /bg_list_info
    May return something like this:
    | $H: The current background list is the custom list `custom`.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    client.hub.background_manager.command_list_info(client)


def ooc_cmd_bglock(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Toggles background changes by non-mods in the current area being allowed/disallowed.

    SYNTAX
    /bglock

    PARAMETERS
    None

    EXAMPLES
    Assuming the current area's background is unlocked
    >>> /bglock
    Locks the background.
    >>> /bglock
    Unlocks the background.
    """

    Constants.assert_command(client, arg, is_mod=True, parameters='=0')

    client.area.bg_lock = not client.area.bg_lock
    client.area.broadcast_ooc('A mod has set the background lock to {}.'
                              .format(client.area.bg_lock))
    logger.log_server('[{}][{}]Changed bglock to {}'
                      .format(client.area.id, client.get_char_name(), client.area.bg_lock), client)


def ooc_cmd_bg_period(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Changes the background of the current area associated with the given period.
    Returns an error if area background is locked and you are unathorized or if the sought
    background does not exist.

    SYNTAX
    /bg_period <period_name> <background_name>

    PARAMETERS
    <period_name>: Period name
    <background_name>: New background name, possibly with spaces (e.g. Principal's Room)

    EXAMPLES
    >>> /bg_period night Beach (night)
    Changes background to Beach (night) whenever the area has a night period active.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='>1')
    if not client.is_mod and client.area.bg_lock:
        raise AreaError("This area's background is locked.")

    args = arg.split()
    tod_name = args[0]
    bg_name = ' '.join(args[1:])

    client.area.change_background_tod(bg_name, tod_name, validate=False)
    client.send_ooc(f'You changed the background associated with period `{tod_name}` to '
                    f'`{bg_name}`.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] changed the background '
                           f'associated with period `{tod_name}` to `{bg_name}`.',
                           is_zstaff_flex=True)
    logger.log_server('[{}][{}]Changed background associated with period `{}` to {}'
                      .format(client.area.id, client.get_char_name(), tod_name, bg_name), client)


def ooc_cmd_bg_period_end(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Removes the background of the current area associated with the given period
    Returns an error if area background is locked and you are unathorized or if the sought
    background does not exist.

    SYNTAX
    /bg_period_end <period_name>

    PARAMETERS
    <period_name>: Period name

    EXAMPLES
    >>> /bg_period_end night
    Removes the background associated with the night period of the current area.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')
    if not client.is_mod and client.area.bg_lock:
        raise AreaError("This area's background is locked.")

    client.area.change_background_tod('', arg, validate=False)
    client.send_ooc(
        f'You removed the background associated with period `{arg}`.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] removed the background '
                           f'associated with period `{arg}`.',
                           is_zstaff_flex=True)
    logger.log_server('[{}][{}]Removed background associated with period `{}`'
                      .format(client.area.id, client.get_char_name(), arg), client)


def ooc_cmd_bilock(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    Changes the passage status between given areas by name or ID. Passages are unidirectional, so
    to change a passage in just one direction, use /unilock instead.
    If given one area, it will change the passage status between the current area and the given one.
    If given two areas instead, it  will change the passage status between them (but requires
    staff role to use).
    Returns an error if you are unauthorized to create new passages or change existing ones in
    any of the relevant areas. In particular, non-staff members are not allowed to create passages
    that did not exist when the areas were loaded or that a staff member did not create before.

    SYNTAX
    /bilock <target_area>
    /bilock <target_area_1>, <target_area_2>

    PARAMETERS
    <target_area>: Area whose passage status with the current area will be changed.
    <target_area_1>: Area whose passage status with <target_area_2> will be changed.
    <target_area_2>: Area whose passage status with <target_area_1> will be changed.

    EXAMPLES
    Assuming you are in area 0 when executing these commands and originally the only existing
    passage lock is from area 1 'Class Trial Room' to area 2 'Class Trial Room, 2'...
    >>> /bilock Class Trial Room
    Locks the passage between area 0 and Class Trial Room.
    >>> /bilock 1, 2
    Unlocks the passage from Class Trial Room to Class Trial Room, 2; and locks it from Class Trial
    Room, 2 to Class Trial Room.
    >>> /bilock Class Trial Room,\ 2, 0
    Locks the passage in both directions between areas 0 and Class Trial Room, 2 (note the ,\ in
    the command).
    """

    Constants.assert_command(client, arg, parameters='&1-2', split_commas=True)
    areas = arg.split(', ')
    if len(areas) == 2 and not client.is_staff():
        raise ClientError('You must be authorized to use the two-parameter version of this '
                          'command.')

    areas = Constants.parse_two_area_names(client, areas, area_duplicate=False,
                                           check_valid_range=False)
    now_reachable = client.hub.area_manager.change_passage_lock(client, areas, bilock=True,
                                                                change_passage_visibility=False)

    status = {True: 'unlocked', False: 'locked'}
    now0, now1 = status[now_reachable[0]], status[now_reachable[1]]
    name0, name1 = areas[0].name, areas[1].name

    if now_reachable[0] == now_reachable[1]:
        client.send_ooc(
            'You have {} the passage between {} and {}.'.format(now0, name0, name1))
        client.send_ooc_others('(X) {} [{}] has {} the passage between {} and {} ({}).'
                               .format(client.displayname, client.id, now0,
                                       name0, name1, client.area.id),
                               is_zstaff_flex=True)
        logger.log_server('[{}][{}]Has {} the passage between {} and {}.'
                          .format(client.area.id, client.get_char_name(), now0, name0, name1))

    else:
        client.send_ooc('You have {} the passage from {} to {} and {} it the other way around.'
                        .format(now0, name0, name1, now1))
        client.send_ooc_others('(X) {} [{}] has {} the passage from {} and {} and {} it the other '
                               'way around ({}).'
                               .format(client.displayname, client.id, now0,
                                       name0, name1, now1, client.area.id),
                               is_zstaff_flex=True)
        logger.log_server('[{}][{}]Has {} the passage from {} to {} and {} it the other way around.'
                          .format(client.area.id, client.get_char_name(), now0, name0, name1, now1))


def ooc_cmd_bilockh(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Similar to /bilock. However, passages that are locked in this way are hidden from area lists
    and /minimap; and passages that are unlocked are revealed in area lists and /minimap.

    SYNTAX
    /bilockh <target_area>
    /bilockh <target_area_1>, <target_area_2>

    PARAMETERS
    <target_area>: Area whose passage status with the current area will be changed.
    <target_area_1>: Area whose passage status with <target_area_2> will be changed.
    <target_area_2>: Area whose passage status with <target_area_1> will be changed.

    EXAMPLES
    Assuming you are in area 0 when executing these commands and originally the only existing
    passage lock is from area 1 'Class Trial Room' to area 2 'Class Trial Room, 2'...
    >>> /bilockh Class Trial Room
    Locks the passage between area 0 and Class Trial Room.
    >>> /bilockh 1, 2
    Unlocks the passage from Class Trial Room to Class Trial Room, 2; and locks it from Class Trial
    Room, 2 to Class Trial Room.
    >>> /bilockh Class Trial Room,\ 2, 0
    Locks the passage in both directions between areas 0 and Class Trial Room, 2 (note the ,\ in
    the command.
    """

    Constants.assert_command(
        client, arg, parameters='&1-2', is_staff=True, split_commas=True)

    areas = Constants.parse_two_area_names(client, arg.split(', '), area_duplicate=False,
                                           check_valid_range=False)
    now_reachable = client.hub.area_manager.change_passage_lock(client, areas, bilock=True,
                                                                change_passage_visibility=True)

    status = {True: 'unlocked and revealed', False: 'locked and hid'}
    now0, now1 = status[now_reachable[0]], status[now_reachable[1]]
    name0, name1 = areas[0].name, areas[1].name

    if now_reachable[0] == now_reachable[1]:
        client.send_ooc(
            'You have {} the passage between {} and {}.'.format(now0, name0, name1))
        client.send_ooc_others('(X) {} [{}] has {} the passage between {} and {} ({}).'
                               .format(client.displayname, client.id, now0,
                                       name0, name1, client.area.id),
                               is_zstaff_flex=True)
        logger.log_server('[{}][{}]Has {} the passage between {} and {}.'
                          .format(client.area.id, client.get_char_name(), now0, name0, name1))

    else:
        client.send_ooc('You have {} the passage from {} to {} and {} it the other way around.'
                        .format(now0, name0, name1, now1))
        client.send_ooc_others('(X) {} [{}] has {} the passage from {} and {} and {} it the other '
                               'way around ({}).'
                               .format(client.displayname, client.id, now0,
                                       name0, name1, now1, client.area.id),
                               is_zstaff_flex=True)
        logger.log_server('[{}][{}]Has {} the passage from {} to {} and {} it the other way around.'
                          .format(client.area.id, client.get_char_name(), now0, name0, name1, now1))


def ooc_cmd_blind(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Changes the blind status of a user by client ID.
    Blind players will receive no character sprites nor background with IC messages and cannot
    use "visual" commands such as /look, /getarea, etc.
    Immediately after blinding/unblinding, the target will receive sense-appropiate blood
    notifications in the area if needed (e.g. players bleeding, blood trails, etc.).
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /blind <client_id>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)

    EXAMPLES
    Assuming user with client ID 1 starts sighted...
    >>> /blind 1
    Blinds that player.
    >>> /blind 1
    Unblinds that player.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')
    target = Constants.parse_id(client, arg)

    status = {False: 'unblinded', True: 'blinded'}
    new_blind = not target.is_blind

    if client != target:
        client.send_ooc('You have {} {} [{}].'
                        .format(status[new_blind], target.displayname, target.id))
        target.send_ooc('You have been {}.'.format(status[new_blind]))
        target.send_ooc_others('(X) {} [{}] has {} {} [{}] ({}).'
                               .format(client.displayname, client.id, status[new_blind],
                                       target.displayname, target.id, target.area.id),
                               not_to={client}, is_zstaff_flex=True)
    else:
        client.send_ooc('You have {} yourself.'.format(status[new_blind]))
        client.send_ooc_others('(X) {} [{}] has {} themselves ({}).'
                               .format(client.displayname, client.id, status[new_blind],
                                       client.area.id),
                               is_zstaff_flex=True)

    target.change_blindness(new_blind)


def ooc_cmd_blockdj(client: ClientManager.Client, arg: str):
    """ (OFFICER ONLY)
    Revokes the ability of a user by client ID (number in brackets) or IPID (number in
    parentheses) to change music.
    If given IPID, it will affect all clients opened by the target. Otherwise, it will just affect
    the given client.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /blockdj <client_id>
    /blockdj <client_ipid>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    EXAMPLES
    >>> /blockdj 1
    Revokes DJ permissions to the user with client ID 1.
    >>> /blockdj 1234567890
    Revokes DJ permissions to all clients opened by the user with IPID 1234567890.
    """

    Constants.assert_command(client, arg, is_officer=True, parameters='=1')

    # Block DJ permissions to matching targets
    for c in Constants.parse_id_or_ipid(client, arg):
        c.is_dj = False
        logger.log_server(
            'Revoked DJ permissions to {}.'.format(c.ipid), client)
        client.area.broadcast_ooc(
            '{} had their DJ permissions revoked.'.format(c.displayname))


def ooc_cmd_bloodtrail(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Toggles a user by client ID leaving a blood trail wherever they go or not. OOC announcements
    are made to players joining an area regarding the existence of a blood trail and where it leads
    to. Turning off a user leaving a blood trail does not clean the blood in the area. For that,
    use /bloodtrail_clean.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /bloodtrail <client_id>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)

    EXAMPLE
    Assuming a user with client ID 0 starts without leaving a blood trail
    >>> /bloodtrail 0
    This user will now leave a blood trail wherever they go.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')
    target = Constants.parse_id(client, arg)

    status = {False: 'no longer', True: 'now'}
    status2 = {False: 'stop', True: 'start'}
    target.is_bleeding = not target.is_bleeding

    if target.is_bleeding:
        target.area.bleeds_to.add(target.area.name)

    target.send_ooc('You are {} bleeding.'.format(status[target.is_bleeding]))
    if target.is_visible and target.area.lights and target.area == client.area:
        connector = ''
    else:
        connector = '(X) '

    if target != client:
        client.send_ooc('{}You made {} [{}] {} bleeding.'
                        .format(connector, target.displayname, target.id,
                                status2[target.is_bleeding]))
        target.send_ooc_others('(X) {} [{}] made {} {} bleeding ({}).'
                               .format(client.displayname, client.id, target.displayname,
                                       status2[target.is_bleeding], target.area.id),
                               is_zstaff_flex=True, not_to={client})
    else:
        target.send_ooc_others('(X) {} [{}] made themselves {} bleeding ({}).'
                               .format(client.displayname, client.id, status2[target.is_bleeding],
                                       target.area.id),
                               is_zstaff_flex=True, not_to={client})

    target.area_changer.notify_others_blood(target, target.area, target.displayname,
                                            status='stay', send_to_staff=False)


def ooc_cmd_bloodtrail_clean(client: ClientManager.Client, arg: str):
    """
    Cleans the blood trails of the current area or (STAFF ONLY) given areas by area ID or name
    separated by commas. If not given any areas, it will clean the blood trail of the current area.
    Blind non-staff players (or players in a dark area) who attempt to run this command will only
    smear the blood in the area, and regardless of whether there was blood or not, they will
    believe they cleaned it.
    Attempting to clean blood in a clean area or an area where there is someone bleeding will fail.

    SYNTAX
    /bloodtrail_clean {area_1}, {area_2}, ....

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {area_n}: Area ID or name

    EXAMPLES
    Assuming you are in area 0...
    >>> /bloodtrail_clean
    Cleans the blood trail in area 0.
    >>> /bloodtrail_clean 3, Class Trial Room,\ 2
    Cleans the blood trail in area 3 and Class Trial Room, 2 (note the ,\).
    """

    if not arg:
        areas_to_clean = [client.area]
    else:
        if not client.is_staff():
            raise ClientError('You must be authorized to do that.')
        # Make sure the input is valid before starting
        raw_areas_to_clean = arg.split(", ")
        areas_to_clean = set(Constants.parse_area_names(
            client, raw_areas_to_clean))

    successful_cleans = set()
    for area in areas_to_clean:
        if not area.bleeds_to and not area.blood_smeared:
            if client.is_staff() or not (client.is_blind or not area.lights):
                if not arg:
                    mes = 'You could not find any blood in the area.'
                else:
                    mes = 'There is no blood in area {}.'.format(area.name)
                client.send_ooc(mes)
                continue
            # Blind non-staff members will believe they clean the area.

        # Check if someone is currently bleeding in the area,
        # which would prevent it from being cleaned.
        # Yes, you can use for/else in Python, it works exactly like regular flags.
        for c in area.clients:
            if c.is_bleeding:
                mes = ''
                if not client.is_staff() and not client.is_blind:
                    mes = 'You tried to clean the place up, but the blood just keeps coming.'
                elif client.is_staff():
                    mes = ('(X) {} in area {} is still bleeding, so the area cannot be cleaned.'
                           .format(c.displayname, area.name))

                if mes:
                    client.send_ooc(mes)
                    break
        else:
            if (client.is_blind or not area.lights) and not (area.bleeds_to or area.blood_smeared):
                # Poke fun
                client.send_ooc_others('(X) {} [{}] tried to clean the blood trail in the area, '
                                       'unaware that there was no blood to begin with.'
                                       .format(client.displayname, client.id),
                                       in_area=area, is_zstaff_flex=True)
                client.send_ooc_others('{} tried to clean the blood trail in the area, '
                                       'unaware that there was no blood to begin with.'
                                       .format(client.displayname),
                                       in_area=area, to_blind=False, is_zstaff_flex=False,
                                       pred=lambda c: area.lights)
            elif not client.is_staff() and (client.is_blind or not area.lights):
                client.send_ooc_others('{} tried to clean the blood trail in the area, but '
                                       'only managed to smear it all over the place.'
                                       .format(client.displayname),
                                       in_area=area, to_blind=False, is_zstaff_flex=False,
                                       pred=lambda c: area.lights)
                area.blood_smeared = True
            else:
                client.send_ooc_others('{} cleaned the blood trail in your area.'
                                       .format(client.displayname), is_zstaff_flex=False,
                                       in_area=area, to_blind=False, pred=lambda c: area.lights)
                area.bleeds_to = set()
                area.blood_smeared = False
            successful_cleans.add(area.name)

    if successful_cleans:
        if not arg:
            message = client.area.name
            client.send_ooc('You cleaned the blood trail in your area.')
            aname1 = 'your area'
            aname2 = 'area {}'.format(client.area.name)

            if client.is_staff():
                mes = '(X) {} [{}] cleaned the blood trail in {}.'
                client.send_ooc_others(mes.format(client.displayname, client.id, aname1),
                                       is_zstaff_flex=True, in_area=True)
                client.send_ooc_others(mes.format(client.displayname, client.id, aname2),
                                       is_zstaff_flex=True, in_area=False)
            else:
                mes = ''

                if (client.is_blind or not area.lights) and area.blood_smeared:
                    mes = ('(X) {} [{}] tried to clean the blood trail in {}, but as they could '
                           'not see, they only managed to smear it all over the place.')
                elif not (client.is_blind or not area.lights):
                    mes = '(X) {} [{}] cleaned the blood trail in {}.'

                client.send_ooc_others(mes.format(client.displayname, client.id, aname1),
                                       is_zstaff_flex=True, in_area=True)
                client.send_ooc_others(mes.format(client.displayname, client.id, aname2),
                                       is_zstaff_flex=True, in_area=False)

        elif len(successful_cleans) == 1:
            message = str(successful_cleans.pop())
            client.send_ooc(
                'You cleaned the blood trail in area {}.'.format(message))
            client.send_ooc_others('(X) {} [{}] cleaned the blood trail in area {}.'
                                   .format(client.displayname, client.id, message),
                                   is_zstaff_flex=True)
        elif len(successful_cleans) > 1:
            message = Constants.cjoin(successful_cleans)
            client.send_ooc(
                'You cleaned the blood trails in areas {}.'.format(message))
            client.send_ooc_others('(X) {} [{}] cleaned the blood trails in areas {}.'
                                   .format(client.displayname, client.id, message),
                                   is_zstaff_flex=True)
        logger.log_server('[{}][{}]Cleaned the blood trail in {}.'
                          .format(client.area.id, client.get_char_name(), message), client)


def ooc_cmd_bloodtrail_list(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Lists all areas that contain non-empty blood trails and how those look like.

    SYNTAX
    /bloodtrail_list

    PARAMETERS
    None

    EXAMPLES
    >>> /bloodtrail_list
    May return something like this:
    | $H: == Blood trails in this server ==
    | *(0) Basement: Class Trial Room 1, Class Trial Room 3
    | *(1) Class Trial Room 1: Basement
    | *(3) Class Trial Room 3: Basement
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    # Get all areas with blood in them
    areas = sorted([area for area in client.hub.area_manager.get_areas()
                    if len(area.bleeds_to) > 0 or area.blood_smeared],
                   key=lambda x: x.name)

    # No areas found means there are no blood trails
    if not areas:
        raise ClientError('No areas have blood.')

    # Otherwise, build the list of all areas with blood
    info = '== Blood trails in this server =='
    for area in areas:
        area_bleeds_to = sorted(area.bleeds_to)

        if area_bleeds_to == [area.name]:
            pre_info = area.name
        else:
            area_bleeds_to.remove(area.name)
            pre_info = ", ".join(area_bleeds_to)

        if area.blood_smeared:
            pre_info += ' (SMEARED)'

        info += '\r\n*({}) {}: {}'.format(area.id, area.name, pre_info)

    client.send_ooc(info)


def ooc_cmd_bloodtrail_set(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sets (and replaces!) the blood trail of the current area to link all relevant areas by area ID
    or name separated by commas. If not given any areas, it will set the blood trail to be a single
    unconnected pool of blood in the area.
    This command will automatically add the current area to the blood trail if not explicitly
    included, as it does not make too much physical sense to have a trail lead out of an area
    while there being no blood in the current area.
    Requires /bloodtrail_clean to undo.

    SYNTAX
    /bloodtrail_set {area_1}, {area_2}, ....

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {area_n}: Area ID or name

    EXAMPLES
    Assuming you are in area 0...
    >>> /bloodtrail_set
    Sets the blood trail in area 0 to be a single pool of blood.
    >>> /bloodtrail_set 3, Class Trial Room,\ 2
    Sets the blood trail in area 0 to go to area 3 and Class Trial Room, 2 (note the ,\).
    """

    Constants.assert_command(client, arg, is_staff=True)

    if not arg:
        areas_to_link = [client.area]
        message = 'be an unconnected pool of blood'
    else:
        # Make sure the input is valid before starting
        raw_areas_to_link = arg.split(", ")
        areas_to_link = set(Constants.parse_area_names(
            client, raw_areas_to_link) + [client.area])
        message = 'go to {}'.format(Constants.cjoin(
            [a.name for a in areas_to_link], the=True))

    client.send_ooc('Set the blood trail in this area to {}.'.format(message))
    client.send_ooc_others('The blood trail in this area was set to {}.'.format(message),
                           is_zstaff_flex=False, in_area=True, to_blind=False)
    client.send_ooc_others('(X) {} [{}] set the blood trail in area {} to {}.'
                           .format(client.displayname, client.id, client.area.name, message),
                           is_zstaff_flex=True)
    client.area.bleeds_to = {area.name for area in areas_to_link}


def ooc_cmd_bloodtrail_smear(client: ClientManager.Client, arg: str):
    """
    Smears the blood trails of the current area or (STAFF ONLY) given areas by area ID or name
    separated by commas. If not given any areas, it will smear the blood trail of the current area.
    As long as the area has smeared blood, no new blood trails will be recorded and any visual
    indication of preexisting blood trails will be replaced with a 'Smeared' indication for
    non-staff members.
    Returns an error if the area has no blood or its blood is already smeared.

    SYNTAX
    /bloodtrail_smear {area_1}, {area_2}, ....

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {area_n}: Area ID or name

    EXAMPLES
    Assuming you are in area 0...
    >>> /bloodtrail_smear
    Smears the blood trail in area 0.
    >>> /bloodtrail_smear 3, Class Trial Room,\ 2
    Smears the blood trail in area 3 and Class Trial Room, 2 (note the ,\).
    """

    if not arg:
        areas_to_smear = [client.area]
    else:
        if not client.is_staff():
            raise ClientError('You must be authorized to do that.')
        # Make sure the input is valid before starting
        raw_areas_to_smear = arg.split(", ")
        areas_to_smear = set(Constants.parse_area_names(
            client, raw_areas_to_smear))

    successful_smears = set()
    for area in areas_to_smear:
        if not area.bleeds_to and not client.is_staff():
            if not arg:
                mes = 'You could not find any blood in the area.'
            else:
                mes = 'There is no blood in area {}.'.format(area.name)
            client.send_ooc(mes)
            continue

        if area.blood_smeared:
            client.send_ooc(
                'Area {} already has its blood trails smeared.'.format(area.name))
        else:
            if area.lights:
                client.send_ooc_others('{} smeared the blood trail in your area.'
                                       .format(client.displayname), is_zstaff_flex=False,
                                       in_area=area, to_blind=False)
            area.blood_smeared = True
            successful_smears.add(area.name)

    if successful_smears:
        if not arg:
            yarea = 'your area'
            oarea = 'area {}'.format(client.area.name)

            message = client.area.name
            client.send_ooc('You smeared the blood trail in your area.')

            mes = '(X) {} [{}] smeared the blood trail in {}.'
            client.send_ooc_others(mes.format(client.displayname, client.id, yarea),
                                   is_zstaff_flex=True, in_area=True)
            client.send_ooc_others(mes.format(client.displayname, client.id, oarea),
                                   is_zstaff_flex=True, in_area=False)
        elif len(successful_smears) == 1:
            message = str(successful_smears.pop())
            client.send_ooc(
                "You smeared the blood trail in area {}.".format(message))
            client.send_ooc_others('(X) {} [{}] smeared the blood trail in area {}.'
                                   .format(client.displayname, client.id, message),
                                   is_zstaff_flex=True)
        elif len(successful_smears) > 1:
            message = Constants.cjoin(successful_smears)
            client.send_ooc(
                "You smeared the blood trails in areas {}.".format(message))
            client.send_ooc_others('(X) {} [{}] smeared the blood trails in areas {}.'
                                   .format(client.displayname, client.id, message),
                                   is_zstaff_flex=True)
        logger.log_server('[{}][{}]Smeared the blood trail in {}.'
                          .format(client.area.id, client.get_char_name(), message), client)


def ooc_cmd_can_iniswap(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Toggles iniswapping by non-staff in the current area being allowed/disallowed.

    SYNTAX
    /can_iniswap

    PARAMETERS
    None

    EXAMPLES
    Assuming the current area is currently allowing iniswaps...
    >>> /can_iniswap
    Disallows iniswaps in the area.
    >>> /can_iniswap
    Allows iniswaps in the area.
    """

    Constants.assert_command(client, arg, is_mod=True, parameters='=0')

    status = {True: 'now', False: 'no longer'}
    client.area.iniswap_allowed = not client.area.iniswap_allowed

    client.area.broadcast_ooc('Iniswapping is {} allowed in this area.'
                              .format(status[client.area.iniswap_allowed]))
    logger.log_server('[{}][{}]Set iniswapping as {} allowed in the area.'
                      .format(client.area.id, client.get_char_name(),
                              status[client.area.iniswap_allowed]), client)


def ooc_cmd_can_passagelock(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Toggles the ability of using /unilock and /bilock for non-staff members in the current area.
    In particular, the area cannot be used as an argument either implicitly or explicitly in
    /bilock, or implicitly in /unilock if ability is turned off (but can be used explicitly).

    SYNTAX
    /can_passagelock

    PARAMETERS
    None

    EXAMPLE
    Assuming the current area is currently allowing the use of both commands...
    >>> /can_passagelock
    Non-staff members can no longer use /bilock or /unilock.
    >>> /can_passagelock
    Non-staff members can now use /bilock and /unilock again.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    client.area.change_reachability_allowed = not client.area.change_reachability_allowed
    status = {True: 'enabled', False: 'disabled'}

    client.area.broadcast_ooc('A staff member has {} the use of /unilock or /bilock that '
                              'affect this area.'
                              .format(status[client.area.change_reachability_allowed]))


def ooc_cmd_can_rollp(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Toggles private rolls by non-staff in the current area being allowed/disallowed.

    SYNTAX
    /can_rollp

    PARAMETERS
    None

    EXAMPLES
    Assuming the current area is currently allowing the use of private rolls...
    >>> /can_rollp
    Non-staff members can no longer use /rollp.
    >>> /can_rollp
    Non-staff members can now use /rollp.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    client.area.rollp_allowed = not client.area.rollp_allowed
    status = {False: 'disabled', True: 'enabled'}

    client.area.broadcast_ooc('A staff member has {} the use of private roll commands in this '
                              'area.'.format(status[client.area.rollp_allowed]))
    logger.log_server('[{}][{}]{} private roll commands in this area.'
                      .format(client.area.id, client.get_char_name(),
                              status[client.area.rollp_allowed].capitalize()), client)


def ooc_cmd_can_rpgetarea(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Toggles users being able/unable to use /getarea in the current area.

    SYNTAX
    /can_rpgetarea

    PARAMETERS
    None

    EXAMPLES
    Assuming the current area is currently allowing /getarea...
    >>> /can_rpgetarea
    Non-staff members can no longer use /getarea.
    >>> /can_rpgetarea
    Non-staff members can now use /getarea.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    client.area.rp_getarea_allowed = not client.area.rp_getarea_allowed
    status = {False: 'disabled', True: 'enabled'}

    client.area.broadcast_ooc('A staff member has {} the use of /getarea in this area.'
                              .format(status[client.area.rp_getarea_allowed]))
    logger.log_server('[{}][{}]{} /getarea in this area.'
                      .format(client.area.id, client.get_char_name(),
                              status[client.area.rp_getarea_allowed].capitalize()), client)


def ooc_cmd_can_rpgetareas(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Toggles users being able/unable to use /getareas in the current area.

    SYNTAX
    /can_rpgetareas

    PARAMETERS
    None

    EXAMPLES
    Assuming the current area is currently allowing /getareas...
    >>> /can_rpgetareas
    Non-staff members can no longer use /getareas.
    >>> /can_rpgetareas
    Non-staff members can now use /getareas.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    client.area.rp_getareas_allowed = not client.area.rp_getareas_allowed
    status = {False: 'disabled', True: 'enabled'}

    client.area.broadcast_ooc('A staff member has {} the use of /getareas in this area.'
                              .format(status[client.area.rp_getareas_allowed]))
    logger.log_server('[{}][{}]{} /getareas in this area.'
                      .format(client.area.id, client.get_char_name(),
                              status[client.area.rp_getareas_allowed].capitalize()), client)


def ooc_cmd_char_list(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sets the current character list of your current hub (what characters a player may use at any
    given time).
    If given no arguments, it will return the character list to its original value
    (in config/characters.yaml).
    Returns an error if the given character list name included relative directories,
    was not found, caused an OS error when loading, or raised a YAML or asset syntax error when
    loading.

    SYNTAX
    /char_list <char_list>

    PARAMETERS
    <char_list>: Name of the intended character list

    EXAMPLES
    >>> /char_list Transylvania
    Load the "Transylvania" character list.
    >>> /char_list
    Reset the character list to its original value.
    """

    Constants.assert_command(client, arg, is_staff=True)

    client.hub.character_manager.command_list_load(client, arg)


def ooc_cmd_char_list_info(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Returns the character list of your current hub.

    SYNTAX
    /char_list_info

    PARAMETERS
    None

    EXAMPLES
    >>> /char_list_info
    May return something like this:
    | $H: The current character list is the custom list `custom`.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    client.hub.character_manager.command_list_info(client)


def ooc_cmd_charlog(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    List all character details a user by client ID or IPID has had during the session.

    If given IPID, it will obtain the character details log of all the clients opened by the target.
    Otherwise, it will just obtain the log of the given client.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /charlog <client_id>
    /charlog <client_ipid>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    EXAMPLES
    >>> /charlog 1
    For the user with client ID 1, it may return something like this
    | $H: == Character details log of client 1 ==
    | *Sat Jun 1 18:52:32 2021 | Changed character to Phantom_HD
    | *Sat Jun 1 18:52:32 2021 | Changed character ini to Phantom_HD/Phantom
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')

    # Obtain matching targets's character details log
    for c in Constants.parse_id_or_ipid(client, arg):
        info = c.get_charlog()
        client.send_ooc(info)


def ooc_cmd_charselect(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    Opens your the character selection screen
    OR (MOD ONLY) forces another user by identifier to have that screen open, freeing up their
    character in the process.

    SYNTAX
    /charselect
    /charselect {client_id}
    /charselect {client_ipid}

    PARAMETERS
    {client_id}: Client identifier (number in brackets in /getarea).
    {client_ipid}: IPID for the client (number in parentheses in /getarea).

    EXAMPLES
    >>> /charselect
    Open character selection screen for the current player.
    >>> /charselect 1
    Forces open the character selection screen for the user with client ID 1.
    >>> /charselect 1234567890
    Forces open the character selection screen for the user with IPID 1234567890.
    """

    # Open for current user case
    if not arg:
        client.send_ooc('You opened the character select screen.')
        client.char_select()

    # Force open for different user
    else:
        if not client.is_mod:
            raise ClientError('You must be authorized to do that.')

        for c in Constants.parse_id_or_ipid(client, arg):
            client.send_ooc(
                f'You forced {c.displayname} to open the character select screen.')
            if client != c:
                c.send_ooc(
                    'You were forced to open the character select screen.')
            client.send_ooc_others(f'{client.name} [{client.id}] forced {c.displayname} [{c.id}] '
                                   f'to open the character select screen ({c.area.id}).',
                                   not_to={c}, is_officer=True, in_hub=None)
            c.char_select()


def ooc_cmd_char_restrict(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Toggle a character by folder name (not showname!) being able to be used in the current area
    by non-staff members.
    Returns an error if the character name is not recognized.

    SYNTAX
    /char_restrict <char_name>

    PARAMETERS
    <char_name>: Character name to restrict.

    EXAMPLES
    Assuming Phantom_HD is initially unrestricted...
    >>> /char_restrict Phantom_HD
    Restrict the use of Phantom_HD.
    >>> /char_restrict Phantom_HD
    Unrestrict the use of Phantom_HD.
    """

    try:
        Constants.assert_command(client, arg, is_staff=True, parameters='>0')
    except ArgumentError:
        raise ArgumentError('This command takes one character name.')

    if not client.hub.character_manager.is_character(arg):
        raise ArgumentError(
            'Unrecognized character folder name: {}'.format(arg))

    status = {True: 'enabled', False: 'disabled'}
    new_stat = status[arg in client.area.restricted_chars]

    client.send_ooc('You have {} the use of character `{}` in this area.'
                    .format(new_stat, arg))
    client.send_ooc_others('A staff member has {} the use of character {} in this area.'
                           .format(new_stat, arg), is_zstaff_flex=False, in_area=True)
    client.send_ooc_others('(X) {} [{}] has {} the use of character `{}` in area {} ({}).'
                           .format(client.displayname, client.id, new_stat, arg, client.area.name,
                                   client.area.id), is_zstaff=True)

    # If intended character not in area's restriction, add it
    if arg not in client.area.restricted_chars:
        client.area.restricted_chars.add(arg)
        # For all clients using the now restricted character, switch them to some other character.
        for c in client.area.clients:
            if not c.is_staff() and c.get_char_name() == arg:
                try:
                    new_char_id = c.area.get_rand_avail_char_id(
                        allow_restricted=False)
                except AreaError:
                    # Force into spectator mode if all other available characters are taken
                    new_char_id = -1
                c.change_character(new_char_id, announce_zwatch=False)
                c.send_ooc('Your character has been set to restricted in this area by a staff '
                           'member. Switching you to `{}`.'.format(c.get_char_name()))
                c.send_ooc_others('(X) Client {} had their character changed from `{}` to '
                                  '`{}` in your zone as their old character was just '
                                  'restricted in their new area ({}).'
                                  .format(c.id, arg, c.get_char_name(), c.area.id),
                                  is_zstaff_flex=True)
    else:
        client.area.restricted_chars.remove(arg)


def ooc_cmd_chars_restricted(client: ClientManager.Client, arg: str):
    """
    Returns a list of all characters that are restricted in an area.

    SYNTAX
    /chars_restricted

    PARAMETERS
    None

    EXAMPLES
    If only Phantom_HD is restricted in the current area...
    >>> /chars_restricted
    Returns 'Phantom_HD'
    """

    Constants.assert_command(client, arg, parameters='=0')

    info = '== Characters restricted in area {} =='.format(client.area.name)
    # If no characters restricted, print a manual message.
    if len(client.area.restricted_chars) == 0:
        info += '\r\n*No characters restricted.'
    # Otherwise, build the list of all restricted chars.
    else:
        for char_name in client.area.restricted_chars:
            info += '\r\n*{}'.format(char_name)

    client.send_ooc(info)


def ooc_cmd_cid(client: ClientManager.Client, arg: str):
    """
    Returns the client ID of the given target (number in brackets in /getarea), or your own if
    not given a target.
    Returns an error if, given a target identifier, it does not match any identifiers visible to
    you among players in the same area.

    SYNTAX
    /cid <user_ID>

    PARAMETERS
    <user_id>: Either the client ID, character name, edited-to character, custom showname or OOC
    name of the intended recipient.

    EXAMPLES
    If Phantom_HD is in the same area as you, iniswapped to Spam_HD, has client ID 3, has
    showname Phantom and OOC Name ThePhantom
    >>> /cid Phantom_HD
    Returns 'The client ID of Phantom_HD is 3.'
    >>> /cid Spam_HD
    Returns 'The client ID of Spam_HD is 3.'
    >>> /cid 3
    Returns 'The client ID of 3 is 3.'
    >>> /cid Phantom
    Returns 'The client ID of Phantom is 3.'
    >>> /cid ThePhantom
    Returns 'The client ID of ThePhantom is 3.'
    >>> /cid
    Returns 'Your client ID is 0.' (assuming your client ID is actually 0)
    """

    if not arg:
        client.send_ooc('Your client ID is {}.'.format(client.id))
    else:
        cm = client.server.client_manager
        target, _, _ = cm.get_target_public(client, arg, only_in_area=True)
        client.send_ooc('The client ID of {} is {}.'.format(arg, target.id))


def ooc_cmd_cleardoc(client: ClientManager.Client, arg: str):
    """
    Clears the current area's doc.

    SYNTAX
    /cleardoc

    PARAMETERS
    None

    EXAMPLES
    >>> /cleardoc
    Clears the current area's doc.
    """

    Constants.assert_command(client, arg, parameters='=0')

    client.area.broadcast_ooc(
        '{} cleared the doc link.'.format(client.displayname))
    logger.log_server('[{}][{}]Cleared document. Old link: {}'
                      .format(client.area.id, client.get_char_name(), client.area.doc), client)
    client.area.change_doc()


def ooc_cmd_cleargm(client: ClientManager.Client, arg: str):
    """ (OFFICER ONLY)
    Logs out a game master by client ID or all game masters in the server if not given an ID.
    Returns an error if the given identifier does not correspond to a user, if given a target
    they are already not a GM, or if no GMs are currently logged in.

    SYNTAX
    /cleargm {client_id}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {client_id}: Client identifier (number in brackets in /getarea)

    EXAMPLE
    >>> /cleargm
    Logs out all GMs in the server.
    /cleargm 3
    Logs out the client with ID 3 from the GM rank.
    """

    Constants.assert_command(client, arg, is_officer=True)

    gm_list = list()
    if arg:
        targets = [Constants.parse_id(client, arg)]
    else:
        targets = client.server.get_clients()

    for c in targets:
        if c.is_gm:
            gm_list.append('{} [{}]'.format(c.name, c.id))
            c.send_ooc('You are no longer a GM.')
            c.logout()

    if arg:
        target = targets[0]
        if not gm_list:
            raise ClientError(f'Client {target.id} is already not a GM.')
        client.send_ooc(
            f'You have logged out client {client.id} from their GM rank.')
        client.send_ooc_others(f'{client.name} [{client.id}] has logged out {target.name} '
                               f'[{target.id}] from their GM rank.',
                               is_officer=True, in_hub=None)
    else:
        if not gm_list:
            raise ClientError('No GMs are currently connected.')
        output = Constants.cjoin(gm_list, sort=False)
        client.send_ooc(
            f'You have logged out the following clients from their GM rank: {output}.')
        client.send_ooc_others(f'{client.name} [{client.id}] has logged out these clients '
                               f'from their GM rank: {output}.',
                               is_officer=True, in_hub=None)


def ooc_cmd_clock(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sets up a day cycle that will tick one hour every given number of seconds and provide a time
    announcement to a given range of areas. Starting hour is also given. The clock ID is by default
    your client ID. Doing /clock while running an active clock will silently overwrite the old
    clock with the new one.
    Requires /clock_end to undo.
    Returns an error if the given hour start is not a nonnegative number or beyond the indicated
    number of hours in a day, if the number of hours in a day is not a positive integer, or if the
    hour length is not a positive integer.

    SYNTAX
    /clock <area_range_start> <area_range_end> <main_hour_length> <hour_start> {hours_in_day}

    PARAMETERS
    <area_range_start>: Send notifications from this area onwards up to...
    <area_range_end>: Send notifications up to (and including) this area.
    <main_hour_length>: Main length of each ingame hour (in seconds)
    <hour_start>: Starting hour (integer from 0 to 23)

    OPTIONAL PARAMETERS
    {hours_in_day}: Number of hours in a day (by default 24).

    EXAMPLES
    >>> /clock 16 116 900 8
    Starts a 900-second hour clock spanning areas 16 through 116, with starting hour 8 AM.
    >>> /clock 0 5 10 19 15
    Starts a 10-second hour clock of 15 hours spanning areas 0 through 5, with starting hour 7 PM.
    """

    Constants.assert_command(client, arg, is_staff=True,
                             parameters='&4-5', split_spaces=True)

    # Inputs already validated, move on
    args = arg.split(' ')
    if len(args) == 4:
        pre_area_1, pre_area_2, pre_hour_length, pre_hour_start = args
        hours_in_day = 24
    else:
        pre_area_1, pre_area_2, pre_hour_length, pre_hour_start, hours_in_day = args

    areas = Constants.parse_two_area_names(
        client, [pre_area_1, pre_area_2], check_valid_range=True)
    area_1, area_2 = areas[0].id, areas[1].id

    try:
        hour_length = int(pre_hour_length)
        if hour_length <= 0:
            raise ValueError
    except ValueError:
        raise ArgumentError(f'Invalid hour length {pre_hour_length}.')

    try:
        hours_in_day = int(hours_in_day)
        if hours_in_day <= 0:
            raise ValueError
    except ValueError:
        raise ArgumentError(f'Invalid number of hours per day {hours_in_day}.')

    try:
        hour_start = int(pre_hour_start)
        if hour_start < 0 or hour_start >= hours_in_day:
            raise ValueError
    except ValueError:
        raise ArgumentError(f'Invalid hour start {pre_hour_start}.')

    # Code after this assumes input is validated

    # If already existing day cycle. Will overwrite preexisting one
    # But first, make sure normies do not get a new notification.
    normie_notif = not client.server.task_manager.is_task(
        client, 'as_day_cycle')

    client.send_ooc(f'You initiated a day cycle of length {hour_length} seconds per hour in areas '
                    f'{area_1} through {area_2}. The cycle ID is {client.id}.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] initiated a day cycle of '
                           f'length {hour_length} seconds of {hours_in_day} hours in areas '
                           f'{area_1} through {area_2}. The cycle ID is {client.id} '
                           f'({client.area.id}).', is_zstaff_flex=True)
    if normie_notif:
        client.send_ooc_others(f'{client.displayname} initiated a day cycle.',
                               is_zstaff_flex=False, pred=lambda c: area_1 <= c.area.id <= area_2)

    client.server.task_manager.new_task(client, 'as_day_cycle', {
        'area_1': area_1,
        'area_2': area_2,
        'hour_length': hour_length,
        'hour_start': hour_start,
        'hours_in_day': hours_in_day,
        'send_first_hour': normie_notif,
    })


def ooc_cmd_clock_end(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    End the day cycle established by a user by client ID (or own if not given ID)
    Returns an error if the given player has no associated active day cycle.

    SYNTAX
    /clock_end {client_id}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {client_id}: Client identifier (number in brackets in /getarea)

    EXAMPLE
    >>> /clock_end 0
    Cancels the day cycle established by the user with client ID 0.
    """

    Constants.assert_command(client, arg, is_staff=True)

    if not arg:
        arg = str(client.id)

    try:
        c = Constants.parse_id(client, arg)
    except ClientError:
        raise ArgumentError('Client {} is not online.'.format(arg))

    try:
        client.server.task_manager.delete_task(c, 'as_day_cycle')
    except TaskError.TaskNotFoundError:
        raise ClientError(
            'Client {} has not initiated any day cycles.'.format(arg))


def ooc_cmd_clock_pause(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Pauses the day cycle established by a user by client ID (or own if not given an ID).
    Requires /clock_unpause to undo.
    Returns an error if the given player has no associated active day cycle, or if their day cycle
    is already paused.

    SYNTAX
    /clock_pause {client_id}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {client_id}: Client identifier (number in brackets in /getarea)

    EXAMPLE
    >>> /clock_pause 0
    Pauses the day cycle established by the user with client ID 0.
    """

    Constants.assert_command(client, arg, is_staff=True)

    if not arg:
        arg = str(client.id)

    try:
        c = Constants.parse_id(client, arg)
    except ClientError:
        raise ArgumentError('Client {} is not online.'.format(arg))

    try:
        task = client.server.task_manager.get_task(c, 'as_day_cycle')
    except TaskError.TaskNotFoundError:
        raise ClientError(
            'Client {} has not initiated any day cycles.'.format(arg))

    if task.parameters['is_unknown']:
        raise ClientError(
            'You may not pause the day cycle while the time is unknown.')
    if task.parameters['is_paused']:
        raise ClientError('Day cycle is already paused.')

    task.parameters['refresh_reason'] = 'pause'
    client.server.task_manager.force_asyncio_cancelled_error(task)


def ooc_cmd_clock_period(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Adds a period to the day cycle you established. Whenever the day cycle clock ticks
    into a time part of the period after a given hour length of seconds, all clients in the
    affected areas will be ordered to change to that time of day's version of their theme.
    Time of day periods go from their given hour start all the way until the next period.
    If the period name already exists, its hour start will be overwritten.
    If the hour length is not given, it will use the main hour length of the day cycle.
    If some period already starts at the given hour start, its name will be overwritten.
    Returns an error if you have not started a day cycle, or if the hour start is not an integer
    from 0 inclusive to the number of hours in a day set up for the day cycle exclusive, or if given
    an hour length and it is not a positive integer.

    SYNTAX
    /clock_period <name> <hour_start>
    /clock_period <name> {hour_length} <hour_start>

    PARAMETERS
    <name>: Name of the period.
    <hour_start>: Start time of the period.

    OPTIONAL PARAMETERS
    {hour_length}: Length of each ingame hour (in seconds). Defaults to the main hour length.

    EXAMPLE
    Assuming the commands are run in order...
    >>> /clock_period day 8
    Sets up a period that goes from 8 AM to 8 AM.
    >>> /clock_period night 150 22
    Sets up a night period that goes from 10 PM to 8 AM, each hour in the period ticking every 150
    seconds. Day period now goes from 8 AM to 10 PM.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='&2-3')

    try:
        task = client.server.task_manager.get_task(client, 'as_day_cycle')
    except TaskError.TaskNotFoundError:
        raise ClientError('You have not initiated any day cycles.')

    args = arg.split()
    hour_length = task.parameters['main_hour_length']
    hours_in_day = task.parameters['hours_in_day']

    name = args[0].lower()
    pre_hour_start = args[2] if len(args) == 3 else args[1]
    pre_hour_length = args[1] if len(args) == 3 else str(hour_length)

    try:
        hour_start = int(pre_hour_start)
        if not 0 <= hour_start < hours_in_day:
            raise ValueError
    except ValueError:
        raise ArgumentError(f'Invalid period start hour {pre_hour_start}.')

    try:
        hour_length = int(pre_hour_length)
        if hour_length <= 0:
            raise ValueError
    except ValueError:
        raise ArgumentError(f'Invalid period hour length {pre_hour_length}.')

    task.parameters['new_period_start'] = (hour_start, name, hour_length)
    task.parameters['refresh_reason'] = 'period'
    client.server.task_manager.force_asyncio_cancelled_error(task)


def ooc_cmd_clock_period_end(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Removes a previously created period to the day cycle you established.
    If the removed period is the one currently active, the period becomes whatever the new period
    should be using the remaining periods if there are any, or fully deactivated if there are no
    other periods left.
    Returns an error if you have not started a day cycle, or if the period does not exist.

    SYNTAX
    /clock_period_end <name>

    PARAMETERS
    <name>: Name of the period.

    EXAMPLE
    Assuming the commands are run in order...
    >>> /clock_period_end day
    Removes the period called day.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')

    try:
        task = client.server.task_manager.get_task(client, 'as_day_cycle')
    except TaskError.TaskNotFoundError:
        raise ClientError('You have not initiated any day cycles.')

    task.parameters['new_period_start'] = (-1, arg, 0)
    task.parameters['refresh_reason'] = 'period'
    client.server.task_manager.force_asyncio_cancelled_error(task)


def ooc_cmd_clock_set(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Updates the main hour length and current hour of the client's day cycle without restarting it,
    changing its area range or notifying normal players. If the day cycle time was unknown, the
    time is updated in the same manner (effectively taking it out of unknown mode).
    The hour length of any active periods are not modified and have priority over the main hour
    length.
    Returns an error if you have not started a day cycle, or if the hour is not an
    integer from 0 inclusive to the number of hours in a day set up for the day cycle exclusive.

    SYNTAX
    /clock_set <hour_length> <hour>

    PARAMETERS
    <hour_length>: Length of each ingame hour (in seconds)
    <hour>: New hour

    EXAMPLES
    >>> /clock_set 900 8
    Updates the day cycle to be a 900-second hour clock with current time 8 AM.
    >>> /clock_set 10 19
    Updates the day cycle to be a 10-second hour clock with current time 7 PM.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=2')

    try:
        task = client.server.task_manager.get_task(client, 'as_day_cycle')
    except TaskError.TaskNotFoundError:
        raise ClientError('You have not initiated any day cycles.')

    pre_hour_length, pre_hour_start = arg.split(' ')
    try:
        hour_length = int(pre_hour_length)
        if hour_length <= 0:
            raise ValueError
    except ValueError:
        raise ArgumentError('Invalid hour length {}.'.format(pre_hour_length))

    try:
        hour_start = int(pre_hour_start)
        hours_in_day = task.parameters['hours_in_day']
        if hour_start < 0 or hour_start >= hours_in_day:
            raise ValueError
    except ValueError:
        raise ArgumentError('Invalid hour start {}.'.format(pre_hour_start))

    task.parameters['new_day_cycle_args'] = (hour_length, hour_start)
    task.parameters['refresh_reason'] = 'set'
    client.server.task_manager.force_asyncio_cancelled_error(task)


def ooc_cmd_clock_set_hours(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sets up the number of hours a day cycle clock has per day.
    If the new number of hours in a day exceeds the current hour, the hour will be set to 0.
    If there were any periods set to start at an hour beyond the new number of hours in a day, they
    will be removed, and users in the area will be set to an appropriate period if necessary.
    Returns an error if you have not started a day cycle, or if the number is not a positive number.

    SYNTAX
    /clock_set_hours <hours_in_day>

    PARAMETERS
    <hours_in_day>: New number of hours in the day.

    EXAMPLES
    >>> /clock_set_hours 24
    Sets your day cycle to have 24 hours.
    >>> /clock_set_hours 30
    Sets your day cycle to have 30 hours.
    >>> /clock_set_hours 2
    Sets your day cycle to have 2 hours.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')

    try:
        task = client.server.task_manager.get_task(client, 'as_day_cycle')
    except TaskError.TaskNotFoundError:
        raise ClientError('You have not initiated any day cycles.')

    try:
        hours_in_day = int(arg)
        if hours_in_day <= 0:
            raise ValueError
    except ValueError:
        raise ArgumentError(f'Invalid number of hours per day {hours_in_day}.')

    task.parameters['hours_in_day'] = hours_in_day
    task.parameters['refresh_reason'] = 'set_hours'
    client.server.task_manager.force_asyncio_cancelled_error(task)


def ooc_cmd_clock_unknown(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sets the client's day cycle time to unknown. Time does not flow in this mode, and clients in
    the area range will be ordered to switch to their unknown time of day version of their theme.
    Requires /clock_set to undo.
    Returns an error if you have not started a day cycle, or if the time is already unknown.

    SYNTAX
    /clock_unknown

    PARAMETERS
    None

    EXAMPLES
    >>> /clock_unknown
    Set the time to be unknown.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    try:
        task = client.server.task_manager.get_task(client, 'as_day_cycle')
    except TaskError.TaskNotFoundError:
        raise ClientError('You have not initiated any day cycles.')

    if task.parameters['is_unknown']:
        raise ClientError('Your day cycle already has unknown time.')

    task.parameters['refresh_reason'] = 'unknown'
    client.server.task_manager.force_asyncio_cancelled_error(task)


def ooc_cmd_clock_unpause(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Unpauses the day cycle established by a user by client ID (or own if not given an ID).
    Requires /clock_pause to undo.
    Returns an error if the given player has no associated active day cycle, or if their day cycle
    is already unpaused.

    SYNTAX
    /clock_unpause {client_id}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {client_id}: Client identifier (number in brackets in /getarea)

    EXAMPLE
    >>> /clock_unpause 0
    Unpauses the day cycle established by the user with client ID 0.
    """

    Constants.assert_command(client, arg, is_staff=True)

    if not arg:
        arg = str(client.id)

    try:
        c = Constants.parse_id(client, arg)
    except ClientError:
        raise ArgumentError('Client {} is not online.'.format(arg))

    try:
        task = client.server.task_manager.get_task(c, 'as_day_cycle')
    except TaskError.TaskNotFoundError:
        raise ClientError(
            'Client {} has not initiated any day cycles.'.format(arg))

    if task.parameters['is_unknown']:
        raise ClientError(
            'You may not unpause the day cycle while the time is unknown.')
    if not task.parameters['is_paused']:
        raise ClientError('Day cycle is already unpaused.')

    task.parameters['refresh_reason'] = 'unpause'
    client.server.task_manager.force_asyncio_cancelled_error(task)


def ooc_cmd_coinflip(client: ClientManager.Client, arg: str):
    """
    Flips a coin and returns the result. If given a call, it includes the call with the result.

    SYNTAX
    /coinflip {call}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {call}: A call to the coin flip

    EXAMPLES
    If Phantom is running the following...
    >>> /coinflip
    May return something like "Phantom flipped a coin and got tails."
    >>> /coinflip `heads`
    May return something like "Phantom called `heads`, flipped a coin and got heads"
    """

    coin = ['heads', 'tails']
    flip = random.choice(coin)
    if arg:
        mes = '{} called `{}`, flipped a coin and got {}.'.format(
            client.displayname, arg, flip)
    else:
        mes = '{} flipped a coin and got {}.'.format(client.displayname, flip)
    client.area.broadcast_ooc(mes)
    logger.log_server('[{}][{}]Used /coinflip and got {}.'
                      .format(client.area.id, client.get_char_name(), flip), client)


def ooc_cmd_cure(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Cures the target of some of three effects (blindness, deafened, or gagged) as follows:
     For each effect in the cure:
     * If the target is subject to some poison that as one of its effects will cause the effect in
       the future, cancel that part of the poison.
     * If the target is currently experiencing that effect (either as a result of a poison that
       kicked in or being manually set before), remove the effect from the target.
     * If neither is true, do nothing for that effect.
     In particular, cancel that part of the poison and effect from the target if they are subject
     to them.
    Returns an error if the given identifier does not correspond to a user, or if the effects
    contain an unrecognized/repeated character.

    SYNTAX
    /cure <client_id> <effects>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <effects>: Effects to cure (a string consisting of non-case-sensitive 'b', 'd', and/or 'g' in
    some order corresponding to the initials of the supported effects)

    EXAMPLES
    Assuming user with client ID 1 is blind, deafened and gagged and these are run one after the other...
    >>> /cure 1 b
    Cures that user of blindness.
    >>> /cure 1 Bd
    Cures that user of deafedness (note they were not blind).
    >>> /cure 1 gDB
    Cures that user of being gagged (note they were neither deafened or blind).
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=2')
    raw_target, raw_effects = arg.split(' ')
    target = Constants.parse_id(client, raw_target)
    effects = Constants.parse_effects(client, raw_effects)

    sorted_effects = sorted(effects, key=lambda effect: effect.name)
    for effect in sorted_effects:
        # Check if the client is subject to a countdown for that effect
        try:
            client.server.task_manager.delete_task(target, effect.async_name)
        except TaskError.TaskNotFoundError:
            pass  # Do nothing if not subject to one

        if target != client:
            target.send_ooc(
                'You were cured of the effect `{}`.'.format(effect.name))
            client.send_ooc('You cured {} [{}] of the effect `{}`.'
                            .format(target.displayname, target.id, effect.name))
            client.send_ooc_others('(X) {} [{}] cured {} [{}] of the effect `{}` ({}).'
                                   .format(client.displayname, client.id, target.displayname,
                                           target.id, effect.name, client.area.id),
                                   is_zstaff_flex=True, not_to={target})
        else:
            client.send_ooc(
                'You cured yourself of the effect `{}`.'.format(effect.name))
            client.send_ooc_others('(X) {} [{}] cured themselves of the effect `{}` ({}).'
                                   .format(client.displayname, client.id, effect.name,
                                           client.area.id),
                                   is_zstaff_flex=True)

        effect.function(target, False)


def ooc_cmd_currentmusic(client: ClientManager.Client, arg: str):
    """
    Returns the music currently playing in the area, who played it, and its source if available in
    the music list file.
    Returns an error if no music is playing.

    SYNTAX
    /currentmusic

    PARAMETERS
    None

    EXAMPLES
    >>> /currentmusic
    Returns information about the current music.
    """

    Constants.assert_command(client, arg, parameters='=0')

    if not client.area.current_music:
        raise ClientError('There is no music currently playing.')

    current_music = client.area.current_music
    current_music_player = client.area.current_music_player
    current_music_source = client.area.current_music_source
    if current_music_source:
        client.send_ooc(f'The current music is {current_music}, was sourced from '
                        f'{current_music_source}, and was played by {current_music_player}.')
    else:
        client.send_ooc(f'The current music is {current_music} and was played by '
                        f'{current_music_player}.')


def ooc_cmd_deafen(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Changes the deafened status of a user by client ID.
    Deaf players will be unable to read IC messages properly or receive other audio cues from
    commands such as /knock, /scream, etc.
    Immediately after deafening/undeafening, the target will receive sense-appropiate blood
    notifications in the area if needed (e.g. players bleeding while sneaking).
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /deafen <client_id>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)

    EXAMPLES
    Assuming user with client ID 1 is ccurently able to hear...
    >>> /deafen 1
    Deafens that user.
    >>> /deafen 1
    Undeafens that user.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')
    target = Constants.parse_id(client, arg)

    status = {False: 'undeafened', True: 'deafened'}
    new_deaf = not target.is_deaf

    if client != target:
        client.send_ooc('You have {} {} [{}].'
                        .format(status[new_deaf], target.displayname, target.id))
        target.send_ooc('You have been {}.'.format(status[new_deaf]))
        target.send_ooc_others('(X) {} [{}] has {} {} [{}] ({}).'
                               .format(client.displayname, client.id, status[new_deaf],
                                       target.displayname, target.id, target.area.id),
                               is_zstaff_flex=True, not_to={client})
    else:
        client.send_ooc('You have {} yourself.'.format(status[new_deaf]))
        client.send_ooc_others('(X) {} [{}] has {} themselves ({}).'
                               .format(client.displayname, client.id, status[new_deaf],
                                       client.area.id),
                               is_zstaff_flex=True)

    target.change_deafened(new_deaf)


def ooc_cmd_defaultarea(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Set the default area by area ID for all future clients to join when joining your hub.
    Returns an error if the area ID is invalid.

    SYNTAX
    /defaultarea <area_id>

    PARAMETERS
    <area_id>: Intended default area ID

    EXAMPLES
    >>> /defaultarea 1
    Set area 1 to be the default area.
    """

    Constants.assert_command(client, arg, is_mod=True, parameters='=1')

    try:
        area = client.hub.area_manager.get_area_by_id(int(arg))
    except ValueError:
        raise ArgumentError('Expected numerical value for area ID.')
    except AreaError:
        raise ClientError(
            'ID {} does not correspond to a valid area ID.'.format(arg))

    client.hub.area_manager.set_default_area(area)
    client.send_ooc('Set default area of your hub to {}.'.format(arg))


def ooc_cmd_dicelog(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Obtains the last 20 roll results from the target by client ID or your own if not given any.
    Returns an error if the identifier does not correspond to a user.

    SYNTAX
    /dicelog {client_id}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {client_id}: Client identifier (number in brackets in /getarea)

    EXAMPLES
    >>> /dicelog
    Returns your last 20 rolls.
    >>> /dicelog 1
    Returns the last 20 rolls of the user with client ID 1.
    """

    Constants.assert_command(client, arg, is_staff=True)
    if not arg:
        arg = str(client.id)

    # Obtain target's dicelog
    target = Constants.parse_id(client, arg)
    info = target.get_dicelog()
    client.send_ooc(info)


def ooc_cmd_dicelog_area(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Obtains the last 20 roll resuls from an area by its ID or name or your current one if not given
    any.
    Returns an error if the identifier does not correspond to an area.

    SYNTAX
    /dicelog_area {target_area}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {target_area}: Area whose rolls will be listed

    EXAMPLES
    >>> /dicelog_area
    Returns the last 20 rolls of your area.
    >>> /dicelog_area 1
    Returns the last 20 rolls of Area 1.
    """

    Constants.assert_command(client, arg, is_staff=True)
    if not arg:
        arg = str(client.area.id)

    # Obtain target area's dicelog
    target = Constants.parse_area_names(client, [arg])[0]
    info = target.get_dicelog()
    client.send_ooc(info)


def ooc_cmd_discord(client: ClientManager.Client, arg: str):
    """
    Returns the server's Discord server invite link.

    SYNTAX
    /discord

    PARAMETERS
    None

    EXAMPLE
    >>> /discord
    Sends the Discord invite link
    """

    Constants.assert_command(client, arg, parameters='=0')

    client.send_ooc('Discord Invite Link: {}'.format(
        client.server.config['discord_link']))


def ooc_cmd_disemconsonant(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Disemconsonants all IC and OOC messages of a user by client ID (number in brackets) or IPID
    (number in parentheses). In particular, all their messages will have all their consonants
    removed. If given IPID, it will affect all clients opened by the target. Otherwise, it will just
    affect the given client. Requires /undisemconsonant to undo.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /disemconsonant <client_id>
    /disemconsonant <client_ipid>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    EXAMPLES
    >>> /disemconsonant 1
    Disemconsonants the user with client ID 1.
    >>> /disemconsonant 1234567890
    Disemconsonants all clients opened by the user with IPID 1234567890.
    """

    Constants.assert_command(client, arg, is_mod=True, parameters='=1')

    # Disemconsonant matching targets
    for c in Constants.parse_id_or_ipid(client, arg):
        c.disemconsonant = True
        logger.log_server('Disemconsonanted {}.'.format(c.ipid), client)
        client.area.broadcast_ooc(
            "{} was disemconsonanted.".format(c.displayname))


def ooc_cmd_disemvowel(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Disemvowels all IC and OOC messages of a user by client ID (number in brackets) or IPID
    (number in parentheses). In particular, all their messages will have all their vowels removed.
    If given IPID, it will affect all clients opened by the target. Otherwise, it will just affect
    the given client. Requires /undisemvowel to undo.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /disemvowel <client_id>
    /disemvowel <client_ipid>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    EXAMPLES
    >>> /disemvowel 1
    Disemvowels the user with client ID 1.
    >>> /disemvowel 1234567890
    Disemwvowels all clients opened by the user with IPID 1234567890.
    """

    Constants.assert_command(client, arg, is_mod=True, parameters='=1')

    # Disemvowel matching targets
    for c in Constants.parse_id_or_ipid(client, arg):
        c.disemvowel = True
        logger.log_server('Disemvowelled {}.'.format(c.ipid), client)
        client.area.broadcast_ooc(
            "{} was disemvowelled.".format(c.displayname))


def ooc_cmd_dj_list(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sets the current DJ list of your current hub (what music list a player will see when joining an
    area of your hub if they do not have a personal music list active).
    If given no arguments, it will return the DJ list to its original value
    (in config/music.yaml).
    Returns an error if the given music list name included relative directories,
    was not found, caused an OS error when loading, or raised a YAML or asset syntax error when
    loading.

    SYNTAX
    /dj_list <dj_list>

    PARAMETERS
    <dj_list>: Name of the intended music list to serve as DJ list.

    EXAMPLES
    >>> /dj_list trial
    Load the "trial" DJ list.
    >>> /dj_list
    Reset the DJ list to its original value.
    """

    Constants.assert_command(client, arg, is_staff=True)

    client.hub.music_manager.command_list_load(client, arg)

    for target in client.hub.get_players():
        if target.music_manager.is_default_file_loaded():
            target.send_ooc('As you had no personal music list loaded, you will be shown the hub '
                            'music list.')
            target.send_music_list_view()
        else:
            target.send_ooc('As you had a personal music list loaded, you will not be shown the '
                            'hub music list. Display the hub music list by running /music_list.')


def ooc_cmd_dj_list_info(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Returns the DJ list of your current hub.

    SYNTAX
    /dj_list_info

    PARAMETERS
    None

    EXAMPLES
    >>> /dj_list_info
    May return something like this:
    | $H: The current DJ list is the custom list `trial`.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    client.hub.music_manager.command_list_info(client)


def ooc_cmd_doc(client: ClientManager.Client, arg: str):
    """
    Returns the area's current doc link, or sets it to a new one.

    SYNTAX
    /doc {doc_link}

    PARAMETERS
    {doc_link}: Link to new document.

    EXAMPLES
    >>> /doc https://www.google.com
    Sets the document link to the Google homepage.
    >>> /doc
    Returns the current document (e.g. https://www.google.com)
    """

    # Clear doc case
    if not arg:
        client.send_ooc('Document: {}'.format(client.area.doc))
        logger.log_server('[{}][{}]Requested document. Link: {}'
                          .format(client.area.id, client.get_char_name(), client.area.doc), client)
    # Set new doc case
    else:
        client.area.change_doc(arg)
        client.area.broadcast_ooc(
            '{} changed the doc link.'.format(client.displayname))
        logger.log_server('[{}][{}]Changed document to: {}'
                          .format(client.area.id, client.get_char_name(), arg), client)


def ooc_cmd_dump(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Prepares a server dump containing debugging information about the server and saves it in the
    server log files.

    SYNTAX
    /dump

    PARAMETERS
    None

    EXAMPLES
    >>> /dump
    May return something like this:
    | $H: Generated server dump file logs/[2020-12-23T200220]D.log.
    """

    Constants.assert_command(client, arg, is_mod=True, parameters='=0')

    dump_message = f'Client {client.id} requested a server dump.'
    file = logger.log_error(dump_message, client.server, errortype='D')
    client.send_ooc(f'Generated server dump file {file}.')


def ooc_cmd_exit(client: ClientManager.Client, arg: str):
    """
    Makes you exit the server.

    SYNTAX
    /exit

    PARAMETERS
    None

    EXAMPLE
    >>> /exit
    Makes you exit the server.
    """

    Constants.assert_command(client, arg, parameters='=0')

    client.send_ooc('You have exited the server.')
    client.disconnect()


def ooc_cmd_files(client: ClientManager.Client, arg: str):
    """
    Obtains the download link of a user by client ID (number in brackets).
    If given no identifier, it will return your download link.
    A warning is also given in either case reminding you to be careful of clicking external
    links, as the server provides no guarantee on the safety of the link.
    Returns an error if the given identifier does not correspond to a user or if the target has not
    set a download link for their files.

    SYNTAX
    /files
    /files <user_id>

    PARAMETERS
    <user_id>: Either the client ID (number in brackets in /getarea), character name, edited-to
               character, custom showname or OOC name of the intended recipient.

    EXAMPLES
    Assuming user with client ID 1 on character Phantom_HD and iniswapped to Spam_HD has set their
    files' download link to https://example.com ...
    >>> /files 1
    May return something like this:
    | $H: Files set by client 1 for Spam_HD: https://example.com
    | $H: Links are spoopy. Exercise caution when opening external links.
    """

    if arg:
        target, match, _ = client.server.client_manager.get_target_public(
            client, arg)

        if target.files:
            if match.isdigit():
                match = 'client {}'.format(match)
            client.send_ooc('Files set by {} for `{}`: {}'
                            .format(match, target.files[0], target.files[1]))
            client.send_ooc(
                'Links are spoopy. Exercise caution when opening external links.')
        else:
            if match.isdigit():
                match = 'Client {}'.format(match)
            raise ClientError(
                '{} has not provided a download link for their files.'.format(match))
    else:
        if client.files:
            client.send_ooc('Files set by yourself for `{}`: {}'
                            .format(client.files[0], client.files[1]))
            client.send_ooc(
                'Links are spoopy. Exercise caution when opening external links.')
        else:
            raise ClientError(
                'You have not provided a download link for your files.')


def ooc_cmd_files_area(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    Obtains the download link of the files of all other users visible to you in the area who have
    set them.
    If the visible name of the user is not the same as the folder of their actual character,
    both are displayed.
    A warning is also given in either case reminding you to be careful of clicking external
    links, as the server provides no guarantee on the safety of the link.
    Returns an error you are not staff and are either blind or their area's lights are off,
    or if no visible users in the area set their files.

    SYNTAX
    /files_area

    PARAMETERS
    None

    EXAMPLES
    >>> /files_area 1
    May return something like this:
    | $H: (X) === Players in area Basement who have set their files ===
    | [1] Phantom (Spam_HD): hhh
    | [0] Eggs_HD: Hi
    """

    Constants.assert_command(client, arg, parameters='=0')

    msg = ''
    if client.is_blind:
        if not client.is_staff():
            raise ClientError('You are blind, so you cannot see anything.')
        msg = '(X) '
    if not client.area.lights:
        if not client.is_staff():
            raise ClientError(
                'The lights are off, so you cannot see anything.')
        msg = '(X) '

    players = [player for player in client.get_visible_clients(
        client.area) if player.files]

    if not players:
        raise ClientError(msg + 'No players in the area have set their files.')

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
            priority -= 2 ** 2
        if player.party and player.party == client.party:
            priority -= 2 ** 1

        player_list.append([priority, name, player.id, player])
        # We add player.id as a tiebreaker if both priority and name are the same
        # This can be the case if, say, two SPECTATOR are in the same area.
        # player.id is unique, so it helps break ties
        # player instances do not have order, so they are a bad way to sort ties.

    player_list.sort()
    for (_, name, _, player) in player_list:
        if player.files[0] == name:
            player_description += (
                '\r\n[{}] {}: {}'.format(player.id, name, player.files[1])
            )
        else:
            player_description += (
                '\r\n[{}] {} ({}): {}'.format(player.id, name,
                                              player.files[0], player.files[1])
            )

    msg += (
        f"=== Players in area {client.area.name} who have set their files ==={player_description}"
    )
    client.send_ooc(msg)
    client.send_ooc(
        'Links are spoopy. Exercise caution when opening external links.')


def ooc_cmd_files_set(client: ClientManager.Client, arg: str):
    """
    Sets the download link to the character you are using (or has iniswapped to if available)
    as the given argument; otherwise, clears it.

    SYNTAX
    /files_set
    /files_set <url>

    PARAMETERS
    <url>: URL to the download link of the character you are using.

    EXAMPLES
    If user with client ID 1 is on character Phantom_HD and iniswapped to Spam_HD
    >>> /files_set https://example.com
    Sets the download link to Spam_HD to https://example.com
    """

    client.change_files(arg)


def ooc_cmd_follow(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    Starts following a user by their client ID. When the target area moves area, you will follow
    them automatically except if disallowed by the new area. You must be using a non-participant
    character to follow another user, or (STAFF ONLY) may use any character to follow another user.
    Requires /unfollow to undo.
    Returns an error if you are part of a party or you are using a participant character with
    insufficient permissions.

    SYNTAX
    /follow <client_id>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)

    EXAMPLE
    >>> /follow 1
    Starts following the user with client ID 1.
    """

    try:
        Constants.assert_command(client, arg, is_staff=True, parameters='=1')
    except ClientError.UnauthorizedError:
        Constants.assert_command(client, arg, parameters='=1')
        if client.has_participant_character():
            raise ClientError('You must be authorized to follow while having a participant '
                              'character.')

    if client.party:
        raise PartyError('You cannot follow someone while in a party.')

    c = Constants.parse_id(client, arg)
    client.follow_user(c)
    logger.log_server('{} began following {}.'
                      .format(client.get_char_name(), c.get_char_name()), client)


def ooc_cmd_g(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    Sends a global message in the OOC chat visible to all users in the server who have not disabled
    global chat. The message includes your area and display name. Moderators and community
    managers also get to see your IPID.
    Returns an error if you have global chat off, send an empty message, or are not an officer
    and attempt to send a message in an area where global messages are disallowed or when the
    server disallows global messages.

    SYNTAX
    /g <message>

    PARAMETERS
    <message>: Message to be sent

    EXAMPLE
    >>> /g Hello World
    Sends Hello World to global chat.
    """

    try:
        Constants.assert_command(client, arg, parameters='>0')
    except ArgumentError:
        raise ArgumentError("You cannot send an empty message.")

    if not client.is_officer() and not client.server.global_allowed:
        raise ClientError('Global chat is currently locked.')
    if not client.is_officer() and not client.area.global_allowed:
        raise ClientError(
            'You must be authorized to send global messages in this area.')
    if client.muted_global:
        raise ClientError('You have the global chat muted.')

    client.server.broadcast_global(client, arg)
    logger.log_server('[{}][{}][GLOBAL]{}.'
                      .format(client.area.id, client.get_char_name(), arg), client)


def ooc_cmd_gag(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Changes the gagged status of a user by client ID.
    Gagged players will be unable to talk IC properly or use other talking features such as /scream.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /gag <client_id>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)

    EXAMPLES
    Assuming user with client ID 1 starts hearing...
    >>> /gag 1
    Gags that user.
    >>> /gag 1
    Ungags that user.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')
    target = Constants.parse_id(client, arg)

    status = {False: 'ungagged', True: 'gagged'}
    new_gagged = not target.is_gagged

    if client != target:
        client.send_ooc('You have {} {} [{}].'
                        .format(status[new_gagged], target.displayname, target.id))
        target.send_ooc('You have been {}.'.format(status[new_gagged]))
        target.send_ooc_others('(X) {} [{}] has {} {} [{}] ({}).'
                               .format(client.displayname, client.id, status[new_gagged],
                                       target.displayname, target.id, target.area.id),
                               is_zstaff_flex=True, not_to={client})
    else:
        client.send_ooc('You have {} yourself.'.format(status[new_gagged]))
        client.send_ooc_others('(X) {} [{}] has {} themselves ({}).'
                               .format(client.displayname, client.id, status[new_gagged],
                                       client.area.id),
                               is_zstaff_flex=True)

    target.change_gagged(new_gagged)


def ooc_cmd_getarea(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    Lists the characters (and associated client IDs) in the current area
    OR (STAFF ONLY) lists the character (and associated client IDs) in the given area by area ID
    or name.
    Returns an error if you are in an area that disables /getarea, if
    you are blind and not staff, or if the given identifier does not correspond to an area.

    SYNTAX
    /getarea
    /getarea <target_area>

    PARAMETERS
    <target_area>: The area whose characters will be listed. By default it is your area.

    EXAMPLE
    If Phantom is a staff member in area 0
    >>> /getarea
    | $H: == Area 0: Basement ==
    | [0] Phantom_HD
    | [1] Spam_HD (Spam, Spam, Spam...)
    >>> /getarea 1
    May return something like this:
    | $H: == Area 1: Courtroom ==
    | [2] Eggs_HD (Eggy Egg)
    | [3] Judge_HD (Gavel Guy)
    """

    if arg:
        if not client.is_staff():
            raise ClientError.UnauthorizedError('You must be authorized to use the one-parameter '
                                                'version of this command.')
        area_id = Constants.parse_area_names(client, [arg])[0].id
    else:
        area_id = client.area.id

    if not client.is_staff() and client.is_blind:
        raise ClientError('You are blind, so you cannot see anything.')

    client.send_area_info(client.area, area_id, False, include_shownames=True)


def ooc_cmd_getareas(client: ClientManager.Client, arg: str):
    """
    List the characters (and associated client IDs) in each area.
    Returns an error if you are in an area that disables /getareas,
    or if you are blind and not staff.

    SYNTAX
    /getareas

    PARAMETERS
    None

    EXAMPLE
    >>> /getareas
    May return something like this:
    | $H: == Area List ==
    | == Area 0: Basement ==
    | [0] Phantom_HD
    | [1] Spam_HD (Spam, Spam, Spam...)
    | == Area 1: Class Trial Room 1 ==
    | [2] Eggs_HD (Not Spam?)
    """

    Constants.assert_command(client, arg, parameters='=0')

    if not client.is_staff() and client.is_blind:
        raise ClientError('You are blind, so you cannot see anything.')

    client.send_area_info(client.area, -1, False, include_shownames=True)


def ooc_cmd_gimp(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Gimps all IC messages of a user by client ID (number in brackets) or IPID (number in
    parentheses). In particular, their message will be replaced by one of the messages listed in
    config/gimp.yaml. If given IPID, it will affect all clients opened by the
    user. Otherwise, it will just affect the given client. Requires /ungimp to undo.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /gimp <client_id>
    /gimp <client_ipid>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    EXAMPLES
    >>> /gimp 1
    Gimps the user with client ID 1.
    >>> /gimp 1234567890
    Gimps all clients opened by the user with IPID 1234567890.
    """

    Constants.assert_command(client, arg, is_mod=True, parameters='=1')

    # Gimp matching targets
    for c in Constants.parse_id_or_ipid(client, arg):
        c.gimp = True
        logger.log_server('Gimping {}.'.format(c.ipid), client)
        client.area.broadcast_ooc("{} was gimped.".format(c.displayname))


def ooc_cmd_globalic(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Send client's subsequent IC messages to users only in specified areas. Can take either area IDs
    or area names. If you are not in intended destination range, it will NOT send messages
    to your area. Requires /unglobalic to undo.
    If given two areas, it will send the IC messages to all areas between the given ones inclusive.
    If given one area, it will send the IC messages only to the given area.
    Returns an error if the given identifier does not correspond to an area.

    SYNTAX
    /globalic <target_area>
    /globalic <area_range_start>, <area_range_end>

    PARAMETERS
    <target_area>: Send IC messages just to this area.

    <area_range_start>: Send IC messages from this area onwards up to...
    <area_range_end>: Send IC messages up to (and including) this area.

    EXAMPLES
    >>> /globalic 1, Courtroom 3
    Send IC messages to areas 1 through "Courtroom 3" (if you are in area 0, you will not see your
    own message).
    >>> /globalic 3
    Send IC messages just to area 3.
    >>> /globalic 1, 1
    Send IC messages just to area 1.
    >>> /globalic Courtroom,\ 2, Courtroom 3
    Send IC messages to areas "Courtroom, 2" through "Courtroom 3" (note the escape character).
    """

    Constants.assert_command(
        client, arg, parameters='&1-2', is_staff=True, split_commas=True)
    areas = Constants.parse_two_area_names(client, arg.split(', '))

    client.multi_ic = areas

    if areas[0] == areas[1]:
        client.send_ooc(
            'Your IC messages will now be sent to area {}.'.format(areas[0].name))
    else:
        client.send_ooc('Your IC messages will now be sent to areas {} through {}.'
                        .format(areas[0].name, areas[1].name))
    client.send_ooc('Set up a global IC prefix with /globalic_pre')


def ooc_cmd_globalic_pre(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    If given an argument, it sets the client's message prefix that must be included in their IC
    messages in order for them to be globally sent as part of a /globalic command. Messages that
    do not start with this prefix will only be sent to their current area as usual. This prefix
    will also be filtered out from their message.
    If given nothing, it removes the prefix requirement and all messages will be sent globally if
    /globalic is on.

    SYNTAX
    /globalic_pre {prefix}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {prefix}: Message prefix

    EXAMPLES
    Assuming /globalic is on...
    >>> /globalic_pre |||
    Only IC messages that start with ||| will be sent globally.
    >>> /globalic_pre
    All IC messages will be sent globally.
    """

    Constants.assert_command(client, arg, is_staff=True)

    client.multi_ic_pre = arg
    if arg:
        client.send_ooc('You have set your global IC prefix to {}'.format(arg))
    else:
        client.send_ooc('You have removed your global IC prefix.')


def ooc_cmd_glock(client: ClientManager.Client, arg: str):
    """ (OFFICER ONLY)
    Toggles players that are not CM or mod being able to use /g and /zg or not.

    SYNTAX
    /glock

    PARAMETERS
    None

    EXAMPLE
    Assuming global chat was not locked originally...
    >>> /glock
    Locks the global chat.
    >>> /glock
    Unlocks the global chat.
    """

    Constants.assert_command(client, arg, is_officer=True, parameters='=0')

    client.server.global_allowed = not client.server.global_allowed
    status = {False: 'locked', True: 'unlocked'}

    client.send_ooc('You have {} the global chat.'.format(
        status[client.server.global_allowed]))
    client.send_ooc_others('A mod has {} the global chat.'
                           .format(status[client.server.global_allowed]),
                           is_officer=False, in_hub=None)
    client.send_ooc_others('{} [{}] has {} the global chat.'
                           .format(client.name, client.id, status[client.server.global_allowed]),
                           is_officer=True, in_hub=None)
    logger.log_server('{} has {} the global chat.'
                      .format(client.name, status[client.server.global_allowed]), client)


def ooc_cmd_gm(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Similar to /g, but with the following changes:
    *Includes a "[GLOBAL-MOD]" tag to the message to indicate a mod sent the message.
    *Uses the OOC username as opposed to the character name when displaying the message.
    Returns an error if you have global chat off or send an empty message.

    SYNTAX
    /gm <message>

    PARAMETERS
    <message>: Message to be sent

    EXAMPLE
    >>> /gm Hello World
    Sends Hello World to globat chat, preceded with [GLOBAL-MOD].
    """

    try:
        Constants.assert_command(client, arg, is_mod=True, parameters='>0')
    except ArgumentError:
        raise ArgumentError("You cannot send an empty message.")

    if client.muted_global:
        raise ClientError('You have the global chat muted.')

    client.server.broadcast_global(client, arg, as_mod=True)
    logger.log_server('[{}][{}][GLOBAL-MOD]{}.'
                      .format(client.area.id, client.get_char_name(), arg), client)


def ooc_cmd_gmself(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Makes all opened multiclients login as game master without them needing to put in a GM password.
    Opened multiclients that are already logged in as game master are unaffected.
    Returns an error if all opened multiclients are already game masters.

    SYNTAX
    /gmself

    PARAMETERS
    None

    EXAMPLES
    If user with client ID 0 is GM has multiclients with ID 1 and 3, neither GM, and runs...
    >>> /gmself
    Logs in clients 1 and 3 as game master.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    targets = [c for c in client.get_multiclients() if not c.is_gm]
    if not targets:
        raise ClientError(
            'All opened clients are already logged in as game master.')

    for target in targets:
        target.login(client.server.config['gmpass'], target.auth_gm, 'game master',
                     announce_to_officers=False)

    client.send_ooc('Logged in client{} {} as game master.'
                    .format('s' if len(targets) > 1 else '',
                            Constants.cjoin([target.id for target in targets])))


def ooc_cmd_guide(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sends an IC personal message to a specified user by some ID. Unlike /whisper, the messages do
    not have your showname nor do they send notifications to other users in the area.
    Elevated notifications are sent to zone watchers/staff members on /guide, which include the
    message content, so this is not meant to act as a private means of communication between
    users, for which /pm is recommended.
    As this is meant to act as a "subconscious/guider/personal narrator" command, deafened players
    are not affected and receive the message as is.
    Returns an error if the target could not be found, if the message is empty, if you are
    IC-muted, or if you attempt to guide yourself.

    SYNTAX
    /guide <user_ID> <message>

    PARAMETERS
    <user_id>: Either the client ID (number in brackets in /getarea), character name, edited-to
               character, custom showname or OOC name of the intended recipient.
    <message>: Message to be sent.

    EXAMPLES
    >>> /guide 1 Hey, is that blood?
    Sends that message to user with client ID 1.
    >>> /guide 0 Check out his clothes!
    Sends that message to user with client ID 0.
    """

    try:
        Constants.assert_command(client, arg, is_staff=True, parameters='>1')
    except ArgumentError:
        raise ArgumentError('Not enough arguments. Use /guide <target> <message>. Target should '
                            'be ID, char-name, edited-to character, custom showname or OOC-name.')
    if client.is_muted:
        raise ClientError('You have been muted by a moderator.')

    cm = client.server.client_manager
    target, _, msg = cm.get_target_public(client, arg)
    msg = msg[:256]  # Cap

    if client == target:
        raise ClientError('You cannot guide yourself.')

    client.send_ooc(
        f'You gave the following guidance to {target.displayname}: `{msg}`.')
    target.send_ooc(f'You hear a guiding voice in your head say `{msg}`.')
    target.send_ic(msg=msg, showname='[G] ???',
                   hide_character=1, bypass_text_replace=True)

    client.send_ooc_others('(X) {} [{}] gave the following guidance to {}: `{}` ({}).'
                           .format(client.displayname, client.id, target.displayname, msg,
                                   client.area.id),
                           is_zstaff_flex=target.area, not_to={target})


def ooc_cmd_handicap(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY+VARYING REQUIREMENTS)
    Sets a movement handicap on a user by client ID or IPID so that they need to wait a set
    amount of time between changing areas. This will override any previous handicaps the client(s)
    may have had, including custom ones and server ones (such as through sneak). Server handicaps
    will override custom handicaps if the server handicap is longer. However, as soon as the server
    handicap is over, it will recover the old custom handicap.
    If given IPID, it will set the movement handicap on all the clients opened by the target.
    Otherwise, it will just do it to the given client.
    Search by IPID can only be performed by CMs and mods.
    Requires /unhandicap to undo.
    Returns an error if the given identifier does not correspond to a user, or if given a
    non-positive length of time.

    SYNTAX
    /handicap <client_id> <length> {name} {announce_if_over}
    /handicap <client_ipid> <length> {name} {announce_if_over}

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)
    <length>: Handicap length (in seconds)

    OPTIONAL PARAMETERS
    {name}: Name of the handicap (e.g. "Injured", "Sleepy", etc.). By default it is "Handicap".
    {announce_if_over}: If the server will send a notification once the target may move areas after
    waiting for their handicap timer. By default it is true. For the server not to send them, put
    one of these keywords: False, false, 0, No, no

    EXAMPLES
    >>> /handicap 0 5
    Sets a 5 second movement handicap on the user with client ID 0.
    >>> /handicap 1234567890 10 Injured
    Sets a 10 second movement handicap called "Injured" on the clients with IPID 1234567890.
    >>> /handicap 1 15 StabWound False
    Sets a 15 second movement handicap called "StabWound" on the user with client ID 0 which will
    not send notifications once the timer expires.
    """

    Constants.assert_command(client, arg, is_staff=True,
                             parameters='&2-4', split_spaces=True)

    args = arg.split(' ')

    # Obtain targets
    targets = Constants.parse_id_or_ipid(client, args[0])

    # Check if valid length and convert to seconds
    length = Constants.parse_time_length(args[1])  # Also internally validates

    # Check name
    if len(args) >= 3:
        name = args[2]
    else:
        name = "Handicap"  # No spaces!

    # Check announce_if_over status
    if len(args) >= 4 and args[3] in ['False', 'false', '0', 'No', 'no']:
        announce_if_over = False
    else:
        announce_if_over = True

    for c in targets:
        client.send_ooc('You imposed a movement handicap "{}" of length {} seconds on {}.'
                        .format(name, length, c.displayname))
        client.send_ooc_others('(X) {} [{}] imposed a movement handicap "{}" of length {} seconds '
                               'on {} in area {} ({}).'
                               .format(client.displayname, client.id, name, length, c.displayname,
                                       client.area.name, client.area.id),
                               is_zstaff_flex=True, not_to={c})

        c.change_handicap(True, length=length, name=name,
                          announce_if_over=announce_if_over)


def ooc_cmd_help(client: ClientManager.Client, arg: str):
    """
    Returns a brief description of the command syntax and its functionality of a command by name
    according to your current rank, or if unauthorized to use it, display its functionality
    as if you had the minimum rank they need to run it but warn you that you need said rank to
    use it. The syntax and functionality descriptions are pulled from README.md on server boot-up.
    If not given a command name, returns the website with all available commands and their
    instructions (usually a GitHub repository).
    Returns an error if a given command name had no associated instructions on README.md.

    SYNTAX
    /help
    /help <command_name>

    PARAMETERS
    <command_name>: Name of the command (e.g. help)

    EXAMPLES
    >>> /help
    Displays website with all commands and instructions.
    >>> /help help
    Displays the syntax and functionality of the help command.
    """

    if not arg:
        url = 'https://github.com/Keightiie/TsuserverDR#commands'
        help_msg = ('Available commands, source code and issues can be found here: {} . If you are '
                    'looking for help with a specific command, do /help <command_name>'.format(url))
        client.send_ooc(help_msg)
        return

    ranks_to_try = [
        ('normie', True),
        ('gm', client.is_staff()),
        ('cm', client.is_officer()),
        ('mod', client.is_mod)
    ]

    # Try and find the most elevated description
    command_info, found_match, command_authorization = None, False, False
    for (rank, authorized) in ranks_to_try:
        try:
            pre_info = client.server.commandhelp[rank][arg]
        except KeyError:
            continue

        found_match = True
        if not authorized:  # Check if client is authorized to use this command with this rank
            break  # If not authorized now, won't be authorized later, so break out

        command_info = pre_info
        # This means at least one suitable variant of the command
        command_authorization = True
        # that can be run with the user's rank was found

    # If a command was found somewhere among the user's available commands, command_info
    # would be non-empty.
    if not found_match:
        raise ClientError('Could not find help for command "{}"'.format(arg))

    message = 'Help for command "{}"'.format(arg)
    # If user was not authorized to run the command, display help for command version that requires
    # the least rank possible.
    if not command_authorization:
        command_info = pre_info

    for detail in command_info:
        message += ('\n' + detail)

    if not command_authorization:
        message += ('\nYou need rank at least {} to use this command.'.format(rank))

    client.send_ooc(message)


def ooc_cmd_help_more(client: ClientManager.Client, arg: str):
    """
    Returns additional information about a command, obtained by reading the associated description
    in the commands.py server file. Such information is usually more descriptive than the one in
    the README.md (which is brief by design), as well as including potential interactions and ways
    the command can fail.
    Returns an error if a given command name had no associated instructions in the file, or if its
    description is otherwise unparseable.

    SYNTAX
    /help_more <command_name>

    PARAMETERS
    <command_name>: Name of command.

    EXAMPLES
    >>> /help_more help_more
    Returns additional information about the command `help_more` (namely, the text you are reading
    now).
    """

    Constants.assert_command(client, arg, parameters='=1')

    try:
        command = getattr(client.server.commands, f'ooc_cmd_{arg}')
    except AttributeError:
        raise ClientError(f'Could not find more help for command `{arg}`.')

    raw_doc = command.__doc__
    doc = raw_doc.strip().replace('\t', '').split('\n')
    doc = [line.strip() for line in doc]
    if not doc:
        raise ClientError(f'Unable to generate more help for command `{arg}`.')
    if raw_doc[0] == '\n':
        doc.insert(0, '(NONE)')

    parsed_doc = [[], [], [], [], [], []]
    modes = {
        'SYNTAX': 2,
        'PARAMETERS': 3,
        'OPTIONAL PARAMETERS': 4,
        'EXAMPLE': 5,
        'EXAMPLES': 5,
    }

    parsed_doc[0].append(doc[0])

    mode = 1
    for line in doc[1:]:
        if not line:
            continue
        if line in modes:
            mode = modes[line]
        parsed_doc[mode].append(line)

    if not parsed_doc[1] or not parsed_doc[2] or not parsed_doc[3] or not parsed_doc[5]:
        raise ClientError(f'Unable to generate more help for command `{arg}`.')

    client.send_ooc(f'Generating additional help for command {arg}...')

    # Rank requirement
    output = 'RANK REQUIREMENTS: '
    output += parsed_doc[0][0].replace('(', '').replace(')', '').strip()
    client.send_ooc(output)

    # Description
    output = 'DESCRIPTION\r\n '
    for line in parsed_doc[1]:
        if line.startswith('Returns an error'):
            output += '\r\n'
        output += line + ' '
    client.send_ooc(output.strip())

    # Syntax
    output = 'SYNTAX\r\n'
    for line in parsed_doc[2][1:]:
        output += line + '\r\n'
    client.send_ooc(output.strip())

    # Parameters
    output = 'PARAMETERS'
    for line in parsed_doc[3][1:]:
        if line.startswith('<') or line == 'None':
            output += '\r\n'
        output += line + ' '
    client.send_ooc(output.strip())

    # Optional parameters
    if parsed_doc[4]:
        output = 'OPTIONAL PARAMETERS'
        for line in parsed_doc[4][1:]:
            if line.startswith('{'):
                output += '\r\n'
            output += line + ' '
        client.send_ooc(output.strip())

    # Examples
    output = 'EXAMPLES\r\n'
    for line in parsed_doc[5][1:]:
        if line.startswith('>>> '):
            output += '\r\n' + line + '\r\n'
        elif line.startswith('| '):
            output += '\r\n' + line + '\r\n'
        else:
            output += line + ' '
    client.send_ooc(output.replace('\r\n\r\n', '\r\n').strip())


def ooc_cmd_hub(client: ClientManager.Client, arg: str):
    """
    Either lists all hubs in the server or changes your area to a new given area.
    Returns an error if you are already in the target hub or you are unable to move to the default
    area of the new hub.

    SYNTAX
    /hub
    /hub <new_hub_numerical_id>

    PARAMETERS
    <new_hub_numerical_id>: Numerical ID of the hub

    EXAMPLES
    >>> /hub
    Lists all hubs in the server.
    >>> /hub 1
    Moves you to hub 1.
    """

    Constants.assert_command(client, arg, parameters='<2')

    args = arg.split()
    # List all hubs
    if not args:
        client.send_limited_hub_list()

    # Switch to new area
    else:
        try:
            numerical_id = int(args[0])
        except ValueError:
            raise ArgumentError('Hub ID must be a number.')

        try:
            hub = client.hub.manager.get_managee_by_numerical_id(numerical_id)
        except HubError.ManagerInvalidGameIDError:
            raise HubError.ManagerInvalidGameIDError('Hub not found.')

        client.change_hub(hub, from_party=(client.party is not None))


def ooc_cmd_hub_create(client: ClientManager.Client, arg: str):
    """ (OFFICER ONLY)
    Creates a new hub with the given name, or with a default generated name if not given one.
    The numerical ID of the hub will be the lowest non-taken numerical hub ID.

    SYNTAX
    /hub_create {name}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {name}: Name of the hub

    EXAMPLES
    Assuming that two hubs with numerical IDs 0 and 2 respectively exist...
    >>> /hub_create
    Creates hub with numerical ID 1.
    >>> /hub_create hubby hub
    Creates hub with numerical ID 3 and name "hubby hub".
    """

    Constants.assert_command(client, arg, is_officer=True)

    hub = client.hub.manager.new_managee()
    if arg:
        hub.set_name(arg)

    for target in client.server.get_clients():
        target.send_music_list_view()

    if arg:
        client.send_ooc(
            f'You created hub {hub.get_numerical_id()} with name {hub.get_name()}.')
        client.send_ooc_others(f'{client.name} [{client.id}] created hub {hub.get_numerical_id()} '
                               f'with name {hub.get_name()}.', is_officer=True, in_hub=None)
    else:
        client.send_ooc(f'You created hub {hub.get_numerical_id()}.')
        client.send_ooc_others(f'{client.name} [{client.id}] created hub {hub.get_numerical_id()}.',
                               is_officer=True, in_hub=None)


def ooc_cmd_hub_end(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    (STAFF ONLY) Deletes the current hub if not given a numerical ID, or
    (OFFICER ONLY) of the given hub by numerical ID.
    Players in the deleted hub are moved to the default hub of the server.
    Returns an error if given a numerical ID and it is not the numerical ID of a hub in the server,
    or if the server has only one hub.

    SYNTAX
    /hub_end
    /hub_end <hub_id>

    PARAMETERS
    <hub_id>: Numerical ID

    EXAMPLES
    >>> /hub_end
    Deletes the current hub.
    >>> /hub_end 2
    Deletes the hub with numerical ID 2.
    """

    try:
        Constants.assert_command(client, arg, is_officer=True, parameters='<2')
    except ClientError.UnauthorizedError:
        Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    if not arg:
        arg = client.hub.get_numerical_id()

    try:
        hub = client.hub.manager.get_managee_by_numerical_id(arg)
    except HubError.ManagerInvalidGameIDError:
        raise ClientError(f'Hub {arg} not found.')

    try:
        client.hub.manager.delete_managee(hub)
    except HubError.ManagerCannotManageeNoManagees:
        raise ClientError(
            f'You cannot delete a hub when it is the only one of the server.')

    for target in client.server.get_clients():
        target.send_music_list_view()

    client.send_ooc(f'You deleted hub {hub.get_numerical_id()}.')
    client.send_ooc_others(f'{client.name} [{client.id}] deleted hub {hub.get_numerical_id()}.',
                           is_officer=True, in_hub=None)


def ooc_cmd_hub_info(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    (STAFF ONLY) Return information about the current hub if not given a numerical ID, or
    (OFFICER ONLY) of the given hub by numerical ID.
    Returns an error if given a numerical ID and it is not the numerical ID of a hub in the server.

    SYNTAX
    /hub_info
    /hub_info <hub_id>

    PARAMETERS
    <hub_id>: Numerical ID

    EXAMPLES
    >>> /hub_info
    May return something like this:
    | [17:34] $H: == Hub 0 ==
    | *GMs: 1. NonGMs: 0
    | *Area list: config/areas.yaml
    | *Background list: config/bg_lists/beach.yaml
    | *Character list: config/char_lists/custom.yaml
    | *DJ list: config/music.yaml
    """

    try:
        Constants.assert_command(client, arg, is_officer=True, parameters='<2')
    except ClientError.UnauthorizedError:
        Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    if not arg:
        arg = client.hub.get_numerical_id()

    try:
        hub = client.hub.manager.get_managee_by_numerical_id(arg)
    except HubError.ManagerInvalidGameIDError:
        raise ClientError(f'Hub {arg} not found.')

    info = hub.get_info()
    client.send_ooc(info)


def ooc_cmd_hub_password(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Changes the hub password.

    SYNTAX
    /hub_password <password>

    PARAMETERS
    <password>: New password

    EXAMPLES
    >>> /hub_password 11037
    Sets the hub password to 11037.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='>0')

    client.hub.set_password(arg)
    client.send_ooc('You have changed the password of your hub.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] changed the password of your '
                           f'hub. Do /hub_password_info to retrieve it.',
                           is_zstaff_flex=True, is_officer=False)
    hid = client.hub.get_numerical_id()
    client.send_ooc_others(f'{client.name} [{client.id}] changed the password of hub {hid}. Do '
                           f'/hub_password_info {hid} to retrieve it.',
                           is_officer=True, in_hub=None)


def ooc_cmd_hub_password_info(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    (STAFF ONLY) Gets the password of the current hub or, (OFFICER ONLY) the given hub by numerical
    ID.
    Returns an error if given a numerical ID and it is not the numerical ID of a hub in the server.

    SYNTAX
    /hub_password_info
    /hub_password_info <hub_id>

    PARAMETERS
    <hub_id>: Numerical ID

    EXAMPLES
    >>> /hub_password_info
    May return something like this:
    | $H: The hub password is `2124`.
    """

    try:
        Constants.assert_command(client, arg, is_officer=True, parameters='<2')
    except ClientError.UnauthorizedError:
        Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    if not arg:
        arg = client.hub.get_numerical_id()

    try:
        hub = client.hub.manager.get_managee_by_numerical_id(arg)
    except HubError.ManagerInvalidGameIDError:
        raise ClientError(f'Hub {arg} not found.')

    password = hub.get_password()
    client.send_ooc(f'The hub password is `{password}`.')


def ooc_cmd_hub_rename(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Changes the name of a hub by its numerical ID if given a name, or clears it if not given one.

    SYNTAX
    /hub_rename
    /hub_rename <name>

    PARAMETERS
    <name>: Name

    EXAMPLES
    >>> /hub_rename Great Hub
    Changes the name of the hub to Great Hub.
    >>> /hub_rename
    Clears the name of the hub.
    """

    Constants.assert_command(client, arg, is_staff=True)

    hub = client.hub
    hub.set_name(arg)

    if arg:
        client.send_ooc(f'You have renamed your hub to `{arg}`.')
        client.send_ooc_others(f'{client.displayname} [{client.id}] renamed your hub to `{arg}` '
                               f'({client.area.id}).', is_zstaff_flex=True)
    else:
        client.send_ooc('You have cleared the name of your hub.')
        client.send_ooc_others(f'{client.displayname} [{client.id}] cleared the name of your hub '
                               f'({client.area.id}).', is_zstaff_flex=True)

    for target in client.server.get_clients():
        target.send_music_list_view()


def ooc_cmd_iclock(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Toggles IC messages by non-staff or players without IC lock bypass in the current area being
    allowed/disallowed. If now disallowed, any user with an active IC lock bypass will lose it.
    Returns an error if a GM attempts to lock IC in an area where such an action is forbidden.

    SYNTAX
    /iclock

    PARAMETERS
    None

    EXAMPLES
    Assuming the area starts with IC lock off...
    >>> /iclock
    Turns IC lock on.
    >>> /iclock
    Turns IC lock off.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')
    if not client.is_officer() and (client.is_gm and not client.area.gm_iclock_allowed):
        raise ClientError(
            'GMs are not authorized to change IC locks in this area.')

    client.area.ic_lock = not client.area.ic_lock
    status = {True: 'locked', False: 'unlocked'}

    client.send_ooc('You {} the IC chat in this area.'.format(
        status[client.area.ic_lock]))
    client.send_ooc_others(f'The IC chat has been {status[client.area.ic_lock]} in this area.'
                           .format(), is_zstaff_flex=False, in_area=True)
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] has '
                           f'{status[client.area.ic_lock]} the IC chat in area {client.area.name} '
                           f'({client.area.id}).', is_zstaff_flex=True)

    logger.log_server('[{}][{}]Changed IC lock to {}'
                      .format(client.area.id, client.get_char_name(), client.area.ic_lock), client)

    if not client.area.ic_lock:
        # Remove ic lock bypasses
        affected_players = list()
        for player in client.area.clients:
            if player.can_bypass_iclock and not player.is_staff():
                affected_players.append(player)

        if affected_players:
            for player in affected_players:
                player.send_ooc('You have lost your IC lock bypass as the IC chat in '
                                'your area has been unlocked.')
                player.send_ooc_others(f'(X) {player.displayname} [{player.id}] has lost their IC '
                                       f'lock bypass as the IC chat in their area has '
                                       f'been unlocked ({client.area.id}).',
                                       is_zstaff_flex=client.area)
                player.can_bypass_iclock = False


def ooc_cmd_iclock_bypass(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Provides a non-staff player permission to talk in their current area if the area is IC locked.
    Returns an error if the given identifier does not correspond to a user, if the target is
    already staff or if the IC chat in the area of the target is not locked.

    SYNTAX
    /iclock_bypass <client_id>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)

    EXAMPLES
    Assuming user with user with client ID 1 starts without a bypass...
    >>> /iclock_bypass 1
    Grants that user an IC lock bypass
    >>> /iclock_bypass 1
    Revokes that user of their IC lock bypass
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')
    target = Constants.parse_id(client, arg)

    if target.is_staff():
        raise ClientError(
            'Target is already staff and thus does not require an IC lock bypass.')
    # As we require staff to run the command, but the target cannot be staff, we are guaranteed
    # that target != client.
    if not target.area.ic_lock:
        raise ClientError(
            'The IC chat in the area of the target is not locked.')

    target.can_bypass_iclock = not target.can_bypass_iclock

    if target.can_bypass_iclock:
        client.send_ooc(
            f'You have granted {target.displayname} [{target.id}] an IC lock bypass.')
        target.send_ooc('You have been granted an IC lock bypass.')
        target.send_ooc_others(f'(X) {client.displayname} [{client.id}] has granted '
                               f'{target.displayname} [{target.id}] an IC lock bypass '
                               f'({target.area.id}).', is_zstaff_flex=True, not_to={client})
    else:
        client.send_ooc(f'You have revoked {target.displayname} [{target.id}] of their IC lock '
                        'bypass.')
        target.send_ooc('You have been revoked of your IC lock bypass.')
        target.send_ooc_others(f'(X) {client.displayname} [{client.id}] has revoked '
                               f'{target.displayname} [{target.id}] of their IC lock bypass '
                               f'({target.area.id}).', is_zstaff_flex=True, not_to={client})


def ooc_cmd_ignore(client: ClientManager.Client, arg: str):
    """
    Marks another user as ignored. You will no longer receive any IC messages from that user,
    even those that come as a result of OOC commands. The target will not be notified of the
    ignore command being executed on them.
    Requires /unignore to undo.
    Returns an error if the given identifier does not correspond to a user, if the target is
    yourself, or if you are already ignoring the target.

    SYNTAX
    /ignore <user_id>

    PARAMETERS
    <user_id>: Either the client ID (number in brackets in /getarea), character name, edited-to
               character, custom showname or OOC name of the intended recipient.

    EXAMPLES
    >>> /ignore 1
    Ignores user with client ID 1.
    """

    Constants.assert_command(client, arg, parameters='>0')

    target, _, _ = client.server.client_manager.get_target_public(client, arg)

    if target == client:
        raise ClientError('You may not ignore yourself.')
    if target in client.ignored_players:
        raise ClientError(
            f'You are already ignoring {target.displayname} [{target.id}].')

    client.ignored_players.add(target)
    client.send_ooc(
        f'You are now ignoring {target.displayname} [{target.id}].')


def ooc_cmd_invite(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    Adds a client based on some ID to the area's invite list. Only staff members can invite based
    on IPID. Invites are IPID based, so anyone with the same IPID becomes part of the area's invite
    list.
    Search by IPID can only be performed by CMs and mods.
    Returns an error if the given identifier does not correspond to a user or if target is already
    invited.

    SYNTAX
    /invite <client_ipid>
    /invite <user_id>

    PARAMETERS
    <client_ipid>: IPID for the client (number in parentheses in /getarea)
    <user_id>: Either the client ID (number in brackets in /getarea), character name, edited-to
               character, custom showname or OOC name of the intended recipient.

    EXAMPLES
    >>> /invite 1
    Invites the user with client ID 1.
    >>> /invite 1234567890
    Invites all clients of the user with IPID 1234567890.
    """

    Constants.assert_command(client, arg, parameters='>0')

    if not client.area.is_locked and not client.area.is_modlocked:
        raise ClientError('Area is not locked.')

    targets = list()  # Start with empty list
    if client.is_officer() and arg.isdigit():
        targets = client.server.client_manager.get_targets(
            client, TargetType.IPID, int(arg), False)
        if targets:
            some_target = targets[0]
    if not targets:
        # Under the hood though, we need the IPID of the target, so we will still end up obtaining
        # it anyway. We want to get all clients whose IPID match the IPID of whatever we match
        some_target, _, _ = client.server.client_manager.get_target_public(
            client, arg)
        targets = client.server.client_manager.get_targets(client, TargetType.IPID,
                                                           some_target.ipid, False)

    # Check if target is already invited
    if some_target.ipid in client.area.invite_list:
        raise ClientError('Target is already invited to your area.')

    # Add to invite list and notify targets
    client.area.invite_list[some_target.ipid] = None
    for c in targets:
        # If inviting yourself, send special message
        if client == c:
            client.send_ooc('You have invited yourself to this area.')
        else:
            client.send_ooc(
                'Client {} has been invited to your area.'.format(c.id))
            c.send_ooc('You have been invited to area {}.'.format(
                client.area.name))


def ooc_cmd_judgelog(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    List the last 20 judge actions performed in the current area. This includes using the judge
    buttons and changing the penalty bars. If given an argument, it will return the judgelog of the
    given area by area ID or name. Otherwise, it will obtain the one from the current area.
    Returns an error if the given identifier does not correspond to an area.

    SYNTAX
    /judgelog {target_area}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {target_area}: area whose judgelog will be returned (either ID or name)

    EXAMPLE
    If currently in the Basement (area 0)...
    >>> /judgelog
    You may get something like the next example
    >>> /judgelog 0
    May return something like this:
    | $H: == Judge log of Basement (0) ==
    | *Sat Jun 29 12:06:03 2019 | [1] Judge (1234567890) used judge button testimony1.
    | *Sat Jun 29 12:06:07 2019 | [1] Judge (1234567890) used judge button testimony4.
    | *Sat Jun 29 12:06:12 2019 | [1] Judge (1234567890) changed penalty bar 2 to 9.
    | *Sat Jun 29 12:06:12 2019 | [1] Judge (1234567890) changed penalty bar 2 to 8.
    | *Sat Jun 29 12:06:14 2019 | [1] Judge (1234567890) changed penalty bar 1 to 9.
    | *Sat Jun 29 12:06:15 2019 | [1] Judge (1234567890) changed penalty bar 1 to 8.
    | *Sat Jun 29 12:06:16 2019 | [1] Judge (1234567890) changed penalty bar 1 to 7.
    | *Sat Jun 29 12:06:17 2019 | [1] Judge (1234567890) changed penalty bar 1 to 8.
    | *Sat Jun 29 12:06:19 2019 | [1] Judge (1234567890) changed penalty bar 2 to 9.
    """

    Constants.assert_command(client, arg, is_staff=True)
    if not arg:
        arg = client.area.name

    # Obtain matching area's judgelog
    for area in Constants.parse_area_names(client, [arg]):
        info = area.get_judgelog()
        client.send_ooc(info)


def ooc_cmd_kick(client: ClientManager.Client, arg: str):
    """ (OFFICER ONLY)
    Kicks a user from the server. The target is identified by either client ID (number in brackets)
    or IPID (number in parentheses). If given IPID, it will kick all clients opened by the target.
    Otherwise, it will just kick the given client.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /kick <client_id>
    /kick <client_ipid>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    EXAMPLES
    >>> /kick 1
    Kicks the user with client ID 1.
    >>> /kick 1234567890
    Kick all clients opened by the user with IPID 1234567890.
    """

    Constants.assert_command(client, arg, is_officer=True, parameters='=1')

    # Kick matching targets
    for c in Constants.parse_id_or_ipid(client, arg):
        client.send_ooc(
            'You kicked {} [{}/{}].'.format(c.displayname, c.ipid, c.hdid))
        client.send_ooc_others('{} was kicked.'.format(c.displayname),
                               is_officer=False, in_area=True, in_hub=True)
        client.send_ooc_others('{} [{}] kicked {} [{}/{}].'
                               .format(client.name, client.id, c.displayname, c.ipid, c.hdid),
                               is_officer=True, in_hub=None)
        logger.log_server('Kicked {}.'.format(c.ipid), client)
        c.disconnect()


def ooc_cmd_kickself(client: ClientManager.Client, arg: str):
    """
    Kicks other clients you opened. Useful whenever you lose connection and the old client is
    ghosting.
    Returns an error if you do not have other clients open.

    SYNTAX
    /kickself

    PARAMETERS
    None

    EXAMPLES
    >>> /kickself
    Kicks other clients you opened.
    """

    Constants.assert_command(client, arg, parameters='=0')

    kick_list = list()
    for target in client.get_multiclients():
        if target != client:
            kick_list.append(f'{target.displayname} [{target.id}]')
            target.disconnect()

    if not kick_list:
        raise ClientError('You do not have other clients open.')
    output = Constants.cjoin(kick_list, sort=False)
    client.send_ooc(f'You have kicked these other clients of yours: {output}.')


def ooc_cmd_knock(client: ClientManager.Client, arg: str):
    """
    'Knock' on some area's door, sending a notification to users in said area.
    Returns an error if the area could not be found, if you are already in the target area,
    if the area cannot be reached as per the DEFAULT server configuration (as users may lock
    passages, but that does not mean the door no longer exists, usually), or if you are either
    in an area marked as lobby or attempting to knock the door to a lobby area.

    SYNTAX
    /knock <area_name>
    /knock <area_id>

    PARAMETERS
    <area_name>: Name of the area whose door you want to knock.
    <area_id>: ID of the area whose door you want to knock.

    EXAMPLES
    >>> /knock 0
    Knock the door to area 0
    >>> /knock Courtroom, 2
    Knock the door to area "Courtroom, 2"
    """

    Constants.assert_command(client, arg, parameters='=1')

    # Get area by either name or ID
    try:
        target_area = client.hub.area_manager.get_area_by_name(arg)
    except AreaError:
        try:
            target_area = client.hub.area_manager.get_area_by_id(int(arg))
        except Exception:
            raise ArgumentError('Could not parse area name {}.'.format(arg))

    # Filter out edge cases
    if target_area.name == client.area.name:
        raise ClientError('You cannot knock on the door of your current area.')
    if client.area.lobby_area:
        raise ClientError('You cannot knock doors from a lobby area.')
    if target_area.lobby_area:
        raise ClientError('You cannot knock the door to a lobby area.')

    if target_area.name not in client.area.default_reachable_areas | client.area.reachable_areas:
        raise ClientError('You tried to knock on the door to {} but you realized the room is too '
                          'far away.'.format(target_area.name))

    client.send_ooc(
        'You knocked on the door to area {}.'.format(target_area.name))
    client.send_ooc_others('Someone knocked on your door from area {}.'.format(client.area.name),
                           is_zstaff_flex=False, in_area=target_area, to_deaf=False)
    client.send_ooc_others('(X) {} [{}] knocked on the door to area {} in area {} ({}).'
                           .format(client.displayname, client.id, target_area.name,
                                   client.area.name, client.area.id),
                           is_zstaff_flex=True)

    for c in client.area.clients:
        c.send_ic(msg='', hide_character=1, ding=0 if c.is_deaf else 7)
    for c in target_area.clients:
        c.send_ic(msg='', hide_character=1, ding=0 if c.is_deaf else 7)


def ooc_cmd_lasterror(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Obtain the latest uncaught error as a result of a client packet. This message emulates what is
    output on the server console (i.e. it includes the full traceback as opposed to just the last
    error which is what is usually sent to the offending client).
    Note that ClientErrors, ServerErrors, AreaErrors and ArgumentErrors are usually caught by the
    server itself, and would not normally cause issues.
    Returns an error if no errors had been raised and not been caught since server bootup.

    SYNTAX
    /lasterror

    PARAMETERS
    None

    EXAMPLE
    >>> /lasterror
    May return something like this:
    | $H: The last uncaught error message was the following:
    | TSUSERVERDR HAS ENCOUNTERED AN ERROR HANDLING A CLIENT PACKET
    | *Server version: TsuserverDR 4.3.5-a1 (m220906a)
    | *Server time: Tue Sep  6 10:25:55 2022
    | *Packet details: CT ['Iuvee', '/exec 1']
    | *Client version: ('DRO', '1.2.3')
    | *Client status: C::0:2202575700:Iuvee:Kaede Akamatsu_HD:Iuvee:True:0
    | *Area status: A::0:Basement:1
    |
    | Traceback (most recent call last):
    | File "D:\\AO\\TsuserverDR\\server\\network\\ao_protocol.py", line 158, in _process_message
    |     dispatched.function(self.client, pargs)
    | File "D:\\AO\\TsuserverDR\\server\\network\\ao_commands.py", line 672, in net_cmd_ct
    |     function(client, arg)
    | File "D:\\AO\\TsuserverDR\\server\\commands.py", line 11420, in ooc_cmd_exec
    |     debuge
    | NameError: name 'debuge' is not defined
    """

    Constants.assert_command(client, arg, is_mod=True, parameters='=0')

    if not client.server.last_error:
        raise ClientError('No error messages have been raised and not been caught since server '
                          'bootup.')

    pre_info, _, _, _ = client.server.last_error
    client.send_ooc(
        f'The last uncaught error message was the following:\n{pre_info}')


def ooc_cmd_lights(client: ClientManager.Client, arg: str):
    """ (VARYING PRIVILEGES)
    Toggles lights "on" or "off" in the current area, or (STAFF ONLY) tries to toggle in each of
    the areas given, if given.
    If you are blind and attempt to change the lights, it will only switch the light status rather
    than follow the "on" or "off" argument.
    If one of the target's area has its background locked, it requires mod privileges for that
    area's lights to be turned off.
    If turned off, the background of the target area will change to the server's blackout
    background.
    If turned on, the background of the target area will revert to its non-blackout background.
    Returns an error if no areas are given and either you are nonmod and the background's area is
    locked, you are nonstaff and the area has no lights to change, or the new lights status
    corresponds to the current lights status.

    SYNTAX
    /lights <new_status>
    /lights <new_status> {area_1} {area_2} ...

    PARAMETERS
    <new_status>: 'on' or 'off'

    OPTIONAL PARAMETERS
    {area_n}: Area ID

    EXAMPLES
    Assuming lights were initially turned on...
    >>> /lights off
    Turns off lights
    >>> /lights on
    Turns on lights
    >>> /lights on 1 2
    Tries to turns on lights in areas 1 and 2.
    >>> /lights off 2 3
    Tries to turns off lights in areas 2 and 3.
    """

    try:
        Constants.assert_command(client, arg, parameters='>0')
    except ArgumentError:
        raise ArgumentError('You must specify either on or off.')

    args = arg.split()
    if len(args) > 1 and not client.is_staff():
        raise ClientError.UnauthorizedError('You must be authorized to use the more-than-one-'
                                            'parameter version of this command.')

    if args[0] not in ['off', 'on']:
        raise ClientError('Expected on or off.')

    if not client.is_staff() and client.is_blind:
        new_lights = not client.area.lights
    else:
        new_lights = (args[0] == 'on')

    if len(args) == 1:
        if not client.is_staff() and not client.area.has_lights:
            raise AreaError('This area has no lights to turn off or on.')
        if not client.is_mod and client.area.bg_lock:
            raise AreaError('The background of this area is locked.')

        client.area.change_lights(new_lights, initiator=client)
    else:
        # Must be staff to be here.
        areas = args[1:]
        target_areas = Constants.parse_area_names(client, areas)

        cannot_change = list()
        failed_change = list()
        success_change = list()

        for area in target_areas:
            if (not client.is_mod and area.bg_lock) or not area.has_lights:
                cannot_change.append(area)
                continue
            try:
                area.change_lights(new_lights, initiator=client, area=area)
                success_change.append(area)
            except AreaError:
                failed_change.append(area)

        if cannot_change:
            client.send_ooc(f'It is not possible to change the lights in these areas: '
                            f'{Constants.cjoin([area.name for area in cannot_change])}.')
        if failed_change:
            client.send_ooc(f'The lights in these areas were already {args[0]}: '
                            f'{Constants.cjoin([area.name for area in failed_change])}.')
        if success_change:
            client.send_ooc(f'You have turned {args[0]} the lights in these areas: '
                            f'{Constants.cjoin([area.name for area in success_change])}.')
            client.send_ooc_others(f'(X) {client.displayname} [{client.id}] has turned {args[0]} '
                                   f'the lights in these areas: '
                                   f'{Constants.cjoin([area.name for area in success_change])}'
                                   f'({client.area.id}).', is_zstaff_flex=True)


def ooc_cmd_lm(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Similar to /lm, but only broadcasts the message to users in the current area, regardless of
    their global chat status.
    Returns an error if you send an empty message.

    SYNTAX
    /lm <message>

    PARAMETERS
    <message>: Message to be sent

    EXAMPLE
    >>> /lm Hello World
    Sends `Hello World` to all users in the current area, preceded with [MOD].
    """

    try:
        Constants.assert_command(client, arg, is_mod=True, parameters='>0')
    except ArgumentError:
        raise ArgumentError('You cannot send an empty message.')

    for c in client.area.clients:
        c.send_ooc(arg, '{}[MOD][{}]'.format(
            client.server.config['hostname'], client.displayname))
    logger.log_server('[{}][{}][LOCAL-MOD]{}.'
                      .format(client.area.id, client.get_char_name(), arg), client)


def ooc_cmd_lock(client: ClientManager.Client, arg: str):
    """
    Locks the current area, preventing anyone not in the area (except staff) from joining. It also
    clears out the current invite list.
    Returns an error if the area does not allow locking or is already locked.

    SYNTAX
    /lock

    PARAMETERS
    None

    EXAMPLE
    >>> /lock
    Locks the area.
    """

    Constants.assert_command(client, arg, parameters='=0')

    if not client.area.locking_allowed:
        raise ClientError('Area locking is disabled in this area.')
    if client.area.is_locked:
        raise ClientError('Area is already locked.')

    client.area.is_locked = True
    for i in client.area.clients:
        client.area.invite_list[i.ipid] = None

    client.area.broadcast_ooc('Area locked.')


def ooc_cmd_toggle_legacy_jukebox(client: ClientManager.Client, arg: str):
    """
    Toggles legacy jukebox behavior in the current area. When enabled,
    the current song do not automatically play whenever
    a client joins the area.
    """

    Constants.assert_command(client, arg, is_staff=True)

    client.area.legacy_jukebox = not client.area.legacy_jukebox
    state_string = ("disabled", "enabled")[client.area.legacy_jukebox]
    client.area.broadcast_ooc(f'Legacy jukebox is now {state_string}.')


def ooc_cmd_login(client: ClientManager.Client, arg: str):
    """
    Logs you in as a moderator, provided you input the correct password.

    SYNTAX
    /login <mod_password>

    PARAMETERS
    <mod_password>: Mod password, found in config/config.yaml

    EXAMPLES
    >>> /login Mod
    Attempt to log in as mod with "Mod" as password.
    """

    client.login(arg, client.auth_mod, 'moderator')


def ooc_cmd_logincm(client: ClientManager.Client, arg: str):
    """
    Logs you in as a community manager, provided you input the correct password.

    SYNTAX
    /logincm <cm_password>

    PARAMETERS
    <cm_password>: Community manager password, found in config/config.yaml

    EXAMPLES
    >>> /logincm CM
    Attempt to log in as community maanger with "CM" as password.
    """

    client.login(arg, client.auth_cm, 'community manager')


def ooc_cmd_logingm(client: ClientManager.Client, arg: str):
    """
    Logs you in as a game master, provided you input the correct password.

    SYNTAX
    /logingm <gm_password>

    PARAMETERS
    <gm_password>: Game master password, found via /hub_password_info or in config/config.yaml

    EXAMPLES
    >>> /logingm GM
    Attempt to log in as game master with "GM" as password.
    """

    client.login(arg, client.auth_gm, 'game master')


def ooc_cmd_logout(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Logs you out from all staff roles.

    SYNTAX
    /logout

    PARAMETERS
    None

    EXAMPLE
    >>> /logout
    Logs you out.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    if client.is_mod:
        role = 'moderator'
    elif client.is_cm:
        role = 'community manager'
    else:
        role = 'game master'

    client.send_ooc('You are no longer logged in.')
    client.send_ooc_others('{} [{}] is no longer a {}.'
                           .format(client.name, client.id, role),
                           is_officer=True, in_hub=None)
    client.logout()


def ooc_cmd_look(client: ClientManager.Client, arg: str):
    """
    Obtain the current area's description, which is either the description in the area list
    configuration, or a customized one defined via /look_set. If the area has no set description,
    it will return the server's default description stored in the default_area_description server
    parameter. If the area has its lights turned off, it will send a generic 'cannot see anything'
    message to non-staff members.

    SYNTAX
    /look

    PARAMETERS
    None

    EXAMPLES
    Assuming the current area's description is "Literally a courtroom"...
    >>> /look
    Returns "Literally a courtroom"
    """

    msg = ''
    if client.is_blind:
        if not client.is_staff():
            raise ClientError('You are blind, so you cannot see anything.')
        msg = '(X) '
    if not client.area.lights:
        if not client.is_staff():
            raise ClientError(
                'The lights are off, so you cannot see anything.')
        msg = '(X) '

    if arg:
        cm = client.server.client_manager
        target, _, _ = cm.get_target_public(client, arg, only_in_area=True)
        if not target.status:
            msg += f'You look at {target.displayname} and find nothing particularly remarkable.'
        else:
            msg += f'You look at {target.displayname} and note this: {target.status}'
    else:
        _, _, area_description, _, player_description = client.area.get_look_output_for(
            client)

        msg += (
            f'=== Look results for {client.area.name} ===\r\n'
            f'*About the people: you see {player_description}\r\n'
            f'*About the area: {area_description}'
        )

    client.send_ooc(msg)


def ooc_cmd_look_clean(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Restores the default area descriptions of the given areas by area ID or name separated by
    commas. If not given any areas, it will restore the default area description of the current
    area.

    SYNTAX
    /look_clean {area_1}, {area_2}, ....

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {area_n}: Area ID or name

    EXAMPLE
    Assuming you are in area 0...
    >>> /look_clean
    Restores the default area description in area 0.
    >>> /look_clean 3, Class Trial Room,\ 2
    Restores the default area descriptions in area 3 and Class Trial Room, 2 (note the ,\).
    """

    Constants.assert_command(client, arg, is_staff=True)

    if not arg:
        areas_to_clean = [client.area]
    else:
        # Make sure the input is valid before starting
        raw_areas_to_clean = arg.split(", ")
        areas_to_clean = set(Constants.parse_area_names(
            client, raw_areas_to_clean))

    successful_cleans = set()
    for area in areas_to_clean:
        area.description = area.default_description
        client.send_ooc_others('The area description was updated to {}.'.format(area.description),
                               is_zstaff_flex=False, in_area=area)
        successful_cleans.add(area.name)

    if len(successful_cleans) == 1:
        message = str(successful_cleans.pop())
        client.send_ooc('Restored the original area description of area {}.'
                        .format(message))
        client.send_ooc_others('(X) {} [{}] restored the original area description of area {}.'
                               .format(client.displayname, client.id, message),
                               is_zstaff_flex=True)
    elif len(successful_cleans) > 1:
        message = Constants.cjoin(successful_cleans)
        client.send_ooc('Restored the original area descriptions of areas {}.'
                        .format(message))
        client.send_ooc_others('(X) {} [{}] restored the original area descriptions of areas {}.'
                               .format(client.displayname, client.id, message),
                               is_zstaff_flex=True)

    logger.log_server('[{}][{}]Reset the area description in {}.'
                      .format(client.area.id, client.get_char_name(), message), client)


def ooc_cmd_look_list(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Lists all areas that contain custom descriptions.

    SYNTAX
    /look_list

    PARAMETERS
    None

    EXAMPLE
    Assuming area 0 called Basement is the only one with a custom description, and its description
    happens to be "Not a courtroom"...
    >>> /look_list
    May return something like this:
    | $H: == Areas in this server with custom descriptions ==
    | *(0) Basement: Not a courtroom
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    info = '== Areas in this server with custom descriptions =='
    # Get all areas with changed descriptions
    areas = [area for area in client.hub.area_manager.get_areas()
             if area.description != area.default_description]

    # No areas found means there are no areas with changed descriptions
    if len(areas) == 0:
        info += '\r\n*No areas have changed their description.'
    # Otherwise, build the list of all areas with changed descriptions
    else:
        for area in areas:
            info += '\r\n*({}) {}: {}'.format(area.id,
                                              area.name, area.description)

    client.send_ooc(info)


def ooc_cmd_look_set(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sets (and replaces!) the area description of the current area to the given one.
    If not given any description, it will set the description to be the area's default description.
    Requires /look_clean to undo.

    SYNTAX
    /look_set {area_description}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {area_description}: New area description

    EXAMPLES
    Assuming you are in area 0, which was set to have a default description of "A courtroom"...
    >>> /look_set "Not literally a courtroom"
    Sets the area description in area 0 to be "Not literally a courtroom".
    >>> /look_set
    Sets the area description in area 0 to be the default "A courtroom".
    """

    Constants.assert_command(client, arg, is_staff=True)

    if not arg:
        client.area.description = client.area.default_description
        client.send_ooc('Reset the area description to its original value.')
        client.send_ooc_others('(X) {} [{}] reset the area description of your area to its '
                               'original value.'
                               .format(client.displayname, client.id),
                               is_zstaff_flex=True, in_area=True)
        client.send_ooc_others('(X) {} [{}] reset the area description of area {} to its original '
                               'value.'
                               .format(client.displayname, client.id, client.area.name),
                               is_zstaff_flex=True, in_area=False)
        logger.log_server('[{}][{}]Reset the area description in {}.'
                          .format(client.area.id, client.get_char_name(), client.area.name), client)

    else:
        client.area.description = arg
        client.send_ooc('Updated the area descriptions to `{}`.'.format(arg))
        client.send_ooc_others('(X) {} [{}] set the area description of your area to `{}`.'
                               .format(client.displayname, client.id, client.area.description),
                               is_zstaff_flex=True, in_area=True)
        client.send_ooc_others('(X) {} [{}] set the area descriptions of area {} to `{}`.'
                               .format(client.displayname, client.id, client.area.name,
                                       client.area.description),
                               is_zstaff_flex=True, in_area=False)
        logger.log_server('[{}][{}]Set the area descriptions to {}.'
                          .format(client.area.id, client.get_char_name(), arg), client)


def ooc_cmd_lurk(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Initiates an area lurk callout timer in the area so that non-spectator regular players who do
    not speak IC after a set amount of seconds are called out in OOC to other users in the area
    (but not themselves).
    Actions that reset a user's personal callout timer are: speaking IC (even if gagged), using
    /whisper or /guide, changing character, changing area and switching to spectator.
    Actions that start a user's personal callout timer are: moving to an area with an active lurk
    callout timer, switching from spectator to a character, or logging out from a ranked position.
    Deaf and blind players in the area do not receive callout notifications from other users.
    If a called out player is gagged, a special message is sent instead.
    If an area had an active lurk callout timer and all players leave the area, the lurk callout
    timer is deactivated and no players will be subject to one when moving to the area until a new
    area lurk callout timer is started.
    If an active area lurk callout timer is present when running the command, it will overwrite
    the existing area lurk callout timer and reset all valid targets' callout timers.
    Returns an error if the lurk callout length is non-positive or exceeds the server limit (6
    hours).

    SYNTAX
    /lurk <length>

    PARAMETERS
    <length>: Area lurk callout time length (in seconds)

    EXAMPLES
    >>> /lurk 60
    Sets a 60-second area lurk callout timer, players who remain silent for a minute will be
    called out.
    >>> /lurk 2
    Sets a 2-second area lurk callout timer, players who remain silent for 2 seconds will be
    called out.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')

    # Check if valid length and convert to seconds
    lurk_length = Constants.parse_time_length(arg)  # Also internally validates
    client.area.lurk_length = lurk_length

    for c in client.area.clients:
        c.check_lurk()

    client.send_ooc('(X) You have enabled a lurk callout timer of length {} seconds in this area.'
                    .format(lurk_length))
    client.send_ooc_others('(X) {} has enabled a lurk callout timer of length {} seconds in your '
                           'area.'.format(client.name, lurk_length),
                           is_zstaff_flex=True, in_area=True)
    client.send_ooc_others('(X) {} has enabled a lurk callout timer of length {} seconds in area '
                           '{} ({}).'
                           .format(client.name, lurk_length, client.area.name, client.area.id),
                           is_zstaff_flex=True, in_area=False)


def ooc_cmd_lurk_end(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Cancels an existing area lurk callout timer in the area, and all non-spectator regular players'
    personal lurk callout timers in the area.
    Returns an error if no area lurk callout timer is active in the area.

    SYNTAX
    /lurk_end

    PARAMETERS
    None

    EXAMPLE
    For current area with an active 10-second area lurk callout timer
    >>> /lurk_end
    Cancels the area lurk callout timer, players may now remain silent for 10 seconds and not be
    called out.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    if client.area.lurk_length == 0:
        raise ClientError('This area has no active lurk callout timer.')

    client.area.lurk_length = 0
    # End the lurk timer of all clients who have active lurk callout timers in the area
    for c in client.area.clients:
        c.check_lurk()

    client.send_ooc('(X) You have ended the lurk callout timer in this area.')
    client.send_ooc_others('(X) {} has ended the lurk callout timer in your area.'
                           .format(client.name), is_zstaff_flex=True, in_area=True)
    client.send_ooc_others('(X) {} has ended the lurk callout timer in area {} ({}).'
                           .format(client.name, client.area.name, client.area.id),
                           is_zstaff_flex=True, in_area=False)


def ooc_cmd_make_gm(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY+VARYING REQUIREMENTS)
    Makes a user by client ID a GM without them needing to put in a GM password.
    Returns an error if the target is already a GM, or if you are not community manager or
    moderator and try to GM a client that is not a multiclient of them.

    SYNTAX
    /make_gm <client_id>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)

    EXAMPLES
    >>> /make_gm 3
    Makes the client with ID 3 a GM.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')

    target = Constants.parse_id(client, arg)

    if not client.is_officer() and target not in client.get_multiclients():
        raise ClientError('You must be authorized to login as game masters players other than your '
                          'multiclients.')
    if target.is_gm:
        raise ClientError('Client {} is already a GM.'.format(target.id))

    target.login(client.server.config['gmpass'], target.auth_gm, 'game master',
                 announce_to_officers=False)
    client.send_ooc('Logged client {} as a GM.'.format(target.id))
    client.send_ooc_others('{} [{}] has been logged in as a game master by {} [{}].'
                           .format(target.name, target.id, client.name, client.id),
                           is_officer=True, in_hub=None)


def ooc_cmd_mindreader(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Toggles a client by ID being a mind reader or not (i.e. can read all thoughts caused by /think,
    not just those initiated by the player), or yourself if not given an argument.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /mindreader
    /mindreader <client_id>

    OPTIONAL PARAMETERS
    {client_id}: Client identifier (number in brackets in /getarea)

    EXAMPLE
    Assuming a user with client ID 0 starts as not being a mind reader...
    >>> /mindreader 0
    This user can now read all thoughts.
    >>> /mindreader 0
    This user can no longer read thoughts not initiated by the user.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='<2')

    # Invert current mindreader status of matching targets
    if not arg:
        target = client
    else:
        target = Constants.parse_id(client, arg)
    target.is_mindreader = not target.is_mindreader

    status = {False: 'no longer', True: 'now'}
    status2 = {False: 'no longer a', True: 'a'}
    if client != target:
        client.send_ooc(f'{target.displayname} ({target.id}) is {status[target.is_mindreader]} a '
                        f'mind reader.')
        client.send_ooc_others(f'(X) {client.displayname} ({client.id}) made {target.displayname} '
                               f'({target.id}) be {status2[target.is_mindreader]} mind reader '
                               f'({client.area.id}).', is_zstaff_flex=True)
        target.send_ooc(
            f'You are {status[target.is_transient]} a mind reader.')
    else:
        client.send_ooc(
            f'You made yourself be {status2[target.is_mindreader]} mind reader.')
        client.send_ooc_others(f'(X) {client.displayname} ({client.id}) made themselves be '
                               f'{status2[target.is_mindreader]} mind reader '
                               f'({client.area.id}).', is_zstaff_flex=True)


def ooc_cmd_minimap(client: ClientManager.Client, arg: str):
    """
    Lists all areas that can be reached from the current area according to areas.yaml and passages
    set in-game.
    Returns all areas if no passages were defined or created for the current area.

    SYNTAX
    /minimap

    PARAMETERS
    None

    EXAMPLE
    >>> /minimap
    May return something like this:
    | $H: == Minimap for Basement ==
    | 1-Class Trial Room 1
    | 3-Class Trial Room 3
    | 4-Test 1
    | 5-Test 2
    | 6-Test 3
    | 7-Test 4
    """

    Constants.assert_command(client, arg, parameters='=0')

    info = '== Minimap for {} =='.format(client.area.name)
    if client.area.visible_areas == client.hub.area_manager.area_names:
        # Useful abbreviation
        info += '\r\n<ALL>'
    else:
        # Get all reachable areas and sort them by area ID
        sorted_areas = sorted(client.area.visible_areas,
                              key=lambda name: client.hub.area_manager.get_area_by_name(name).id)

        # No areas found or just the current area found means there are no reachable areas.
        if len(sorted_areas) == 0 or sorted_areas == [client.area.name]:
            info += '\r\n*No areas available.'
        # Otherwise, build the list of all reachable areas
        else:
            for area_name in sorted_areas:
                if area_name == client.area.name:
                    continue
                area = client.hub.area_manager.get_area_by_name(area_name)
                info += f'\r\n{area.id}-{area_name}'

    client.send_ooc(info)


def ooc_cmd_modlock(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Sets the current area as accessible only to moderators. Players in the area at the time of the
    lock will be able to leave and return to the area, regardless of authorization.
    Requires /unlock to undo.
    Returns an error if the area is already mod-locked or if the area is set to be not lockable.

    SYNTAX
    /modlock

    PARAMETERS
    None

    EXAMPLE
    >>> /modlock
    Sets the current area as accessible only to moderators.
    """

    Constants.assert_command(client, arg, is_mod=True, parameters='=0')

    if not client.area.locking_allowed:
        raise ClientError('Area locking is disabled in this area.')
    if client.area.is_modlocked:
        raise ClientError('Area is already mod-locked.')

    client.area.is_modlocked = True
    client.area.broadcast_ooc('Area mod-locked.')
    for i in client.area.clients:
        client.area.invite_list[i.ipid] = None


def ooc_cmd_motd(client: ClientManager.Client, arg: str):
    """
    Returns the server's Message Of The Day.

    SYNTAX
    /motd

    PARAMETERS
    None

    EXAMPLES
    >>> /motd
    May return something like this:
    | $H: === MOTD ===
    | Welcome to my server!
    | =============
    """

    Constants.assert_command(client, arg, parameters='=0')

    client.send_motd()


def ooc_cmd_multiclients(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY+VARYING REQUIREMENTS)
    Lists all clients and the areas they are opened by a user by client ID or IPID.
    Search by IPID can only be performed by CMs and mods.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /multiclients <client_id>
    /multiclients <client_ipid>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    EXAMPLES
    Assuming user with client ID 1 with IPID 1234567890 is in the Basement (area 0) and has
    another client open with client ID 4...
    >>> /multiclients 1
    May return something like the example below, except with 1 instead of 1234567890.
    >>> /multiclients 1234567890
    May return something like this:
    | $H: == Clients of 1234567890 ==
    | == Area 0: Basement ==
    | [1] Spam_HD (1234567890)
    | == Area 4: Test 1 ==
    | [4] Eggs_HD (1234567890)
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')

    target = Constants.parse_id_or_ipid(client, arg)[0]
    info = target.prepare_area_info(client.area, -1, False, as_mod=client.is_staff(),
                                    include_ipid=client.is_officer(),
                                    only_my_multiclients=True)
    info = '== Clients of {} =={}'.format(arg, info)
    client.send_ooc(info)


def ooc_cmd_music_list(client: ClientManager.Client, arg: str):
    """
    Sets your current personal music list. This list is persistent between area changes and works on
    a client basis.
    If given no arguments, it will return the music list to its default value
    (in config/music.yaml).
    Clients that do not process 'SM' packets can use this command without crashing, but it will
    have no visual effect.
    Returns an error if the given music list name included relative directories,
    was not found, caused an OS error when loading, or raised a YAML or asset syntax error when
    loading.

    SYNTAX
    /music_list <music_list>

    PARAMETERS
    <music_list>: Name of the intended music list

    EXAMPLES
    >>> /music_list dr2
    Load the "dr2" music list.
    >>> /music_list
    Reset the music list to its default value.
    """

    Constants.assert_command(client, arg)

    client.music_manager.command_list_load(
        client, arg, send_notifications=False)

    if arg:
        client.send_ooc(f'You are now seeing the personal music list `{arg}`.')
    else:
        if client.music_manager.if_default_show_hub_music:
            client.send_ooc('You are now seeing the hub music list.')
        else:
            client.send_ooc(
                'You are now seeing the default server music list.')
    client.send_music_list_view()


def ooc_cmd_music_list_info(client: ClientManager.Client, arg: str):
    """
    Returns your current music list.

    SYNTAX
    /music_list_info

    PARAMETERS
    None

    EXAMPLES
    >>> /music_list_info
    May return something like this:
    | $H: The current music list is the custom list `trial`.
    """

    Constants.assert_command(client, arg, parameters='=0')

    client.music_manager.command_list_info(client)


def ooc_cmd_mute(client: ClientManager.Client, arg: str):
    """ (OFFICER ONLY)
    Mutes given user based on client ID or IPID so that they are unable to speak in IC chat.
    If given IPID, it will mute all clients opened by the target. Otherwise, it will just mute the
    given client.
    Requires /unmute to undo.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /mute <client_id>
    /mute <client_ipid>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    EXAMPLES
    >>> /mute 1
    Mutes user with client ID 1.
    >>> /mute 1234567890
    Mutes all clients opened by the user with IPID 1234567890.
    """

    Constants.assert_command(client, arg, is_officer=True, parameters='=1')

    # Mute matching targets
    for c in Constants.parse_id_or_ipid(client, arg):
        logger.log_server('Muted {}.'.format(c.ipid), client)
        client.area.broadcast_ooc("{} was muted.".format(c.displayname))
        c.is_muted = True


def ooc_cmd_notecard(client: ClientManager.Client, arg: str):
    """
    Sets the content of your own notecard.
    Content over 1024 characters will be discarded.

    SYNTAX
    /notecard <content>

    PARAMETERS
    <content>: Content of your notecard

    EXAMPLE
    >>> /notecard Hello world
    Sets the content of your notecard to `Hello world`.
    """

    Constants.assert_command(client, arg, parameters='>0')

    client.notecard = arg[:1024]
    client.send_ooc(f'You set your notecard to `{client.notecard}`.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] set their notecard to '
                           f'`{client.notecard}`.', is_zstaff_flex=True)


def ooc_cmd_notecard_clear(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    Clears the content of your own notecard or, (STAFF ONLY) that of a given player by client ID.
    Returns an error if the target's notecard was already cleared, or if the given identifier
    does not correspond to a user.

    SYNTAX
    /notecard_clear {client_id}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {client_id}: Client identifier (number in brackets in /getarea)

    EXAMPLES
    >>> /notecard_clear
    Clears your own notecard
    >>> /notecard_clear 2
    Clears the notecard of player with client ID 2.
    """

    Constants.assert_command(client, arg, parameters='<2')

    if arg and not client.is_staff():
        raise ClientError.UnauthorizedError('You must be authorized to use the one-parameter '
                                            'version of this command.')
    if arg:
        target = Constants.parse_id(client, arg)
    else:
        target = client

    if target == client:
        if not client.notecard:
            raise ClientError('Your notecard is already empty.')
        client.notecard = ''
        client.send_ooc('Your notecard is now cleared.')
        client.send_ooc_others(f'(X) {client.displayname} [{client.id}] cleared their notecard.',
                               is_zstaff_flex=True)
    else:
        if not target.notecard:
            raise ClientError(f'The notecard of {target.displayname} [{target.id}] is '
                              f'already empty.')
        target.notecard = ''
        target.send_ooc('Your notecard was cleared.')
        client.send_ooc_others(f'(X) {client.displayname} [{client.id}] cleared the '
                               f'notecard of {target.displayname} [{target.id}] ({client.area.id})',
                               is_zstaff_flex=True, not_to={target})


def ooc_cmd_notecard_clear_area(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Clears the content of the notecards of all players in your current area.
    Returns an error if no player in the area has a notecard set.

    SYNTAX
    /notecard_clear_area

    PARAMETERS
    None

    EXAMPLES
    >>> /notecard_clear_area
    Clears the notecards of all players in your current area.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    targets = [target for target in client.area.clients if target.notecard]
    if not targets:
        raise ClientError(
            'No players in your current area have a notecard set.')

    for target in targets:
        target.notecard = ''

    client.send_ooc('You cleared the notecards of all players in the area.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] cleared the notecards of all '
                           f'players in their area ({client.area.id}).', is_zstaff_flex=True)
    client.send_ooc_others(f'The notecards of all players in your area were cleared.',
                           is_zstaff_flex=False, in_area=client.area)


def ooc_cmd_notecard_info(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    Returns the content of your current notecard or, (STAFF ONLY) that of a given player by
    client ID.
    Returns an error if the target's notecard is not set, or if the given identifier
    does not correspond to a user.

    SYNTAX
    /notecard_info {client_id}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {client_id}: Client identifier (number in brackets in /getarea)

    EXAMPLES
    >>> /notecard_info
    Gets the content of your own notecard.
    >>> /notecard_info 2
    Gets the content of the notecard of player with client ID 2.
    """

    Constants.assert_command(client, arg, parameters='<2')

    if arg and not client.is_staff():
        raise ClientError.UnauthorizedError('You must be authorized to use the one-parameter '
                                            'version of this command.')
    if arg:
        target = Constants.parse_id(client, arg)
    else:
        target = client

    if target == client:
        if not client.notecard:
            raise ClientError('Your notecard is empty.')
        client.send_ooc(f'Your notecard says `{client.notecard}`.')
    else:
        if not target.notecard:
            raise ClientError(
                f'The notecard of {target.displayname} [{target.id}] is empty.')
        client.send_ooc(f'The notecard of {target.displayname} [{target.id}] says '
                        f'`{target.notecard}`.')


def ooc_cmd_notecard_check(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Returns the contents of all notecards set by players in the current area.
    Returns an error if no player in the current area have any notecards set.

    SYNTAX
    /notecard_check

    PARAMETERS
    None

    EXAMPLES
    >>> /notecard_check
    Returns the contents of all notecards set by players in the current area.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    with_notecards = [
        target for target in client.area.clients if target.notecard]
    if not with_notecards:
        raise ClientError('No players in your current have any notecards set.')

    output = ''
    for target in sorted(with_notecards):
        output += f'\r\n[{target.id}] {target.displayname}: {target.notecard}'

    client.send_ooc(f'== Notecards in the current area =='
                    f'{output}')


def ooc_cmd_notecard_list(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Returns the contents of all notecards set by players in the hub.
    Returns an error if no player in the hub have any notecards set.

    SYNTAX
    /notecard_list

    PARAMETERS
    None

    EXAMPLES
    >>> /notecard_list
    Returns the contents of all notecards set by players in the hub.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    with_notecards = [
        target for target in client.hub.get_players() if target.notecard]
    if not with_notecards:
        raise ClientError('No players in the hub have any notecards set.')

    output = ''
    for target in sorted(with_notecards):
        output += f'\r\n[{target.id}] {target.displayname} ({target.area.id}): {target.notecard}'

    client.send_ooc(f'== Active notecards =='
                    f'{output}')


def ooc_cmd_notecard_reveal(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Reveals the contents of all notecards set by players in the area (possibly indicating that
    no notecards were set) to all players in the area.

    SYNTAX
    /notecard_reveal

    PARAMETERS
    None

    EXAMPLES
    >>> /notecard_reveal
    Reveals the contents of all notecards set by players in the area.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    with_notecards = [
        target for target in client.area.clients if target.notecard]

    output = ''
    for target in sorted(with_notecards):
        output += f'\r\n[{target.id}] {target.displayname}: {target.notecard}'
    if not output:
        output = '\r\n*No player in the area has set a notecard.'

    client.send_ooc('You revealed all notecards in the area.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] revealed all notecards in '
                           f'area {client.area.name} ({client.area.id}).', is_zstaff_flex=True)
    client.area.broadcast_ooc(
        f'The notecards in the area were revealed: {output}')


def ooc_cmd_notecard_reveal_count(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Tallies the number of times each notecard content of a player in the area was the content of
    some player in the area (possibly indicating that no notecards were set) and reveals the tally
    to all players in the area. This does not reveal who wrote which notecard.
    Two notecard contents are said to be the same if they are the same ignoring leading or trailing
    whitespace, as well as any capitalization or fullstops at the end.

    SYNTAX
    /notecard_reveal_count

    PARAMETERS
    None

    EXAMPLES
    >>> /notecard_reveal_count
    Reveals the frequency of each notecard.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    raw_notecards = [
        target.notecard for target in client.area.clients if target.notecard]
    if not raw_notecards:
        output = '\r\n*No player in the area has set a notecard.'
    else:
        notecards = []
        for raw_notecard in raw_notecards:
            notecard = raw_notecard.strip().upper()
            if notecard.endswith('.'):
                notecard = notecard[:-1]
            notecards.append(notecard)
        notecards.sort()
        tally = collections.Counter(notecards)
        output = ''
        for (value, count) in tally.most_common():
            output += f'\r\n*{value}: {count} of {tally.total()}'

    client.send_ooc('You revealed the tally of all notecards in the area.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] revealed the tally of all '
                           f'notecards in area {client.area.name} ({client.area.id}).',
                           is_zstaff_flex=True)
    client.area.broadcast_ooc(
        f'The tally of all notecards in the area was revealed: {output}')


def ooc_cmd_noteworthy(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Toggles the area being noteworthy or not. If made noteworthy, all players in the area will
    be notified in OOC and IC (as well as all watchers of a zone having the area but only in OOC),
    except those simultaneously blind and deaf, who receive no notifications.

    SYNTAX
    /noteworthy

    PARAMETERS
    None

    EXAMPLES
    Assuming the area starts being not noteworthy...
    >>> /noteworthy
    Sets the area as noteworthy.
    >>> /noteworthy
    Sets the area as not noteworthy.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    client.area.noteworthy = not client.area.noteworthy
    status = '' if client.area.noteworthy else 'no longer '
    client.send_ooc(f'You have marked your area as {status}noteworthy.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] has marked your area as '
                           f'{status}noteworthy.',
                           is_zstaff_flex=True, in_area=True)
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] has marked their area as '
                           f'{status}noteworthy ({client.area.id}).',
                           is_zstaff_flex=True, in_area=False)
    if client.area.noteworthy:
        client.send_ooc_others('Something catches your attention.', is_zstaff_flex=False,
                               in_area=True, pred=lambda c: not (c.is_deaf and c.is_blind))
        client.area.broadcast_ic_attention(ding=True)

    logger.log_server('[{}][{}]Set noteworthy status to {}'
                      .format(client.area.id, client.get_char_name(), client.area.noteworthy),
                      client)


def ooc_cmd_noteworthy_info(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Gets the noteworthy status and noteworthy text of the current area.

    SYNTAX
    /noteworthy_info

    PARAMETERS
    None

    EXAMPLES
    >>> /noteworthy_info
    | $H: The current area is currently noteworthy. The current noteworthy text is `[Test]`.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    status = {True: 'is', False: 'is not'}
    client.send_ooc(f'The current area {status[client.area.noteworthy]} currently noteworthy. '
                    f'The current noteworthy text is `{client.area.noteworthy_text}`.')


def ooc_cmd_noteworthy_set(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sets (and replaces!) the noteworthy text of the current area to the given one.
    If not given any text, it will set the text to be the area's default noteworthy text.
    The noteworthy text does not reset or change if the noteworthy status of an area changes.

    SYNTAX
    /noteworthy_set {text}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {text}: New noteworthy text.

    EXAMPLES
    Assuming you are in area 0
    >>> /noteworthy_set [You notice some broken glass on the floor]
    Sets the area noteworthy text in area 0 to be "[You notice some broken glass on the floor]".
    >>> /noteworthy_set
    Sets the area noteworthy text in area 0 to be the default text.
    """

    Constants.assert_command(client, arg, is_staff=True)

    if not arg:
        client.area.noteworthy_text = client.area.default_noteworthy_text
        client.send_ooc(
            'Reset the area noteworthy text to its original value.')
        client.send_ooc_others('(X) {} [{}] reset the area noteworthy text of your area to its '
                               'original value.'
                               .format(client.displayname, client.id),
                               is_zstaff_flex=True, in_area=True)
        client.send_ooc_others('(X) {} [{}] reset the area noteworthy text of area {} to its '
                               'original value.'
                               .format(client.displayname, client.id, client.area.name),
                               is_zstaff_flex=True, in_area=False)
        logger.log_server('[{}][{}]Reset the area noteworthy text in {}.'
                          .format(client.area.id, client.get_char_name(), client.area.name), client)

    else:
        client.area.noteworthy_text = arg
        client.send_ooc(
            'Updated the area noteworthy text to `{}`.'.format(arg))
        client.send_ooc_others('(X) {} [{}] set the area noteworthy text of your area to `{}`.'
                               .format(client.displayname, client.id, client.area.noteworthy_text),
                               is_zstaff_flex=True, in_area=True)
        client.send_ooc_others('(X) {} [{}] set the area noteworthy text of area {} to `{}`.'
                               .format(client.displayname, client.id, client.area.name,
                                       client.area.noteworthy_text),
                               is_zstaff_flex=True, in_area=False)
        logger.log_server('[{}][{}]Set the area noteworthy text to {}.'
                          .format(client.area.id, client.get_char_name(), arg), client)


def ooc_cmd_nsd(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Starts an NSD with the players of your trial in your area with time limit if given, defaulting
    to no time limit if not given. The NSD creator is automatically added as a NSD leader.
    Players in the area not part of the trial, already part of a minigame or that do not have a
    character are not added to the NSD. Players added to the NSD are ordered to switch to the
    'nsd' gamemode.
    Returns an error if you are not part of a trial or leader of one, if the trial reached its
    NSD limit, if you are already part of a minigame or do not have a participant character, or if
    the time is negative or above the server time limit.

    SYNTAX
    /nsd {length}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {length}: time in seconds, or in mm:ss, or in h:mm:ss; limited to TIMER_LIMIT in function
              Constants.parse_time_length. If given, it must be a positive integer.

    EXAMPLES
    >>> /nsd 3:00
    Starts an NSD with 3 minutes of time.
    >>> /nsd 120
    Starts an NSD with 120 seconds of time.
    """

    try:
        Constants.assert_command(client, arg, is_staff=True, parameters='<2')
    except ArgumentError:
        seconds = 300
    else:
        if not arg or arg == "0":
            seconds = 0
        else:
            seconds = Constants.parse_time_length(
                arg)  # Also internally validates

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial. You must start a trial with /trial before '
                          'starting a nonstop debate.')
    if not trial.is_leader(client):
        raise ClientError('You are not a leader of your trial.')

    try:
        nsd = trial.new_nsd(
            creator=client,
            autoadd_on_creation_existing_users=False,
            timer_start_value=seconds,
            require_participant_character=True,
            autoadd_on_trial_player_add=trial.get_autoadd_on_client_enter()
        )
    except TrialError.ManagerTooManyGamesError:
        raise ClientError('The trial already has an active nonstop debate. End the previous one '
                          'with /nsd_end.')
    except NonStopDebateError.AreaHitGameConcurrentLimitError:
        raise ClientError('This area already hosts another nonstop debate.')
    except NonStopDebateError.UserHitGameConcurrentLimitError:
        raise ClientError(
            'You are already part of another minigame in your trial.')
    except NonStopDebateError.UserHasNoCharacterError:
        raise ClientError(
            'You must have a participant character to create a nonstop debate.')

    if seconds > 0:
        client.send_ooc(f'You have created nonstop debate `{nsd.get_id()}` in area '
                        f'{client.area.name} with time limit {seconds} seconds.')
    else:
        client.send_ooc(f'You have created nonstop debate `{nsd.get_id()}` in area '
                        f'{client.area.name} with no time limit.')

    nsd.add_leader(client)

    for user in client.area.clients:
        if user == client:
            continue
        try:
            nsd.add_player(user)
        except NonStopDebateError.UserNotPlayerError:
            client.send_ooc(f'Unable to add player {user.displayname} [{user.id}]: '
                            f'they are not part of your trial.')
        except NonStopDebateError.UserHitGameConcurrentLimitError:
            client.send_ooc(f'Unable to add player {user.displayname} [{user.id}]: '
                            f'they are already part of another minigame.')
        except NonStopDebateError.UserHasNoCharacterError:
            client.send_ooc(f'Unable to add player {user.displayname} [{user.id}]: '
                            f'they must have a participant character to join this minigame.')

    players = sorted(nsd.get_players(), key=lambda c: c.displayname)
    player_list = '\n'.join([
        f'[{player.id}] {player.displayname}' for player in players
    ])

    client.send_ooc(f'These players were automatically added to your nonstop debate: '
                    f'\n{player_list}')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] created a nonstop debate '
                           f'`{nsd.get_id()}` in area {client.area.name} ({client.area.id}).',
                           is_zstaff_flex=True)
    client.send_ooc_others(f'You were added to nonstop debate `{nsd.get_id()}`.',
                           pred=lambda c: c in trial.get_players())
    client.send_ooc_others(f'Nonstop debate `{nsd.get_id()}` started in your area.',
                           pred=lambda c: c in nsd.get_nonplayer_users_in_areas())


def ooc_cmd_nsd_accept(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Accepts a break response given by a user of your NSD and ends it. That player's influence is
    restored by 0.5 points.
    Returns an error if you are not part of a trial or an NSD or leader of it, or if the NSD is in
    not in post-break intermission mode.

    SYNTAX
    /nsd_accept

    PARAMETERS
    None

    EXAMPLE
    >>> /nsd_accept
    Accepts a break response from the NSD and automatically ends the NSD.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')
    try:
        nsd = trial.get_nsd_of_user(client)
    except TrialError.UserNotInMinigameError:
        raise ClientError('You are not part of a nonstop debate.')
    if not nsd.is_leader(client):
        raise ClientError('You are not a leader of your nonstop debate.')

    # Save because NSD is destroyed!
    leaders, regulars = nsd.get_leaders(), nsd.get_regulars()
    nonplayers = nsd.get_nonplayer_users_in_areas()

    try:
        existing = nsd.accept_break()
    except NonStopDebateError.NSDNotInModeError:
        raise ClientError(
            'You may not accept a break for your nonstop debate at this moment.')

    if existing:
        client.send_ooc('You accepted the break and ended the nonstop debate. The breaker '
                        'recovered 0.5 influence.')
        client.send_ooc_others(f'(X) {client.displayname} [{client.id}] accepted the break and '
                               f'ended the nonstop debate. The breaker recovered 0.5 influence.',
                               pred=lambda c: c in leaders)
    else:
        client.send_ooc('You accepted the break and ended the nonstop debate. Since the breaker '
                        'had since disconnected or left the nonstop debate, their influence '
                        'remained unchanged.')
        client.send_ooc_others(f'(X) {client.displayname} [{client.id}] accepted the break and '
                               f'ended the nonstop debate. Since the breaker had since '
                               f'disconnected or left the nonstop debate, their influence '
                               f'remained unchanged.',
                               pred=lambda c: c in leaders)
    client.send_ooc_others('Your nonstop debate was ended by an accepted break.',
                           pred=lambda c: c in regulars)
    client.send_ooc_others('The nonstop debate you were watching was ended by an accepted break.',
                           pred=lambda c: c in nonplayers)


def ooc_cmd_nsd_add(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Adds another user to your NSD.
    Returns an error if you are not a part of a trial or an NSD or is not a leader, if the
    NSD reached its player limit, or if the target cannot be found, is not part of the trial, does
    not have a participant character or is part of some NSD.

    SYNTAX
    /nsd_add <user_ID> <message>

    PARAMETERS
    <user_id>: Either the client ID (number in brackets in /getarea), character name, edited-to
               character, custom showname or OOC name of the intended recipient.
    <message>: Message to be sent.

    EXAMPLES
    >>> /nsd_add 1
    Adds the user with client ID 1 to the trial.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='>0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')

    try:
        nsd = trial.get_nsd_of_user(client)
    except TrialError.UserNotInMinigameError:
        raise ClientError('You are not part of a nonstop debate.')
    if not nsd.is_leader(client):
        raise ClientError('You are not a leader of your nonstop debate.')

    cm = client.server.client_manager
    target, _, _ = cm.get_target_public(client, arg, only_in_area=True)

    try:
        nsd.add_player(target)
    except NonStopDebateError.UserNotPlayerError:
        raise ClientError('This player is not part of your trial.')
    except NonStopDebateError.UserNotInAreaError:
        raise ClientError(
            'This player is not part of an area part of this nonstop debate.')
    except NonStopDebateError.UserHasNoCharacterError:
        raise ClientError('This player must have a participant character to join this nonstop '
                          'debate.')
    except NonStopDebateError.UserHitGameConcurrentLimitError:
        raise ClientError(
            'This player is already part of another nonstop debate.')
    except NonStopDebateError.UserAlreadyPlayerError:
        raise ClientError(
            'This player is already part of this nonstop debate.')

    client.send_ooc(
        f'You added {target.displayname} [{target.id}] to your nonstop debate.')
    client.send_ooc_others(f'(X) {client.displayname} added {target.displayname} [{target.id}] '
                           f'to your nonstop debate.',
                           pred=lambda c: c in trial.get_leaders())
    target.send_ooc(f'You were added to the nonstop debate `{nsd.get_id()}`.')


def ooc_cmd_nsd_autoadd(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Toggles your NSD automatically attempting to add users as players who themselves are added as
    players of the parent trial on/off.
    Returns an error if you are not part of a trial or an NSD, or are not a leader of your NSD.

    SYNTAX
    /nsd_autoadd

    PARAMETERS
    None

    EXAMPLES
    Assuming autoadd is off...
    >>> /nsd_autoadd
    Turns autoadd on.
    >>> /nsd_autoadd
    Turns autoadd off.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')
    try:
        nsd = trial.get_nsd_of_user(client)
    except TrialError.UserNotInMinigameError:
        raise ClientError('You are not part of a nonstop debate.')
    if not nsd.is_leader(client):
        raise ClientError('You are not a leader of your nonstop debate.')

    status = {True: 'now', False: 'no longer'}
    new_autoadd = not nsd.get_autoadd_on_trial_player_add()
    nsd.set_autoadd_on_trial_player_add(new_autoadd)

    client.send_ooc(f'Your nonstop debate will {status[new_autoadd]} attempt to automatically add '
                    f'future users who are added as players of your trial.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] has set your nonstop debate so '
                           f'that it will {status[new_autoadd]} attempt to automatically add '
                           f'future users who are added as players of your trial.',
                           pred=lambda c: c in nsd.get_leaders())


def ooc_cmd_nsd_end(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Ends your NSD. Every player of the NSD is ordered to switch back to the 'trial' gamemode.
    Returns an error if you are not a part of a trial or NSD, or are not a leader of it.

    SYNTAX
    /nsd_end

    PARAMETERS
    None

    EXAMPLE
    >>> /nsd_end
    Ends your NSD.
    """

    Constants.assert_command(client, arg, parameters='=0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')
    try:
        nsd = trial.get_nsd_of_user(client)
    except TrialError.UserNotInMinigameError:
        raise ClientError('You are not part of a nonstop debate.')
    if not nsd.is_leader(client):
        raise ClientError('You are not a leader of your nonstop debate.')

    leaders = nsd.get_leaders()
    regulars = nsd.get_regulars()
    nonplayers = nsd.get_nonplayer_users_in_areas()

    nsd.destroy()

    client.send_ooc('You ended your nonstop debate.')
    client.send_ooc_others('The nonstop debate you were watching was ended.',
                           pred=lambda c: c in nonplayers)
    client.send_ooc_others('Your nonstop debate was ended.',
                           pred=lambda c: c in regulars)
    client.send_ooc_others(f'(X) {client.displayname} ended your nonstop debate.',
                           pred=lambda c: c in leaders)


def ooc_cmd_nsd_info(client: ClientManager.Client, arg: str):
    """
    Returns information about your current NSD.
    Returns an error if you are not part of a trial or an NSD.

    SYNTAX
    /nsd_info

    PARAMETERS
    None

    EXAMPLE
    >>> /nsd_info
    Returns NSD info.
    """

    Constants.assert_command(client, arg, parameters='=0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')
    try:
        nsd = trial.get_nsd_of_user(client)
    except TrialError.UserNotInMinigameError:
        raise ClientError('You are not part of a nonstop debate.')

    nid = nsd.get_id()
    area = next(iter(nsd.get_areas()))
    leaders = nsd.get_leaders()
    regulars = nsd.get_regulars()

    num_members = len(leaders.union(regulars))
    leaders = ', '.join(
        [f'{c.displayname} [{c.id}]' for c in leaders]) if leaders else 'None'
    regulars = ', '.join(
        [f'{c.displayname} [{c.id}]' for c in regulars]) if regulars else 'None'
    info = (f'Nonstop debate {nid} [{num_members}/-] ({area.id}). '
            f'Leaders: {leaders}. Regular members: {regulars}.')
    client.send_ooc(info)


def ooc_cmd_nsd_join(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Enrolls you into a nonstop debate by nonstop debate ID.
    Returns an error if you are not part of a trial, if the NSD ID is invalid, if you are not part
    of an area part of the NSD, if you do not have a participant character when trying to join the
    NSD, or if you are already part of this or another NSD.

    SYNTAX
    /nsd_join <nsd_id>

    PARAMETERS
    <nsd_id>: NSD ID

    EXAMPLES
    >>> /nsd_join trial0g0
    Makes you join NSD trial0g0.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='>0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')

    try:
        nsd = trial.get_minigame_by_id(arg)
    except TrialError.ManagerInvalidGameIDError:
        raise ClientError(f'Unrecognized nonstop debate ID `{arg}`.')

    try:
        nsd.add_player(client)
    except NonStopDebateError.UserNotInAreaError:
        raise ClientError(
            'You are not part of an area part of this nonstop debate.')
    except NonStopDebateError.UserHasNoCharacterError:
        raise ClientError(
            'You must have a participant character to join this nonstop debate.')
    except NonStopDebateError.UserHitGameConcurrentLimitError:
        raise ClientError('You are already part of another nonstop debate.')
    except NonStopDebateError.UserAlreadyPlayerError:
        raise ClientError('You are already part of this nonstop debate.')

    client.send_ooc(f'You joined nonstop debate `{arg}`.')
    client.send_ooc('Become a leader of your nonstop debate with /nsd_lead')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] joined your nonstop debate.',
                           pred=lambda c: c in nsd.get_leaders())


def ooc_cmd_nsd_kick(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Kicks a user by user ID off your NSD.
    Returns an error if you are not part of a trial or NSD or leader of it, if the target is not
    found or already not a part of your NSD, or if the target is you.

    SYNTAX
    /nsd_kick <user_id>

    PARAMETERS
    <user_id>: Either the client ID (number in brackets in /getarea), character name, edited-to
               character, custom showname or OOC name of the intended recipient.

    EXAMPLES
    >>> /nsd_kick 1 5
    Kicks client ID 1 off your trial.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='>0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')
    try:
        nsd = trial.get_nsd_of_user(client)
    except TrialError.UserNotInMinigameError:
        raise ClientError('You are not part of a nonstop debate.')
    if not nsd.is_leader(client):
        raise ClientError('You are not a leader of your nonstop debate.')

    cm = client.server.client_manager
    target, _, _ = cm.get_target_public(client, arg, only_in_area=True)
    if client == target:
        raise ClientError('You cannot kick yourself off your nonstop debate.')

    try:
        nsd.remove_player(target)
    except NonStopDebateError.UserNotPlayerError:
        raise ClientError('This player is not part of your nonstop debate.')

    client.send_ooc(
        f'You have kicked {target.displayname} [{target.id}] off your nonstop debate.')
    target.send_ooc('You were kicked off your nonstop debate.')
    client.send_ooc_others(f'(X) {client.name} [{client.id}] has kicked {target.displayname} '
                           f'[{target.id}] off your nonstop debate.',
                           pred=lambda c: c != target and c in trial.get_leaders())


def ooc_cmd_nsd_lead(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Makes you a leader of your NSD.
    Returns an error if you are not part of a trial or an NSD, or if you are already leader of
    the NSD.

    SYNTAX
    /nsd_lead

    PARAMETERS
    None

    EXAMPLE
    >>> /nsd_lead
    Makes you leader of the NSD.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')
    try:
        nsd = trial.get_nsd_of_user(client)
    except TrialError.UserNotInMinigameError:
        raise ClientError('You are not part of a nonstop debate.')

    try:
        nsd.add_leader(client)
    except NonStopDebateError.UserAlreadyLeaderError:
        raise ClientError('You are already a leader of this nonstop debate.')

    client.send_ooc('You are now a leader of your nonstop debate.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] is now a leader of your '
                           f'nonstop debate.', pred=lambda c: c in nsd.get_leaders())


def ooc_cmd_nsd_leave(client: ClientManager.Client, arg: str):
    """
    Makes you leave your current NSD. It will also notify all other remaining trial leaders of
    your departure.
    If you were the only member of the NSD, the NSD will be destroyed.
    Returns an error if you are not part of a trial or an NSD.

    SYNTAX
    /nsd_leave

    PARAMETERS
    None

    EXAMPLES
    >>> /nsd_leave
    Makes you leave your current NSD.
    """

    Constants.assert_command(client, arg, parameters='=0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')

    try:
        nsd = trial.get_nsd_of_user(client)
    except TrialError.UserNotInMinigameError:
        raise ClientError('You are not part of a nonstop debate.')
    nid = nsd.get_id()  # Get ID now because NSD may be deleted
    # Get nonplayers now because NSD may be deleted
    nonplayers = nsd.get_nonplayer_users_in_areas()
    client.send_ooc(f'You have left nonstop debate `{nid}`.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] has left your nonstop debate.',
                           pred=lambda c: c in nsd.get_leaders())
    nsd.remove_player(client)

    if nsd.is_unmanaged():
        client.send_ooc(f'Your nonstop debate `{nid}` was automatically '
                        f'ended as it lost all its players.')
        client.send_ooc_others(f'(X) Nonstop debate `{nid}` was automatically '
                               f'ended as it lost all its players.',
                               is_zstaff_flex=True, not_to=nonplayers)
        client.send_ooc_others('The nonstop debate you were watching was automatically ended '
                               'as it lost all its players.',
                               is_zstaff_flex=False, pred=lambda c: c in nonplayers)


def ooc_cmd_nsd_loop(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sets your current NSD to be in looping mode. While in looping mode, messages recorded during
    recording mode will be played one after another, and no IC messages that do not have
    counter, consent or perjury bullets are allowed. Such bulleted messages if sent while in
    looping mode will put the NSD in intermission mode; and so will playing all of the recorded
    messages.
    Returns an error if you are not part of a trial or NSD or leader for it, or if the NSD is not
    in intermission or post-break intermission mode.

    SYNTAX
    /nsd_loop

    PARAMETERS
    None

    EXAMPLE
    >>> /nsd_loop
    Loops your NSD.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')
    try:
        nsd = trial.get_nsd_of_user(client)
    except TrialError.UserNotInMinigameError:
        raise ClientError('You are not part of a nonstop debate.')
    if not nsd.is_leader(client):
        raise ClientError('You are not a leader of your nonstop debate.')

    try:
        nsd.set_looping()
    except NonStopDebateError.NSDAlreadyInModeError:
        raise ClientError('The nonstop debate is already in this mode.')
    except NonStopDebateError.NSDNotInModeError:
        raise ClientError('You may not loop a nonstop debate at this moment.')
    else:
        client.send_ooc('You have set your nonstop debate to start looping.')
        client.send_ooc_others(f'(X) {client.displayname} [{client.id}] has set your nonstop '
                               f'debate to start looping.', pred=lambda c: c in nsd.get_leaders())
        client.send_ooc_others('Your nonstop debate is now looping.',
                               pred=lambda c: c in nsd.get_regulars())
        client.send_ooc_others('The nonstop debate you are watching is now looping.',
                               pred=lambda c: c in nsd.get_nonplayer_users_in_areas())


def ooc_cmd_nsd_pause(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Pauses your current NSD and puts it in intermission mode. Players part of the NSD are put in
    the 'trial' gamemode.
    Returns an error if you are not part of a trial or NSD or leader for it, or if the NSD is not
    in recording or looping mode.

    SYNTAX
    /nsd_pause

    PARAMETERS
    None

    EXAMPLE
    >>> /nsd_pause
    Pauses your NSD.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')
    try:
        nsd = trial.get_nsd_of_user(client)
    except TrialError.UserNotInMinigameError:
        raise ClientError('You are not part of a nonstop debate.')
    if not nsd.is_leader(client):
        raise ClientError('You are not a leader of your nonstop debate.')

    try:
        nsd.set_intermission()
    except NonStopDebateError.NSDAlreadyInModeError:
        raise ClientError('The nonstop debate is already in this mode.')
    except NonStopDebateError.NSDNotInModeError:
        raise ClientError('You may not pause a nonstop debate at this moment.')
    else:
        client.send_ooc('You have paused your nonstop debate.')
        client.send_ooc_others(f'(X) {client.displayname} [{client.id}] has paused your nonstop '
                               f'debate.', pred=lambda c: c in nsd.get_leaders())
        client.send_ooc_others('Your nonstop debate was paused.',
                               pred=lambda c: c in nsd.get_regulars())
        client.send_ooc_others('The nonstop debate you were watching was paused.',
                               pred=lambda c: c in nsd.get_nonplayer_users_in_areas())


def ooc_cmd_nsd_resume(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Resumes the mode the NSD was in before it was put in intermission mode.
    Returns an error if you are not part of a trial or an NSD or leader of it, or if the NSD is in
    not in intermission or post-break intermission mode.

    SYNTAX
    /nsd_loop

    PARAMETERS
    None

    EXAMPLE
    >>> /nsd_loop
    Loops your NSD
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')
    try:
        nsd = trial.get_nsd_of_user(client)
    except TrialError.UserNotInMinigameError:
        raise ClientError('You are not part of a nonstop debate.')
    if not nsd.is_leader(client):
        raise ClientError('You are not a leader of your nonstop debate.')

    try:
        resumed_mode = nsd.resume()
    except NonStopDebateError.NSDNotInModeError:
        raise ClientError(
            'You may not resume a nonstop debate at this moment.')
    else:
        mode = resumed_mode.name.lower()
        if mode == 'prerecording':
            mode = 'recording'
        client.send_ooc(
            f'You have put your nonstop debate back in {mode} mode.')
        client.send_ooc_others(f'(X) {client.displayname} [{client.id}] has put your nonstop '
                               f'debate back in {mode} mode.',
                               pred=lambda c: c in nsd.get_leaders())
        client.send_ooc_others(f'Your nonstop debate is now in {mode} mode again.',
                               pred=lambda c: c in nsd.get_regulars())
        client.send_ooc_others(f'The nonstop debate you are watching is now in {mode} mode again.',
                               pred=lambda c: c in nsd.get_nonplayer_users_in_areas())


def ooc_cmd_nsd_reject(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Rejects a break response given by a user of your NSD. That player's influence is decreased
    by 1 point. The NSD will remain in post-break intermission mode, but NSD leaders will be
    prompted to end or resume the NSD.
    Returns an error if you are not part of a trial or an NSD or leader of it, or if the NSD is in
    not in post-break intermission mode.

    SYNTAX
    /nsd_reject

    PARAMETERS
    None

    EXAMPLE
    >>> /nsd_reject
    Rejects a break response from the NSD
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')
    try:
        nsd = trial.get_nsd_of_user(client)
    except TrialError.UserNotInMinigameError:
        raise ClientError('You are not part of a nonstop debate.')
    if not nsd.is_leader(client):
        raise ClientError('You are not a leader of your nonstop debate.')

    try:
        existing = nsd.reject_break()
    except NonStopDebateError.NSDNotInModeError:
        raise ClientError(
            'You may not reject a break for your nonstop debate at this moment.')

    if existing:
        client.send_ooc(
            'You rejected the break. The breaker lost 1 influence.')
        client.send_ooc_others(f'(X) {client.displayname} [{client.id}] rejected the break. The '
                               f'breaker lost 1 influence.',
                               pred=lambda c: c in nsd.get_leaders())
    else:
        client.send_ooc('You rejected the break. Since the breaker had since disconnected or left '
                        'the nonstop debate, their influence remained unchanged.')
        client.send_ooc_others(f'(X) {client.displayname} [{client.id}] rejected the break. Since '
                               f'the breaker had since disconnected or left the nonstop debate, '
                               f'their influence remained unchanged.',
                               pred=lambda c: c in nsd.get_leaders())

    client.send_ooc(
        'Send /nsd_resume to resume the debate, /nsd_end to end the debate.')
    client.send_ooc_others('The break was rejected, so the debate continues!',
                           pred=lambda c: c in nsd.get_regulars())
    client.send_ooc_others('The break was rejected, so the debate continues!',
                           pred=lambda c: c in nsd.get_nonplayer_users_in_areas())


def ooc_cmd_nsd_unlead(client: ClientManager.Client, arg: str):
    """
    Removes your NSD leader role.
    Returns an error if you are not part of a trial or an NSD, or if you are already not leader
    of that NSD.

    SYNTAX
    /nsd_unlead

    PARAMETERS
    None

    EXAMPLE
    >>> /nsd_unlead
    Removes your trial leader role.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')
    try:
        nsd = trial.get_nsd_of_user(client)
    except TrialError.UserNotInMinigameError:
        raise ClientError('You are not part of a nonstop debate.')

    try:
        nsd.remove_leader(client)
    except TrialError.UserNotLeaderError:
        raise ClientError(
            'You are already not a leader of this nonstop debate.')

    client.send_ooc('You are no longer a leader of your nonstop debate.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] is no longer a leader of your '
                           f'nonstop debate.', pred=lambda c: c in nsd.get_leaders())


def ooc_cmd_online(client: ClientManager.Client, arg: str):
    """
    Returns how many players are online.

    SYNTAX
    /online

    PARAMETERS
    None

    EXAMPLE
    Assuming there are 2 players online in a server of maximum capacity 100...
    >>> /online
    Will return: "Online: 2/100"
    """

    Constants.assert_command(client, arg, parameters='=0')

    client.send_ooc("Online: {}/{}"
                    .format(client.server.get_player_count(), client.server.config['playerlimit']))


def ooc_cmd_ooc_mute(client: ClientManager.Client, arg: str):
    """ (OFFICER ONLY)
    Mutes a user from the OOC chat by their OOC username.
    Requires /ooc_unmute to undo.
    Returns an error if no player has the given OOC username.

    SYNTAX
    /ooc_mute <ooc_name>

    PARAMETERS
    <ooc_name>: Client OOC username

    EXAMPLE
    >>> /ooc_mute Aba
    Mutes from OOC the user with username `Aba`.
    """

    try:
        Constants.assert_command(client, arg, is_officer=True, parameters='>0')
    except ArgumentError:
        raise ArgumentError(
            'You must specify a target. Use /ooc_mute <ooc_name>.')

    targets = client.server.client_manager.get_targets(
        client, TargetType.OOC_NAME, arg, False)
    if not targets:
        raise ArgumentError('Targets not found. Use /ooc_mute <ooc_name>.')

    for c in targets:
        c.is_ooc_muted = True
        logger.log_server('OOC-muted {}.'.format(c.ipid), client)
        client.area.broadcast_ooc("{} was OOC-muted.".format(c.name))


def ooc_cmd_ooc_unmute(client: ClientManager.Client, arg: str):
    """ (OFFICER ONLY)
    Unmutes a user from the OOC chat by their OOC username.
    Requires /ooc_mute to undo.
    Returns an error if no player has the given OOC username.

    SYNTAX
    /ooc_unmute <ooc_name>

    PARAMETERS
    <ooc_name>: Client OOC username

    EXAMPLE
    >>> /ooc_unmute Aba
    Unmutes from OOC the user with username `Aba`.
    """

    try:
        Constants.assert_command(client, arg, is_officer=True, parameters='>0')
    except ArgumentError:
        raise ArgumentError(
            'You must specify a target. Use /ooc_unmute <ooc_name>.')

    targets = client.server.client_manager.get_targets(
        client, TargetType.OOC_NAME, arg, False)
    if not targets:
        raise ArgumentError('Target not found. Use /ooc_mute <ooc_name>.')

    for c in targets:
        c.is_ooc_muted = False
        logger.log_server('OOC-unmuted {}.'.format(c.ipid), client)
        client.area.broadcast_ooc("{} was OOC-unmuted.".format(c.name))


def ooc_cmd_paranoia(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Changes the player paranoia level of a user by client ID, which affects the probability a
    user receives a phantom peek message every phantom peek cycle. The player paranoia level
    is a percentage from -100 to 100, by default 2.
    A phantom peek message is a message that looks like one received from being an area that was
    just peeked into.
    A phantom peek cycle is a cycle of a length randomly chosen between 150 to 450 seconds, after
    which the server, with probability "player paranoia + zone paranoia", starts a timer of length
    a random number less than 150 seconds, after which it sends the user a phantom peek message
    if they are not blind and not staff, in an area that is not a lobby or private area, and they
    have a participant character selected. A new phantom peek cycle is restarted regardless of
    success after the old one expires.
    Returns an error if the given identifier does not correspond to a user, or if the new player
    paranoia level is not a number from -100 to 100.

    SYNTAX
    /paranoia <client_id> <player_paranoia_level>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <player_paranoia_level>: New intended player paranoia level

    EXAMPLES
    >>> /paranoia 2 5
    Sets the player paranoia level of user with client ID 2 to 5%.
    >>> /paranoia 10 -10
    Sets the player paranoia level of user with client ID 10 to -10%.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=2')

    raw_id, raw_paranoia = arg.split(' ')
    target = Constants.parse_id(client, raw_id)
    try:
        paranoia = float(raw_paranoia)
    except ValueError:
        raise ClientError('New player paranoia value must be a number.')
    if not (-100 <= paranoia <= 100):
        raise ClientError(
            'New player paranoia value must be a number from -100 to 100.')

    target.paranoia = paranoia
    client.send_ooc(f'You set the player paranoia level of {target.displayname} [{target.id}] to '
                    f'{paranoia}.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] set the player paranoia level '
                           f'of {target.displayname} [{target.id}] to {paranoia} '
                           f'({client.area.id}).',
                           is_zstaff_flex=True)


def ooc_cmd_paranoia_info(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Gets the current player paranoia level by client ID.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /paranoia_info <client_id>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)

    EXAMPLES
    >>> /paranoia_info 7
    Gets the player paranoia level of user with client ID 7.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')

    target = Constants.parse_id(client, arg)
    if target.paranoia == 2:
        client.send_ooc(f'The paranoia level of {target.displayname} [{target.id}] is the '
                        f'default level of 2.')
    else:
        client.send_ooc(f'The paranoia level of {target.displayname} [{target.id}] is '
                        f'{target.paranoia}.')


def ooc_cmd_party(client: ClientManager.Client, arg: str):
    """
    Creates a party and makes you the leader of it. Party members will all move in groups
    automatically. It also returns a party ID players can use to join the party.
    Returns an error if you are in area where the lights are off, if the server has
    reached its party limit, or if you are following someone.

    SYNTAX
    /party

    PARAMETERS
    None

    EXAMPLES
    >>> /party
    Creates a party.
    """

    Constants.assert_command(client, arg, parameters='=0')

    if not client.is_staff() and client.is_blind:
        raise ClientError('You cannot create a party as you are blind.')
    if not client.area.lights:
        raise AreaError('You cannot create a party while the lights are off.')
    if client.following:
        raise PartyError('You cannot create a party while following someone.')

    party = client.server.party_manager.new_party(client, tc=True)
    client.send_ooc('You have created party {}.'.format(party.get_id()))
    client.send_ooc('Invite others to your party with /party_invite <user_id>')
    client.send_ooc_others('(X) {} [{}] has created party {} ({}).'
                           .format(client.displayname, client.id, party.get_id(), client.area.id),
                           is_zstaff_flex=True)


def ooc_cmd_party_end(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    Ends your party if not given arguments, or (STAFF ONLY) ends a party by party ID.
    Also sends notifications to the former members if you were visible.
    Returns an error for non-authorized users if they try to end other parties or they are not
    a leader of their own party.

    SYNTAX
    /party_end {party_id}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {party_id}: Party to end

    EXAMPLES
    Assuming you were part of party 11037...
    >>> /party_end
    Ends party 11037.
    >>> /party_end 73011
    Ends party 73011.
    """

    try:
        Constants.assert_command(client, arg, is_staff=True, parameters='<2')
    except ClientError.UnauthorizedError:
        Constants.assert_command(client, arg, parameters='=0')

    if not arg:
        party = client.get_party()
    else:
        party = client.server.party_manager.get_party(arg)

    if not party.is_leader(client) and not client.is_staff():
        raise PartyError('You are not a leader of your party.')

    client.server.party_manager.end_party(party)
    if arg:
        client.send_ooc('You have ended party {}.'.format(party.get_id()))
    else:
        client.send_ooc('You have ended your party.')

    culprit = client.displayname if not arg else 'A staff member'
    for x in party.get_members(uninclude={client}):
        if x.is_staff() or client.is_visible:
            x.send_ooc('{} has ended your party.'.format(culprit))


def ooc_cmd_party_id(client: ClientManager.Client, arg: str):
    """
    Obtains your party ID.
    Returns an error if you are not part of a party.

    SYNTAX
    /party_id

    PARAMETERS
    None

    EXAMPLES
    Assuming you were part of party 11037...
    >>> /party_id
    May return something like "Your party ID is 11037".
    """

    Constants.assert_command(client, arg, parameters='=0')

    party = client.get_party(tc=True)
    client.send_ooc('Your party ID is: {}'.format(party.get_id()))


def ooc_cmd_party_invite(client: ClientManager.Client, arg: str):
    """
    Sends an invite to another user by client ID to join the party. The invitee will receive an
    OOC message with your name and party ID so they can join.
    The invitee must be in the same area as you. If that is not the case (and you
    used a client ID), but the invitee is in an area that can be reached by screams and is not
    deaf, they will receive a notification of the party invitation attempt, but will not be invited.
    Returns an error if you are not part of a party, you are not a party leader or staff member,
    if the target is not in the same area as you, or if the target is already invited.

    SYNTAX
    /party_invite <client_id>

    PARAMETERS
    <user_id>: Either the client ID (number in brackets in /getarea), character name, edited-to
               character, custom showname or OOC name of the intended recipient.

    EXAMPLES
    >>> /party_invite 2
    Invites the user with client ID 2 to join your party.
    """

    Constants.assert_command(client, arg, parameters='=1')

    party = client.get_party(tc=True)
    if not party.is_leader(client) and not client.is_staff():
        raise PartyError('You are not a leader of your party.')

    c, _, _ = client.server.client_manager.get_target_public(client, arg)
    # Check if invitee is in the same area
    if c.area != party.area:
        if c.area.name in client.area.scream_range and not c.is_deaf:
            msg = ('You hear screeching of someone asking you to join their party but they seem '
                   'too far away to even care all that much.')
            c.send_ooc(msg)
        raise PartyError('The player is not in your area.')

    party.add_invite(c, tc=False)

    client.send_ooc(
        'You have invited {} to join your party.'.format(c.displayname))
    for x in party.get_leaders(uninclude={client}):
        x.send_ooc('{} has invited {} to join your party.'
                   .format(client.displayname, c.displayname))
    c.send_ooc('{} has invited you to join their party {}.'
               .format(client.displayname, party.get_id()))
    c.send_ooc('Accept the invitation with /party_join {}'.format(party.get_id()))


def ooc_cmd_party_join(client: ClientManager.Client, arg: str):
    """
    Enrolls you into a party by party ID provided you were previously invited to it.
    Returns an error if the party ID does not exist, you are already part of a party, if the
    party reached its maximum number of members, or if you are following someone.

    SYNTAX
    /party_join <party_id>

    PARAMETERS
    <party_id>: Party ID

    EXAMPLES
    >>> /party_join 11037
    If previously invited, you will join party 11037.
    """

    Constants.assert_command(client, arg, split_spaces=True, parameters='=1')
    if client.following:
        raise PartyError('You cannot join a party while following someone.')

    party = client.server.party_manager.get_party(arg)
    party.add_member(client, tc=True)

    client.send_ooc('You have joined party {}.'.format(party.get_id()))

    for c in party.get_members(uninclude={client}):
        if c.is_staff() or client.is_visible:
            c.send_ooc('{} has joined your party.'.format(client.displayname))


def ooc_cmd_party_kick(client: ClientManager.Client, arg: str):
    """
    Kicks a user by some ID off your party. Also sends a notification to party leaders and the
    target if you were visible.
    Returns an error if you are not a leader of your party or the target is not a member.

    SYNTAX
    /party_kick <client_id>

    PARAMETERS
    <user_id>: Either the client ID (number in brackets in /getarea), character name, edited-to
               character, custom showname or OOC name of the intended recipient.

    EXAMPLES
    >>> /party_kick 2
    Kicks the user with client ID 2 off your party.
    """

    Constants.assert_command(client, arg, parameters='=1')

    party = client.get_party()
    if not party.is_leader(client) and not client.is_staff():
        raise PartyError('You are not a leader of your party.')

    c, _, _ = client.server.client_manager.get_target_public(client, arg)
    if c == client:
        raise PartyError('You cannot kick yourself off your party.')

    party.remove_member(c)
    client.send_ooc('You have kicked {} off your party.'.format(c.displayname))
    if c.is_staff() or client.is_visible:
        c.send_ooc('{} has kicked you off your party.'.format(
            client.displayname))
    for x in party.get_leaders(uninclude={client}):
        if x.is_staff() or client.is_visible:
            x.send_ooc('{} has kicked {} off your party.'
                       .format(client.displayname, c.displayname))


def ooc_cmd_party_lead(client: ClientManager.Client, arg: str):
    """
    Sets you as leader of your party and announces all other party leaders of it. Party leaders
    can send invites to other users to join the party.
    Returns an error if you are not part of a party or you are already a leader.

    SYNTAX
    /party_lead

    PARAMETERS
    None

    EXAMPLES
    >>> /party_lead
    Sets you as leader of your party.
    """

    Constants.assert_command(client, arg, parameters='=0')

    party = client.get_party()
    party.add_leader(client, tc=True)
    client.send_ooc('You are now a leader of your party.')
    for c in party.get_leaders(uninclude={client}):
        if c.is_staff() or client.is_visible:
            c.send_ooc('{} is now a leader of your party.'.format(
                client.displayname))


def ooc_cmd_party_leave(client: ClientManager.Client, arg: str):
    """
    Makes you leave your current party. It will also notify all other remaining members if you were
    not sneaking. If instead you were the only member of the party, the party will be ended.
    Returns an error if you are not part of a party.

    SYNTAX
    /party_leave

    PARAMETERS
    None

    EXAMPLES
    >>> /party_leave
    Makes you leave your current party.
    """

    Constants.assert_command(client, arg, parameters='=0')

    party = client.get_party(tc=True)
    party.remove_member(client)

    client.send_ooc('You have left party {}.'.format(party.get_id()))

    for c in party.get_members(uninclude={client}):
        if c.is_staff() or client.is_visible:
            c.send_ooc('{} has left your party.'.format(client.displayname))


def ooc_cmd_party_list(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Lists all active parties in the server. Includes details such as: party ID, the number of
    members it has and its member limit, the area the party is at, and who are its leaders and
    regular members.
    Returns an error if there are no active parties.

    SYNTAX
    /party_list

    PARAMETERS
    None

    EXAMPLES
    >>> /party_list
    May return something like this:
    | $H: == Active parties ==
    | *Party 11037 [2/7] (3). Leaders: Phantom_HD. Regular members: Spam_HD
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    info = '== Active parties =='
    for party in client.server.party_manager.get_parties():
        pid, area, player_limit, raw_leaders, raw_regulars = party.get_details()
        num_members = len(raw_leaders.union(raw_regulars))
        leaders = ', '.join(
            [c.displayname for c in raw_leaders]) if raw_leaders else 'None'
        regulars = ', '.join(
            [c.displayname for c in raw_regulars]) if raw_regulars else 'None'
        info += ('\r\n*Party {} [{}/{}] ({}). Leaders: {}. Regular members: {}.'
                 .format(pid, num_members, player_limit, area.id, leaders, regulars))
    client.send_ooc(info)


def ooc_cmd_party_members(client: ClientManager.Client, arg: str):
    """
    Obtains the leaders and regular members of your party. Any members that are sneaking will
    continue to appear in this list.
    Returns an error if you are not part of a party.

    SYNTAX
    /party_members

    PARAMETERS
    None

    EXAMPLES
    >>> /party_members
    May return something like this:
    | == Members of party 11037 ==
    | *Leaders: Phantom_HD, Spam_HD
    | *Members: Eggs_HD
    """

    Constants.assert_command(client, arg, parameters='=0')

    party = client.get_party(tc=True)
    regulars, leaders = party.get_members_leaders()
    regulars, leaders = sorted(regulars), sorted(leaders)
    info = '== Members of party {} =='.format(party.get_id())
    if leaders:
        names = ' '.join([f'[{c.id}] {c.displayname}' for c in leaders])
        info += '\r\n*Leaders: {}'.format(names)
    if regulars:
        names = ' '.join([f'[{c.id}] {c.displayname}' for c in regulars])
        info += '\r\n*Members: {}'.format(names)
    client.send_ooc(info)


def ooc_cmd_party_uninvite(client: ClientManager.Client, arg: str):
    """
    Revokes an invitation for a user by some ID to join your party. They will no longer be able
    to join your party until they are invited again.
    Returns an error if you are not part of a party, you are not a party leader or staff member, if
    the target is not invited, or if some ID other than client ID was used and the target is not in
    the area of the party.

    SYNTAX
    /party_uninvite <client_id>

    PARAMETERS
    <user_id>: Either the client ID (number in brackets in /getarea), character name, edited-to
               character, custom showname or OOC name of the intended recipient.

    EXAMPLES
    >>> /party_uninvite 2
    Revokes the invitation sent to user with client ID 2 to join your party.
    """

    Constants.assert_command(client, arg, split_spaces=True, parameters='=1')

    party = client.get_party(tc=True)
    if not party.is_leader(client) and not client.is_staff():
        raise PartyError('You are not a leader of your party.')

    c, _, _ = client.server.client_manager.get_target_public(client, arg)
    party.remove_invite(c, tc=False)

    client.send_ooc(
        'You have uninvited {} to join your party.'.format(c.displayname))
    for x in party.get_leaders(uninclude={client}):
        x.send_ooc('{} has uninvited {} to join your party.'
                   .format(client.displayname, c.displayname))
    c.send_ooc('{} has revoked your invitation to join their party {}.'
               .format(client.displayname, party.get_id()))


def ooc_cmd_party_unlead(client: ClientManager.Client, arg: str):
    """
    Removes your party leader role and announces all other party leaders of it. If a party has no
    leaders, all leader functions are available to all members.
    Returns an error if you are not part of a party or you are not a leader of your party.

    SYNTAX
    /party_unlead

    PARAMETERS
    None

    EXAMPLES
    >>> /party_unlead
    Removes your party leader role.
    """

    Constants.assert_command(client, arg, parameters='=0')

    party = client.get_party()
    party.remove_leader(client, tc=True)
    client.send_ooc('You are no longer a leader of your party.')
    for x in party.get_leaders(uninclude={client}):
        if x.is_staff() or client.is_visible:
            x.send_ooc('{} is no longer a leader of your party.'.format(
                client.displayname))


def ooc_cmd_party_whisper(client: ClientManager.Client, arg: str):
    """
    Sends an IC personal message to everyone in your party. The messages have your showname and
    your message, but does not include your sprite.
    Elevated notifications are sent to zone watchers/staff members on whispers to other people,
    which include the message content, so this is not meant to act as a private means of
    communication between players, for which /pm is recommended.
    Whispers sent by sneaked players include an empty showname so as to not reveal their identity,
    except if some members of the party are sneaking as well, in which case they will receive the
    message with showname.
    Deafened recipients will receive a nerfed message if whispered to.
    Non-zone watchers/non-staff players in the same area as the whisperer will be notified that
    they whispered to their target (but will not receive the content of the message), provided they
    are not blind (in which case no notification is sent) and that this was not a self-whisper.
    Returns an error if you or the target are not part of a party, if the message is empty or if you
    is gagged or IC-muted.

    SYNTAX
    /party_whisper <user_ID> <message>

    PARAMETERS
    <user_id>: Either the client ID (number in brackets in /getarea), character name, edited-to
               character, custom showname or OOC name of the intended recipient.
    <message>: Message to be sent.

    EXAMPLES
    >>> /party_whisper Hey, all!
    Sends that message to all players of the party.
    """

    try:
        Constants.assert_command(client, arg, parameters='>0')
    except ArgumentError:
        raise ArgumentError('Not enough arguments. Use /party_whisper <message>. Target should '
                            'be ID, char-name, edited-to character, custom showname or OOC-name.')

    party = client.get_party(tc=True)
    if client.is_muted:
        raise ClientError('You have been muted by a moderator.')
    if client.is_gagged:
        raise ClientError(
            'Your attempt at whispering failed because you are gagged.')

    msg = arg[:256]  # Cap
    public_area = not client.area.private_area

    client.send_ooc(f'You whispered `{msg}` to your party members.')
    client.send_ic(msg=msg, pos=client.pos, folder=client.char_folder, char_id=client.char_id,
                   showname='[PW] ' + client.showname_else_char_showname, hide_character=1,
                   bypass_deafened_starters=True)  # send_ic handles nerfing for deafened

    members = party.get_members() - {client}
    pid = party.get_id()

    if client.is_visible:
        for target in members:
            target.send_ooc(f'{client.displayname} whispered `{msg}` to your party.',
                            to_deaf=False)
            target.send_ooc(f'{client.displayname} seemed to whisper something to your party, but '
                            f'you could not make it out.', to_deaf=True, to_blind=False)
            target.send_ooc('Someone seemed to whisper something to your party, but you could '
                            'not make it out.', to_deaf=True, to_blind=True)

            target.send_ic(msg=msg, pos=client.pos, char_id=client.char_id,
                           folder=client.char_folder,
                           showname='[PW] ' + client.showname_else_char_showname, hide_character=1,
                           pred=lambda _: not (
                                   target.is_deaf and target.is_blind),
                           bypass_deafened_starters=True)  # send_ic handles nerfing for deafened
            target.send_ic(msg=msg, pos=client.pos, char_id=client.char_id,
                           folder=None, showname='???', hide_character=1,
                           pred=lambda _: (target.is_deaf and target.is_blind),
                           bypass_deafened_starters=True)  # send_ic handles nerfing for deafened
        if public_area:
            client.send_ooc_others(f'(X) {client.displayname} [{client.id}] whispered `{msg}` to '
                                   f'their party {pid} ({client.area.id}).',
                                   is_zstaff_flex=True, not_to=members)
            client.send_ooc_others('You see a group of people huddling together.',
                                   in_area=True, to_blind=False, is_zstaff_flex=False,
                                   not_to=members)
        else:
            # For private areas, zone watchers and staff get normal whisper reports if in the same
            # area.
            client.send_ooc_others('(X) You see a group of people huddling together.',
                                   in_area=True, is_zstaff_flex=True, not_to=members)
    else:
        sneaked = {member for member in members if not member.is_visible}
        not_sneaked = members - sneaked
        for target in sneaked:
            target.send_ooc(f'{client.displayname} whispered `{msg}` to your party while '
                            f'sneaking.', to_deaf=False)
            target.send_ooc(f'{client.displayname} seemed to whisper something to your party while '
                            f'sneaking, but you could not make it out.', to_deaf=True,
                            to_blind=False)
            # No different notification
            target.send_ooc('Someone seemed to whisper something to your party, but you could '
                            'not make it out.', to_deaf=True, to_blind=True)
            target.send_ic(msg=msg, pos=client.pos, char_id=client.char_id,
                           folder=client.char_folder,
                           showname='[PW] ' + client.showname_else_char_showname, hide_character=1,
                           pred=lambda _: not (
                                   target.is_deaf and target.is_blind),
                           bypass_deafened_starters=True)  # send_ic handles nerfing for deafened
            target.send_ic(msg=msg, pos=client.pos, char_id=client.char_id,
                           folder=None, showname='???', hide_character=1,
                           pred=lambda _: (target.is_deaf and target.is_blind),
                           bypass_deafened_starters=True)  # send_ic handles nerfing for deafened

        for target in not_sneaked:
            target.send_ooc(f'You heard someone whisper `{msg}`, but you could not seem to tell '
                            f'where it came from.', to_deaf=False)
            target.send_ooc(
                'Your ears seemed to pick up something.', to_deaf=True)
            target.send_ic(msg=msg, pos='jud', showname='???', hide_character=1,
                           bypass_deafened_starters=True)

        if public_area:
            client.send_ooc_others(f'(X) {client.displayname} [{client.id}] whispered `{msg}` to '
                                   f'their party {pid} while sneaking ({client.area.id}).',
                                   is_zstaff_flex=True, not_to=members)
            client.send_ooc_others('You heard someone whisper `{msg}`, but you could not seem to '
                                   f'tell where it came from.',
                                   in_area=True, to_deaf=False, is_zstaff_flex=False,
                                   not_to=members)
            client.send_ooc_others('Your ears seemed to pick up something.',
                                   in_area=True, to_deaf=True, is_zstaff_flex=True,
                                   not_to=members)
        else:
            # For private areas, zone watchers and staff get normal whisper reports if in the same
            # area.
            client.send_ooc_others('(X) You see a group of people huddling together',
                                   in_area=True, is_zstaff_flex=True, not_to=members)


def ooc_cmd_passage_clear(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Clears all the passage locks that start in the areas between two given ones by name or ID, or
    does that only to the given area if not given any. In particular, players in any of the affected
    areas will be able to freely move to any other from the area they were in.
    Note that, as passages are unidirectional, passages from areas outside the given range that end
    in an area that is in the range will be conserved.

    SYNTAX
    /passage_clear
    /passage_clear <area_range_start>, <area_range_end>

    PARAMETERS
    <area_range_start>: Start of area range (inclusive)
    <area_range_end>: End of area range (inclusive)

    EXAMPLES
    Assuming you are in area 0...
    >>> /passage_clear
    Clears the passages starting in area 0.
    >>> /passage_clear 16, 116
    Restores the passages starting in areas 16 through 116.
    """

    Constants.assert_command(client, arg, is_staff=True,
                             parameters='<3', split_commas=True)

    areas = Constants.parse_two_area_names(client, arg.split(', '))

    for i in range(areas[0].id, areas[1].id + 1):
        area = client.hub.area_manager.get_area_by_id(i)
        area.reachable_areas = client.hub.area_manager.area_names

    if areas[0] == areas[1]:
        client.send_ooc(
            'Area passage locks have been removed in {}.'.format(areas[0].name))
    else:
        client.send_ooc('Area passage locks have been removed in areas {} through {}'
                        .format(areas[0].name, areas[1].name))


def ooc_cmd_passage_restore(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Restores the passages in the areas between two given ones by name or ID to their original state
    when the areas were loaded, or does that to the current area if not given any.
    Note that, as passages are unidirectional, passages from areas outside the given range that end
    in an area that is in the range will be conserved.

    SYNTAX
    /passage_restore
    /passage_restore <area_range_start>, <area_range_end>

    PARAMETERS
    <area_range_start>: Start of area range (inclusive)
    <area_range_end>: End of area range (inclusive)

    EXAMPLES
    Assuming you are in area 0...
    >>> /passage_restore
    Restores the passages starting in area 0 to default.
    >>> /passage_restore 16, 116
    Restores the passages starting in areas 16 through 116.
    """

    Constants.assert_command(client, arg, is_staff=True,
                             parameters='<3', split_commas=True)

    areas = Constants.parse_two_area_names(client, arg.split(', '))

    for i in range(areas[0].id, areas[1].id + 1):
        area = client.hub.area_manager.get_area_by_id(i)
        area.reachable_areas = set(list(area.default_reachable_areas)[:])
        area.change_reachability_allowed = area.default_change_reachability_allowed

    if areas[0] == areas[1]:
        client.send_ooc(
            'Passages in this area have been restored to their original state.')
    else:
        client.send_ooc('Passages in areas {} through {} have been restored to their original '
                        'state.'.format(areas[0].name, areas[1].name))


def ooc_cmd_peek(client: ClientManager.Client, arg: str):
    """
    Obtains information about an area visible from the current area equivalent to doing /look there.
    If the area is not locked, there is an unlocked passage connecting it to the current area, and
    the target area's lights are on, the peek succeeds, and players in the area are notified that
    a peek occurred with a 75% chance each, provided the peeker is not sneaking, you are not
    blind and the area's lights are turned on; otherwise, no notification is sent.
    Otherwise, the peek fails, and no notifications are sent to players in the area.
    If the peek succeeds or fails (but is not void), zone watchers are notified of the attempt, and
    so are players in the same area as the peeker, provided such players are able to see the peeker
    via /look.
    Returns an error if you are blind, or try to peek into their current area or into an area that
    is a private area, a lobby area, or an area with no visible passage from the current area.

    SYNTAX
    /peek <area_id>

    PARAMETERS
    <area_id>: ID of the area whose door you want to peek.

    EXAMPLES
    >>> /peek 1
    Peek into area 1.
    """

    Constants.assert_command(client, arg, parameters='>0')

    if client.is_blind:
        raise ClientError('You are blind, so you cannot see anything.')

    # Obtain target area, which also does validation
    target_area = Constants.parse_area_names(client, [arg])[0]
    if target_area == client.area:
        raise ClientError('You cannot peek into your current area.')
    if target_area.name not in client.area.visible_areas:
        raise ClientError('You do not see a passage to that area.')
    if target_area.lobby_area:
        raise ClientError('You cannot peek into lobby areas.')
    if target_area.private_area:
        raise ClientError('You cannot peek into private areas.')

    area_lock_ok = not (target_area.is_locked and not client.is_staff()
                        and client.ipid not in target_area.invite_list)
    reachable_ok = target_area.name in client.area.reachable_areas
    # Two cases:
    # 1. if passage exists and area not locked
    # 2. Either is not true

    if area_lock_ok and reachable_ok:
        if target_area.lights:
            _, _, area_description, _, player_description = target_area.get_look_output_for(
                client)
            client.send_ooc(
                f'You peek into area {target_area.name} and note the following:\r\n'
                f'*About the people in there: you see {player_description}\r\n'
                f'*About the area: {area_description}'
            )
            if client.is_visible:
                client.send_ooc_others(f'You see {client.displayname} is peeking into area '
                                       f'{target_area.name}.', to_blind=False,
                                       in_area=client.area, is_zstaff_flex=False)
                client.send_ooc_others('You feel as though you are being peeked on.',
                                       in_area=target_area, is_zstaff_flex=False,
                                       pred=lambda _: random.random() < 0.75)
                client.send_ooc_others(f'(X) {client.displayname} [{client.id}] peeked into area '
                                       f'{target_area.name} from area {client.area.name} '
                                       f'({client.area.id}).', is_zstaff_flex=True)
            else:
                client.send_ooc_others(f'(X) {client.displayname} [{client.id}] peeked into area '
                                       f'{target_area.name} from area {client.area.name} '
                                       f'({client.area.id}) while sneaking.', is_zstaff_flex=True)
        else:
            client.send_ooc(f'You peek into area {target_area.name} but cannot see anything as its '
                            f'lights are out.')
            client.send_ooc_others(f'(X) {client.displayname} [{client.id}] tried to peek into '
                                   f'area {target_area.name} from area {client.area.name}, but was '
                                   f'unable to gather anything meaningful as its lights were out '
                                   f'({client.area.id}).', is_zstaff_flex=True)
            client.send_ooc_others(f'You see {client.displayname} is peeking into area '
                                   f'{target_area.name}.', to_blind=False,
                                   in_area=client.area, is_zstaff_flex=False,
                                   pred=lambda c: client in c.get_visible_clients(client.area))
    else:
        client.send_ooc(f'You tried to peek into area {target_area.name}, but the passage to it '
                        f'was locked.')
        client.send_ooc_others(f'(X) {client.displayname} [{client.id}] tried to peek into area '
                               f'{target_area.name} from area {client.area.name}, but was unable '
                               f'to as the passage to it was locked ({client.area.id}).',
                               is_zstaff_flex=True)
        client.send_ooc_others(f'You see {client.displayname} try to peek into area '
                               f'{target_area.name}, but fail to do so as the passage to it was '
                               f'locked.', to_blind=False,
                               in_area=client.area, is_zstaff_flex=False,
                               pred=lambda c: client in c.get_visible_clients(client.area))


def ooc_cmd_ping(client: ClientManager.Client, arg: str):
    """
    Returns "Pong" and nothing else. Useful to check if you have lost connection.

    SYNTAX
    /ping

    PARAMETERS
    None

    EXAMPLES
    >>> /ping
    Returns "Pong".
    """

    Constants.assert_command(client, arg, parameters='=0')

    client.send_ooc('Pong.')


def ooc_cmd_play(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    Plays a given track, even if not explicitly in the music list. It is the way to play custom
    music. If the area parameter 'song_switch_allowed' is set to true, anyone in the area can use
    this command even if they are not logged in as game master.

    Returns an error if you are not a game master and the area does not allow the use of
    /play, if you are IC-muted, if you do not have DJ privileges, or if you trigger the server
    music flood guard.

    SYNTAX
    /play <track_name>
    /play <track_name> <fade_type>

    PARAMETERS
    <track_name>: Track to play
    <fade_type>: The fade behavior for the new song. May be: in, out, mix

    EXAMPLES
    >>> /play Trial(AJ).opus
    Plays Trial(AJ).opus.
    >>> /play CustomTrack.opus
    Plays CustomTrack.opus, which will only be audible to users with CustomTrack.opus.
    >>> /play CustomTrack.opus in
    Plays CustomTrack.opus, the song will be faded in as it begins playing.
    >>> /play CustomTrack.opus out
    Plays CustomTrack.opus, the previous song will fade out before the new one begins playing.
    >>> /play CustomTrack.opus mix
    Plays CustomTrack.opus, fade will combine both in and out behavior.
    """

    try:
        Constants.assert_command(client, arg, is_staff=True, parameters='>0')
    except ClientError.UnauthorizedError:
        if not client.area.song_switch_allowed:
            raise
    except ArgumentError:
        raise ArgumentError('You must specify a song.')

    if client.is_muted:  # Checks to see if the client has been muted by a mod
        raise ClientError("You have been muted by a moderator.")
    if not client.is_dj:
        raise ClientError('You were blockdj\'d by a moderator.')

    delay = client.change_music_cd()
    if delay:
        raise ClientError(f'You changed song too many times recently. Please try again after '
                          f'{Constants.time_format(delay)}.')

    track_name = arg
    fade_option = FadeOption.NO_FADE

    try:
        arg_list = arg.split()
        fade_option = FadeOption[arg_list.pop().upper()]
        track_name = ' '.join(arg_list)
    except Exception:
        pass

    client.area.play_track(
        track_name, client, raise_if_not_found=False, reveal_sneaked=False, fade_option=fade_option)

    client.send_ooc('You have played track `{}` in your area.'
                    .format(track_name))
    client.send_ooc_others('(X) {} [{}] has played track `{}` in your area.'
                           .format(client.displayname, client.id, track_name),
                           is_zstaff_flex=True, in_area=True)

    # Warn if track is not in the music list
    try:
        client.music_manager.get_music_data(track_name)
    except MusicError.MusicNotFoundError:
        client.send_ooc(f'Warning: `{track_name}` is not a recognized track name, so the server will not '
                        f'loop it.')


def ooc_cmd_pm(client: ClientManager.Client, arg: str):
    """
    Sends a personal message to a specified user.
    Returns an error if the target could not be found, if you or the target muted PMs, or if
    multiple users match the given identifier.

    SYNTAX
    /pm <user_id> <message>

    PARAMETERS
    <user_id>: Either the client ID (number in brackets in /getarea), character name, edited-to
               character, custom showname or OOC name of the intended recipient.
    <message>: Message to be sent.

    EXAMPLES
    >>> /pm Santa What will I get for Christmas?
    Sends that message to the user with OOC name is Santa.
    >>> /pm 0 Nothing
    Sends that message to the user with client ID 0.
    >>> /pm Santa_HD Sad
    Sends that message to the user with character name Santa_HD.
    """

    try:
        Constants.assert_command(client, arg, parameters='>1')
    except ArgumentError:
        raise ArgumentError('Not enough arguments. Use /pm <target> <message>. Target should be '
                            'ID, char-name, edited-to character, custom showname or OOC-name.')
    if client.pm_mute:
        raise ClientError('You have muted all PM conversations.')

    cm = client.server.client_manager
    target, recipient, msg = cm.get_target_public(client, arg)

    # Attempt to send the message to the target, provided they do not have PMs disabled.
    if target.pm_mute:
        raise ClientError('This user muted all PM conversations.')

    client.send_ooc('PM sent to {}. Message: {}'.format(recipient, msg))
    target.send_ooc('PM from {} in {} ({}): {}'
                    .format(client.name, client.area.name, client.displayname, msg))


def ooc_cmd_pm_gms(client: ClientManager.Client, arg: str):
    """
    Sends a personal message to all users with rank of GM or above other than yourself in your hub.
    Returns an error if no such users could be found, or if you or all such users muted PMs.

    SYNTAX
    /pm <message>

    PARAMETERS
    <message>: Message to be sent.

    EXAMPLES
    >>> /pm_gms What will I get for Christmas?
    Sends that message to all GMs in your hub.
    """

    Constants.assert_command(client, arg, parameters='>0')
    if client.pm_mute:
        raise ClientError('You have muted all PM conversations.')

    targets = {target for target in client.hub.get_players()
               if target.is_staff()}
    targets = targets - {client}
    if not targets:
        raise ClientError('No GMs are available in your hub.')

    # Only send messages to targets who have not muted PMs
    targets = {target for target in targets if not target.pm_mute}
    if not targets:
        raise ClientError('No GMs available in your hub have PMs enabled.')

    msg = arg
    client.send_ooc(
        f'PM sent to all GMs in hub {client.hub.get_numerical_id()}. Message: {msg}.')
    for target in targets:
        target.send_ooc(f'(X) PM from {client.displayname} [{client.id}] in {client.area.name} '
                        f'({client.area.id}) to all GMs in your hub: {msg}')


def ooc_cmd_poison(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Poisons the target with some of three effects (blindness, deafened or gagged) that kick in
    a specified length of time. Multiple effects can be used within the same poison.
    If the target is already subject to some poison, stack them together as follows:
     For each effect in the new poison:
     * If the target's current poison does not include the effect, poison the target such that the
       effect kicks in the new poison's established length.
     * Otherwise, poison the target such that the effect kicks in the new poison's established
       length or the remaining length of the old poison, whichever is shorter.
    If for some effect of the poison the target is already subject to it after its time expires
    (which would happen if some staff manually sets it in), do nothing for that effect.
    Returns an error if the given identifier does not correspond to a user, if the length is not a
    positive number or exceeds the server time limit, or if the effects contain an unrecognized or
    repeated character.

    SYNTAX
    /poison <client_id> <effects> <length>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <effects>: Effects to apply with the current poison (a string consisting of non-case-sensitive
    'b', 'd', and/or 'g' in some order corresponding to the initials of the supported effects)
    <length>: Time to wait before the effects take place (in seconds)

    EXAMPLES
    Assuming these are run immediately one after the other...
    >>> /poison 1 b 10
    Poisons user with client ID 1 with a poison that in 10 seconds will turn them blind.
    >>> /poison 1 bD 8
    Poisons user with client ID 1 with a poison that in 8 seconds will turn them blind and deafened
    (old poison discarded).
    >>> /poison 1 Dg 15
    Poisons user with client ID 1 with a poison that in 8 seconds will turn them gagged in 15 seconds
    (old deafened poison of 8 seconds remains).
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=3')
    raw_target, raw_effects, raw_length = arg.split(' ')
    target = Constants.parse_id(client, raw_target)
    effects = Constants.parse_effects(client, raw_effects)
    length = Constants.parse_time_length(raw_length)

    effect_results = target.set_timed_effects(effects, length)
    target_message = ''
    self_message = ''
    zstaff_message = ''

    for effect_name in sorted(effect_results.keys()):
        effect_length, effect_reapplied = effect_results[effect_name]
        formatted_effect_length = Constants.time_format(effect_length)

        if effect_length == length and not effect_reapplied:
            target_message = ('{}\r\n*{}: acts in {}.'
                              .format(target_message, effect_name, formatted_effect_length))
            self_message = ('{}\r\n*{}: acts in {}.'
                            .format(self_message, effect_name, formatted_effect_length))
            zstaff_message = ('{}\r\n*{}: acts in {}.'
                              .format(zstaff_message, effect_name, formatted_effect_length))
        elif effect_length == length and effect_reapplied:
            # The new effect time was lower than the remaining time for the current effect
            target_message = ('{}\r\n*{}: now acts in {}.'
                              .format(target_message, effect_name, formatted_effect_length))
            self_message = ('{}\r\n*{}: now acts in {}.'
                            .format(self_message, effect_name, formatted_effect_length))
            zstaff_message = ('{}\r\n*{}: now acts in {}.'
                              .format(zstaff_message, effect_name, formatted_effect_length))
        else:
            target_message = ('{}\r\n*{}: still acts in {}.'
                              .format(target_message, effect_name, formatted_effect_length))
            self_message = ('{}\r\n*{}: still acts in {} (remaining effect time shorter than new '
                            'length).'.format(self_message, effect_name, formatted_effect_length))
            zstaff_message = ('{}\r\n*{}: still acts in {} (remaining time shorter than new '
                              'length).'.format(zstaff_message, effect_name,
                                                formatted_effect_length))

    if target != client:
        target.send_ooc('You were poisoned. The following effects will apply shortly: {}'
                        .format(target_message))
        client.send_ooc('You poisoned {} [{}] with the following effects: {}'
                        .format(target.displayname, target.id, self_message))
        client.send_ooc_others('(X) {} [{}] poisoned {} [{}] with the following effects ({}): {}'
                               .format(client.displayname, client.id, target.displayname, target.id,
                                       client.area.id, zstaff_message),
                               is_zstaff_flex=True, not_to={target})
    else:
        client.send_ooc('You poisoned yourself with the following effects: {}'
                        .format(self_message))
        client.send_ooc_others('(X) {} [{}] poisoned themselves with the following effects ({}): {}'
                               .format(client.displayname, client.id, client.area.id,
                                       zstaff_message),
                               is_zstaff_flex=True)


def ooc_cmd_pos(client: ClientManager.Client, arg: str):
    """
    Switches the character to the given position, or to its original position if not given one.
    Returns an error if position is invalid.

    SYNTAX
    /pos {new_position}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {new_position}: New character position (jud, def, pro, hlp, hld)

    EXAMPLES
    >>> /pos jud
    Switches to the judge position.
    >>> /pos
    Resets to original position.
    """

    # Resetting to original position
    if not arg:
        client.change_position()
        client.send_ooc('Position reset.')

    # Switching position
    else:
        client.change_position(arg)
        client.area.broadcast_evidence_list()
        client.send_ooc('Position changed.')


def ooc_cmd_pos_force(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Changes the IC position of a particular player, or all players in your current area if not
    specified, to the given one.
    Returns an error if the position is not a valid position, or if the given identifier does not
    correspond to a user.

    SYNTAX
    /pos_force <position> {client_id}

    PARAMETERS
    <position>: Either def, pro, hld, hlp, jud, wit

    OPTIONAL PARAMETERS
    {client_id}: Client identifier (number in brackets in /getarea)

    EXAMPLES
    >>> /pos_force pro
    Changes the position of all players in your current area to pro.
    >>> /pos_force wit 2
    Changes the position of user with client ID 2 to wit.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='&1-2')

    args = arg.split(' ')
    pos = args[0]
    if pos not in ('def', 'pro', 'hld', 'hlp', 'jud', 'wit'):
        raise ClientError('Invalid position. '
                          'Possible values: def, pro, hld, hlp, jud, wit.')

    if len(args) == 2:
        targets = [Constants.parse_id(client, args[1])]
        all_in_area = False
    else:
        targets = client.area.clients
        all_in_area = True

    for target in targets:
        target.change_position(pos)
        target.area.broadcast_evidence_list()

    if all_in_area:
        client.send_ooc(
            f'You forced all players in your area to be in position {pos}.')
        client.send_ooc_others(f'(X) {client.displayname} [{client.id}] forced the position of all '
                               f'players in area {client.area.name} to {pos} ({client.area.id}).',
                               is_zstaff_flex=True)
    else:
        client.send_ooc(
            f'You forced {client.displayname} [{client.id}] to be in position {pos}.')
        client.send_ooc_others(f'(X) {client.displayname} [{client.id}] forced the position of '
                               f'{targets[0].displayname} [{targets[0].id}] to {pos} '
                               f'({client.area.id}).',
                               is_zstaff_flex=True)
    client.send_ooc_others(f'Your position was changed to {pos}.',
                           is_zstaff_flex=False, part_of=targets)


def ooc_cmd_randomchar(client: ClientManager.Client, arg: str):
    """
    Switches your character to a random character.
    Returns an error if no character is available.

    SYNTAX
    /randomchar

    PARAMETERS
    None

    EXAMPLE
    >>> /randomchar
    Switches your character to a random character.
    """

    Constants.assert_command(client, arg, parameters='=0')

    free_id = client.area.get_rand_avail_char_id(
        allow_restricted=client.is_staff())
    client.change_character(free_id)
    client.send_ooc('Randomly switched to `{}`.'.format(
        client.get_char_name()))


def ooc_cmd_randommusic(client: ClientManager.Client, arg: str):
    """
    Plays a randomly chosen track from your current music list.
    Returns an error if you are IC-muted, if you do not have DJ privileges, or if you trigger the
    server music flood guard.

    SYNTAX
    /randommusic

    PARAMETERS
    None

    EXAMPLES:
    >>> /randommusic
    May play 'Ikoroshia.opus', 'Despair Searching.opus', etc.
    """

    Constants.assert_command(client, arg, parameters='=0')

    if client.is_muted:  # Checks to see if the client has been muted by a mod
        raise ClientError("You have been muted by a moderator.")
    if not client.is_dj:
        raise ClientError('You were blockdj\'d by a moderator.')

    delay = client.change_music_cd()
    if delay:
        raise ClientError(f'You changed song too many times recently. Please try again after '
                          f'{Constants.time_format(delay)}.')

    # Find all music tracks
    music_names = list()
    music_list = client.music_manager.get_music()

    for item in music_list:
        songs = item['songs']
        for song in songs:
            name = song['name']
            music_names.append(name)

    if not music_names:
        raise ClientError('No music tracks found in the current music list.')

    random_music = random.choice(music_names)
    client.area.play_track(random_music, client,
                           raise_if_not_found=False, reveal_sneaked=False)

    client.send_ooc('You have played the randomly chosen track `{}` in your area.'
                    .format(random_music))
    client.send_ooc_others('(X) {} [{}] has played the randomly chosen track `{}` in your area.'
                           .format(client.displayname, client.id, random_music),
                           is_zstaff_flex=True, in_area=True)


def ooc_cmd_refresh(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Reloads the following files for your hub: characters, default music list, and background list.

    SYNTAX
    /refresh

    PARAMETERS
    None

    EXAMPLE
    >>> /refresh
    Reloads hub assets.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    client.hub.refresh()
    client.send_ooc('You have refreshed your hub.')


def ooc_cmd_reload(client: ClientManager.Client, arg: str):
    """
    Reloads your current character (equivalent to switching to the current character).

    SYNTAX
    /reload

    PARAMETERS
    None

    EXAMPLE
    >>> /reload
    Reloads your current character.
    """

    Constants.assert_command(client, arg, parameters='=0')

    client.reload_character()
    client.send_ooc('Character reloaded.')


def ooc_cmd_reload_commands(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Reloads the commands.py file. Use only if restarting is not a viable option.
    Note that this ONLY updates the contents of this file. If anything you update relies on other
    files (for example, you call a method in client_manager), they will still use the old contents,
    regardless of whatever changes you may have made to the other files.

    SYNTAX
    /reload_commands

    PARAMETERS
    None

    EXAMPLE
    >>> /reload_commands
    Reloads the commands file.
    """

    Constants.assert_command(client, arg, is_mod=True, parameters='=0')

    outcome = client.server.reload_commands()
    if outcome:
        info = "\n{}: {}".format(type(outcome).__name__, outcome)
        raise ClientError(
            'Server ran into a problem while reloading the commands: {}'.format(info))

    client.send_ooc("The commands have been reloaded.")


def ooc_cmd_remove_h(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Removes all letter H's from all IC and OOC messages of a user by client ID (number in
    brackets) or IPID (number in parentheses).
    If given IPID, it will affect all clients opened by the target. Otherwise, it will just affect
    the given client.
    Requires /unremove_h to undo.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /remove_h <client_id>
    /remove_h <client_ipid>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    EXAMPLES
    >>> /remove_h 1
    Has all messages sent by the user with client ID 1 have their H's removed.
    >>> /remove_h 1234567890
    Has all messages sent by all clients opened by the user with IPID 1234567890 have their H's
    removed.
    """

    Constants.assert_command(client, arg, is_mod=True, parameters='=1')

    # Removes H's to matching targets
    for c in Constants.parse_id_or_ipid(client, arg):
        c.remove_h = True
        logger.log_server('Removing h from {}.'.format(c.ipid), client)
        client.area.broadcast_ooc("Removed h from {}.".format(c.displayname))


def ooc_cmd_reveal(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY+VARYING REQUIREMENTS)
    Sets given user based on client ID or IPID to no longer be sneaking so that they are visible
    through /getarea(s).
    If given IPID, it will affect all clients opened by the target. Otherwise, it will just affect
    the given client.
    Search by IPID can only be performed by CMs and mods.
    If no target is given, the target will be yourself.
    If the target is not sneaking, the reveal will fail.
    Requires /sneak to undo.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /reveal
    /reveal <client_id>
    /reveal <client_ipid>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    EXAMPLES
    >>> /reveal 1
    Set user with client ID 1 to no longer be sneaking.
    >>> /reveal 1234567890
    Set all clients opened by the user with IPID 1234567890 to no longer be sneaking.
    """

    Constants.assert_command(client, arg, is_staff=True)

    if arg:
        targets = Constants.parse_id_or_ipid(client, arg)
    else:
        targets = [client]
    # Unsneak matching targets
    for c in targets:
        if c.is_visible:
            client.send_ooc('Target client is already not sneaking.')
            continue

        if c != client:
            client.send_ooc("{} is no longer sneaking.".format(c.displayname))
            client.send_ooc_others('(X) {} [{}] revealed {} [{}] ({}).'
                                   .format(client.displayname, client.id, c.displayname, client.id,
                                           c.area.id),
                                   not_to={c}, is_zstaff=True)
        else:
            client.send_ooc_others('(X) {} [{}] revealed themselves ({}).'
                                   .format(client.displayname, client.id, c.area.id),
                                   is_zstaff=True)
        c.change_visibility(True)


def ooc_cmd_roll(client: ClientManager.Client, arg: str):
    """
    Rolls a given number of dice with given number of faces and modifiers. If certain parameters
    are not given, command assumes preset defaults. The result is broadcast to all players in the
    area as well as staff members who have turned foreign roll notifications with /toggle_allrolls.
    The roll is also logged in the client's and area's dice log.
    Returns an error if parameters exceed specified constants or an invalid mathematical operation
    is put as a modifier.

    For modifiers, the modifier's result will ignore the given number of faces cap and instead use
    NUMFACES_MAX (so dice rolls can exceed number of faces). However, the modifier's result is
    bottom capped at 1 (so non-positive values are not allowed). Modifiers follow PEMDAS, and if
    not given the dice result (character "r"), will try and perform the operation directly.

    SYNTAX
    /roll {num_faces} {modifier}
    /roll {num_dice}d<num_faces> {modifier}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {num_faces}: Number of faces the dice will have (capped at NUMFACES_MAX).
    {num_dice}: Number of dice to roll (capped at NUMDICE_MAX).
    {modifier}: Operation to perform on rolls.

    EXAMPLES
    Assuming DEF_NUMDICE = 1, DEF_NUMFACES = 6, DEF_MODIFIER = '' ...
    >>> /roll
    Rolls a d6.
    >>> /roll 20
    Rolls a d20.
    >>> /roll 5d30
    Rolls 5 d30's.
    >>> /roll d20 +3
    Rolls a d20 and adds 3 to the result.
    >>> /roll 1d20 +3*2
    Rolls a d20 and adds 3*2=6 to the result.
    >>> /roll 6 -1+3*r
    Rolls a d6, multiplies the result by 3 and subtracts 1 to it.
    >>> /roll 3d6 (-1+3)*r
    Rolls 3 d6's and multiplies each result by 2.
    """

    roll_result, num_faces = Constants.dice_roll(arg, 'roll', client.server)
    roll_message = 'rolled {} out of {}'.format(roll_result, num_faces)
    client.send_ooc('You {}.'.format(roll_message))
    client.send_ooc_others('{} {}.'.format(
        client.displayname, roll_message), in_area=True)
    client.send_ooc_others('(X) {} [{}] {} in {} ({}).'
                           .format(client.displayname, client.id, roll_message,
                                   client.area.name, client.area.id),
                           is_zstaff_flex=client.area, in_area=False,
                           pred=lambda c: c.get_foreign_rolls)
    client.add_to_dicelog(roll_message + '.')
    client.area.add_to_dicelog(client, roll_message + '.')
    logger.log_server('[{}][{}]Used /roll and got {} out of {}.'
                      .format(client.area.id, client.get_char_name(), roll_result, num_faces),
                      client)


def ooc_cmd_rollp(client: ClientManager.Client, arg: str):
    """
    Similar to /roll, but instead announces roll results (and who rolled) only to yourself and
    staff members who are in the area or who have foreign roll notifications with /toggle_allrolls.
    The roll is also logged in the client's and area's dice log, but marked as private.
    Returns an error if current area does not authorize /rollp and user is not logged in.

    SYNTAX
    /rollp {num_faces} {modifier}
    /rollp {num_dice}d<num_faces> {modifier}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {num_faces}: Number of faces the dice will have (capped at NUMFACES_MAX).
    {num_dice}: Number of dice to roll (capped at NUMDICE_MAX).
    {modifier}: Operation to perform on rolls.

    EXAMPLES
    Assuming DEF_NUMDICE = 1, DEF_NUMFACES = 6, DEF_MODIFIER = '' ...
    >>> /rollp
    Rolls a d6.
    >>> /rollp 20
    Rolls a d20.
    >>> /rollp 5d30
    Rolls 5 d30's.
    >>> /rollp d20 +3
    Rolls a d20 and adds 3 to the result.
    >>> /rollp 1d20 +3*2
    Rolls a d20 and adds 3*2=6 to the result.
    >>> /rollp 6 -1+3*r
    Rolls a d6, multiplies the result by 3 and subtracts 1 to it.
    >>> /rollp 3d6 (-1+3)*r
    Rolls 3 d6's and multiplies each result by 2.
    """

    if not client.area.rollp_allowed and not client.is_staff():
        raise ClientError(
            'This command has been restricted to authorized users only in this area.')

    roll_result, num_faces = Constants.dice_roll(arg, 'rollp', client.server)
    roll_message = 'privately rolled {} out of {}'.format(
        roll_result, num_faces)
    client.send_ooc('You {}.'.format(roll_message))
    client.send_ooc_others(
        'Someone rolled.', is_zstaff_flex=False, in_area=True)
    client.send_ooc_others('(X) {} [{}] {}.'.format(client.displayname, client.id, roll_message),
                           is_zstaff_flex=True, in_area=True)
    client.send_ooc_others('(X) {} [{}] {} in {} ({}).'
                           .format(client.displayname, client.id, roll_message, client.area.name,
                                   client.area.id),
                           is_zstaff_flex=client.area, in_area=False,
                           pred=lambda c: c.get_foreign_rolls)

    client.add_to_dicelog(roll_message + '.')
    client.area.add_to_dicelog(client, roll_message + '.')

    salt = ''.join(random.choices(
        string.ascii_uppercase + string.digits, k=16))
    encoding = hashlib.sha1(
        (str(roll_result) + salt).encode('utf-8')).hexdigest() + '|' + salt
    logger.log_server('[{}][{}]Used /rollp and got {} out of {}.'
                      .format(client.area.id, client.get_char_name(), encoding, num_faces), client)


def ooc_cmd_rplay(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Plays a given track in currently reachable areas, even if not explicitly in the music list.
    It is the way to play custom music in multiple areas.

    SYNTAX
    /rplay <track_name>
    /rplay <track_name> <fade_type>

    PARAMETERS
    <track_name>: Track to play
    <fade_type>: The fade behavior for the new song. May be: in, out, mix

    EXAMPLES
    >>> /rplay Trial(AJ).opus
    Plays Trial(AJ).opus.
    >>> /rplay CustomTrack.opus
    Plays CustomTrack.opus, which will only be audible to users with CustomTrack.opus.
    >>> /rplay CustomTrack.opus in
    Plays CustomTrack.opus, the song will be faded in as it begins playing.
    >>> /rplay CustomTrack.opus out
    Plays CustomTrack.opus, the previous song will fade out before the new one begins playing.
    >>> /rplay CustomTrack.opus mix
    Plays CustomTrack.opus, fade will combine both in and out behavior.
    """

    try:
        Constants.assert_command(client, arg, is_staff=True, parameters='>0')
    except ArgumentError:
        raise ArgumentError('You must specify a song.')

    areas = {client.hub.area_manager.get_area_by_name(reachable_area_name)
             for reachable_area_name in client.area.visible_areas}

    track_name = arg
    fade_option = FadeOption.NO_FADE

    try:
        arg_list = arg.split()
        fade_option = FadeOption[arg_list.pop().upper()]
        track_name = ' '.join(arg_list)
    except Exception:
        pass

    for area in areas:
        area.play_track(track_name, client, raise_if_not_found=False,
                        reveal_sneaked=False, fade_option=fade_option)

    client.send_ooc('You have played track `{}` in the areas reachable from your area.'
                    .format(track_name))
    client.send_ooc_others('(X) {} [{}] has played track `{}` in the areas reachable from your '
                           'area.'
                           .format(client.displayname, client.id, track_name),
                           is_zstaff_flex=True, in_area=True)
    client.send_ooc_others('(X) {} [{}] has played track `{}` in the areas reachable from area '
                           '{}, which included your area.'
                           .format(client.displayname, client.id, track_name, client.area.name),
                           is_zstaff_flex=True, in_area=areas - {client.area})

    # Warn if track is not in the music list
    try:
        client.music_manager.get_music_data(track_name)
    except MusicError.MusicNotFoundError:
        client.send_ooc(f'(X) Warning: `{track_name}` is not a recognized track name, so the server will '
                        f'not loop it.')


def ooc_cmd_scream(client: ClientManager.Client, arg: str):
    """
    Sends a message in the OOC chat visible to all staff members and non-deaf users that are in an
    area whose screams are reachable from your area whose IC chat is not locked. It also
    sends an IC message with the scream message. If the area of the screamer is marked private,
    the scream only goes to the current area.
    If you are gagged, a special message is instead sent to non-deaf players in the same area.
    If a recipient is deaf, they receive a special OOC message and a blank IC message.
    Staff always get normal message
    Returns an error if you have global chat off, send an empty message, is muted or their
    current area's IC chat is locked.

    SYNTAX
    /scream <message>

    PARAMETERS
    <message>: Message to be sent

    EXAMPLE
    >>> /scream Hello World
    Sends `Hello World` to users in scream reachable areas+staff.
    """

    try:
        Constants.assert_command(client, arg, parameters='>0')
    except ArgumentError:
        raise ArgumentError('You cannot send an empty message.')
    if client.muted_global:
        raise ClientError('You have the global chat muted.')
    if client.is_muted:
        raise ClientError("You have been muted by a moderator.")
    if not client.is_staff() and client.area.ic_lock:
        raise ClientError('The IC chat in this area is currently locked.')

    arg = arg[:256]  # Cap

    if not client.is_gagged:
        client.send_ooc(f'You screamed `{arg}`.')

        if not client.area.private_area:
            client.send_ooc_others(msg=f"You heard {client.displayname} scream `{arg}` nearby.",
                                   is_zstaff_flex=False, to_deaf=False,
                                   pred=lambda c: (not c.muted_global and
                                                   (c.area == client.area or
                                                    ((client.is_staff() or not c.area.ic_lock) and
                                                     c.area.name in client.area.scream_range))))
            client.send_ooc_others(f'(X) {client.displayname} [{client.id}] screamed `{arg}` '
                                   f'({client.area.id}).', is_zstaff_flex=True,
                                   pred=lambda c: not c.muted_global)
        else:
            client.send_ooc_others(msg=f"You heard {client.displayname} scream `{arg}` nearby.",
                                   is_zstaff_flex=False, to_deaf=False, in_area=True,
                                   pred=lambda c: not c.muted_global)
            client.send_ooc_others(f'(X) {client.displayname} [{client.id}] screamed `{arg}` '
                                   f'({client.area.id}).', is_zstaff_flex=True, in_area=True,
                                   pred=lambda c: not c.muted_global)

        client.send_ic(msg=arg, pos=client.pos, folder=client.char_folder, char_id=client.char_id,
                       showname='[S] ' + client.showname_else_char_showname, hide_character=1)

        if not client.area.private_area:
            client.send_ic_others(msg=arg, to_deaf=False,
                                  showname='[S] ' +
                                           client.showname_else_char_showname,
                                  folder=client.char_folder, char_id=client.char_id,
                                  bypass_deafened_starters=True,  # send_ic handles nerfing for deaf
                                  pred=lambda c: (not c.muted_global and
                                                  (c.area == client.area or
                                                   ((client.is_staff() or not c.area.ic_lock) and
                                                    c.area.name in client.area.scream_range))))
            client.send_ic_others(msg=arg, to_deaf=True,
                                  showname='???',
                                  folder=client.char_folder, char_id=client.char_id,
                                  bypass_deafened_starters=True,  # send_ic handles nerfing for deaf
                                  pred=lambda c: (not c.muted_global and
                                                  (c.area == client.area or
                                                   ((client.is_staff() or not c.area.ic_lock) and
                                                    c.area.name in client.area.scream_range))))
        else:
            client.send_ic_others(msg=arg, to_deaf=False,
                                  showname='[S]' +
                                           client.showname_else_char_showname,
                                  folder=client.char_folder, char_id=client.char_id,
                                  in_area=client.area,
                                  bypass_deafened_starters=True,  # send_ic handles nerfing for deaf
                                  pred=lambda c: not c.muted_global)

    else:
        client.send_ooc('You attempted to scream but you have no mouth.')
        client.send_ooc_others('You hear some grunting noises.', is_zstaff_flex=False,
                               to_deaf=False, in_area=True, pred=lambda c: not c.muted_global)
        # Deaf players get no notification on a gagged player screaming
        client.send_ooc_others(f'(X) {client.displayname} [{client.id}] attempted to scream '
                               f'`{arg}` while gagged ({client.area.id}).',
                               is_zstaff_flex=True, pred=lambda c: not c.muted_global)

    client.check_lurk()
    logger.log_server(
        f'[{client.area.id}][{client.get_char_name()}][SCREAM]{arg}.', client)


def ooc_cmd_scream_range(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Returns the current area's scream range (i.e. users in which areas who would hear a /scream from
    the current area).

    SYNTAX
    /scream_range

    PARAMETERS
    None

    EXAMPLES
    >>> /scream_range
    Obtains the current area's scream range, for example {'Basement'}
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    info = '== Areas in scream range of area {} =='.format(client.area.name)
    # If no areas in scream range, print a manual message.
    if len(client.area.scream_range) == 0:
        info += '\r\n*No areas.'
    # Otherwise, build the list of all areas.
    else:
        areas = [client.hub.area_manager.get_area_by_name(area_name)
                 for area_name in client.area.scream_range]
        for area in sorted(areas, key=lambda area: area.id):
            info += '\r\n*{}-{}'.format(area.id, area.name)

    client.send_ooc(info)


def ooc_cmd_scream_set(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Toggles the ability of ONE given area by name or ID to hear a scream from the current area on
    or off. This only modifies the given area's status in the current area's scream range, unlike
    /scream_set_range. Note that scream ranges are unidirectional, so if you want two areas to hear
    one another, you must use this command twice.
    Returns an error if an invalid area name or area ID is given, or if the current area is the
    target of the selection.

    SYNTAX
    /scream_set <target_area>

    PARAMETERS
    <target_area>: The area whose ability to hear screams from the current area must be switched.

    EXAMPLES
    Assuming Area 2: Class Trial Room, 2 starts as not part of the current area's (say Basement)
    scream range...
    >>> /scream_set Class Trial Room,\ 2
    Adds "Class Trial Room, 2" to the scream range of Basement (note the \ escape character)
    >>> /scream_set 2
    Removes "Class Trial Room, 2" from the scream range of Basement.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')

    # This should just return a list with one area
    intended_area = Constants.parse_area_names(client, arg.split(', '))
    if len(intended_area) > 1:
        raise ArgumentError(
            'This command takes one area name (did you mean /scream_set_range ?).')

    # Convert the one element list into the area name
    intended_area = intended_area[0]
    if intended_area == client.area:
        raise ArgumentError(
            'You cannot add or remove the current area from the scream range.')

    # If intended area not in range, add it
    if intended_area.name not in client.area.scream_range:
        client.area.scream_range.add(intended_area.name)
        client.send_ooc('Added area {} to the scream range of area {}.'
                        .format(intended_area.name, client.area.name))
        client.send_ooc_others('(X) {} [{}] added area {} to the scream range of area {} ({}).'
                               .format(client.displayname, client.id, intended_area.name,
                                       client.area.name, client.area.id), is_zstaff_flex=True)
        logger.log_server('[{}][{}]Added area {} to the scream range of area {}.'
                          .format(client.area.id, client.get_char_name(), intended_area.name,
                                  client.area.name), client)
    else:  # Otherwise, add it
        client.area.scream_range.remove(intended_area.name)
        client.send_ooc('Removed area {} from the scream range of area {}.'
                        .format(intended_area.name, client.area.name))
        client.send_ooc_others('(X) {} [{}] removed area {} from the scream range of area {} ({}).'
                               .format(client.displayname, client.id, intended_area.name,
                                       client.area.name, client.area.id), is_zstaff_flex=True)
        logger.log_server('[{}][{}]Removed area {} from the scream range of area {}.'
                          .format(client.area.id, client.get_char_name(), intended_area.name,
                                  client.area.name), client)


def ooc_cmd_scream_set_range(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sets the current area's scream range to a given list of areas by name or ID separated by commas.
    This completely overrides the old scream range, unlike /scream_set.
    Passing in no arguments sets the scream range to nothing (i.e. a soundproof room).
    Note that scream ranges are unidirectional, so if you want two areas to hear one another, you
    must use this command twice.
    The special keyword <ALL> means all areas in the hub should be able to listen to screams
    from the current area. The special keyword <REACHABLE_AREAS> means all areas reachable from
    the current area.
    Returns an error if an invalid area name or area ID is given, if the current area is part of
    the selection, or if a special keyword is used in conjunction with another argument.

    SYNTAX
    /scream_set_range {area_1}, {area_2}, {area_3}, ...

    PARAMETERS
    {area_n}: An area to add to the current scream range. Can be either an area name or area ID.

    EXAMPLES:
    Assuming the current area is Basement...
    >>> /scream_set_range Class Trial Room 3
    Sets Basement's scream range to "Class Trial Room 3"
    >>> /scream_set_range Class Trial Room,\ 2, 1, Class Trial Room 3
    Sets Basement's scream range to "Class Trial Room, 2" (note the \ escape character"), area 1 and
    "Class Trial Room 3".
    >>> /scream_set_range
    Sets Basement's scream range to no areas.
    >>> /scream_set_range <ALL>
    Sets Basement's scream range to be all areas.
    >>> /scream_set_range <REACHABLE_AREAS>
    Sets Basement's scream range to be all areas reachable from Basement.
    """

    Constants.assert_command(client, arg, is_staff=True)

    if not arg:
        client.area.scream_range = set()
        area_names = '{}'
    else:
        raw_areas = arg.split(', ')
        if '<ALL>' in raw_areas:
            if len(raw_areas) != 1:
                raise ArgumentError('You may not include multiple areas when including a special '
                                    'keyword.')
            area_names = '<ALL>'
            client.area.scream_range = {area.name for area in client.hub.area_manager.get_areas()
                                        if area != client.area}
        elif '<REACHABLE_AREAS>' in raw_areas:
            if len(raw_areas) != 1:
                raise ArgumentError('You may not include multiple areas when including a special '
                                    'keyword.')
            area_names = '<REACHABLE_AREAS>'
            client.area.scream_range = client.area.reachable_areas.copy() - \
                                       {client.area.name}
        else:
            areas = Constants.parse_area_names(client, raw_areas)
            if client.area in areas:
                raise ArgumentError(
                    'You cannot add the current area to the scream range.')
            area_names = {area.name for area in areas}
            client.area.scream_range = area_names

    client.send_ooc('Set the scream range of area {} to be: {}.'
                    .format(client.area.name, area_names))
    client.send_ooc_others('(X) {} [{}] set the scream range of area {} to be: {} ({}).'
                           .format(client.displayname, client.id, client.area.name, area_names,
                                   client.area.id), is_zstaff_flex=True)
    logger.log_server('[{}][{}]Set the scream range of area {} to be: {}.'
                      .format(client.area.id, client.get_char_name(), client.area.name,
                              area_names), client)


def ooc_cmd_shoutlog(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    List the last 20 shouts performed in the current area (Hold it, Objection, Take That, etc.).
    If given an argument, it will return the shoutlog of the given area by area ID or name.
    Otherwise, it will obtain the one from the current area.
    Returns an error if the given identifier does not correspond to an area.

    SYNTAX
    /shoutlog {target_area}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {target_area}: Area whose shoutlog will be returned (either ID or name).

    EXAMPLES
    Assuming currently in the Basement (area 0)...
    >>> /shoutlog
    You may get something like the next example
    >>> /shoutlog 0
    May return something like this:
    | $H: == Shout log of Basement (0) ==
    | *Sat Jun 29 13:15:56 2019 | [1] Phantom (1234567890) used shout 1 with the message: I consent
    | *Sat Jun 29 13:16:41 2019 | [1] Phantom (1234567890) used shout 3 with the message: u wrong m9
    """

    Constants.assert_command(client, arg, is_staff=True)
    if not arg:
        arg = client.area.name

    # Obtain matching area's shoutlog
    for area in Constants.parse_area_names(client, [arg]):
        info = area.get_shoutlog()
        client.send_ooc(info)


def ooc_cmd_showname(client: ClientManager.Client, arg: str):
    """
    If given an argument, sets the client's showname to that. Otherwise, it clears their showname
    to use the default setting (character showname). These custom shownames override whatever client
    showname the current character has, and is persistent between between character swaps, area
    changes, etc.
    Returns an error if new custom showname exceeds the server limit (server parameter
    'showname_max_length', is already used in the current area, if shownames have been frozen
    and you are not logged in, if you did not have a showname and attempted to clear
    it anyway, or if you had a showname and attempted to set it to the same value.

    SYNTAX
    /showname <new_showname>
    /showname

    PARAMETERS
    <new_showname>: New desired showname.

    EXAMPLES
    >>> /showname Phantom
    Sets your showname to Phantom.
    >>> /showname
    Clears your showname.
    """

    client.command_change_showname(arg, True)


def ooc_cmd_showname_freeze(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Toggles non-staff members being able to use /showname or not.
    It does NOT clear their shownames (see /showname_nuke).
    Staff can still use /showname_set to set shownames of others.

    SYNTAX
    /showname_freeze

    PARAMETERS
    None

    EXAMPLE
    Assuming shownames are not frozen originally...
    >>> /showname_freeze
    Freezes all shownames. Only staff members can change or remove them.
    >>> /showname_freeze
    Unfreezes all shownames. Everyone can use /showname again.
    """

    Constants.assert_command(client, arg, is_mod=True, parameters='=0')

    client.server.showname_freeze = not client.server.showname_freeze
    status = {False: 'unfrozen', True: 'frozen'}

    client.send_ooc('You have {} all shownames.'.format(
        status[client.server.showname_freeze]))
    client.send_ooc_others('A mod has {} all shownames.'
                           .format(status[client.server.showname_freeze]),
                           is_officer=False, in_hub=None)
    client.send_ooc_others('{} [{}] has {} all shownames.'
                           .format(client.name, client.id, status[client.server.showname_freeze]),
                           is_officer=True, in_hub=None)
    logger.log_server('{} has {} all shownames.'
                      .format(client.name, status[client.server.showname_freeze]), client)


def ooc_cmd_showname_history(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    List all shownames a user by client ID or IPID has had during the session. Output
    differentiates between self-initiated showname changes (such as the ones via /showname) by
    using "Self" and third-party-initiated ones by using "Was" (such as /showname_set, or by
    changing areas and having a showname conflict).

    If given IPID, it will obtain the showname history of all the clients opened by the target.
    Otherwise, it will just obtain the showname history of the given client.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /showname_history <client_id>
    /showname_history <client_ipid>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    EXAMPLE
    >>> /showname_history 1
    May return something like this:
    | $H: == Showname history of client 1 ==
    | *Sat Jun 1 18:52:32 2019 | Self set to Cas
    | *Sat Jun 1 18:52:56 2019 | Was set to NotCas
    | *Sat Jun 1 18:53:47 2019 | Was set to Ces
    | *Sat Jun 1 18:53:54 2019 | Self cleared
    | *Sat Jun 1 18:54:36 2019 | Self set to Cos
    | *Sat Jun 1 18:54:46 2019 | Was cleared
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')

    # Obtain matching targets's showname history
    for c in Constants.parse_id_or_ipid(client, arg):
        info = c.get_showname_history()
        client.send_ooc(info)


def ooc_cmd_showname_nuke(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Clears all shownames from non-staff members.

    SYNTAX
    /showname_nuke

    PARAMETERS
    None

    EXAMPLE
    >>> /showname_nuke
    Clears all shownames.
    """

    Constants.assert_command(client, arg, is_mod=True, parameters='=0')

    for c in client.server.get_clients():
        if not c.is_staff() and c.showname != '':
            c.change_showname('')

    client.send_ooc('You have nuked all shownames.')
    client.send_ooc_others('A mod has nuked all shownames.',
                           is_officer=False, in_hub=None)
    client.send_ooc_others('{} [{}] has nuked all shownames.'
                           .format(client.name, client.id), is_officer=True, in_hub=None)
    logger.log_server(
        '{} has nuked all shownames.'.format(client.name), client)


def ooc_cmd_showname_set(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    If given a second argument, sets the showname of the given client by client ID or IPID to that.
    Otherwise, it clears their showname to use the default setting (character showname).
    These custom shownames override whatever showname the current character has, and is persistent
    between between character swaps/area changes/etc.
    If given IPID, it will set the shownames of all the clients opened by the target. Otherwise, it
    will just set the showname of the given client.
    Returns an error if the given identifier does not correspond to a user.
    Does nothing for targets whose shownames could not be set to the given value.

    SYNTAX
    /showname_set <client_id> {new_showname}
    /showname_set <client_ipid> {new_showname}

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea).
    <client_ipid>: IPID for the client (number in parentheses in /getarea).

    OPTIONAL PARAMETERS
    {new_showname}: New desired showname.

    EXAMPLES
    >>> /showname_set 1 Phantom
    Sets the showname of the user with client ID 1 to Phantom.
    >>> /showname_set 1234567890
    Clears the showname of the client(s) with IPID 1234567890.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='>0')

    try:
        separator = arg.index(" ")
    except ValueError:
        separator = len(arg)

    user_id = arg[:separator]
    showname = arg[separator + 1:]

    # Set matching targets's showname
    for c in Constants.parse_id_or_ipid(client, user_id):
        old_showname = c.showname
        if old_showname == showname == '':
            client.send_ooc(f'Unable to clear the showname of client {c.id}: '
                            f'target already does not have a showname.')
            continue
        if old_showname == showname:
            client.send_ooc(f'Unable to set the showname of client {c.id}: '
                            f'target already has that showname.')
            continue

        try:
            c.change_showname(showname)
        except (ClientError, ValueError) as exc:
            client.send_ooc(
                f'Unable to set the showname of client {c.id}: {exc}')
            continue

        if showname:
            if old_showname:
                s_message = ('You have changed the showname of client {} from `{}` to `{}`.'
                             .format(c.id, old_showname, showname))
                w_message = ('(X) {} [{}] changed the showname of client {} from `{}` to `{}` in '
                             'your zone ({}).'
                             .format(client.displayname, client.id, c.id, old_showname, c.showname,
                                     c.area.id))
                o_message = ('Your showname was changed from `{}` to `{}` by a staff member.'
                             .format(old_showname, showname))
                l_message = ('Changed showname of {} from {} to {}.'
                             .format(c.ipid, old_showname, showname))
            else:
                s_message = 'You have set the showname of client {} to `{}`.'.format(
                    c.id, showname)
                w_message = ('(X) {} [{}] set the showname of client {} to `{}` in your zone ({}).'
                             .format(client.displayname, client.id, c.id, c.showname, c.area.id))
                o_message = ('Your showname was set to `{}` by a staff member.'
                             .format(showname))
                l_message = ('Set showname of {} to {}.'
                             .format(c.ipid, showname))
        else:
            s_message = 'You have cleared the showname of client {}.'.format(
                c.id)
            w_message = ('(X) {} [{}] cleared the showname `{}` of client {} in your zone ({}).'
                         .format(client.displayname, client.id, old_showname, c.id, c.area.id))
            o_message = 'Your showname `{}` was cleared by a staff member.'.format(
                old_showname)
            l_message = 'Cleared showname {} of {}.'.format(
                old_showname, c.ipid)

        client.send_ooc(s_message)
        client.send_ooc_others(w_message, not_to={c}, is_zstaff=c.area)
        c.send_ooc(o_message)
        logger.log_server(l_message, client)


def ooc_cmd_sneak(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY+VARYING REQUIREMENTS)
    Sets given user based on client ID or IPID to be sneaking so that they are invisible through
    /getarea(s), /showname_list and /area.
    If given IPID, it will affect all clients opened by the target. Otherwise, it will just affect
    the given client.
    Search by IPID can only be performed by CMs and mods.
    If no target is given, the target will be yourself.
    If the target is in a private area, or in a lobby area and you are not an officer, or is
    already sneaked, the sneak will fail.
    Requires /reveal to undo.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /sneak
    /sneak <client_id>
    /sneak <client_ipid>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    EXAMPLES
    >>> /sneak 1
    Set user with client ID 1 to be sneaking.
    >>> /sneak 1234567890
    Set all clients opened by the user with IPID 1234567890 to be sneaking.
    """

    Constants.assert_command(client, arg, is_staff=True)

    if arg:
        targets = Constants.parse_id_or_ipid(client, arg)
    else:
        targets = [client]

    # Sneak matching targets
    for c in targets:
        if client.is_gm and c.area.lobby_area:
            client.send_ooc('Target client is in a lobby area. You have insufficient permissions '
                            'to hide someone in such an area.')
            continue
        if c.area.private_area:
            client.send_ooc('Target client is in a private area. You are not allowed to hide '
                            'someone in such an area.')
            continue
        if not c.is_visible:
            client.send_ooc('Target client is already sneaking.')
            continue

        if c != client:
            client.send_ooc("{} is now sneaking.".format(c.displayname))
            client.send_ooc_others('(X) {} [{}] sneaked {} [{}] ({}).'
                                   .format(client.displayname, client.id, c.displayname,
                                           c.id, c.area.id),
                                   not_to={c}, is_zstaff=True)
        else:
            client.send_ooc_others('(X) {} [{}] sneaked themselves ({}).'
                                   .format(client.displayname, client.id, c.area.id),
                                   is_zstaff=True)
        c.change_visibility(False)


def ooc_cmd_sneakself(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY+VARYING REQUIREMENTS)
    Makes all opened multiclients be sneaked without having to manually sneak them.
    Opened multiclients that are already sneaked are unaffected.
    If a multiclient is in a private area, or in a lobby area and you are not an officer, or is
    already sneaked, the sneak will fail for that multiclient.
    Returns an error if no opened multiclients can successfully be sneaked.

    SYNTAX
    /sneakself

    EXAMPLES
    If user with client ID 0 is GM has multiclients with ID 1 and 3, neither sneaked, and runs...
    >>> /sneakself
    Sneaks clients 0, 1 and 3.
    """

    Constants.assert_command(client, arg, is_staff=True)

    targets = [c for c in client.get_multiclients() if c.is_visible]
    targets = [c for c in targets if not c.area.private_area]
    if not client.is_officer():
        targets = [c for c in targets if c.area.lobby_area]
    if not targets:
        raise ClientError('No opened clients can be sneaked.')

    # Sneak matching targets
    for c in targets:
        c.change_visibility(False)

    client.send_ooc("You sneaked all of your valid multiclients.")
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] sneaked all their valid '
                           f'multiclients [{client.id}] ({client.area.id}).',
                           not_to=set(targets), is_zstaff=True)

    non_targets = [c for c in client.get_multiclients() if c not in targets]
    if non_targets:
        s_non_targets = Constants.cjoin(
            [f'{c.displayname} [{c.id}]' for c in non_targets])
        client.send_ooc(
            f'The following clients could not be sneaked: {s_non_targets}')


def ooc_cmd_spectate(client: ClientManager.Client, arg: str):
    """
    Switches your current character to the SPECTATOR character.
    Returns an error if your character is already a SPECTATOR.

    SYNTAX
    /spectate

    PARAMETERS
    None

    EXAMPLES
    >>> /spectate
    Returns "You are now spectating." or "You are already spectating."
    """

    Constants.assert_command(client, arg, parameters='=0')

    # If user is already SPECTATOR, no need to change.
    if client.char_id == -1:
        raise ClientError('You are already spectating.')

    # Change the character to SPECTATOR
    client.change_character(-1)
    client.send_ooc('You are now spectating.')


def ooc_cmd_summon(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY+VARYING REQUIREMENTS)
    Summons a user by client ID or IPID to a given area by area ID or name, or your area if
    not given an area. GMs cannot perform this command on users in lobby areas.
    If given IPID, it will summon all clients you opened. Otherwise, it will just summon the given
    user. Search by IPID can only be performed by CMs and mods.
    Returns an error if the given identifier does not correspond to a user, or if there was some
    sort of error in the process of summoning the user to the area (e.g. full area).

    SYNTAX
    /summon <client_id> {target_area}
    /summon <client_ipid> {target_area}

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    OPTIONAL PARAMETERS
    {target_area}: Intended area to summon the user to, by area ID or name

    EXAMPLES
    Assuming yo are in area 0...
    >>> /summon 1
    Summons the user with client ID 1 to area 0.
    >>> /summon 1234567890 3
    Summons all the clients opened by the user with IPID 1234567890 to area 3.
    >>> /summon 0987654321 Lobby
    Summons all the clients opened by the user with IPID 0987654321 to Lobby.
    >>> /summon 3 Class Trial Room,\ 2
    Summons the user with client ID 1 to Class Trial Room, 2 (note the ,\).
    """

    Constants.assert_command(client, arg, is_staff=True,
                             parameters='>0', split_spaces=True)

    arg = arg.split(' ')

    if client.area.lobby_area and not client.is_officer():
        raise ClientError(
            'You must be authorized to summon clients in lobby areas.')

    if len(arg) == 1:
        area = client.area
    else:
        area = Constants.parse_area_names(client, [" ".join(arg[1:])])[0]

    for c in Constants.parse_id_or_ipid(client, arg[0]):
        # Failsafe in case summoned player has their character changed during the summon
        old_displayname = c.displayname
        old_area = c.area

        try:
            c.change_area(area, override_passages=True, override_effects=True, ignore_bleeding=True,
                          ignore_autopass=True)
        except ClientError as error:
            error_mes = ", ".join([str(s) for s in error.args])
            client.send_ooc('Unable to summon {} [{}] to area {}: {}'
                            .format(old_displayname, c.id, area.id, error_mes))
        else:
            client.send_ooc('You summoned {} [{}] from area {} to area {}.'
                            .format(old_displayname, c.id, old_area.id, area.id))
            c.send_ooc(
                'You were summoned from the area to area {}.'.format(area.id))
            client.send_ooc_others('(X) {} [{}] summoned {} [{}] from area {} to area {}.'
                                   .format(client.displayname, client.id, old_displayname, c.id,
                                           old_area.id, area.id),
                                   not_to={c}, is_staff=True)

            if old_area.is_locked or old_area.is_modlocked:
                try:  # Try and remove the IPID from the area's invite list
                    old_area.invite_list.pop(c.ipid)
                except KeyError:
                    # only happens if target joined the locked area through mod powers
                    pass

            if client.party:
                party = client.party
                party.remove_member(client)
                client.send_ooc('You were also kicked off your party.')
                for member in party.get_members():
                    member.send_ooc(
                        '{} was summoned off your party.'.format(old_displayname))


def ooc_cmd_st(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Send a message to the private server-wide staff chat. Only staff members can send and receive
    messages from it (i.e. it is not a report command for normal users).

    SYNTAX
    /st <message>

    PARAMETERS
    <message>: Your message

    EXAMPLES
    >>> /st Need help in area 0
    Sends "Need help in area 0" to all staff members.
    """

    Constants.assert_command(client, arg, is_staff=True)

    pre = '{} [Staff] {}'.format(client.server.config['hostname'], client.name)
    for c in client.hub.get_players():
        c.send_ooc(arg, username=pre, pred=lambda c: c.is_staff())
    logger.log_server('[{}][STAFFCHAT][{}][{}]{}.'
                      .format(client.area.id, client.get_char_name(), client.name, arg), client)


def ooc_cmd_status(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    Obtains the status of a user by ther ID. If given no identifier, it will return your status.
    Returns an error if the given identifier does not correspond to a user, if the target has not
    set their status or if you are not a staff and would not be able to see the target in
    /getarea (regardless of whether /getarea is allowed in the area or not).

    SYNTAX
    /status
    /status <user_id>

    PARAMETERS
    <user_id>: Either the client ID (number in brackets in /getarea), character name, edited-to
               character, custom showname or OOC name of the intended recipient.

    EXAMPLES
    Assuming client 1 on character Phantom_HD has a custom description...
    >>> /status 1
    May return something like this:
    | $H: You note the following about Phantom_HD: 'Phantom is carrying a bag.'
    """

    msg = ''
    if client.is_blind:
        if not client.is_staff():
            raise ClientError('You are blind, so you cannot see anything.')
        msg = '(X) '
    if not client.area.lights:
        if not client.is_staff():
            raise ClientError(
                'The lights are off, so you cannot see anything.')
        msg = '(X) '

    if arg:
        cm = client.server.client_manager
        target, _, _ = cm.get_target_public(
            client, arg, only_in_area=not client.is_staff())

        if target.status:
            msg += (
                f'You note the following about {target.displayname}: {target.status}')
        else:
            msg += (
                f'You do not note anything unusual about {target.displayname}.')
    else:
        if client.status:
            msg += (f'You note the following about yourself: {client.status}')
        else:
            msg += ('You do not note anything unusual about yourself.')

    client.send_ooc(msg)


def ooc_cmd_status_set(client: ClientManager.Client, arg: str):
    """
    Sets your player status as the given argument; otherwise, clears it.
    Returns an error if you attempt to clear an already empty player status.

    SYNTAX
    /status_set
    /status_set <status>

    PARAMETERS
    <status>: New status

    EXAMPLES
    Assuming user with client ID 1 is on character Phantom_HD and iniswapped to Spam_HD...
    >>> /status_set Phantom is carrying a bag
    Sets the status to `Phantom is carrying a bag.`
    """

    if not arg and not client.status:
        raise ClientError('You already have no player status.')

    if arg:
        client.status = arg
        client.send_ooc(f'You have set your player status to {arg}')
        client.send_ooc_others(f'(X) {client.displayname} [{client.id}] set their player status '
                               f'to `{client.status}` ({client.area.id}).',
                               is_zstaff_flex=True)

        refreshed_clients = client.refresh_remembered_status()
        for c in refreshed_clients:
            c.send_ooc(f'You note something different about {client.displayname}.',
                       is_zstaff_flex=False)

        client.area.broadcast_ic_attention(
            cond=lambda c: c in refreshed_clients, ding=False)

    else:
        client.status = ''
        client.send_ooc('You have removed your player status.')
        client.send_ooc_others(f'(X) {client.displayname} [{client.id}] removed their player '
                               f'status ({client.area.id}).', is_zstaff_flex=True)

        refreshed_clients = client.refresh_remembered_status()
        for c in refreshed_clients:
            c.send_ooc(f'You no longer note something different about {client.displayname}.',
                       is_zstaff_flex=False)


def ooc_cmd_status_set_other(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sets the player status of some user by user ID as the given argument; otherwise, clears it.
    Returns an error if the target is not found, the target is you or you attempt to
    clear an already empty player status.

    SYNTAX
    /status_set_other <user_id>
    /status_set_other <user_id> <status>

    PARAMETERS
    <user_id>: Either the client ID (number in brackets in /getarea), character name, edited-to
               character, custom showname or OOC name of the intended recipient.
    <status>: New status

    EXAMPLES
    Assuming user with client ID 1 is on character Phantom_HD and iniswapped to Spam_HD...
    >>> /status_set_other Phantom_HD Phantom is carrying a bag
    Sets the status of Phantom to `Phantom is carrying a bag.`
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='>0')

    cm = client.server.client_manager
    target, _, new_status = cm.get_target_public(client, arg)
    new_status = new_status[:1024]  # Cap

    if client == target:
        raise ClientError('You cannot set your own status with this command.')
    if not new_status and not target.status:
        raise ClientError(
            f'{target.displayname} already does not have a player status.')

    client.send_ooc(
        f'You set the player status of {target.displayname} to `{new_status}`.')
    if not (target.is_blind and target.is_deaf):
        target.send_ooc('Your status was updated. Do /status to check it out.')

    if new_status:
        target.status = new_status
        client.send_ooc_others(f'(X) {client.displayname} [{target.id}] set the player status '
                               f'of {target.displayname} to `{new_status}` ({client.area.id}).',
                               is_zstaff_flex=True, not_to={target})

        refreshed_clients = target.refresh_remembered_status()
        for c in refreshed_clients:
            if c == client:
                continue
            c.send_ooc(f'You now note something about {target.displayname}.',
                       is_zstaff_flex=False)
        target.area.broadcast_ic_attention(ding=False)

    else:
        # By previous if, player must have had a status before
        target.status = ''
        client.send_ooc_others(f'(X) {client.displayname} [{target.id}] cleared the player '
                               f'status of {target.displayname} ({client.area.id}).',
                               is_zstaff_flex=True, not_to={target})

        refreshed_clients = target.refresh_remembered_status()
        for c in refreshed_clients:
            if c == client:
                continue
            c.send_ooc(f'You no longer note something different about {target.displayname}.',
                       is_zstaff_flex=False)


def ooc_cmd_switch(client: ClientManager.Client, arg: str):
    """
    Switches your current character to a different one.
    Returns an error if the character is unavailable or non-existant.

    SYNTAX
    /switch <char_name>

    PARAMETERS
    <char_name>: Character name

    EXAMPLES
    >>> /switch Phantom_HD
    Switches character to Phantom_HD.
    """

    try:
        Constants.assert_command(client, arg, parameters='>0')
    except ArgumentError:
        raise ArgumentError('You must specify a character name.')

    # Obtain char_id if character exists and then try and change to given char if available
    char_id = client.hub.character_manager.get_character_id_by_name(arg)
    client.change_character(char_id, force=client.is_mod)
    client.send_ooc(f'Changed character to {arg}.')


def ooc_cmd_think(client: ClientManager.Client, arg: str):
    """
    Sends an IC message that only you can see in IC (a thought), as well as any other players in
    your area that are either zone watchers, GMs+ or mind readers.
    Zone watchers, GMs+ or mind readers receive a copy of the thought in OOC, regardless of them
    having seen the thought because they were in the area or not.
    Players who see the thought in IC get to see it with the last sprite they saw.

    SYNTAX
    /think <message>

    PARAMETERS
    <message>: Thought

    EXAMPLES
    >>> /think Hi
    You think `Hi`.
    """

    Constants.assert_command(client, arg, parameters='>0')

    msg = arg[:256]

    client.send_ic(msg=msg, pos=client.pos, folder=client.char_folder, char_id=client.char_id,
                   showname='[T] ' + client.showname_else_char_showname,
                   bypass_text_replace=True, use_last_received_sprites=True)
    client.send_ooc(f'You thought `{arg}`.')

    client.send_ic_others(msg=msg, pos=client.pos, folder=client.char_folder,
                          char_id=client.char_id,
                          showname='[T] ' + client.showname_else_char_showname,
                          bypass_text_replace=True, use_last_received_sprites=True,
                          is_zstaff_flex=True, in_area=True)
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] thought `{arg}` '
                           f'({client.area.id}).', is_zstaff_flex=True)

    client.send_ic_others(msg=msg, pos=client.pos, folder=client.char_folder,
                          char_id=client.char_id,
                          showname='[T] ' + client.showname_else_char_showname,
                          bypass_text_replace=True, use_last_received_sprites=True,
                          is_zstaff_flex=False, in_area=True, pred=lambda c: c.is_mindreader)
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] thought `{arg}` '
                           f'({client.area.id}).',
                           is_zstaff_flex=False, pred=lambda c: c.is_mindreader)


def ooc_cmd_time(client: ClientManager.Client, arg: str):
    """
    Return the current server date and time. If the server specified a UTC time offset, it will use
    that offset instead (and also include it).

    SYNTAX
    /time

    PARAMETERS
    None

    EXAMPLES
    >>> /time
    May return something like "Sat Apr 27 19:04:17 2019".
    """

    Constants.assert_command(client, arg, parameters='=0')

    offset = client.server.config['utc_offset']
    if offset == 'local':
        current_time = time.strftime('%a %b %e %H:%M:%S %Y')
    else:
        offset_str = offset if float(offset) < 0 else '+{}'.format(offset)
        current_time_str = datetime.datetime.utcnow(
        ) + datetime.timedelta(hours=float(offset))
        current_time = current_time_str.strftime(
            '%a %b %e %H:%M:%S (UTC{}) %Y'.format(offset_str))
    client.send_ooc(current_time)


def ooc_cmd_time12(client: ClientManager.Client, arg: str):
    """
    Return the current server date and time in 12 hour format.
    Also includes the server timezone. If the server specified a UTC time offset, it will use
    that offset.

    SYNTAX
    /time12

    PARAMETERS
    None

    EXAMPLES
    >>> /time12
    May return something like "Sat Apr 27 07:04:47 PM (+0200) 2019".
    """

    Constants.assert_command(client, arg, parameters='=0')

    offset = client.server.config['utc_offset']
    if offset == 'local':
        current_time = time.strftime('%a %b %e %I:%M:%S %p (%z) %Y')
    else:
        offset_str = offset if float(offset) < 0 else '+{}'.format(offset)
        current_time_str = datetime.datetime.utcnow(
        ) + datetime.timedelta(hours=float(offset))
        current_time = current_time_str.strftime('%a %b %e %I:%M:%S %p (UTC{}) %Y'
                                                 .format(offset_str))
    client.send_ooc(current_time)


def ooc_cmd_timer(client: ClientManager.Client, arg: str):
    """
    Starts a countdown timer.
    Non-public timers will only send timer announcements/can only be consulted by the person who
    initiated the timer and staff. Public timers initiated by non-staff will only send timer
    announcements/can only be be consulted by staff and people in the same area as the person who
    initiated the timer. Public timers initiated by staff will send timer announcements/can be
    consulted by anyone at any area.
    Returns an error if the timer length is not a positive number or larger than the server timer
    limit, or if the timer name is already taken if given a name.

    SYNTAX
    /timer <length> {timername} {public}

    PARAMETERS
    <length>: time in seconds, or in mm:ss, or in h:mm:ss.

    OPTIONAL PARAMETERS
    {timername}: Timer name; defaults to username+"Timer" if empty
    {public or not}: Whether the timer is public or not; defaults to public if not fed one of
    "False", "false", "0", "No", "no".

    EXAMPLES
    Assuming you have OOC name Phantom...
    >>> /timer 10
    Starts a public timer "PhantomTimer" of 10 seconds.
    >>> /timer 3:00 T
    Starts a public timer "T" of length 3 minutes.
    >>> /timer 5:53:21 Spam No
    Starts a private timer "Spam" of length 5 hours, 53 mins and 21 secs.
    """

    Constants.assert_command(client, arg, parameters='&1-3', split_spaces=True)

    arg = arg.split(' ')

    # Check if valid length and convert to seconds
    length = Constants.parse_time_length(arg[0])  # Also internally validates

    # Check name
    if len(arg) > 1:
        name = arg[1]
    else:
        name = client.name.replace(" ", "") + "Timer"  # No spaces!
    if name in client.server.task_manager.active_timers:
        raise ClientError('Timer name {} is already taken.'.format(name))

    # Check public status
    if len(arg) > 2 and arg[2] in ['False', 'false', '0', 'No', 'no']:
        is_public = False
    else:
        is_public = True

    # Add to active timers list
    client.server.task_manager.active_timers[name] = client
    client.send_ooc(
        'You initiated a timer "{}" of length {} seconds.'.format(name, length))
    client.send_ooc_others('(X) {} [{}] initiated a timer "{}" of length {} seconds in area {} '
                           '({}).'
                           .format(client.displayname, client.id, name, length,
                                   client.area.name, client.area.id), is_zstaff_flex=True)
    client.send_ooc_others('{} initiated a timer "{}" of length {} seconds.'
                           .format(client.displayname, name, length), is_zstaff_flex=False,
                           pred=lambda c: is_public)

    client.server.task_manager.new_task(client, 'as_timer', {
        'length': length,
        'timer_name': name,
        'is_public': is_public,
    })


def ooc_cmd_timer_end(client: ClientManager.Client, arg: str):
    """
    End given timer by timer name. Requires logging in to end timers initiated by other users.
    Returns an error if timer does not exist or if you are not authorized to end the timer.

    SYNTAX
    /timer_end <timername>

    PARAMETERS
    <timername>: Timer name to cancel

    EXAMPLES
    Assuming player Spam started a timer "S", and the moderator Phantom started a timer "P"...
    >>> /timer_end S
    Both Spam and Phantom would end timer S if either ran this.
    >>> /timer_end P
    Only Phantom would end timer P if either ran this.
    """

    Constants.assert_command(client, arg, parameters='=1', split_spaces=True)

    arg = arg.split(' ')

    timer_name = arg[0]
    try:
        timer_client = client.server.task_manager.active_timers[timer_name]
    except KeyError:
        raise ClientError(
            'Timer {} is not an active timer.'.format(timer_name))

    # Non-staff are only allowed to end their own timers
    if not client.is_staff() and client != timer_client:
        raise ClientError('You must be authorized to do that.')

    task = client.server.task_manager.get_task(timer_client, 'as_timer')
    client.server.task_manager.force_asyncio_cancelled_error(task)


def ooc_cmd_timer_get(client: ClientManager.Client, arg: str):
    """
    Get remaining time from given timer if given a timer name. Otherwise, list all viewable timers.
    Returns an error if you attempt to consult a timer they have no permissions for.

    SYNTAX
    /timer_get {timername}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {timername}: Check time remaining in given timer; defaults to all timers if not given one.

    EXAMPLES
    Assuming a user Spam started a private timer "S", a moderator Phantom started a timer "P",
    and a third player Eggs started a public timer "E"...
    >>> /timer_get
    Spam and Phantom would get the remaining times of S, P and E; Eggs only S and P.
    >>> /timer_get S
    Spam and Phantom would get the remaining time of S, Eggs would get an error.
    >>> /timer_get P
    Spam, Phantom and Eggs would get the remaining time of P.
    >>> /timer_get E
    Spam, Phantom and Eggs would get the remaining time of E.
    """

    Constants.assert_command(client, arg, parameters='<2')
    arg = arg.split(' ') if arg else list()

    string_of_timers = ""

    if len(arg) == 1:
        # Check specific timer
        timer_name = arg[0]
        if timer_name not in client.server.task_manager.active_timers:
            raise ClientError(
                'Timer {} is not an active timer.'.format(timer_name))
        timers_to_check = [timer_name]
    else:  # Case len(arg) == 0
        # List all timers
        timers_to_check = client.server.task_manager.active_timers.keys()
        if not timers_to_check:
            raise ClientError('No active timers.')

    for timer_name in timers_to_check:
        timer_client = client.server.task_manager.active_timers[timer_name]
        task = client.server.task_manager.get_task(timer_client, 'as_timer')
        start = task.creation_time
        length = task.parameters['length']
        is_public = task.parameters['is_public']

        # Non-public timers can only be consulted by staff and the client who started the timer
        if not is_public and not (client.is_staff() or client == timer_client):
            continue

        # Non-staff initiated public timers can only be consulted by all staff and
        # clients in the same area as the timer initiator
        if (is_public and not timer_client.is_staff() and not
        (client.is_staff() or client == timer_client or client.area == timer_client.area)):
            continue

        _, remain_text = Constants.time_remaining(start, length)
        string_of_timers += 'Timer {} has {} remaining.\n*'.format(
            timer_name, remain_text)

    if string_of_timers == "":  # No matching timers
        if len(arg) == 1:  # Checked for a specific timer
            # This case happens when a non-authorized user attempts to check
            # a non-public timer
            string_of_timers = "Timer {} is not an active timer.  ".format(
                timer_name)
            # Double space intentional
        else:  # len(arg) == 0
            # This case happens when a non-authorized user attempts to check
            # all timers and all timers are non-public or non-viewable.
            string_of_timers = "No timers available.  "  # Double space intentional
    elif not arg:  # Used /timer_get
        string_of_timers = "Current active timers:\n*" + string_of_timers  # Add lead

    client.send_ooc(string_of_timers[:-2])  # Ignore last newline character


def ooc_cmd_ToD(client: ClientManager.Client, arg: str):
    """
    Chooses "Truth" or "Dare". Intended to be use for participants in Truth or Dare games.

    SYNTAX
    /ToD

    PARAMETERS
    None

    EXAMPLES
    >>> /ToD
    May return something like 'Phoenix_HD has to do a truth.'
    """

    Constants.assert_command(client, arg, parameters='=0')

    coin = ['truth', 'dare']
    flip = random.choice(coin)
    client.area.broadcast_ooc(
        '{} has to do a {}.'.format(client.displayname, flip))
    logger.log_server('[{}][{}]has to do a {}.'
                      .format(client.area.id, client.get_char_name(), flip), client)


def ooc_cmd_toggle_allpasses(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Toggles receiving autopass notifications from players who do not have autopass on. Note this
    does not toggle autopass for everyone.
    Receiving such notifications is turned off by default.

    SYNTAX
    /toggle_allpasses

    PARAMETERS
    None

    EXAMPLES
    Assuming receive all autopass notifications are off...
    >>> /toggle_allpasses
    Toggles all autopass notifications on.
    >>> /toggle_allpasses
    Toggles all autopass notifications off.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    client.get_nonautopass_autopass = not client.get_nonautopass_autopass
    status = {False: 'no longer', True: 'now'}

    client.send_ooc('You are {} receiving autopass notifications from players without autopass.'
                    .format(status[client.get_nonautopass_autopass]))


def ooc_cmd_toggle_allrolls(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Toggles receiving /roll and /rollp notifications from areas other than the current one.
    Notifications are turned off by default.

    SYNTAX
    /toggle_allrolls

    PARAMETERS
    None

    EXAMPLES
    Assuming receive all rolls notifications are off...
    >>> /toggle_allrolls
    Toggles all rolls notifications on.
    >>> /toggle_allpasses
    Toggles all rolls notifications off.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    client.get_foreign_rolls = not client.get_foreign_rolls
    status = {False: 'no longer', True: 'now'}

    client.send_ooc('You are {} receiving roll results from other areas.'
                    .format(status[client.get_foreign_rolls]))


def ooc_cmd_toggle_fp(client: ClientManager.Client, arg: str):
    """
    Toggles first person mode on or off. If on, you will not receive your character sprites when you
    send messages yourself, but instead will keep whatever the last sprite used was onscreen.

    SYNTAX
    /toggle_fp

    PARAMETERS
    None

    EXAMPLES
    Assuming first person mode is currently off...
    >>> /toggle_fp
    Toggles first person mode on.
    >>> /toggle_fp
    Toggles first person mode off.
    """

    Constants.assert_command(client, arg, parameters='=0')

    client.first_person = not client.first_person
    status = {True: 'now', False: 'no longer'}

    client.send_ooc('You are {} in first person mode.'.format(
        status[client.first_person]))


def ooc_cmd_toggle_fs(client: ClientManager.Client, arg: str):
    """
    Toggles forward sprites mode on or off. If off, no matter what message you send, your
    sprite will not be forwarded to target players, but instead they will see whatever the last
    sprite used was onscreen appear with the message.

    SYNTAX
    /toggle_fs

    PARAMETERS
    None

    EXAMPLES
    Assuming forward sprites mode on...
    >>> /toggle_fs
    Toggles forward sprites mode off.
    >>> /toggle_fs
    Toggles forward sprites mode on.
    """

    Constants.assert_command(client, arg, parameters='=0')

    client.forward_sprites = not client.forward_sprites
    status = {True: 'now', False: 'no longer'}

    client.send_ooc('You are {} in forward sprites mode.'.format(
        status[client.forward_sprites]))


def ooc_cmd_toggle_global(client: ClientManager.Client, arg: str):
    """
    Toggles global messages being sent to you being allowed/disallowed.

    SYNTAX
    /toggle_global

    PARAMETERS
    None

    EXAMPLES
    Assuming receiving global messages mode is on...
    >>> /toggle_global
    Toggles receiving global messages mode off.
    >>> /toggle_global
    Toggles receiving global messages mode on.
    """

    Constants.assert_command(client, arg, parameters='=0')

    client.muted_global = not client.muted_global
    status = {True: 'no longer', False: 'now'}

    client.send_ooc('You will {} receive global messages.'.format(
        status[client.muted_global]))


def ooc_cmd_toggle_music_list_default(client: ClientManager.Client, arg: str):
    """
    Toggles the option that controls which music list shown when no personal music list is active:
    the current hub music list (default), or the server default music list.

    SYNTAX
    /toggle_music_list_default

    PARAMETERS
    None

    EXAMPLES
    Assuming that the current option makes the current hub music list be shown...
    >>> /toggle_music_list_default
    The server default music list will now be shown when no personal music list is active.
    >>> /toggle_music_list_default
    The current hub music list will now be shown when no personal music list is active.
    """

    Constants.assert_command(client, arg, parameters='=0')

    new_value = not client.music_manager.if_default_show_hub_music
    client.music_manager.if_default_show_hub_music = new_value

    if new_value:
        client.send_ooc('You will now see the hub music list whenever you do not have a '
                        'personal music list active.')
    else:
        client.send_ooc('You will now see the server music list whenever you do not have a '
                        'personal music list active.')
    client.send_music_list_view()


def ooc_cmd_toggle_pm(client: ClientManager.Client, arg: str):
    """
    Toggles between being able to receive PMs or not.

    SYNTAX
    /toggle_pm

    PARAMETERS
    None

    EXAMPLES
    Assuming receiving PMs is on...
    >>> /toggle_pm
    Toggles receiving PMs mode off.
    >>> /toggle_pm
    Toggles receiving PMs mode on.
    """

    Constants.assert_command(client, arg, parameters='=0')

    client.pm_mute = not client.pm_mute
    status = {True: 'You will no longer receive PMs.',
              False: 'You will now receive PMs.'}

    client.send_ooc(status[client.pm_mute])


def ooc_cmd_toggle_shownames(client: ClientManager.Client, arg: str):
    """
    Toggles between receiving IC messages with custom shownames or receiving them all with
    character names. When joining, players will receive IC messages with shownames.

    SYNTAX
    /toggle_shownames

    PARAMETERS
    None

    EXAMPLES
    Assuming receiving shownames mode is on....
    >>> /toggle_shownames
    All subsequent messages will only include character names as the message sender.
    >>> /toggle_shownames
    All subsequent messages will include the shownames of the senders if they have one.
    """

    Constants.assert_command(client, arg, parameters='=0')

    client.show_shownames = not client.show_shownames
    status = {False: 'off', True: 'on'}

    client.send_ooc('Shownames turned {}.'.format(
        status[client.show_shownames]))


def ooc_cmd_transient(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY+VARYING REQUIREMENTS)
    Toggles a client by IP or IPID being transient or not to passage locks (i.e. can access all
    areas or only reachable areas)
    If given IPID, it will invert the transient status of all the clients opened by the target.
    Otherwise, it will just do it to the given client.
    Search by IPID can only be performed by CMs and mods.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /transient <client_id>
    /transient <client_ipid>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    EXAMPLE
    Assuming a user with client ID 0 and IPID 1234567890 starts as not being transient to
    passage locks...
    >>> /transient 0
    This user can now access all areas regardless of passage locks.
    >>> /transient 1234567890
    This user can now only access only reachable areas.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')

    # Invert current transient status of matching targets
    status = {False: 'no longer', True: 'now'}
    for c in Constants.parse_id_or_ipid(client, arg):
        c.is_transient = not c.is_transient
        client.send_ooc('{} ({}) is {} transient to passage locks.'
                        .format(c.displayname, c.area.id, status[c.is_transient]))
        c.send_ooc('You are {} transient to passage locks.'.format(
            status[c.is_transient]))
        c.send_music_list_view()  # Update their music list to reflect their new status


def ooc_cmd_trial(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Starts a trial with all players in the area. Players that are already part of a trial or that
    lack a participant character are not added to a trial. The trial creator is automatically added
    as a trial leader.
    Players added to a trial are ordered to switch to the 'trial' theme gamemode.
    Returns an error if the hub has reached its trial limit, or if you are part of another
    trial or have no character.

    SYNTAX
    /trial

    PARAMETERS
    None

    EXAMPLE
    Assuming you are in area 4...
    >>> /trial
    Starts a trial and adds everyone in the area to the trial as players.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    try:
        trial = client.hub.trial_manager.new_managee(
            creator=client,
            autoadd_on_creation_existing_users=False,
            require_participant_character=True,
            autoadd_on_client_enter=False,
            autoadd_minigame_on_player_added=False
        )
    except TrialError.AreaDisallowsBulletsError:
        raise ClientError('This area disallows bullets.')
    except TrialError.AreaHitGameConcurrentLimitError:
        raise ClientError('This area already hosts another trial.')
    except TrialError.ManagerTooManyGamesError:
        raise ClientError('The hub has reached its trial limit.')
    except TrialError.UserHitGameConcurrentLimitError:
        raise ClientError('You are already part of another trial.')
    except TrialError.UserHasNoCharacterError:
        raise ClientError(
            'You must have a participant character to create a trial.')

    client.send_ooc(
        f'You have created trial `{trial.get_id()}` in area {client.area.name}.')
    trial.add_leader(client)

    for user in client.area.clients:
        if user == client:
            continue
        try:
            trial.add_player(user)
        except TrialError.UserHitGameConcurrentLimitError:
            client.send_ooc(f'Unable to add player {user.displayname} [{user.id}]: '
                            f'they are already part of another trial.')
        except TrialError.UserHasNoCharacterError:
            client.send_ooc(f'Unable to add player {user.displayname} [{user.id}]: '
                            f'they must have a participant character to join this trial.')

    players = sorted(trial.get_players(), key=lambda c: c.displayname)
    player_list = '\n'.join([
        f'[{player.id}] {player.displayname}' for player in players
    ])

    client.send_ooc(
        f'These players were automatically added to your trial: \n{player_list}')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] created trial '
                           f'`{trial.get_id()}` in area {client.area.name} ({client.area.id}).',
                           is_zstaff_flex=True)
    client.send_ooc_others(f'You were added to trial `{trial.get_id()}`.',
                           pred=lambda c: c in trial.get_players())
    client.send_ooc_others(f'Trial `{trial.get_id()}` started in your area.',
                           pred=lambda c: c in trial.get_nonplayer_users_in_areas())


def ooc_cmd_trial_add(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Adds another user to your the trial.
    Returns an error if you are not a part of a trial or is not a leader, if the trial
    reached its player limit, or if the target cannot be found, does not have a participant
    character or is part of some trial.

    SYNTAX
    /trial_add <user_ID> <message>

    PARAMETERS
    <user_id>: Either the client ID (number in brackets in /getarea), character name, edited-to
               character, custom showname or OOC name of the intended recipient.
    <message>: Message to be sent.

    EXAMPLES
    >>> /trial_add 1
    Adds the user with client ID 1 as a player of the trial.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='>0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')
    if not trial.is_leader(client):
        raise ClientError('You are not a leader of your trial.')

    cm = client.server.client_manager
    target, _, _ = cm.get_target_public(client, arg, only_in_area=True)

    try:
        trial.add_player(target)
    except TrialError.UserNotInAreaError:
        raise ClientError(
            'This player is not part of an area part of this trial.')
    except TrialError.UserHasNoCharacterError:
        raise ClientError(
            'This player must have a participant character to join this trial.')
    except TrialError.UserHitGameConcurrentLimitError:
        raise ClientError('This player is already part of another trial.')
    except TrialError.UserAlreadyPlayerError:
        raise ClientError('This player is already part of this trial.')

    client.send_ooc(
        f'You added {target.displayname} [{target.id}] to your trial.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] added {target.displayname} '
                           f'[{target.id}] to your trial.',
                           pred=lambda c: c in trial.get_leaders())
    target.send_ooc(f'You were added to trial `{trial.get_id()}`.')


def ooc_cmd_trial_autoadd(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Toggles your trial automatically attempting to add users who join an area part of the trial
    on/off.
    Returns an error if you are not part of a trial or are not a leader of it.

    SYNTAX
    /trial_autoadd

    PARAMETERS
    None

    EXAMPLES
    Assuming autoadd is off...
    >>> /trial_autoadd
    Turns autoadd on.
    >>> /trial_autoadd
    Turns autoadd off.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')
    if not trial.is_leader(client):
        raise ClientError('You are not a leader of your trial.')

    status = {True: 'now', False: 'no longer'}
    new_autoadd = not trial.get_autoadd_on_client_enter()
    trial.set_autoadd_on_client_enter(new_autoadd)

    client.send_ooc(f'Your trial will {status[new_autoadd]} attempt to automatically add future '
                    f'users who enter an area part of your trial.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] has set your trial so that it '
                           f'will {status[new_autoadd]} attempt to automatically add future '
                           f'users who enter an area part of your trial.',
                           pred=lambda c: c in trial.get_leaders())


def ooc_cmd_trial_end(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Ends your trial. Every player of the trial is ordered to switch back to the 'default' gamemode.
    Returns an error if you are not a part of a trial or are not a leader of it.

    SYNTAX
    /trial_end

    PARAMETERS
    None

    EXAMPLE
    >>> /trial_end
    Ends your trial.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')
    if not trial.is_leader(client):
        raise ClientError('You are not a leader of your trial.')

    # Save leaders and regulars before destruction
    leaders = trial.get_leaders()
    regulars = trial.get_regulars()
    nonplayers = trial.get_nonplayer_users_in_areas()
    trial.end()

    client.send_ooc('You ended your trial.')
    client.send_ooc_others('The trial you were watching was ended.',
                           pred=lambda c: c in nonplayers)
    client.send_ooc_others('Your trial was ended.',
                           pred=lambda c: c in regulars)
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] ended your trial.',
                           pred=lambda c: c in leaders)


def ooc_cmd_trial_focus(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sets the focus level of a player in your trial by user ID.
    Returns an error if you are not part of a trial or leader of it, if the target is not found or
    not part of your trial, or if the focus value is not a number from 0 to 10.

    SYNTAX
    /trial_focus <user_id>

    PARAMETERS
    <user_id>: Either the client ID (number in brackets in /getarea), character name, edited-to
               character, custom showname or OOC name of the intended recipient.
    <message>: Message to be sent.

    EXAMPLES
    >>> /trial_focus 1 5
    Sets the focus level of client ID 1 to 5.
    >>> /trial_focus Phantom_HD 0
    Sets the focus level of Phantom_HD to 0.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='>1')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')
    if not trial.is_leader(client):
        raise ClientError('You are not a leader of your trial.')

    cm = client.server.client_manager
    target, _, _ = cm.get_target_public(client, arg, only_in_area=True)
    try:
        new_focus = float(arg.split(' ')[-1])
    except ValueError:
        raise ClientError('New focus value must be a number.')

    try:
        trial.set_focus(target, new_focus)
    except TrialError.UserNotPlayerError:
        raise ClientError('This player is not part of your trial.')
    except TrialError.FocusIsInvalidError:
        raise ClientError(
            f'This new focus value {new_focus} is outside the valid range.')

    client.send_ooc(f'You have set the focus level of {target.displayname} [{target.id}] to '
                    f'{new_focus}.')
    if client != target:
        target.send_ooc(f'Your focus level was set to {new_focus}.')
    client.send_ooc_others(f'(X) {client.name} [{client.id}] has set the focus level of '
                           f'{target.displayname} [{target.id}] to {new_focus}.',
                           pred=lambda c: c != target and c in trial.get_leaders())


def ooc_cmd_trial_influence(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sets the influence level of a player in your trial by user ID.
    Returns an error if you are not part of a trial or leader of it, if the target is not found or
    not part of your trial, or if the influence value is not a number from 0 to 10.

    SYNTAX
    /trial_influence <user_id>

    PARAMETERS
    <user_id>: Either the client ID (number in brackets in /getarea), character name, edited-to
               character, custom showname or OOC name of the intended recipient.
    <message>: Message to be sent.

    EXAMPLES
    >>> /trial_influence 1 5
    Sets the influence level of client ID 1 to 5.
    >>> /trial_influence Phantom_HD 0
    Sets the influence level of Phantom_HD to 0.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='>1')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')
    if not trial.is_leader(client):
        raise ClientError('You are not a leader of your trial.')

    cm = client.server.client_manager
    target, _, _ = cm.get_target_public(client, arg, only_in_area=True)
    try:
        new_influence = float(arg.split(' ')[-1])
    except ValueError:
        raise ClientError('New influence value must be a number.')

    try:
        trial.set_influence(target, new_influence)
    except TrialError.UserNotPlayerError:
        raise ClientError('This player is not part of your trial.')
    except TrialError.InfluenceIsInvalidError:
        raise ClientError(
            f'This new influence value {new_influence} is outside the valid range.')

    client.send_ooc(f'You have set the influence level of {target.displayname} [{target.id}] to '
                    f'{new_influence}.')
    if client != target:
        target.send_ooc(f'Your influence level was set to {new_influence}.')
    client.send_ooc_others(f'(X) {client.name} [{client.id}] has set the influence level of '
                           f'{target.displayname} [{target.id}] to {new_influence}.',
                           pred=lambda c: c != target and c in trial.get_leaders())


def ooc_cmd_trial_info(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    Returns information about your current trial. Trial leaders also obtain influence and focus
    values of the players of the trial.
    Returns an error if you are not part of a trial.

    SYNTAX
    /trial_info

    PARAMETERS
    None

    EXAMPLE
    >>> /trial_info
    Returns trial info.
    """

    Constants.assert_command(client, arg, parameters='=0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')

    info = trial.get_info(include_health=trial.is_leader(client))
    client.send_ooc(info)


def ooc_cmd_trial_join(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Enrolls you into a trial by trial ID.
    Returns an error if the trial ID is invalid, if you are not part of an area part of the trial,
    if you do not have a participant character when trying to join the trial, or if you are already
    part of this or another trial.

    SYNTAX
    /trial_join <trial_id>

    PARAMETERS
    <trial_id>: Trial ID

    EXAMPLES
    >>> /trial_join trial0
    Enrolls you in trial trial0.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='>0')

    try:
        trial = client.hub.trial_manager.get_managee_by_id(arg)
    except TrialError.ManagerInvalidGameIDError:
        raise ClientError(f'Unrecognized trial ID `{arg}`.')

    try:
        trial.add_player(client)
    except TrialError.UserNotInAreaError:
        raise ClientError('You are not part of an area part of this trial.')
    except TrialError.UserHasNoCharacterError:
        raise ClientError(
            'You must have a participant character to join this trial.')
    except TrialError.UserHitGameConcurrentLimitError:
        raise ClientError('You are already part of another trial.')
    except TrialError.UserAlreadyPlayerError:
        raise ClientError('You are already part of this trial.')

    client.send_ooc(f'You joined trial `{arg}`.')
    client.send_ooc('Become a leader of your trial with /trial_lead')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] joined your trial.',
                           pred=lambda c: c in trial.get_leaders())


def ooc_cmd_trial_kick(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Kicks a player by user ID off your trial.
    Returns an error if you are not part of a trial or leader of it, if the target is not found
    or already not a part of your trial, or if the target is you.

    SYNTAX
    /trial_kick <user_id>

    PARAMETERS
    <user_id>: Either the client ID (number in brackets in /getarea), character name, edited-to
               character, custom showname or OOC name of the intended recipient.

    EXAMPLES
    /trial_kick 1 5
    >>> Kicks client ID 1 off your trial.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='>0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')
    if not trial.is_leader(client):
        raise ClientError('You are not a leader of your trial.')

    cm = client.server.client_manager
    target, _, _ = cm.get_target_public(client, arg, only_in_area=True)
    if client == target:
        raise TrialError(
            'You cannot kick yourself off your trial (consider using /trial_leave).')

    try:
        trial.remove_player(target)
    except TrialError.UserNotPlayerError:
        raise ClientError('This player is not part of your trial.')

    client.send_ooc(
        f'You have kicked {target.displayname} [{target.id}] off your trial.')
    target.send_ooc('You were kicked off your trial.')
    client.send_ooc_others(f'(X) {client.name} [{client.id}] has kicked {target.displayname} '
                           f'[{target.id}] off your trial.',
                           pred=lambda c: c != target and c in trial.get_leaders())


def ooc_cmd_trial_lead(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Makes you a leader of your trial.
    Returns an error if you are not part of a trial or if you are already leader of that trial.

    SYNTAX
    /trial_lead

    PARAMETERS
    None

    EXAMPLE
    /trial_lead
    >>> Makes you leader of the trial.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')

    try:
        trial.add_leader(client)
    except TrialError.UserAlreadyLeaderError:
        raise ClientError('You are already a leader of this trial.')

    client.send_ooc('You are now a leader of your trial.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] is now a leader of your '
                           f'trial.', pred=lambda c: c in trial.get_leaders())


def ooc_cmd_trial_leave(client: ClientManager.Client, arg: str):
    """
    Makes you leave your current trial and any minigames you may have been a part of. It will
    also notify all other remaining trial leaders of your departure.
    If you were the only member of the trial, the trial will be destroyed.
    Returns an error if you are not part of a trial.

    SYNTAX
    /trial_leave

    PARAMETERS
    None

    EXAMPLES
    /trial_leave
    >>> Makes you leave your current trial.
    """

    Constants.assert_command(client, arg, parameters='=0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')

    tid = trial.get_id()  # Get ID now because trial may be deleted
    nonplayers = trial.get_nonplayer_users_in_areas()

    client.send_ooc(f'You have left trial `{tid}`.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] has left your trial.',
                           pred=lambda c: c in trial.get_leaders())
    trial.remove_player(client)

    if trial.is_unmanaged():
        client.send_ooc(f'Your trial `{tid}` was automatically '
                        f'ended as it lost all its players.')
        client.send_ooc_others(f'(X) Trial `{tid}` was automatically '
                               f'ended as it lost all its players.',
                               is_zstaff_flex=True, not_to=nonplayers)
        client.send_ooc_others('The trial you were watching was automatically ended '
                               'as it lost all its players.',
                               is_zstaff_flex=False, pred=lambda c: c in nonplayers)


def ooc_cmd_trial_unlead(client: ClientManager.Client, arg: str):
    """
    Removes your trial leader role.
    Returns an error if you are not part of a trial or if you are already not leader of that trial.

    SYNTAX
    /trial_unlead

    PARAMETERS
    None

    EXAMPLE
    /trial_unlead
    >>> Removes your trial leader role.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    try:
        trial = client.hub.trial_manager.get_managee_of_user(client)
    except TrialError.UserNotPlayerError:
        raise ClientError('You are not part of a trial.')

    try:
        trial.remove_leader(client)
    except TrialError.UserNotLeaderError:
        raise ClientError('You are already not a leader of this trial.')

    client.send_ooc('You are no longer a leader of your trial.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] is no longer a leader of your '
                           f'trial.', pred=lambda c: c in trial.get_leaders())


def ooc_cmd_unban(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Removes given user from the server banlist, allowing them to rejoin the server.
    Returns an error if given identifier does not correspond to a banned user.

    SYNTAX
    /unban <client_ipid>
    /unban <client_ip>

    PARAMETERS
    <client_ipid>: IPID for the client (number in parentheses in /getarea)
    <client_ip>: user IP

    EXAMPLES
    >>> /unban 1234567890
    Unbans the user with IPID 1234567890.
    >>> /unban 127.0.0.1
    Unbans the user with IP 127.0.0.1.
    """

    arg = arg.strip()
    Constants.assert_command(client, arg, is_mod=True, parameters='>0')

    if arg.isdigit():
        # IPID
        idnt = int(arg.strip())
    else:
        # IP Address
        idnt = arg.strip()

    client.server.ban_manager.remove_ban(idnt)

    client.send_ooc('Unbanned `{}`.'.format(idnt))
    client.send_ooc_others('{} [{}] unbanned `{}`.'
                           .format(client.name, client.id, idnt),
                           is_officer=True, in_hub=None)
    logger.log_server('Unbanned {}.'.format(idnt), client)


def ooc_cmd_unbanhdid(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Removes given user by HDID from the server banlist, allowing them to rejoin the server.
    Returns an error if given HDID does not correspond to a banned user.

    SYNTAX
    /unbanhdid <client_hdid>

    PARAMETERS
    <client_hdid>: User HDID (available in server logs and through a mod /whois)

    EXAMPLES
    >>> /unbanhdid abcd1234
    Unbans user with HDID abcd1234
    """

    Constants.assert_command(client, arg, is_mod=True, parameters='=1')

    if arg not in client.server.hdid_list:
        raise ClientError('Unrecognized HDID {}.'.format(arg))

    # The server checks for any associated banned IPID for a user, so in order to unban by HDID
    # all the associated IPIDs must be unbanned.

    found_banned = False
    for ipid in client.server.hdid_list[arg]:
        if client.server.ban_manager.is_banned(ipid):
            client.server.ban_manager.remove_ban(ipid)
            found_banned = True

    if not found_banned:
        raise ClientError('User is already not banned.')

    client.send_ooc('Unbanned HDID `{}`.'.format(arg))
    client.send_ooc_others('{} [{}] unbanned HDID `{}`.'
                           .format(client.name, client.id, arg),
                           is_officer=True, in_hub=None)
    logger.log_server('HDID-unbanned {}.'.format(arg), client)


def ooc_cmd_unblockdj(client: ClientManager.Client, arg: str):
    """ (OFFICER ONLY)
    Restores the ability of a user by client ID (number in brackets) or IPID (number in
    parentheses) to change music.
    If given IPID, it will affect all clients opened by the target. Otherwise, it will just affect
    the given client.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /unblockdj <client_id>
    /unblockdj <client_ipid>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    EXAMPLES
    >>> /unblockdj 1
    Restores DJ permissions to the user with client ID 1.
    >>> /unblockdj 1234567890
    Restores DJ permissions to all clients opened by the user with IPID 1234567890.
    """

    Constants.assert_command(client, arg, is_officer=True, parameters='=1')

    # Restore DJ permissions to matching targets
    for c in Constants.parse_id_or_ipid(client, arg):
        c.is_dj = True
        logger.log_server(
            'Restored DJ permissions to {}.'.format(c.ipid), client)
        client.area.broadcast_ooc(
            '{} had their DJ permissions restored.'.format(c.displayname))


def ooc_cmd_undisemconsonant(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Removes the disemconsonant effect on all IC and OOC messages of a user by client ID
    (number in brackets) or IPID (number in parentheses).
    If given IPID, it will affect all clients opened by the target. Otherwise, it will just affect
    the given client.
    Requires /disemconsonant to undo.
    Returns an error f the given identifier does not correspond to a user.

    SYNTAX
    /undisemconsonant <client_id>
    /undisemconsonant <client_ipid>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    EXAMPLES
    >>> /undisemconsonant 1
    Undisemconsonants the user with client ID 1.
    >>> /undisemconsonant 1234567890
    Undisemconsonants all clients opened by the user with IPID 1234567890.
    """

    Constants.assert_command(client, arg, is_mod=True, parameters='=1')

    # Undisemconsonant matching targets
    for c in Constants.parse_id_or_ipid(client, arg):
        c.disemconsonant = False
        logger.log_server('Undisemconsonanted {}.'.format(c.ipid), client)
        client.area.broadcast_ooc(
            "{} was undisemconsonanted.".format(c.displayname))


def ooc_cmd_undisemvowel(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Removes the disemvowel effect on all IC and OOC messages of a user by client ID (number in
    brackets) or IPID (number in parentheses).
    If given IPID, it will affect all clients opened by the target. Otherwise, it will just affect
    the given client.
    Requires /disemvowel to undo.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /undisemvowel <client_id>
    /undisemvowel <client_ipid>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    EXAMPLES
    >>> /undisemvowel 1
    Undisemvowel the user with client ID 1.
    >>> /undisemvowel 1234567890
    Undisemvowel all clients opened by the user with IPID 1234567890.
    """

    Constants.assert_command(client, arg, is_mod=True, parameters='=1')

    # Undisemvowel matching targets
    for c in Constants.parse_id_or_ipid(client, arg):
        c.disemvowel = False
        logger.log_server('Undisemvowelled {}.'.format(c.ipid), client)
        client.area.broadcast_ooc(
            "{} was undisemvowelled.".format(c.displayname))


def ooc_cmd_unfollow(client: ClientManager.Client, arg: str):
    """
    Stops following the user you are following.
    Returns an error if you are not following anyone.

    SYNTAX
    /unfollow

    PARAMETERS
    None

    EXAMPLE
    Assuming you were following someone...
    >>> /unfollow
    Stops following the user.
    """

    try:
        Constants.assert_command(client, arg, is_staff=True, parameters='=0')
    except ClientError.UnauthorizedError:
        Constants.assert_command(client, arg, parameters='=0')

    client.unfollow_user()


def ooc_cmd_ungimp(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Ungimps all IC messages of a user by client ID (number in brackets) or IPID (number in
    parentheses).
    If given IPID, it will affect all clients opened by the target. Otherwise, it will just affect
    the given client.
    Requires /gimp to undo.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /ungimp <client_id>
    /ungimp <client_ipid>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    EXAMPLES
    >>> /ungimp 1
    Ungimps the user with client ID 1.
    >>> /ungimp 1234567890
    Ungimps all clients opened by the user with IPID 1234567890.
    """

    Constants.assert_command(client, arg, is_mod=True, parameters='=1')

    # Ungimp matching targets
    for c in Constants.parse_id_or_ipid(client, arg):
        c.gimp = False
        logger.log_server('Ungimping {}.'.format(c.ipid), client)
        client.area.broadcast_ooc("{} was ungimped.".format(c.displayname))


def ooc_cmd_unglobalic(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Send subsequent IC messages to users in the same area as the client (i.e. as normal).
    It is the way to undo a /globalic command.

    SYNTAX
    /unglobalic

    PARAMETERS
    None

    EXAMPLES
    >>> /unglobalic
    Send subsequent messages normally (only to users in current area).
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    client.multi_ic = None
    client.send_ooc(
        'Your IC messages will now be only sent to your current area.')


def ooc_cmd_unhandicap(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY+VARYING REQUIREMENTS)
    Removes movement handicaps on a user by client ID or IPID so that they no longer need to wait
    a set amount of time between changing areas. This will also remove server handicaps, if any
    (such as automatic sneak handicaps).
    If given IPID, it will remove the movement handicap on all the clients opened by the target.
    Otherwise, it will just do it to the given client.
    Requires /handicap to undo.
    Search by IPID can only be performed by CMs and mods.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /unhandicap <client_id>
    /unhandicap <client_ipid>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    EXAMPLES
    >>> /unhandicap 0
    Removes all movement handicaps on the user with client ID 0.
    >>> /unhandicap 1234567890
    Removes all movement handicaps on the clients with IPID 1234567890.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')

    # Obtain targets
    for c in Constants.parse_id_or_ipid(client, arg):
        try:
            name = c.change_handicap(False)
        except ClientError:
            client.send_ooc('{} does not have an active movement handicap.'
                            .format(c.displayname))
        else:
            client.send_ooc('You removed the movement handicap "{}" on {}.'
                            .format(name, c.displayname))
            client.send_ooc_others('(X) {} [{}] removed the movement handicap "{}" on {} in area '
                                   '{} ({}).'
                                   .format(client.displayname, client.id, name, c.displayname,
                                           client.area.name, client.area.id),
                                   is_zstaff_flex=True)


def ooc_cmd_unignore(client: ClientManager.Client, arg: str):
    """
    Marks another user as unignored. You will now receive any IC messages sent from that user.
    The target will not be notified of the unignore command being executed on them.
    Requires /ignore to undo.
    Returns an error if the given identifier does not correspond to a user, if the target is
    yourself, or if you are already not ignoring the target.

    SYNTAX
    /unignore <user_id>

    PARAMETERS
    <user_id>: Either the client ID (number in brackets in /getarea), character name, edited-to
               character, custom showname or OOC name of the intended recipient.

    EXAMPLES
    >>> /unignore 1
    Unignores user with client ID 1.
    """

    Constants.assert_command(client, arg, parameters='>0')

    target, _, _ = client.server.client_manager.get_target_public(client, arg)

    if target == client:
        raise ClientError('You are already not ignoring yourself.')
    if target not in client.ignored_players:
        raise ClientError(
            f'You are already not ignoring {target.displayname} [{target.id}].')

    client.ignored_players.remove(target)
    client.send_ooc(
        f'You are no longer ignoring {target.displayname} [{target.id}].')


def ooc_cmd_unilock(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    Changes the passage status from a given area to another by name or ID. Passages are
    unidirectional, so to change a passage in both directions simultaneously, use /bilock instead.
    If given one area, it will change the passage status FROM the current area TO the given one.
    If given two areas instead, it  will change the passage status FROM the first given area TO
    the second give one (but requires staff role to use).
    Returns an error if you are unauthorized to create new passages or change existing ones in
    the originating area. In particular, non-staff members are not allowed to create passages
    that did not exist when the areas were loaded or that a staff member did not create before.

    SYNTAX
    /unilock <target_area>
    /unilock <target_area_1>, <target_area_2>

    PARAMETERS
    <target_area>: Area whose passage status that starts in the current area will be changed.
    <target_area_1>: Area whose passage status that ends in <target_area_2> will be changed.
    <target_area_2>: Area whose passage status that starts in <target_area_1> will be changed.

    EXAMPLES
    Assuming you are in area 0 when executing these commands and originally the only existing
    passage lock is from area 1 'Class Trial Room' to area 2 'Class Trial Room, 2'...
    /unilock Class Trial Room
    Locks the passage from area 0 to Class Trial Room.
    >>> /unilock 1, 2
    Unlocks the passage from Class Trial Room to Class Trial Room, 2 (keeps it unlocked the other
    way).
    >>> /unilock Class Trial Room,\ 2, 0
    Locks the passage in from Class Trial Room, 2 to area 0 (note the ,\ in the command).
    """

    Constants.assert_command(client, arg, parameters='&1-2', split_commas=True)

    areas = arg.split(', ')
    if len(areas) == 2 and not client.is_staff():
        raise ClientError('You must be authorized to use the two-parameter version of this '
                          'command.')

    areas = Constants.parse_two_area_names(client, areas, area_duplicate=False,
                                           check_valid_range=False)
    now_reachable = client.hub.area_manager.change_passage_lock(client, areas, bilock=False,
                                                                change_passage_visibility=False)

    status = {True: 'unlocked', False: 'locked'}
    now0 = status[now_reachable[0]]
    name0, name1 = areas[0].name, areas[1].name

    client.send_ooc('You have {} the passage from {} to {}.'
                    .format(now0, name0, name1))
    client.send_ooc_others('(X) {} [{}] has {} the passage from {} to {} ({}).'
                           .format(client.displayname, client.id, now0, name0, name1,
                                   client.area.id),
                           is_zstaff_flex=True)
    logger.log_server('[{}][{}]Has {} the passage from {} to {}.'
                      .format(client.area.id, client.get_char_name(), now0, name0, name1))


def ooc_cmd_unilockh(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Similar to /unilock. However, passages that are locked in this way are hidden from area lists
    and /minimap; and passages that are unlocked are revealed in area lists and /minimap.

    SYNTAX
    /unilock <target_area>
    /unilock <target_area_1>, <target_area_2>

    PARAMETERS
    <target_area>: Area whose passage status that starts in the current area will be changed.
    <target_area_1>: Area whose passage status that ends in <target_area_2> will be changed.
    <target_area_2>: Area whose passage status that starts in <target_area_1> will be changed.

    EXAMPLES
    Assuming you are in area 0 when executing these commands and originally the only existing
    passage lock is from area 1 'Class Trial Room' to area 2 'Class Trial Room, 2'...
    >>> /unilock Class Trial Room
    Locks the passage from area 0 to Class Trial Room.
    >>> /unilock 1, 2
    Unlocks the passage from Class Trial Room to Class Trial Room, 2 (keeps it unlocked the other
    way).
    >>> /unilock Class Trial Room,\ 2, 0
    Locks the passage in from Class Trial Room, 2 to area 0 (note the ,\ in the command).
    """

    Constants.assert_command(
        client, arg, parameters='&1-2', is_staff=True, split_commas=True)

    areas = Constants.parse_two_area_names(client, arg.split(', '), area_duplicate=False,
                                           check_valid_range=False)
    now_reachable = client.hub.area_manager.change_passage_lock(client, areas, bilock=False,
                                                                change_passage_visibility=True)

    status = {True: 'unlocked and revealed', False: 'locked and hid'}
    now0 = status[now_reachable[0]]
    name0, name1 = areas[0].name, areas[1].name

    client.send_ooc('You have {} the passage from {} to {}.'
                    .format(now0, name0, name1))
    client.send_ooc_others('(X) {} [{}] has {} the passage from {} to {} ({}).'
                           .format(client.displayname, client.id, now0, name0, name1,
                                   client.area.id),
                           is_zstaff_flex=True)
    logger.log_server('[{}][{}]Has {} the passage from {} to {}.'
                      .format(client.area.id, client.get_char_name(), now0, name0, name1))


def ooc_cmd_uninvite(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    Removes a client based on some ID to the area's invite list. Only staff members can invite based
    on IPID. Invites are IPID based, so anyone with the same IPID is no longer part of the area's
    invite list.
    Search by IPID can only be performed by CMs and mods.
    Returns an error if the given identifier does not correspond to a user or if target is already
    not invited.

    SYNTAX
    /uninvite <client_ipid>
    /uninvite <user_id>

    PARAMETERS
    <client_ipid>: IPID for the client (number in parentheses in /getarea)
    <user_id>: Either the client ID (number in brackets in /getarea), character name, edited-to
               character, custom showname or OOC name of the intended recipient.

    EXAMPLES
    >>> /uninvite 1
    Uninvites the user with client ID 1.
    >>> /uninvite 1234567890
    Uninvites all clients opened by the user with IPID 1234567890.
    """

    Constants.assert_command(client, arg, parameters='=1')

    if not client.area.is_locked and not client.area.is_modlocked:
        raise ClientError('Area is not locked.')

    targets = list()  # Start with empty list
    if client.is_officer() and arg.isdigit():
        targets = client.server.client_manager.get_targets(
            client, TargetType.IPID, int(arg), False)
        if targets:
            some_target = targets[0]
    if not targets:
        # Under the hood though, we need the IPID of the target, so we will still end up obtaining
        # it anyway. We want to get all clients whose IPID match the IPID of whatever we match
        some_target, _, _ = client.server.client_manager.get_target_public(
            client, arg)
        targets = client.server.client_manager.get_targets(client, TargetType.IPID,
                                                           some_target.ipid, False)

    # Check if target is already invited
    if some_target.ipid not in client.area.invite_list:
        raise ClientError('Target is already not invited to your area.')

    # Remove from invite list and notify targets
    client.area.invite_list.pop(some_target.ipid)

    for c in targets:
        # If uninviting yourself, send special message
        if client == c:
            client.send_ooc('You have uninvited yourself from this area.')
        else:
            client.send_ooc(
                'Client {} has been uninvited from your area.'.format(c.id))
            c.send_ooc('You have been uninvited from area {}.'.format(
                client.area.name))


def ooc_cmd_unlock(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    If the area is locked in some manner, attempt to perform exactly one of the following area
    unlocks in order.
    1. If player is a mod and the area is mod-locked, then mod-unlock.
    2. If player is staff and the area is gm-locked, then gm-unlock.
    3. If the area is not mod-locked nor gm-locked, then unlock.

    Returns an error if the area was locked but the unlock could not be performed (would happen due
    to insufficient permissions).

    SYNTAX
    /unlock

    PARAMETERS
    None

    EXAMPLE
    >>> /unlock
    Perform one of the unlocks described above if possible.
    """

    Constants.assert_command(client, arg, parameters='=0')

    if not client.area.is_locked and not client.area.is_modlocked:
        raise ClientError('Area is already open.')

    if client.is_mod and client.area.is_modlocked:
        client.area.modunlock()
    elif not client.area.is_modlocked:
        client.area.unlock()
    else:
        raise ClientError('You must be authorized to do that.')
    client.send_ooc('Area is unlocked.')


def ooc_cmd_unmute(client: ClientManager.Client, arg: str):
    """ (OFFICER ONLY)
    Unmutes given user based on client ID or IPID so that they are unable to speak in IC chat.
    This command does nothing for clients that are not actively muted.
    If given IPID, it will unmute all clients opened by the target. Otherwise, it will just mute the
    given client.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /unmute <client_id>
    /unmute <client_ipid>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    EXAMPLES
    >>> /unmute 1
    Unmutes user with client ID 1.
    >>> /unmute 1234567890
    Unmutes all clients opened by the user with IPID 1234567890.
    """

    Constants.assert_command(client, arg, is_officer=True, parameters='=1')

    # Mute matching targets
    for c in Constants.parse_id_or_ipid(client, arg):
        logger.log_server('Unmuted {}.'.format(c.ipid), client)
        client.area.broadcast_ooc("{} was unmuted.".format(c.displayname))
        c.is_muted = False


def ooc_cmd_unremove_h(client: ClientManager.Client, arg: str):
    """ (MOD ONLY)
    Removes the 'Remove H' effect on all IC and OOC messages of a user by client ID (number in
    brackets) or IPID (number in parentheses).
    If given IPID, it will affect all clients opened by the target. Otherwise, it will just affect
    the given client.
    Requires /remove_h to undo.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /unremove_h <client_id>
    /unremove_h <client_ipid>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    EXAMPLES
    >>> /unremove_h 1
    Removes the 'Remove H' effect on the user with client ID 1.
    >>> /unremove_h 1234567890
    Removes the 'Remove H' effect on all clients opened by the user
                               with IPID 1234567890.
    """

    Constants.assert_command(client, arg, is_mod=True, parameters='=1')

    # Remove the 'Remove H' effect on matching targets
    for c in Constants.parse_id_or_ipid(client, arg):
        c.remove_h = False
        logger.log_server(
            "Removed 'Remove H' effect on {}.".format(c.ipid), client)
        client.area.broadcast_ooc(
            "{} had the 'Remove H' effect removed.".format(c.displayname))


def ooc_cmd_version(client: ClientManager.Client, arg: str):
    """
    Obtains the current version of the server software.

    SYNTAX
    /version

    PARAMETERS
    None

    EXAMPLES
    >>> /version
    May return something like:
    | $H: This server is running TsuserverDR 4.0.0 (190801a)
    """

    Constants.assert_command(client, arg, parameters='=0')

    client.send_ooc('This server is running {}.'.format(client.server.version))


def ooc_cmd_whereis(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY+VARYING REQUIREMENTS)
    Obtains the current area of a user by client ID (number in brackets) or IPID (number in
    parentheses).
    If given IPID, it will obtain the area info for all clients opened by the target. Otherwise, it
    will just obtain the one from the given client.
    Search by IPID can only be performed by CMs and mods.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /whereis <client_id>
    /whereis <client_ipid>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)
    <client_ipid>: IPID for the client (number in parentheses in /getarea)

    EXAMPLES
    Assuming user with client ID 1 with IPID 1234567890 is in the Basement (area 0)...
    >>> /whereis 1
    May return something like this: Client 1 (1234567890) is in Basement (0)
    >>> /whereis 1234567890
    May return something like this: Client 1 (1234567890) is in Basement (0)
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')

    for c in Constants.parse_id_or_ipid(client, arg):
        client.send_ooc("Client {} ({}) is in {} ({})."
                        .format(c.id, c.ipid, c.area.name, c.area.id))


def ooc_cmd_whisper(client: ClientManager.Client, arg: str):
    """
    Sends an IC personal message to a specified user by some ID. The messages have your showname
    and your message, but does not include you sprite.
    Elevated notifications are sent to zone watchers/staff members on whispers to other people,
    which include the message content, so this is not meant to act as a private means of
    communication between players, for which /pm is recommended.
    Whispers sent by sneaked players include an empty showname so as to not reveal their identity.
    Whispers sent to sneaked players will succeed only if you are sneaking and both you
    and recipient are part of the same party. If the attempt fails but you are a staff member,
    you will get a friendly suggestion to use /guide instead.
    Deafened recipients will receive a nerfed message if whispered to.
    Non-zone watchers/non-staff players in the same area as the whisperer will be notified that
    you whispered to their target (but will not receive the content of the message), provided they
    are not blind (in which case no notification is sent) and that this was not a self-whisper.
    Returns an error if the target could not be found, if the message is empty or if you are
    gagged or IC-muted.

    SYNTAX
    /whisper <user_ID> <message>

    PARAMETERS
    <user_id>: Either the client ID (number in brackets in /getarea), character name, edited-to
               character, custom showname or OOC name of the intended recipient.
    <message>: Message to be sent.

    EXAMPLES
    >>> /whisper 1 Hey, client 1!
    Sends that message to user with client ID 1.
    >>> /whisper 0 Yo
    Sends that message to user with client ID 0.
    """

    try:
        Constants.assert_command(client, arg, parameters='>1')
    except ArgumentError:
        raise ArgumentError('Not enough arguments. Use /whisper <target> <message>. Target should '
                            'be ID, char-name, edited-to character, custom showname or OOC-name.')
    if client.is_muted:
        raise ClientError('You have been muted by a moderator.')
    if client.is_gagged:
        raise ClientError(
            'Your attempt at whispering failed because you are gagged.')

    cm = client.server.client_manager
    target, _, msg = cm.get_target_public(client, arg, only_in_area=True)
    msg = msg[:256]  # Cap

    public_area = not client.area.private_area

    final_sender = client.displayname
    final_rec_sender = 'Someone' if (
            target.is_deaf and target.is_blind) else client.displayname
    final_st_sender = client.displayname
    final_target = target.displayname
    final_message = msg

    if client == target:
        # Player whispered to themselves. Why? Dunno, ask them, not me
        client.send_ooc(f'You whispered `{final_message}` to yourself.')
        client.send_ic(msg=msg, pos=client.pos, folder=client.char_folder, char_id=client.char_id,
                       showname='[W] ' + client.showname_else_char_showname,
                       hide_character=1, bypass_deafened_starters=True)
    elif not client.is_visible ^ target.is_visible:
        # Either both client and target are visible
        # Or they are both not, where cm.get_target_public already handles removing sneaked targets
        # if they are not part of the same party as the client (or the client is not staff)
        client.send_ooc(f'You whispered `{final_message}` to {final_target}.')
        client.send_ic(msg=msg, pos=client.pos, folder=client.char_folder, char_id=client.char_id,
                       showname='[W] ' + client.showname_else_char_showname, hide_character=1,
                       bypass_deafened_starters=True)
        client.check_lurk()

        target.send_ooc(
            f'{final_sender} whispered `{final_message}` to you.', to_deaf=False)
        target.send_ooc(f'{final_rec_sender} seemed to whisper something to you, but you could not '
                        f'make it out.', to_deaf=True)
        target.send_ic(msg=msg, pos=client.pos, folder=client.char_folder, char_id=client.char_id,
                       showname='[W] ' + client.showname_else_char_showname, hide_character=1,
                       bypass_deafened_starters=True)  # send_ic handles nerfing for deafened

        if not client.is_visible and public_area:
            # This code should run if client and target are sneaked and part of same party
            # and also if the area is public
            client.send_ooc_others(f'(X) {final_st_sender} [{client.id}] whispered '
                                   f'`{final_message}` to {final_target} [{target.id}] while both '
                                   f'were sneaking and part of the same party ({client.area.id}).',
                                   is_zstaff_flex=True, not_to={target})
        else:
            # Otherwise, announce it to everyone. If the area is private, zone watchers and staff
            # get normal whisper reports if in the same area.
            if public_area:
                client.send_ooc_others(f'(X) {final_st_sender} [{client.id}] whispered '
                                       f'`{final_message}` to {final_target} [{target.id}] '
                                       f'({client.area.id}).', is_zstaff_flex=True, not_to={target})
            client.send_ooc_others(f'{final_sender} whispered something to {final_target}.',
                                   is_zstaff_flex=False if public_area else None, in_area=True,
                                   not_to={target}, to_blind=False)
    elif target.is_visible:
        client.send_ooc(f'You spooked {final_target} by whispering `{final_message}` to them while '
                        f'sneaking.')
        client.send_ic(msg=msg, pos='jud', showname='[W] ' + client.showname_else_char_showname,
                       hide_character=1, bypass_deafened_starters=True)
        client.check_lurk()

        # Note this uses pos='jud' instead of pos=client.pos. This is to mask the position of the
        # sender, so that the target cannot determine who it is based on knowing usual positions
        # of people.
        # If target is deafened, behavior is different
        target.send_ooc(f'You heard someone whisper `{final_message}` and you think it was '
                        f'directed at you, but you could not seem to tell where it came from.',
                        to_deaf=False)
        target.send_ooc('Your ears seemed to pick up something.', to_deaf=True)
        target.send_ic(msg=final_message, pos='jud', showname='???', hide_character=1,
                       bypass_deafened_starters=True)

        if not client.area.private_area:
            client.send_ooc_others(f'(X) {final_st_sender} [{client.id}] whispered '
                                   f'`{final_message}` to {final_target} [{target.id}] while '
                                   f'sneaking ({client.area.id}).', is_zstaff_flex=True,
                                   not_to={target})
    else:  # Sender is not sneaked, target is
        if client.is_staff():
            msg = (f'Your target {target.displayname} is sneaking and whispering to them would '
                   f'reveal them. Instead, use /guide')
            raise ClientError(msg)
        # Normal clients should never get here except if get_target_public is wrong
        # which would be very sad.
        raise ValueError('Never should have come here!')


def ooc_cmd_whois(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY+VARYING REQUIREMENTS)
    Lists A LOT of a client properties. CMs and mods additionally get access to a client's HDID.
    The user can be filtered by either client ID, IPID, HDID, character name (in the same area),
    edited-to character name (in the same area), showname (in the same area), character showname
    (in the same area) or OOC username (in the same area).
    However, only CMs and mods can search through IPID or HDID.
    If multiple clients match the given identifier, only one of them will be returned.
    For best results, use client ID (number in brackets), as this is the only tag that is
    guaranteed to be unique.
    If given no identifier, it will return your properties.
    Returns an error if the given identifier does not correspond to a user.

    SYNTAX
    /whois {target_id}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {target_id}: Either client ID, IPID, character name, iniedited-to character name, showname,
    character showname or OOC name

    EXAMPLES
    For user with client ID 1, IPID 1234567890, HDID abb0011, OOC username Phantom, character
    name Phantom_HD, showname The phantom, character showname Menace all of these do the same
    >>> /whois 1
    Returns client info.
    >>> /whois 1234567890
    Returns client info.
    >>> /whois abb0011
    Returns client info.
    >>> /whois Phantom
    Returns client info.
    >>> /whois The Phantom
    Returns client info.
    >>> /whois Phantom_HD
    Returns client info.
    >>> /whois Menace
    Returns client info.
    """

    Constants.assert_command(client, arg, is_staff=True)
    if not arg:
        targets = [client]
        arg = client.id
    else:
        targets = []

    # If needed, pretend the identifier is a client ID
    if not targets and arg.isdigit():
        targets = client.server.client_manager.get_targets(
            client, TargetType.ID, int(arg), False)

    # If still needed, pretend the identifier is a client IPID (only CM and mod)
    if not targets and arg.isdigit() and client.is_officer():
        targets = client.server.client_manager.get_targets(
            client, TargetType.IPID, int(arg), False)

    # If still needed, pretend the identifier is a client IPID (only CM and mod)
    if not targets and client.is_officer():
        targets = client.server.client_manager.get_targets(
            client, TargetType.HDID, arg, False)

    # If still needed, pretend the identifier is a character name
    if not targets:
        targets = client.server.client_manager.get_targets(
            client, TargetType.CHAR_NAME, arg, True)

    # If still needed, pretend the identifier is an edited-to name
    if not targets:
        targets = client.server.client_manager.get_targets(client, TargetType.CHAR_FOLDER, arg,
                                                           True)

    # If still needed, pretend the identifier is a showname
    if not targets:
        targets = client.server.client_manager.get_targets(
            client, TargetType.SHOWNAME, arg, True)

    # If still needed, pretend the identifier is a character showname
    if not targets:
        targets = client.server.client_manager.get_targets(client, TargetType.CHAR_SHOWNAME, arg,
                                                           True)

    # If still needed, pretend the identifier is an OOC username
    if not targets:
        targets = client.server.client_manager.get_targets(
            client, TargetType.OOC_NAME, arg, True)

    # If still not found, too bad
    if not targets:
        raise ArgumentError('Target not found.')

    # Otherwise, send information
    info = targets[0].get_info(
        as_mod=client.is_mod, as_cm=client.is_cm, identifier=arg)
    client.send_ooc(info)


def ooc_cmd_zone(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Makes a zone that spans the given area range, or just the given area if just given one area, or
    the current area if not given any.
    Returns an error if you are already watching some other zone, or if any of the areas to be
    made part of the zone to be created already belong to some other zone.

    SYNTAX
    /zone
    /zone <sole_area_in_zone>
    /zone <area_range_start>, <area_range_end>

    PARAMETERS
    <sole_area_in_zone>: Sole area to add to the zone
    <area_range_start>: Start of area range (inclusive)
    <area_range_end>: End of area range (inclusive)

    EXAMPLES
    Assuming you are in area 0...
    >>> /zone
    Creates a zone that has area 0.
    >>> /zone Class Trial Room 1
    Creates a zone that only has area Class Trial Room 1
    >>> /zone 16, 116
    Creates a zone that has areas 16 through 116.
    """

    Constants.assert_command(client, arg, is_staff=True)

    # Obtain area range and create zone based on it
    raw_area_names = arg.split(', ') if arg else []
    lower_area, upper_area = Constants.parse_two_area_names(client, raw_area_names,
                                                            check_valid_range=True)
    areas = client.hub.area_manager.get_areas_in_range(lower_area, upper_area)

    try:
        zone_id = client.hub.zone_manager.new_zone(areas, {client})
    except ZoneError.AreaConflictError:
        raise ZoneError(
            'Some of the areas of your new zone are already part of some other zone.')
    except ZoneError.WatcherConflictError:
        raise ZoneError('You cannot create a zone while watching another.')

    # Prepare client output
    if lower_area == upper_area:
        output = 'just area {}'.format(lower_area.id)
    else:
        output = 'areas {} through {}'.format(lower_area.id, upper_area.id)

    client.send_ooc(
        'You have created zone `{}` containing {}.'.format(zone_id, output))
    client.send_ooc_others('(X) {} [{}] has created zone `{}` containing {} ({}).'
                           .format(client.displayname, client.id, zone_id, output, client.area.id),
                           is_officer=True)

    client.send_ooc_others('(X) Your area has been made part of zone `{}`. To be able to receive '
                           'its notifications, start watching it with /zone_watch {}'
                           .format(zone_id, zone_id), is_staff=True, in_area=areas)
    client.send_ooc_others('Your area has been made part of zone `{}`.'.format(zone_id),
                           is_staff=False, in_area=areas)


def ooc_cmd_zone_add(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Adds an area by name or ID to the zone you are watching.
    Returns an error if the area identifier does not correspond to an area, if the area is part of
    some other zone, or if you are not watching a zone.

    SYNTAX
    /zone_add <area_name>
    /zone_add <area_id>

    PARAMETERS
    <area_name>: Name of the area whose door you want to knock.
    <area_id>: ID of the area whose door you want to knock.

    EXAMPLES
    >>> /zone_add 0
    Add area 0 to the zone
    >>> /zone_add Courtroom, 2
    Add area "Courtroom, 2" to the zone
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')

    if not client.zone_watched:
        raise ZoneError('You are not watching a zone.')
    area = Constants.parse_area_names(client, arg).pop()

    try:
        client.zone_watched.add_area(area)
    except ZoneError.AreaConflictError:
        raise ZoneError('Area {} already belongs to a zone.'.format(arg))

    client.send_ooc('You have added area {} to your zone.'.format(area.id))
    client.send_ooc_others('(X) {} [{}] has added area {} to your zone ({}).'
                           .format(client.displayname, client.id, area.id,
                                   client.area.id), is_zstaff=True)

    zone_id = client.zone_watched.get_id()
    for c in area.clients:
        if c == client:
            continue

        if c.is_staff() and c != client and c.zone_watched != client.zone_watched:
            c.send_ooc('(X) Your area has been made part of zone `{}`. To be able to receive '
                       'its notifications, start watching it with /zone_watch {}'
                       .format(zone_id, zone_id))
        else:
            c.send_ooc(
                'Your area has been made part of zone `{}`.'.format(zone_id))


def ooc_cmd_zone_ambient(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sets up the ambient sound effect of all areas in the zone you are watching. Players in areas
    part of the zone, and players that later join an area of the zone, will be ordered to play the
    area ambient sound effect.
    This command is equivalent to calling /ambient in every area of the zone you are watching.
    GMs may still individually change or clear ambient sound effects for areas of the zone after
    running the command, and such actions will override the "zone ambient".

    SYNTAX
    /zone_ambient <ambient_name>

    PARAMETERS
    <ambient_name>: Name of the ambient sound effect

    EXAMPLES
    >>> /zone_ambient wind.wav
    Sets the ambient sound effect of all areas of the current zone to `wind.wav`.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='>0')

    if not client.zone_watched:
        raise ZoneError('You are not watching a zone.')

    zone = client.zone_watched

    targets = zone.get_players()
    client.send_ooc(
        f'You have set the ambient sound effect of all areas of your zone to `{arg}`.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] have set the ambient sound '
                           f'effect of all areas of your zone to `{arg}` ({client.area.id}).',
                           is_zstaff=True)

    for c in targets:
        c.send_area_ambient(name=arg)
    for a in zone.get_areas():
        a.ambient = arg


def ooc_cmd_zone_ambient_end(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Clears the ambient sound effect of all areas of the zone you are watching. Players in an area
    part of the zone will be ordered to stop playing the former area ambient sound effect, and
    players that later join some area of the zone will not play the former area ambient sound
    effect.
    This command is equivalent to calling /ambient_end in every area of the zone you are watching,
    without displaying error messages if it happened to be the case no ambient sound effect was set
    for some (or all) of the areas of the zone.
    GMs may still individually change or clear ambient sound effects for areas of the zone after
    running the command, and such actions will override the "zone ambient".
    Returns an error if you are not watching a zone.

    SYNTAX
    /zone_ambient

    PARAMETERS
    None

    EXAMPLES
    >>> /zone_ambient_end
    Clears the ambient sound effect of all areas of the zone you are watching.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    if not client.zone_watched:
        raise ZoneError('You are not watching a zone.')

    zone = client.zone_watched

    targets = zone.get_players()
    client.send_ooc(
        'You have removed the area ambient sound effect of all areas of your zone.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] removed the area ambient sound '
                           f'effect of all areas of your zone ({client.area.id}).', is_zstaff=True)

    for c in targets:
        c.send_area_ambient(name='')
    for a in zone.get_areas():
        a.ambient = ''


def ooc_cmd_zone_autoglance(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Changes the zone autoglance automatic setting of the zone you are watching from False to True,
    or True to False, and warns all players in an area part of the zone (as well as zone watchers)
    about the change in OOC. Newly created zones have such setting set to False.
    If set to True, the autoglance setting of all players in an area part of the zone will be turned
    on, and so will the autoglance setting of any player who later joins an area part of the zone.
    If such player already had autoglance on, there is no effect. Players are free to change their
    autoglance setting manually via /autoglance. Players who go on to an area part of the zone will
    not have the zone change their autoglance setting on departure.
    If set to False, the autoglance setting of all players in an area part of the zone will be
    turned off. If such player already had autoglance off, there is no effect.
    Returns an error if you are not watching a zone.

    SYNTAX
    /zone_autoglance

    PARAMETERS
    None

    EXAMPLES
    Assuming you are watching newly created zome z0...
    >>> /zone_autoglance
    Sets the zone autoglance automatic setting of the zone z0 to True.
    >>> /zone_autoglance
    Sets the zone autoglance automatic setting of the zone z0 to False.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    if not client.zone_watched:
        raise ZoneError('You are not watching a zone.')

    zone = client.zone_watched
    status = {False: 'off', True: 'on'}

    try:
        zone_autoglance = zone.get_property('Autoglance')
    except ZoneError.PropertyNotFoundError:
        zone_autoglance = False

    zone_autoglance = not zone_autoglance
    zone.set_property('Autoglance', zone_autoglance)

    status = {True: 'on', False: 'off'}
    client.send_ooc(
        f'You turned {status[zone_autoglance]} autoglance in your zone.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] has turned '
                           f'{status[zone_autoglance]} autoglance in your zone '
                           f'({client.area.id}).', is_zstaff=True)
    client.send_ooc_others(f'Autoglance was automatically turned {status[zone_autoglance]} in your '
                           f'zone.', is_zstaff=False, pred=lambda c: c.area.in_zone == zone)

    for player in zone.get_players():
        player.autoglance = zone_autoglance

    logger.log_server(f'[{client.area.id}][{client.get_char_name()}]Changed autoglance in zone '
                      f'{zone.get_id()} to {zone_autoglance}.', client)


def ooc_cmd_zone_autopass(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Changes the zone autopass automatic setting of the zone you are watching from False to True,
    or True to False, and warns all players in an area part of the zone (as well as zone watchers)
    about the change in OOC. Newly created zones have such setting set to False.
    If set to True, the autopass setting of all players in an area part of the zone will be turned
    on, and so will the autopass setting of any player who later joins an area part of the zone.
    If such player already had autopass on, there is no effect. Players are free to change their
    autopass setting manually via /autopass. Players who go on to an area part of the zone will
    not have the zone change their autopass setting on departure.
    If set to False, the autopass setting of all players in an area part of the zone will be turned
    off. If such player already had autopass off, there is no effect.
    Returns an error if you are not watching a zone.

    SYNTAX
    /zone_autopass

    PARAMETERS
    None

    EXAMPLES
    Assuming you are watching newly created zome z0...
    >>> /zone_autopass
    Sets the zone autopass automatic setting of the zone z0 to True.
    >>> /zone_autopass
    Sets the zone autopass automatic setting of the zone z0 to False.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    if not client.zone_watched:
        raise ZoneError('You are not watching a zone.')

    zone = client.zone_watched
    status = {False: 'off', True: 'on'}

    try:
        zone_autopass = zone.get_property('Autopass')
    except ZoneError.PropertyNotFoundError:
        zone_autopass = False

    zone_autopass = not zone_autopass
    zone.set_property('Autopass', zone_autopass)

    status = {True: 'on', False: 'off'}
    client.send_ooc(
        f'You turned {status[zone_autopass]} autopass in your zone.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] has turned '
                           f'{status[zone_autopass]} autopass in your zone '
                           f'({client.area.id}).', is_zstaff=True)
    client.send_ooc_others(f'Autopass was automatically turned {status[zone_autopass]} in your '
                           f'zone.', is_zstaff=False, pred=lambda c: c.area.in_zone == zone)

    for player in zone.get_players():
        player.autopass = zone_autopass

    logger.log_server(f'[{client.area.id}][{client.get_char_name()}]Changed autopass in zone '
                      f'{zone.get_id()} to {zone_autopass}.', client)


def ooc_cmd_zone_end(client: ClientManager.Client, arg: str):
    """ (VARYING REQUIREMENTS)
    Deletes the zone you are watching, so that it is no longer part of the hub's zone list,
    if no argument is given (GM OR ABOVE ONLY), or deletes the zone by its name (CM OR MOD ONLY).
    Returns an error if you are not watching a zone and do not provide a zone ID.

    SYNTAX
    /zone_end

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {zone_id}: ID of zone.

    EXAMPLES
    Assuming you are watching zone 1000...
    >>> /zone_end
    Deletes the zone 1000.
    >>> /zone_end z0
    Deletes the zone z0.
    """

    try:
        Constants.assert_command(client, arg, is_officer=True)
    except ClientError.UnauthorizedError:
        # Case GM, who can only delete a zone they are watching
        try:
            Constants.assert_command(
                client, arg, is_staff=True, parameters='=0')
        except ArgumentError:
            raise ClientError.UnauthorizedError('You must be authorized to use a zone name with '
                                                'this command.')

    if arg:
        try:
            target_zone = client.hub.zone_manager.get_zone(arg)
        except KeyError:
            raise ZoneError('`{}` is not a valid zone ID.'.format(arg))
    else:
        if not client.zone_watched:
            raise ZoneError('You are not watching a zone.')
        target_zone = client.zone_watched

    # Keep backup reference to send to others
    backup_watchers = target_zone.get_watchers()
    backup_id = target_zone.get_id()

    target_zone.manager.delete_zone(backup_id)

    if arg:
        client.send_ooc('You have ended zone `{}`.'.format(backup_id))
    else:
        client.send_ooc('You have ended your zone.')
    client.send_ooc_others('(X) {} [{}] has ended your zone.'
                           .format(client.displayname, client.id), part_of=backup_watchers)
    client.send_ooc_others('(X) {} [{}] has ended zone `{}`.'
                           .format(client.displayname, client.id, backup_id),
                           is_officer=True, not_to=backup_watchers)


def ooc_cmd_zone_global(client: ClientManager.Client, arg: str):
    """
    Sends a global message in the OOC chat visible to all users in the zone your area belongs
    to who have not disabled global chat. The message includes your are and display name.
    Moderators and community managers also get to see the IPID of the sender.
    Returns an error if you have global chat off, send an empty message, or are in an area
    not part of a zone.

    SYNTAX
    /zone_global <message>

    PARAMETERS
    <message>: Message to be sent

    EXAMPLE
    >>> /zone_global Hello World
    Sends Hello World to global chat.
    """

    try:
        Constants.assert_command(client, arg, parameters='>0')
    except ArgumentError:
        raise ArgumentError('You cannot send an empty message.')

    if client.zone_watched:
        target_zone = client.zone_watched
    elif client.area.in_zone:
        target_zone = client.area.in_zone
    else:
        raise ZoneError('You are not in a zone.')

    if not client.is_officer() and not client.server.global_allowed:
        raise ClientError('Global chat is currently locked.')
    if not client.is_officer() and not client.area.global_allowed:
        raise ClientError(
            'You must be authorized to send global messages in this area.')
    if client.muted_global:
        raise ClientError('You have the global chat muted.')

    targets = target_zone.get_watchers()
    for area in target_zone.get_areas():
        targets.update(
            {c for c in area.clients if c.zone_watched in [None, target_zone]})

    for target in targets:
        if target.muted_global:
            continue

        if target.is_mod or target.is_cm:
            target.send_ooc(arg, username=(f'<dollar>ZG[{client.area.id}][{client.displayname}]'
                                           f'[{client.ipid}]'))
        elif target.is_gm:
            target.send_ooc(
                arg, username=f'<dollar>ZG[{client.area.id}][{client.displayname}]')
        else:
            target.send_ooc(arg, username=f'<dollar>ZG[{client.displayname}]')


def ooc_cmd_zone_handicap(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sets a movement handicap on the zone you are watching so that they need to wait a set amount of
    time between changing areas. This will override any previous handicaps the client(s) may have
    had, including custom ones and server ones (such as through sneak). Server handicaps will
    override custom handicaps if the server handicap is longer. However, as soon as the server
    handicap is over, it will recover the old custom handicap.
    Players in an area part of the zone you are watching when the command is run, or who later join
    an area part of the zone will be made subject to the movement handicap. Players subject to this
    handicap that then leave to an area not part of the zone will be made no longer subject to the
    movement handicap.
    Requires /zone_unhandicap to undo.
    Returns an error if you are not watching a zone, or if given a non-positive length of time.

    SYNTAX
    /zone_handicap <length> {name} {announce_if_over}

    PARAMETERS
    <client_ipid>: IPID for the client (number in parentheses in /getarea)
    <length>: Handicap length (in seconds)

    OPTIONAL PARAMETERS
    {name}: Name of the handicap (e.g. "Injured", "Sleepy", etc.). By default it is "ZoneHandicap".
    {announce_if_over}: If the server will send a notification once the target may move areas after
    waiting for their handicap timer. By default it is true. For the server not to send them, put
    one of these keywords: False, false, 0, No, no

    EXAMPLES
    >>> /zone_handicap 5
    Sets a 5 second movement handicap for your current zone.
    >>> /zone_handicap 10 Injured
    Sets a 10 second movement handicap called "Injured" for your current zone.
    >>> /zone_handicap 15 StabWound False
    Sets a 15 second movement handicap called "StabWound" for your current zone which will not
    send notifications once the timer expires.
    """

    Constants.assert_command(client, arg, is_staff=True,
                             parameters='&1-3', split_spaces=True)

    if not client.zone_watched:
        raise ZoneError('You are not watching a zone.')

    zone = client.zone_watched
    # Obtain targets
    targets = zone.get_players()

    args = arg.split(' ')

    # Check if valid length and convert to seconds
    length = Constants.parse_time_length(args[0])  # Also internally validates

    # Check name
    if len(args) >= 2:
        name = args[1]
    else:
        name = "ZoneHandicap"  # No spaces!

    # Check announce_if_over status
    if len(args) >= 3 and args[2] in ['False', 'false', '0', 'No', 'no']:
        announce_if_over = False
    else:
        announce_if_over = True

    client.send_ooc('You imposed a movement handicap "{}" of length {} seconds in your zone.'
                    .format(name, length))
    client.send_ooc_others('(X) {} [{}] imposed a movement handicap "{}" of length {} seconds '
                           'in your zone. ({}).'
                           .format(client.displayname, client.id, name, length, client.area.id),
                           is_zstaff=True)

    zone.set_property('Handicap', (length, name, announce_if_over))

    for c in targets:
        c.change_handicap(True, length=length, name=name,
                          announce_if_over=announce_if_over)


def ooc_cmd_zone_handicap_affect(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY+VARYING REQUIREMENTS)
    Makes a user by client ID be subject to the movement handicap imposed in the zone you are
    watching. This command is ideal to restore zone handicaps if handicaps were removed.
    Returns an error if you are not watching a zone, if the zone you are watching does not have a
    movement handicap set up, if the given identifier does not correspond to a client, or if the
    client is not in an area part of the zone.

    SYNTAX
    /zone_handicap_add <client_id>

    PARAMETERS
    <client_id>: Client identifier (number in brackets in /getarea)

    EXAMPLES
    >>> /zone_handicap_affect 0
    Readds the zone's movement handicaps to the user with client ID 0.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')

    if not client.zone_watched:
        raise ZoneError('You are not watching a zone.')

    zone = client.zone_watched
    if not zone.is_property('Handicap'):
        raise ZoneError('Your zone currently does not have a handicap set up.')

    current_zlength, current_zname, current_zannounce_if_over = zone.get_property(
        'Handicap')

    target = Constants.parse_id(client, arg)
    if not zone.is_area(target.area):
        raise ZoneError('Target client is not in an area part of your zone.')

    client.send_ooc('You made the movement handicap "{}" of length {} seconds in your zone apply '
                    'to {} [{}].'
                    .format(current_zname, current_zlength, target.displayname, target.id))
    client.send_ooc_others('(X) {} [{}] made the movement handicap "{}" of length {} seconds '
                           'in your zone apply to {} [{}]. ({}).'
                           .format(client.displayname, client.id, current_zname, current_zlength,
                                   client.area.id, target.displayname, target.id),
                           is_zstaff=True, not_to={target})

    target.change_handicap(True, length=current_zlength, name=current_zname,
                           announce_if_over=current_zannounce_if_over)


def ooc_cmd_zone_iclock(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Toggles IC messages by non-staff or players without IC lock bypass in the current zone being
    allowed/disallowed. If for a particular area it is the case the IC lock status already matches
    the zone's new IC lock status, no action is taken in that area. Otherwise, the area's IC lock
    status will now be the zone's new IC lock status and, if now disallowed, any user with an
    active IC lock bypass will lose it.
    Returns an error if you are not watching a zone, or if you are a GM and an area part of the zone
    you are watching is such that locking IC in there is forbidden.

    SYNTAX
    /zone_iclock

    PARAMETERS
    None

    EXAMPLES
    Assuming some (if not all) areas in the zone have IC chat not locked...
    >>> /zone_iclock
    Locks IC chat in all areas
    >>> /zone_iclock
    Unlocks IC chat in all areas
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    if not client.zone_watched:
        raise ZoneError('You are not watching a zone.')

    zone = client.zone_watched
    if not client.is_officer() and client.is_gm:
        for area in zone.get_areas():
            if not area.gm_iclock_allowed:
                raise ClientError(f'GMs are not authorized to change IC locks in area '
                                  f'{area.name} part of your zone.')

    try:
        zone_ic_lock = zone.get_property('Ic_lock')
    except ZoneError.PropertyNotFoundError:
        zone_ic_lock = False

    zone_ic_lock = not zone_ic_lock
    zone.set_property('Ic_lock', zone_ic_lock)

    status = {True: 'locked', False: 'unlocked'}
    client.send_ooc(
        'You {} the IC chat in your zone.'.format(status[zone_ic_lock]))
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] has '
                           f'{status[zone_ic_lock]} the IC chat in your zone '
                           f'({client.area.id}).', is_zstaff_flex=True)

    for area in zone.get_areas():
        area.ic_lock = zone_ic_lock

        client.send_ooc_others(f'The IC chat has been {status[area.ic_lock]} in this area.'
                               .format(), is_zstaff_flex=False, in_area=area)

        logger.log_server('[{}][{}]Changed IC lock in zone to {}'
                          .format(area.id, client.get_char_name(), area.ic_lock), client)

        if not area.ic_lock:
            # Remove ic lock bypasses
            affected_players = list()
            for player in area.clients:
                if player.can_bypass_iclock and not player.is_staff():
                    affected_players.append(player)

            if affected_players:
                for player in affected_players:
                    player.send_ooc('You have lost your IC lock bypass as the IC chat in '
                                    'your area has been unlocked.')
                    player.send_ooc_others(f'(X) {player.displayname} [{player.id}] has lost their '
                                           f'IC lock bypass as the IC chat in their area has '
                                           f'been unlocked ({area.id}).', is_zstaff_flex=area)
                    player.can_bypass_iclock = False


def ooc_cmd_zone_info(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Returns information about the zone you are watching. The information returned is:
    * Name of the zone.
    * Areas of the zone.
    * Watchers of the zone.
    * Number of players in areas part of the zone.
    Returns an error if you are not watching a zone.

    SYNTAX
    /zone_info

    PARAMETERS
    None

    EXAMPLES
    >>> /zone_info
    May return something like this:
    | $H: == Zone z0 ==
    | Zone z0. Contains areas: 4-7. Is watched by: [0] Phantom (4) and [1] Spam (5).
    | $H: == Zone Area List ==
    | == Area 4: Test 1 ==
    | [0] Phantom_HD (123456789)
    | == Area 5: Test 2 ==
    | [1] Spam_HD (987654321)
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    if not client.zone_watched:
        raise ZoneError('You are not watching a zone.')

    zone = client.zone_watched
    info = f'== Zone {zone.get_id()} ==\r\n{zone.get_info()}'
    client.send_ooc(info)
    client.send_area_info(client.area, -2, False, include_shownames=True)


def ooc_cmd_zone_lights(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Toggles lights on or off in the background for every area in a zone. If turned off,
    the background will change to the server's blackout background. If turned on,
    the background will revert to the background before the blackout one.
    If an area already has the requested light status, has a locked background, or
    has no lights to change, the area is left alone.
    Returns an error if you are not watching a zone.

    SYNTAX
    /zone_lights

    PARAMETERS
    <new_status>: 'on' or 'off'

    EXAMPLES
    Assuming you are watching z0, with areas 1-4
    >>> /zone_lights off
    Turns every light off in areas 1-4.
    """

    try:
        Constants.assert_command(client, arg, is_staff=True, parameters='>0')
    except ArgumentError:
        raise ArgumentError('You must specify either on or off.')
    if arg not in ['off', 'on']:
        raise ClientError('Expected on or off.')

    if client.zone_watched:
        target_zone = client.zone_watched.get_areas()
        new_lights = (arg == 'on')
    else:
        raise ZoneError('You are not watching a zone.')

    for area in target_zone:
        if area.bg_lock or not area.has_lights:
            continue
        try:
            area.change_lights(new_lights, initiator=client, area=area)
        except AreaError:
            pass

    client.send_ooc('You have turned {} the lights in your zone.'.format(arg))
    client.send_ooc_others('(X) {} [{}] has turned {} the lights in your zone ({}).'
                           .format(client.displayname, client.id, arg, client.area.id),
                           is_zstaff=True)


def ooc_cmd_zone_list(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Lists all active zones in the hub. For each zone, it lists details such as: zone ID,
    the number of players it has, the areas it contains, and who is watching it.
    Returns an error if there are no active zones.

    SYNTAX
    /zone_list

    PARAMETERS
    None

    EXAMPLES
    >>> /zone_list
    May return something like this:
    | $H: == Active zones ==
    | *Zone 1000 [15] (2, 16-116). Watchers: Phantom (16)
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    info = client.hub.zone_manager.get_info()
    client.send_ooc(info)


def ooc_cmd_zone_mode(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sets the mode of a zone you are watching if given an argument, or clears it otherwise.
    Players part of an area in the zone are ordered to switch to this gamemode. Players later
    entering an area part of the zone from an area outside of it will be ordered to switch
    to this gamemode.
    Returns an error if you are not watching a zone.

    SYNTAX
    /zone_mode {gamemode}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {gamemode}: New gamemode

    EXAMPLES
    Assuming you are watching zone z0
    >>> /zone_mode daily
    Sets the zone mode to daily.
    >>> /zone_mode
    Clears the zone mode.
    """

    Constants.assert_command(client, arg, is_staff=True)

    if not client.zone_watched:
        raise ZoneError('You are not watching a zone.')

    client.zone_watched.set_mode(arg)

    if arg:
        client.send_ooc('You have set the gamemode of your zone to be `{}`.'
                        .format(arg))
        client.send_ooc_others('(X) {} [{}] has set the gamemode of your zone to be `{}` ({}).'
                               .format(client.displayname, client.id, arg, client.area.id),
                               is_zstaff=True)
    else:
        client.send_ooc('You have cleared the gamemode of your zone.')
        client.send_ooc_others('(X) {} [{}] has cleared the gamemode of your zone to be ({}).'
                               .format(client.displayname, client.id, client.area.id),
                               is_zstaff=True)


def ooc_cmd_zone_paranoia(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Changes the zone paranoia level of the zone you are watching, which affects the probability a
    user receives a phantom peek message every phantom peek cycle. The zone paranoia level
    is a percentage from -100 to 100, by default 0 (including if not set).
    A phantom peek message is a message that looks like one received from being an area that was
    just peeked into.
    A phantom peek cycle is a cycle of a length randomly chosen between 150 to 450 seconds, after
    which the server, with probability "player paranoia + zone paranoia", starts a timer of length
    a random number less than 150 seconds, after which it sends the user a phantom peek message
    if they are not blind and not staff, in an area that is not a lobby or private area, and they
    have a participant character selected. A new phantom peek cycle is restarted regardless of
    success after the old one expires.
    Returns an error if you are not watching a zone, or if the new zone paranoia level is not a
    number from -100 to 100.

    SYNTAX
    /zone_paranoia <zone_paranoia_level>

    PARAMETERS
    <zone_paranoia_level>: New intended zone paranoia level

    EXAMPLES
    Assuming you are watching zome z0...
    >>> /zone_paranoia_level 5
    Sets the zone paranoia level of zone z0 to 5%.
    >>> /zone_paranoia_level -10
    Sets the zone paranoia level of zone z0 to -10%.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')

    if not client.zone_watched:
        raise ZoneError('You are not watching a zone.')

    zone = client.zone_watched

    try:
        paranoia = float(arg)
    except ValueError:
        raise ClientError('New zone paranoia level must be a number.')
    if not (-100 <= paranoia <= 100):
        raise ClientError(
            'New zone paranoia level must be a number from -100 to 100.')

    zone.set_property('Paranoia', (paranoia,))
    client.send_ooc(f'You set the zone paranoia level of your zone to '
                    f'{paranoia}.')
    client.send_ooc_others(f'(X) {client.displayname} [{client.id}] set the zone paranoia level of '
                           f'your zone to {paranoia} ({client.area.id}).',
                           is_zstaff=True)


def ooc_cmd_zone_paranoia_info(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Gets the zone paranoia level of the zone you are watching.
    Returns an error if you are not watching a zone.

    SYNTAX
    /zone_paranoia_info

    PARAMETERS
    None

    EXAMPLES
    Assuming you are watching zone z0...
    >>> /zone_paranoia_info
    Gets the zone paranoia level of zone z0.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    if not client.zone_watched:
        raise ZoneError('You are not watching a zone.')

    zone = client.zone_watched

    try:
        paranoia, = zone.get_property('Paranoia')
    except ZoneError.PropertyNotFoundError:
        raise ClientError('Your zone has not set a zone paranoia level.')
    else:
        client.send_ooc(f'The paranoia level of your zone is {paranoia}.')


def ooc_cmd_zone_play(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Plays a given track in all areas of the zone, even if not explicitly in the music list.
    It is the way to play custom music in all areas of a zone simultaneously.
    Returns an error if you are not watching a zone.

    SYNTAX
    /zone_play <track_name>
    /zone_play <track_name> <fade_type>

    PARAMETERS
    <track_name>: Track to play
    <fade_type>: The fade behavior for the new song. May be: in, out, mix

    EXAMPLES
    Assuming you are watching zone z0...
    >>> /zone_play Trial(AJ).opus
    Plays Trial(AJ).opus for all areas in zone z0.
    >>> /zone_play CustomTrack.opus
    Plays CustomTrack.opus, which will only be audible to users with CustomTrack.opus) for all areas
    in zone z0.
    >>> /play CustomTrack.opus in
    Plays CustomTrack.opus in all areas in zone z0, the song will be faded in as it begins playing.
    >>> /play CustomTrack.opus out
    Plays CustomTrack.opus in all areas in zone z0, the previous song will fade out before the new one begins playing.
    >>> /play CustomTrack.opus mix
    Plays CustomTrack.opus in all areas in zone z0, fade will combine both in and out behavior.
    """

    try:
        Constants.assert_command(client, arg, is_staff=True, parameters='>0')
    except ArgumentError:
        raise ArgumentError('You must specify a song.')

    if not client.zone_watched:
        raise ZoneError('You are not watching a zone.')

    track_name = arg
    fade_option = FadeOption.NO_FADE

    try:
        arg_list = arg.split()
        fade_option = FadeOption[arg_list.pop().upper()]
        track_name = ' '.join(arg_list)
    except Exception:
        pass

    for zone_area in client.zone_watched.get_areas():
        zone_area.play_track(
            track_name, client, raise_if_not_found=False, reveal_sneaked=False, fade_option=fade_option)

    client.send_ooc('You have played track `{}` in your zone.'
                    .format(track_name))
    client.send_ooc_others('(X) {} [{}] has played track `{}` in your zone ({}).'
                           .format(client.displayname, client.id, track_name, client.area.id),
                           is_zstaff=True)

    # Warn if track is not in the music list
    try:
        client.music_manager.get_music_data(track_name)
    except MusicError.MusicNotFoundError:
        client.send_ooc(f'(X) Warning: `{track_name}` is not a recognized track name, so the server will '
                        f'not loop it.')


def ooc_cmd_zone_set_legacy_jukebox(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sets legacy jukebox behavior in the zone. When enabled,
    the current song do not automatically play whenever
    a client joins the area.
    """

    try:
        Constants.assert_command(client, arg, is_staff=True, parameters='>0')
    except ArgumentError:
        raise ArgumentError('You must specify a state.')

    if not client.zone_watched:
        raise ZoneError('You are not watching a zone.')

    state = arg.lower() in ["true", "1"]
    for zone_area in client.zone_watched.get_areas():
        zone_area.legacy_jukebox = state

    state_string = ("disabled", "enabled")[state]
    client.send_ooc(f'You have {state} legacy jukebox behavior in your zone.')
    client.send_ooc_others('(X) {} [{}] has {} legacy jukebox behavior track in your zone ({}).'
                           .format(client.displayname, client.id, state, client.area.id),
                           is_zstaff=True)


def ooc_cmd_zone_remove(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Removes an area by name or ID from the zone you are watching.
    Returns an error if the area identifier does not correspond to an area, if the area is not part
    of the zone you are watching, or if you are not watching a zone.

    SYNTAX
    /zone_remove <area_name>
    /zone_remove <area_id>

    PARAMETERS
    <area_name>: Name of the area whose door you want to knock.
    <area_id>: ID of the area whose door you want to knock.

    EXAMPLES
    >>> /zone_remove 0
    Remove area 0 from the zone.
    >>> /zone_remove Courtroom, 2
    Remove area "Courtroom, 2" from the zone.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')

    if not client.zone_watched:
        raise ZoneError('You are not watching a zone.')
    area = Constants.parse_area_names(client, arg).pop()

    target_zone = client.zone_watched
    # In case zone gets automatically deleted
    backup_watchers = client.zone_watched.get_watchers()
    try:
        target_zone.remove_area(area)
    except ZoneError.AreaNotInZoneError:
        raise ZoneError('Area {} is not part of your zone.'.format(arg))

    # Announce area removal, taking care of using the backup watchers in case the zone got
    # automatically deleted
    client.send_ooc('You have removed area {} from your zone.'.format(area.id))
    client.send_ooc_others('(X) {} [{}] has removed area {} from your zone.'
                           .format(client.displayname, client.id, area.id), part_of=backup_watchers)

    # Announce automatic deletion if needed.
    zone_id = target_zone.get_id()
    if not target_zone.get_areas():
        for c in backup_watchers:
            c.send_ooc(
                '(X) As your zone no longer covers any areas, it has been deleted.')
        client.send_ooc_others('(X) Zone `{}` was automatically ended as it no longer covered '
                               'any areas.'.format(zone_id), is_officer=True,
                               not_to=backup_watchers)
    # Otherwise, suggest zone watchers who were in the removed area to stop watching the zone
    else:
        for c in area.clients:
            if c == client:
                continue
            if c.is_staff() and c in backup_watchers:
                c.send_ooc('(X) Your area has been removed from your zone. To stop receiving its '
                           'notifications, stop watching it with /zone_unwatch')
            else:
                c.send_ooc('Your area has been removed from your zone.')


def ooc_cmd_zone_tick(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sets the chat tick rate of the zone in milliseconds. All players in an area part of the zone
    will use the imposed chat tick rate to render IC messages.
    Requires /zone_tick_remove to undo.
    Returns an error if you are not watching a zone, or if given a length of time that is either not
    an integer or not a number between 0 and 1000 exclusive.

    SYNTAX
    /zone_tick <length>

    PARAMETERS
    <length>: Chat tick rate (in milliseconds).

    EXAMPLES
    >>> /zone_tick 20
    Sets the zone chat tick rate to 20 ms.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')

    if not client.zone_watched:
        raise ZoneError('You are not watching a zone.')

    zone = client.zone_watched

    try:
        chat_tick_rate = int(arg)
    except ValueError:
        raise ClientError(f'Invalid chat tick rate {arg}')

    if chat_tick_rate <= 0 or chat_tick_rate >= 1000:
        raise ClientError(
            f'The chat tick rate must be a number between 0 and 1000 exclusive.')

    targets = zone.get_players()
    client.send_ooc(
        'You have set the zone chat tick rate to {} ms.'.format(chat_tick_rate))
    client.send_ooc_others('(X) {} [{}] have set the chat tick rate of your zone to {} ms. ({}).'
                           .format(client.displayname, client.id, chat_tick_rate, client.area.id),
                           is_zstaff=True)

    zone.set_property('Chat_tick_rate', chat_tick_rate)

    for c in targets:
        c.send_chat_tick_rate(chat_tick_rate=chat_tick_rate)


def ooc_cmd_zone_tick_remove(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Removes the zone chat tick rate. All players in an area part of a zone will now use their own
    chat tick rate set by their clients to render IC messages.
    Returns an error if you are not watching a zone, or if the zone already does not have a zone
    chat tick rate.

    SYNTAX
    /zone_tick_remove

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    None

    EXAMPLES
    >>> /zone_tick_remove
    Removes the zone chat tick rate.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    if not client.zone_watched:
        raise ZoneError('You are not watching a zone.')

    zone = client.zone_watched

    if not zone.is_property('Chat_tick_rate'):
        raise ClientError('Your zone already has no chat tick rate defined.')

    zone.remove_property('Chat_tick_rate')

    targets = zone.get_players()
    client.send_ooc('You have removed the chat tick rate of your zone.')
    client.send_ooc_others('(X) {} [{}] removed the chat tick rate of your zone. ({}).'
                           .format(client.displayname, client.id, client.area.id),
                           is_zstaff=True)

    for c in targets:
        c.send_chat_tick_rate(chat_tick_rate=None)


def ooc_cmd_zone_unhandicap(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Removes movement handicaps in the zone you are watching so that players in an area part of the
    zone no longer need to wait a set amount of time between changing areas. This will also remove
    server handicaps, if any (such as automatic sneak handicaps).
    Requires /zone_handicap to undo.
    Search by IPID can only be performed by CMs and mods.
    Returns an error if you are not watching a zone, or if the zone does not have a movement
    handicap set up.

    SYNTAX
    /zone_unhandicap

    PARAMETERS
    None

    EXAMPLES
    >>> /zone_unhandicap
    Removes the current zone's zone handicap and all handicaps players in an
                         area part of the zone may have had.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')

    if not client.zone_watched:
        raise ZoneError('You are not watching a zone.')

    zone = client.zone_watched
    if not zone.is_property('Handicap'):
        raise ZoneError('Your zone currently does not have a handicap set up.')

    zone.remove_property('Handicap')
    targets = zone.get_players()

    client.send_ooc('You removed the movement handicap in your zone.')
    client.send_ooc_others('(X) {} [{}] removed the movement handicap in your zone ({}).'
                           .format(client.displayname, client.id, client.area.id),
                           is_zstaff=True)

    for c in targets:
        try:
            c.change_handicap(False)
        except ClientError:
            continue


def ooc_cmd_zone_unwatch(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Makes you no longer watch the zone you are watching.
    Returns an error if you are not watching a zone.

    SYNTAX
    /zone_unwatch

    PARAMETERS
    None

    EXAMPLES
    >>> /zone_unwatch
    Makes you no longer watch your zone.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=0')
    if not client.zone_watched:
        raise ClientError('You are not watching any zone.')

    target_zone = client.zone_watched
    target_zone.remove_watcher(client)

    client.send_ooc(
        'You are no longer watching zone `{}`.'.format(target_zone.get_id()))
    if target_zone.get_watchers():
        client.send_ooc_others('(X) {} [{}] is no longer watching your zone.'
                               .format(client.displayname, client.id),
                               part_of=target_zone.get_watchers())
    elif target_zone.get_players():
        client.send_ooc('(X) Warning: The zone no longer has any watchers.')
    else:
        client.send_ooc('(X) As you were the last person in an area part of it or who was watching '
                        'it, your zone has been deleted.')
        client.send_ooc_others('Zone `{}` was automatically ended as no one was in an '
                               'area part of it or was watching it anymore.'
                               .format(target_zone.get_id()), is_officer=True, in_hub=None)


def ooc_cmd_zone_watch(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Makes you start watching a zone by zone ID.
    Returns an error if the zone ID does not exist or if you are already watching the target
    zone or some other zone.

    SYNTAX
    /zone_watch <zone_ID>

    PARAMETERS
    <zone_ID>: Identifier of zone to watch

    EXAMPLES
    >>> /zone_watch 1000
    Makes you watch zone 1000.
    """

    Constants.assert_command(client, arg, is_staff=True, parameters='=1')

    try:
        target_zone = client.hub.zone_manager.get_zone(arg)
    except KeyError:
        raise ZoneError('`{}` is not a valid zone ID.'.format(arg))

    if target_zone.is_watcher(client):
        raise ZoneError('You are already watching this zone.')

    try:
        target_zone.add_watcher(client)
    except ZoneError.WatcherConflictError:
        raise ZoneError('You cannot watch a zone while watching another.')

    client.send_ooc(
        'You are now watching zone `{}`.'.format(target_zone.get_id()))
    for c in target_zone.get_watchers():
        if c == client:
            continue
    client.send_ooc_others('(X) {} [{}] is now watching your zone ({}).'
                           .format(client.displayname, client.id, client.area.id), is_zstaff=True)


def ooc_cmd_8ball(client: ClientManager.Client, arg: str):
    """
    Calls upon the wisdom of a magic 8 ball. The result is sent to all clients in your area.
    If given a question, it is included as part of the result.

    SYNTAX
    /8ball {question}

    PARAMETERS
    None

    OPTIONAL PARAMETERS
    {question}: Question to ask the magic 8 ball.

    EXAMPLES
    Assuming Phantom is using the magic 8 ball...
    >>> /8ball
    May return something like
    | $H: In response to Phantom, the magic 8 ball says `It is certain`.
    >>> /8ball Am I bae?
    May return something like
    | $H: In response to Phantom's question `Am I bae?`, the magic 8 ball says `My sources say no`.
    """

    responses = ['It is certain',
                 'It is decidedly so',
                 'Without a doubt',
                 'Yes - definitely',
                 'You may rely on it',
                 'As I see it, yes',
                 'Most likely',
                 'Outlook good',
                 'Yes',
                 'Signs point to yes',
                 'Reply hazy, try again',
                 'Ask again later',
                 'Better not tell you now',
                 'Cannot predict now',
                 'Concentrate and ask again',
                 "Don't count on it",
                 'My reply is no',
                 'My sources say no',
                 'Outlook not so good',
                 'Very doubtful',
                 'No',
                 'As I see it, no',
                 'Unlikely',
                 'Absolutely not',
                 'Certainly not']
    response = random.choice(responses)

    if arg:
        output = ("In response to {}'s question `{}`, the magic 8 ball says `{}`."
                  .format(client.displayname, arg, response))
    else:
        output = ("In response to {}, the magic 8 ball says `{}`."
                  .format(client.displayname, response))
    client.area.broadcast_ooc(output)

    logger.log_server('[{}][{}]called upon the magic 8 ball and it said {}.'
                      .format(client.area.id, client.get_char_name(), response), client)


def ooc_cmd_narrate(client: ClientManager.Client, arg: str):
    """ (STAFF ONLY)
    Sends a message from the "Narrator" position to all players in the area. This will override
    any existing IC message, or any hearing properties of the targets.

    SYNTAX
    /narrate <message>

    PARAMETERS
    <message>: Message to send

    EXAMPLES
    >>> /narrate Hello World!
    Sends `Hello World!` to the people in the area as a narrator.
    """

    arg = arg[:256]  # Cap
    Constants.assert_command(client, arg, is_staff=True)

    for c in client.area.clients:
        c.send_ic(msg=arg, hide_character=1, bypass_text_replace=True)


def ooc_cmd_mod_narrate(client: ClientManager.Client, arg: str):
    """ (OFFICER ONLY)
    Sends a message from the "Narrator" position to all players in the area using the mod color.
    This will override any existing IC message, or any hearing properties of the targets.

    SYNTAX
    /mod_narrate <message>

    PARAMETERS
    <message>: Message to send

    EXAMPLES
    >>> /mod_narrate Hello World!
    Sends `Hello World!` to the people in the area as a narrator with mod color.
    """

    arg = arg[:256]  # Cap
    Constants.assert_command(client, arg, is_officer=True)

    for c in client.area.clients:
        c.send_ic(msg=arg, color=5, hide_character=1, bypass_text_replace=True)


def ooc_cmd_exec(client: Union[ClientManager.Client, None], arg: str):
    """
    VERY DANGEROUS. SHOULD ONLY BE ENABLED FOR DEBUGGING.

    DID I MENTION THIS IS VERY DANGEROUS?

    DO NOT ENABLE THIS FUNCTION UNLESS YOU KNOW WHAT YOU ARE DOING.

    I MEAN IT.

    PEOPLE WILL BREAK YOUR SERVER AND POSSIBLY THE HOST MACHINE IT IS ON IF YOU KEEP IT ON.

    DO NOT BE STUPID.

    Executes a Python expression and returns the evaluated expression.
    If passed in a Python statement, it will execute code in the global environment.
    Returns an error if the expression would raise an error in a normal Python environment.

    SYNTAX
    /exec <command>

    PARAMETERS
    <command>

    EXAMPLES
    /exec 1+1
    Returns 2
    /exec while True: client.send_ooc("Hi")
    Commit sudoku
    """

    # IF YOU WANT TO DISABLE /exec: SET debug TO 0 (debug = 0)
    # IF YOU WANT TO ENABLE /exec: SET debug TO 1 (debug = 1)

    debug = 0
    if not debug:
        return None

    if not client:
        # client is None for server.check_exec_active()
        return debug

    # Code after this point assumes debug mode is on!!!
    logger.log_print("Attempting to run instruction {}".format(arg))

    try:
        client.send_ooc(arg, username='>>>')
        result = eval(arg)
        if result is not None:
            client.send_ooc(str(result), username='')
    except Exception:
        try:
            # Temporarily add "client" as a global variable, to allow using
            # expressions such as client.send_ooc("Hi")
            globals()['client'] = client
            exec(arg, globals())
            # client.send_ooc("Executed {}".format(arg))
        except Exception as e:
            try:
                client.send_ooc('Python error: {}: {}'.format(
                    type(e).__name__, e), username='')
            except Exception:
                pass
    globals().pop('client', None)  # Don't really want "client" to be a global variable
    return 1  # Indication that /exec is live


def ooc_cmd_hide_icon(client: ClientManager.Client, arg: str):
    """
    Toggles if your character icon will show up in the player list.

    SYNTAX
    /hide_icon
    """
    message = "You must be authorized to do that."
    if (client.is_gm or client.is_mod or client.is_cm):
        client.icon_visible = not client.icon_visible
        client.area.broadcast_player_list()
        status = {False: 'disabled', True: 'enabled'}
        message = f'You have {status[client.icon_visible]} your character icon.'
    client.send_ooc(message)
