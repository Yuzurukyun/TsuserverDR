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
This module holds all the commands that are either deprecated or are meant to
act as aliases for existing commands in commands.py
"""


def get_command_alias(command):
    """
    Wrapper function for calling commands.
    """
    if command not in command_aliases:
        return ''
    return command_aliases[command]


def get_command_deprecated(command):
    """
    Wrapper function for commands that are deprecated and pending removal.
    """
    if command not in command_deprecated:
        return ''
    return command_deprecated[command]


command_aliases = {
    'slit': 'bloodtrail',
    'pw': 'party_whisper',
    'huddle': 'party_whisper',
    'loginrp': 'logingm',
    'sa': 'getarea',
    'sas': 'getareas',
    'shout': 'scream',
    'unsneak': 'reveal',
    'yell': 'scream',
    'zi': 'zone_info',
    'zg': 'zone_global',
    'showname_list': 'getareas',
    'fa': 'files_area',
    'l': 'look',
    'forcepos': 'pos_force',
    'showname_area': 'getarea',
    'showname_areas': 'getareas',
    'ga': 'getarea',
    'gas': 'getareas',
    'area_kick': 'summon',
}

command_deprecated = dict()
