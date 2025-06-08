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

from __future__ import annotations

import asyncio
import functools
import errno
import hashlib
import hmac
import os
import pathlib
import random
import re
import secrets
import sys
import tempfile
import time
import typing
import warnings
import yaml

from enum import Enum, IntEnum
from io import TextIOWrapper
from typing import Awaitable, Any, Callable, Iterable, List, Set, Tuple, Union

from server.exceptions import ClientError, ServerError, ArgumentError, AreaError
from server.exceptions import TsuserverException

if typing.TYPE_CHECKING:
    from asyncio.proactor_events import _ProactorSocketTransport

    # Avoid circular referencing
    from server.area_manager import AreaManager
    from server.client_manager import ClientManager
    from server.hub_manager import _Hub
    from server.tsuserver import TsuserverDR

"""
MusicFade lets the client know how to behave when it receives a new song to play.
NO_FADE: The old song ends abruptly and the new song immediately begins playing.
FADE_IN: The new song will fade in as it begins to play.
FADE_OUT: The old song will fade out before the new song begins to play.
FADE_MIX: A combination of FadeIn and FadeOut.
"""


class FadeOption(IntEnum):
    NO_FADE = 0
    FADE_IN = 1
    FADE_OUT = 2
    FADE_MIX = 3

    # aliases
    IN = FADE_IN
    OUT = FADE_OUT
    MIX = FADE_MIX

    @staticmethod
    def from_str(in_str: str):
        return str.upper() in FadeOption or FadeOption.NO_FADE


class ArgType(Enum):
    STR = 1
    STR_OR_EMPTY = 2
    INT = 3


class TargetType(Enum):
    # possible keys: ip, OOC, id, cname, ipid, hdid, showname, charfolder (for iniediting)
    IP = 0
    OOC_NAME = 1
    ID = 2
    CHAR_NAME = 3
    IPID = 4
    HDID = 5
    SHOWNAME = 6
    CHAR_FOLDER = 7
    CHAR_SHOWNAME = 8
    ALL = 9


class Effects(Enum):
    B = ('Blindness', 'blinded', lambda client,
                                        value: client.change_blindness(value))
    D = ('Deafness', 'deafened', lambda client,
                                        value: client.change_deafened(value))
    G = ('Gagged', 'gagged', lambda client, value: client.change_gagged(value))

    @property
    def name(self):
        return self.value[0]

    @property
    def action(self):
        return self.value[1]

    @property
    def function(self):
        return self.value[2]

    @property
    def async_name(self):
        return 'as_effect_{}'.format(self.name.lower())


class _UniqueKeySafeLoader(yaml.SafeLoader):
    # Adapted from ErichBSchulz at https://stackoverflow.com/a/63215043
    def construct_mapping(self, node, deep=False):
        mapping = dict()
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                msg = (f'while scanning a mapping\n'
                       f'{node.start_mark}\n'
                       f'duplicate key found in mapping: {key}\n'
                       f'{mapping[key]}\n'
                       f'{key_node.start_mark}')
                raise yaml.YAMLError(msg)
            mapping[key] = key_node.start_mark
        return super().construct_mapping(node, deep)


class FileValidity:
    # The majority of this class should be credited to Cecil Curry
    # See original post at https://stackoverflow.com/a/34102855
    # Chrezm/Iuvee wrote file_exists_or_creatable

    # Sadly, Python fails to provide the following magic number for us.
    ERROR_INVALID_NAME = 123
    '''
    Windows-specific error code indicating an invalid pathname.

    See Also
    ----------
    https://docs.microsoft.com/en-us/windows/win32/debug/system-error-codes--0-499-
        Official listing of all such codes.
    '''

    @staticmethod
    def is_pathname_valid(pathname: str) -> bool:
        '''
        `True` if the passed pathname is a valid pathname for the current OS;
        `False` otherwise.
        '''

        # If this pathname is either not a string or is but is empty, this pathname
        # is invalid.
        try:
            if not isinstance(pathname, str) or not pathname:
                return False

            # Strip this pathname's Windows-specific drive specifier (e.g., `C:\`)
            # if any. Since Windows prohibits path components from containing `:`
            # characters, failing to strip this `:`-suffixed prefix would
            # erroneously invalidate all valid absolute Windows pathnames.
            _, pathname = os.path.splitdrive(pathname)

            # Directory guaranteed to exist. If the current OS is Windows, this is
            # the drive to which Windows was installed (e.g., the "%HOMEDRIVE%"
            # environment variable); else, the typical root directory.
            root_dirname = os.environ.get('HOMEDRIVE', 'C:') \
                if sys.platform == 'win32' else os.path.sep
            # ...Murphy and her ironclad Law
            assert os.path.isdir(root_dirname)

            # Append a path separator to this directory if needed.
            root_dirname = root_dirname.rstrip(os.path.sep) + os.path.sep

            # Test whether each path component split from this pathname is valid or
            # not, ignoring non-existent and non-readable path components.
            for pathname_part in pathname.split(os.path.sep):
                try:
                    os.lstat(root_dirname + pathname_part)
                # If an OS-specific exception is raised, its error code
                # indicates whether this pathname is valid or not. Unless this
                # is the case, this exception implies an ignorable kernel or
                # filesystem complaint (e.g., path not found or inaccessible).
                #
                # Only the following exceptions indicate invalid pathnames:
                #
                # * Instances of the Windows-specific "WindowsError" class
                #   defining the "winerror" attribute whose value is
                #   "ERROR_INVALID_NAME". Under Windows, "winerror" is more
                #   fine-grained and hence useful than the generic "errno"
                #   attribute. When a too-long pathname is passed, for example,
                #   "errno" is "ENOENT" (i.e., no such file or directory) rather
                #   than "ENAMETOOLONG" (i.e., file name too long).
                # * Instances of the cross-platform "OSError" class defining the
                #   generic "errno" attribute whose value is either:
                #   * Under most POSIX-compatible OSes, "ENAMETOOLONG".
                #   * Under some edge-case OSes (e.g., SunOS, *BSD), "ERANGE".
                except OSError as exc:
                    if hasattr(exc, 'winerror'):
                        if exc.winerror == FileValidity.ERROR_INVALID_NAME:
                            return False
                    elif exc.errno in {errno.ENAMETOOLONG, errno.ERANGE}:
                        return False
        # If a "TypeError" exception was raised, it almost certainly has the
        # error message "embedded NUL character" indicating an invalid pathname.
        except TypeError:
            return False
        # If no exception was raised, all path components and hence this
        # pathname itself are valid. (Praise be to the curmudgeonly python.)
        else:
            return True
        # If any other exception was raised, this is an unrelated fatal issue
        # (e.g., a bug). Permit this exception to unwind the call stack.
        #
        # Did we mention this should be shipped with Python already?

    @staticmethod
    def is_path_sibling_creatable(pathname: str) -> bool:
        '''
        `True` if the current user has sufficient permissions to create **siblings**
        (i.e., arbitrary files in the parent directory) of the passed pathname;
        `False` otherwise.
        '''
        # Parent directory of the passed path. If empty, we substitute the current
        # working directory (CWD) instead.
        dirname = os.path.dirname(pathname) or os.getcwd()

        try:
            # For safety, explicitly close and hence delete this temporary file
            # immediately after creating it in the passed path's parent directory.
            with tempfile.TemporaryFile(dir=dirname):
                pass
            return True
        # While the exact type of exception raised by the above function depends on
        # the current version of the Python interpreter, all such types subclass the
        # following exception superclass.
        except EnvironmentError:
            return False

    @staticmethod
    def is_path_exists_or_creatable(pathname: str) -> bool:
        '''
        `True` if the passed pathname is a valid pathname on the current OS _and_
        either currently exists or is hypothetically creatable in a cross-platform
        manner optimized for POSIX-unfriendly filesystems; `False` otherwise.

        This function is guaranteed to _never_ raise exceptions.
        '''
        try:
            # To prevent "os" module calls from raising undesirable exceptions on
            # invalid pathnames, is_pathname_valid() is explicitly called first.
            return FileValidity.is_pathname_valid(pathname) and (
                    os.path.exists(pathname) or
                    FileValidity.is_path_sibling_creatable(pathname))
        # Report failure on non-fatal filesystem complaints (e.g., connection
        # timeouts, permissions issues) implying this path to be inaccessible. All
        # other exceptions are unrelated fatal issues and should not be caught here.
        except OSError:
            return False

    @staticmethod
    def file_exists_or_creatable(pathname: str) -> bool:
        if not FileValidity.is_path_exists_or_creatable(pathname):
            return False

        if pathlib.Path(pathname).is_file():
            return True

        # If execution makes it here, we are in one of two situations
        # pathname exists but is not a file
        # pathname does not exist as a path
        # Therefore, os.path.exists(pathname) is True when we don't want it to, and False when we do
        return not os.path.exists(pathname)


class Constants:
    @staticmethod
    def ic_msg_to_discord(message: str) -> str:
        text = (
            message.replace("}", "")
                .replace("{", "")
                .replace("`", "")
                .replace("|", "")
                .replace("~", "")
                .replace("º", "")
                .replace("№", "")
                .replace("√", "")
                .replace("\\s", "")
                .replace("\\f", "")
        )
        # escape chars
        text = text.replace(
            "@", "@\u200b"
        )  # The only way to escape a Discord ping is a zero width space...
        text = text.replace("<num>", "\\#")
        text = text.replace("<and>", "&")
        text = text.replace("<percent>", "%")
        text = text.replace("<dollar>", "$")
        text = text.replace("*", "\\*")
        text = text.replace("_", "\\_")
        # String is empty if we're strippin
        if not text.strip():
            # Discord blankpost
            text = "_ _"
        return text

    @staticmethod
    def discord_msg_to_ic(message: str) -> str:
        message = Constants.remove_URL(message)
        message = (
            message.replace("}", "\\}")
                .replace("{", "\\{")
                .replace("`", "\\`")
                .replace("|", "\\|")
                .replace("~", "\\~")
                .replace("º", "\\º")
                .replace("№", "\\№")
                .replace("√", "\\√")
                .replace("\\s", "")
                .replace("\\f", "")
        )
        return message

    @staticmethod
    def remove_URL(sample):
        """Remove URLs from a sample string"""
        return re.sub(r"http\S+", "", sample)

    @staticmethod
    def warn_deprecated(original_name: str, new_name: str, to_be_removed_in: str):
        message = (f'Code is using old {original_name} syntax. Please change it (or ask your '
                   f'server developer) so that it uses {new_name} instead. '
                   f'This old syntax will be removed in {to_be_removed_in}.')
        warnings.warn(message, category=UserWarning, stacklevel=3)

    @staticmethod
    def decode_ao_packet(params: List[str]) -> List[str]:
        new_params = [
            (arg.replace('<num>', '#').replace('<percent>', '%')
             .replace('<dollar>', '$').replace('<and>', '&'))
            for arg in params
        ]
        return new_params

    @staticmethod
    def encode_ao_packet(params: List) -> List[str]:
        new_params = [
            (str(arg).replace('#', '<num>').replace('%', '<percent>')
             .replace('$', '<dollar>').replace('&', '<and>'))
            for arg in params
        ]
        return new_params

    @staticmethod
    def fopen(file_name: str, *args, disallow_parent_folder: bool = True,
              **kwargs) -> TextIOWrapper:
        """
        Open file.

        Parameters
        ----------
        file_name : str
            Path to folder relative to root server directory.
        disallow_parent_folder : bool, optional
            If paths including relative directories should be disallowed or not, by default True.

        Returns
        -------
        TextIOWrapper
            File descriptor.

        Raises
        ------
        ServerError.FileInvalidNameError
            If `file_name` includes relative directories and `disallow_parent_folder` is False.
        ServerError.FileNotFoundError
            If the file was not found.
        ServerError.FileOSError
            If there was an operating system error when opening the file.
        """

        if disallow_parent_folder and Constants.includes_relative_directories(file_name):
            info = f'File names may not reference parent or current directories: {file_name}'
            raise ServerError.FileInvalidNameError(info)

        # # We do this manually to prevent accepting filenames like
        # *`con.yaml`, which are reserved in Windows and cause a loop if a naive load is attempted.
        # *`e/f.yaml` if folder 'e' does not exist
        if not FileValidity.file_exists_or_creatable(file_name):
            info = 'File not found: {}'.format(file_name)
            raise ServerError.FileNotFoundError(info, code="FileNotFound")

        try:
            file = open(file_name, *args, **kwargs)
            return file
        except FileNotFoundError:
            # This one handles when file_name does not exist but is creatable
            # This should only be raised if the mode is 'r'
            info = 'File not found: {}'.format(file_name)
            raise ServerError.FileNotFoundError(info, code="FileNotFound")
        except OSError as ex:
            raise ServerError.FileOSError(str(ex), code="OSError")

    @staticmethod
    def includes_relative_directories(path: str) -> bool:
        folders = []
        while True:
            # Based from https://stackoverflow.com/a/3167684
            path, folder = os.path.split(path)

            if folder:
                folders.append(folder)
                continue
            if path:
                folders.append(path)
            break
        return ('.' in folders or '..' in folders)

    @staticmethod
    def is_aoprotocol_injection_vulnerable(name: str) -> bool:
        return name.startswith('%') or '#' in name

    @staticmethod
    def yaml_load(file: TextIOWrapper) -> Any:
        """
        Load a YAML file.

        Parameters
        ----------
        file : TextIOWrapper
            File to open.

        Returns
        -------
        Any
            Contents of the YAML file.

        Raises
        ------
        ServerError.YAMLInvalidError
            If the file was empty, had a YAML syntax error, or could not be decoded using UTF-8.
        """

        # Extract the name of the yaml in case of errors
        separator = max(file.name.rfind('\\'), file.name.rfind('/'))
        file_name = file.name[separator + 1:]

        try:
            contents = yaml.load(file, Loader=_UniqueKeySafeLoader)
            if not contents:
                msg = f'File {file_name} was empty. Populate it properly and try again.'
                raise ServerError.YAMLInvalidError(msg)
            return contents
        except yaml.YAMLError as exc:
            msg = ('File {} returned the following YAML syntax error when loading: `{}`. Fix the syntax '
                   'error and try again.'
                   .format(file_name, exc))
            raise ServerError.YAMLInvalidError(msg)
        except UnicodeDecodeError as exc:
            msg = ('File {} returned the following UnicodeDecode error when loading: `{}`. Make '
                   'sure this is an actual YAML file and that it does not contain any unusual '
                   'characters and try again.'
                   .format(file_name, exc))
            raise ServerError.YAMLInvalidError(msg)

    @staticmethod
    def yaml_dump(data: Any, file: str):
        if not FileValidity.file_exists_or_creatable(file.name):
            msg = f'Unable to create file {file.name}.'
            raise ServerError.FileNotCreatedError(msg)

        dumped = yaml.dump(data, file)
        if dumped is not None:
            msg = f'Unable to save to {file.name}.'
            raise ServerError.FileNotCreatedError(msg)

    @staticmethod
    def get_time() -> str:
        return time.asctime(time.localtime(time.time()))

    @staticmethod
    def get_time_iso() -> str:
        return time.strftime('[%Y-%m-%dT%H:%M:%S]')

    @staticmethod
    def time_remaining(start: float, length: float) -> Tuple[float, str]:
        current = time.time()
        remaining = start + length - current
        return remaining, Constants.time_format(remaining)

    @staticmethod
    def time_elapsed(start: float) -> str:
        current = time.time()
        return Constants.time_format(current - start)

    @staticmethod
    def time_format(length: float) -> str:
        if length < 10:
            text = "{} seconds".format('{0:.1f}'.format(length))
        elif length < 60:
            text = "{} seconds".format(int(length))
        elif length < 3600:
            text = "{}:{}".format(int(length // 60),
                                  '{0:02d}'.format(int(length % 60)))
        else:
            text = "{}:{}:{}".format(int(length // 3600),
                                     '{0:02d}'.format(
                                         int((length % 3600) // 60)),
                                     '{0:02d}'.format(int(length % 60)))
        return text

    @staticmethod
    def trim_extra_whitespace(text: str) -> str:
        # Trim out any leading whitespace characters up to a chain of spaces
        text = re.sub(r'^[\r\n\t\f\v ]*[\r\n\t\f\v]', '', text)
        # And same thing for trailing
        text = re.sub(r'[\r\n\t\f\v][\r\n\t\f\v ]*$', '', text)
        return text

    @staticmethod
    def assert_command(client: ClientManager.Client, arg: str, is_staff=None, is_officer=None,
                       is_mod=None, parameters=None,
                       split_spaces=None, split_commas=False):
        if is_staff is not None:
            if is_staff is True and not client.is_staff():
                raise ClientError.UnauthorizedError(
                    'You must be authorized to do that.')
            if is_staff is False and client.is_staff():
                raise ClientError.UnauthorizedError(
                    'You have too high a rank to do that.')

        if is_officer is not None:
            if is_officer is True and not client.is_officer():
                raise ClientError.UnauthorizedError(
                    'You must be authorized to do that.')
            if is_officer is False and client.is_officer():
                raise ClientError.UnauthorizedError(
                    'You have too high a rank to do that.')

        if is_mod is not None:
            if is_mod is True and not client.is_mod:
                raise ClientError.UnauthorizedError(
                    'You must be authorized to do that.')
            if is_mod is False and client.is_mod():
                raise ClientError.UnauthorizedError(
                    'You have too high a rank to do that.')

        if parameters is not None:
            symbol, num = parameters[0], [int(i)
                                          for i in parameters[1:].split('-')]
            # Set up default values
            if (num[0] > 0 or symbol == '&') and split_spaces is None and split_commas is False:
                split_spaces = True
            elif split_spaces is None:
                split_spaces = False

            if split_spaces:
                arg = arg.split(' ')
            elif split_commas:
                arg = arg.split(', ')

            if arg == ['']:
                arg = list()

            error = None
            if symbol == '=':
                expect = num[0]
                if len(arg) != expect:
                    if expect == 0:
                        expect = 'no'
                    error = ('This command has {} argument{}.', expect)
            elif symbol == '<':
                expect = num[0] - 1
                if len(arg) > expect:
                    error = ('This command has at most {} argument{}.', expect)
            elif symbol == '>':
                expect = num[0] + 1
                if len(arg) < expect:
                    error = ('This command has at least {} argument{}.', expect)
            elif symbol == '&':
                expect = num
                if not expect[0] <= len(arg) <= expect[1]:
                    expect = '{} to {}'.format(expect[0], expect[1])
                    error = ('This command has from {} argument{}.', expect)

            if error:
                raise ArgumentError(error[0].format(
                    error[1], 's' if error[1] != 1 else ''))

    @staticmethod
    def build_cond(
            sender: ClientManager.Client,
            is_staff: Union[bool, None] = None,
            is_officer: Union[bool, None] = None,
            is_mod: Union[bool, None] = None,
            in_hub: Union[bool, _Hub, Set[_Hub], None] = None,
            in_area: Union[bool, AreaManager.Area,
                           Set[AreaManager.Area], None] = None,
            not_to: Union[Set[ClientManager.Client], None] = None,
            part_of: Union[Set[ClientManager.Client], None] = None,
            to_blind: Union[bool, None] = None,
            to_deaf: Union[bool, None] = None,
            is_zstaff: Union[bool, AreaManager.Area, None] = None,
            is_zstaff_flex: Union[bool, AreaManager.Area, None] = None,
            pred: Callable[[ClientManager.Client], bool] = None,
    ) -> Callable[[ClientManager.Client], bool]:
        """
        Acceptable conditions:
            is_staff: If target is GM, CM or Mod
            is_officer: If target is CM or Mod
            is_mod: If target is Mod
            in_hub: If target is in client's hub, or some particular hub
            in_area: If target is in client's area, or some particular area
            part_of: If target is an element of this set
            not_to: If target is not in a set of clients that are filtered out
            to_blind: If target is blind
            to_deaf: If target is deaf
            is_zstaff: If target is GM, CM or Mod, and if they are watching the zone the sender's
             area is in, or the area that is given. This EXPECTS the targets to be watching a
             non-None zone.
            is_zstaff_flex: If target is GM, CM, or Mod, and if they are watching the zone the
             sender's area is in, or the area that is given, or both the target's watched zone
             and the zone the sender's/given area is in are both None for its True and area cases.
            pred: If target satisfies some custom condition
        """
        conditions = list()

        if is_staff is True:
            conditions.append(lambda c: c.is_staff())
        elif is_staff is False:
            conditions.append(lambda c: not c.is_staff())
        elif is_staff is None:
            pass
        else:
            raise KeyError(
                'Invalid argument for build_cond is_staff: {}'.format(is_staff))

        if is_officer is True:
            conditions.append(lambda c: c.is_officer())
        elif is_officer is False:
            conditions.append(lambda c: not c.is_officer())
        elif is_officer is None:
            pass
        else:
            raise KeyError(
                'Invalid argument for build_cond is_officer: {}'.format(is_officer))

        if is_mod is True:
            conditions.append(lambda c: c.is_mod)
        elif is_mod is False:
            conditions.append(lambda c: not c.is_mod)
        elif is_mod is None:
            pass
        else:
            raise KeyError(
                'Invalid argument for build_cond is_mod: {}'.format(is_mod))

        if in_hub is True:
            conditions.append(lambda c: c.hub == sender.hub)
        elif in_hub is False:
            conditions.append(lambda c: c.area != sender.hub)
        # Lazy way of finding if in_hub is hub obj
        elif isinstance(in_hub, type(sender.hub)):
            conditions.append(lambda c: c.hub == in_hub)
        elif isinstance(in_hub, set):
            conditions.append(lambda c: c.hub in in_hub)
        elif in_hub is None:
            pass
        else:
            raise KeyError(
                'Invalid argument for build_cond in_hub: {}'.format(in_hub))

        if in_area is True:
            conditions.append(lambda c: c.area == sender.area)
        elif in_area is False:
            conditions.append(lambda c: c.area != sender.area)
        # Lazy way of finding if in_area is area obj
        elif isinstance(in_area, type(sender.area)):
            conditions.append(lambda c: c.area == in_area)
        elif isinstance(in_area, set):
            conditions.append(lambda c: c.area in in_area)
        elif in_area is None:
            pass
        else:
            raise KeyError(
                'Invalid argument for build_cond in_area: {}'.format(in_area))

        if part_of is not None:
            conditions.append(lambda c: c in part_of)

        if not_to is not None:
            conditions.append(lambda c: c not in not_to)

        if to_blind is True:
            conditions.append(lambda c: c.is_blind)
        elif to_blind is False:
            conditions.append(lambda c: not c.is_blind)
        elif to_blind is None:
            pass
        else:
            raise KeyError(
                'Invalid argument for build_cond to_blind: {}'.format(to_blind))

        if to_deaf is True:
            conditions.append(lambda c: c.is_deaf)
        elif to_deaf is False:
            conditions.append(lambda c: not c.is_deaf)
        elif to_deaf is None:
            pass
        else:
            raise KeyError(
                'Invalid argument for build_cond to_deaf: {}'.format(to_deaf))

        # This is a strict parameter.
        # To be precise, is_zstaff expects the sender to be watching a zone or be in a zone, or
        # if given an area, that it is part of a zone.
        if is_zstaff is True:
            # Only staff members who are watching the sender's zone will receive it, PROVIDED that
            # the sender is watching a zone, or in an area part of a zone. If neither is true,
            # NO notification is sent.
            conditions.append(lambda c: c.is_staff() and c.zone_watched)
            if sender.zone_watched:
                conditions.append(lambda c: (
                        c.zone_watched == sender.zone_watched))
            elif sender.area.in_zone:
                conditions.append(lambda c: (
                        c.zone_watched == sender.area.in_zone))
            else:
                conditions.append(lambda c: False)
        elif is_zstaff is False:
            if sender.zone_watched:
                conditions.append(lambda c: (
                        c.zone_watched != sender.zone_watched))
            elif sender.area.in_zone:
                conditions.append(lambda c: (
                        c.zone_watched != sender.area.in_zone))
            else:
                conditions.append(lambda c: False)
        elif isinstance(is_zstaff, sender.hub.area_manager.Area):
            # Only staff members who are watching the area's zone will receive it, PROVIDED the area
            # is part of a zone. Otherwise, NO notification is sent.
            target_zone = is_zstaff.in_zone
            if target_zone:
                conditions.append(lambda c: c.is_staff()
                                            and c.zone_watched == target_zone)
            else:
                conditions.append(lambda c: False)
        elif is_zstaff is None:
            pass
        else:
            raise KeyError(
                'Invalid argument for build_cond is_zstaff: {}'.format(is_zstaff))

        # This is a less strict parameter. The sender may or may not be in a zone (or the given
        # area may not be in a zone), in which case it will ignore zone limitations and effectively
        # just act as is_staff.
        # This is a BACKWARDS COMPATIBILITY only parameter, designed to keep the pre-4.2 notifs
        # that were sent to all staff members as they were pre-zones, so that if a notif happens
        # outside a zone, it notifies all staff members
        # Please use is_zstaff for 4.2 forwards.
        if is_zstaff_flex is True:
            # Only staff members who are watching the sender's zone will receive it, PROVIDED that
            # the sender is watching a zone, or in an area part of a zone. If neither is true,
            # NO notification is sent.
            conditions.append(lambda c: c.is_staff())
            if sender.zone_watched:
                conditions.append(lambda c: (
                        c.zone_watched == sender.zone_watched))
            elif sender.area.in_zone:
                conditions.append(lambda c: (
                        c.zone_watched == sender.area.in_zone))
        elif is_zstaff_flex is False:
            if sender.zone_watched:
                def condition1(c):
                    return (
                            c.zone_watched != sender.zone_watched)
            elif sender.area.in_zone:
                def condition1(c):
                    return (
                            c.zone_watched != sender.area.in_zone)
            else:
                def condition1(c):
                    return False
            conditions.append(lambda c: condition1(c) or not c.is_staff())
        elif isinstance(is_zstaff_flex, sender.hub.area_manager.Area):
            # Only staff members who are watching the area's zone will receive it, PROVIDED the area
            # is part of a zone. Otherwise, NO notification is sent.
            target_zone = is_zstaff_flex.in_zone
            conditions.append(lambda c: c.is_staff()
                                        and c.zone_watched == target_zone)
        elif is_zstaff_flex is None:
            pass
        else:
            raise KeyError('Invalid argument for build_cond is_zstaff_flex: {}'
                           .format(is_zstaff_flex))

        if pred is not None:
            conditions.append(pred)

        def cond(c):
            return all([cond(c) for cond in conditions])

        return cond

    @staticmethod
    def dice_roll(arg: str, command_type: str, server: TsuserverDR) -> Tuple[str, int]:
        """
        Calculate roll results.
        Confront /roll documentation for more details.
        """

        max_numdice = server.config['max_numdice']
        max_numfaces = server.config['max_numfaces']
        max_modifier_length = server.config['max_modifier_length']
        max_acceptable_term = server.config['max_acceptable_term']
        def_numdice = server.config['def_numdice']
        def_numfaces = server.config['def_numfaces']
        def_modifier = server.config['def_modifier']

        ACCEPTABLE_IN_MODIFIER = '1234567890+-*/().r'
        MAXDIVZERO_ATTEMPTS = 10

        special_calculation = False  # Is it given a modifier? False until proven otherwise
        args = arg.split(' ')
        arg_length = len(args)

        # Parse number of dice, number of faces and modifiers
        if arg:
            if arg_length == 2:
                dice_type, modifiers = args
                if len(modifiers) > max_modifier_length:
                    raise ArgumentError('The modifier is too long to compute. Please try a shorter '
                                        'one.')
            elif arg_length == 1:
                dice_type, modifiers = arg, ''
            else:
                raise ArgumentError('This command takes one or two arguments. Use /{} '
                                    '<num_dice>d<num_faces> <modifiers>'.format(command_type))

            dice_type = dice_type.split('d')
            if len(dice_type) == 1:
                dice_type.insert(0, 1)
            if dice_type[0] == '':
                dice_type[0] = '1'

            try:
                num_dice, num_faces = int(dice_type[0]), int(dice_type[1])
            except ValueError:
                raise ArgumentError('The number of rolls and faces of the dice must be '
                                    'positive integers.')

            if not 1 <= num_dice <= max_numdice:
                raise ArgumentError(
                    'Number of rolls must be between 1 and {}.'.format(max_numdice))
            if not 1 <= num_faces <= max_numfaces:
                raise ArgumentError('Number of faces must be between 1 and {}.'
                                    .format(max_numfaces))

            for char in modifiers:
                if char not in ACCEPTABLE_IN_MODIFIER:
                    raise ArgumentError('The modifier must only include numbers and standard '
                                        'mathematical operations in the modifier.')
                if char == 'r':
                    special_calculation = True
            if '**' in modifiers:  # Exponentiation manually disabled, it can be pretty dangerous
                raise ArgumentError('The modifier must only include numbers and standard '
                                    'mathematical operations in the modifier.')
        else:
            # Default
            num_dice, num_faces, modifiers = def_numdice, def_numfaces, def_modifier

        roll = ''

        for _ in range(num_dice):
            divzero_attempts = 0
            # Roll until no division by zeroes happen (or it gives up)
            while True:
                # raw_roll: original roll
                # mid_roll: result after modifiers (if any) have been applied to original roll
                # final_roll: result after previous result was capped between 1 and max_numfaces

                raw_roll = str(random.randint(1, num_faces))
                if modifiers == '':
                    aux_modifier = ''
                    mid_roll = int(raw_roll)
                else:
                    if special_calculation:  # Ex: /roll 20 3*r+1
                        aux_modifier = modifiers.replace('r', raw_roll) + '='
                    elif modifiers[0].isdigit():  # Ex /roll 20 3
                        aux_modifier = raw_roll + "+" + modifiers + '='
                    else:  # Ex /roll 20 -3
                        aux_modifier = raw_roll + modifiers + '='

                    # Prevent any terms from reaching past max_acceptable_term in order to prevent
                    # server lag due to potentially frivolous dice rolls
                    # In order to do that, it will split the string by the numbers it uses
                    # and check if any individual number is larger than said term.
                    # This also doubles as a second-line defense to junk entries such as "+1..4"
                    aux = aux_modifier[:-1]
                    for j in "+-*/()":
                        aux = aux.replace(j, "!")
                    aux = aux.split('!')
                    for j in aux:
                        try:
                            if j != '' and round(float(j)) > max_acceptable_term:
                                raise ArgumentError('The modifier must take numbers within the '
                                                    'computation limit of the server.')
                        except ValueError:
                            raise ArgumentError(
                                'The modifier has a syntax error.')

                    for j in range(10):
                        # Deals with inputs like 3(r-1), which act like Python functions.
                        # Needed to be done here to prevent Python 3.8 from raising SyntaxWarning
                        if '{}('.format(j) in aux_modifier[:-1]:
                            raise ArgumentError(
                                'The modifier has a syntax error.')

                    try:
                        # By this point it should be 'safe' to run eval
                        mid_roll = round(eval(aux_modifier[:-1]))
                    except SyntaxError:
                        raise ArgumentError('The modifier has a syntax error.')
                    except ZeroDivisionError:
                        divzero_attempts += 1
                        if divzero_attempts == MAXDIVZERO_ATTEMPTS:
                            raise ArgumentError(
                                'The modifier causes divisions by zero too often.')
                        continue
                break

            final_roll = min(max_acceptable_term, max(1, mid_roll))

            # Build output string
            if final_roll != mid_roll:
                # This visually indicates the roll was capped off due to exceeding the
                # acceptable roll range
                final_roll = "|" + str(final_roll)
            else:
                final_roll = str(final_roll)

            if modifiers != '':
                roll += str(raw_roll + ':')
            roll += str(aux_modifier + final_roll) + ', '

        roll = roll[:-2]  # Remove last ', '
        if num_dice > 1:
            roll = '(' + roll + ')'

        return roll, num_faces

    @staticmethod
    def disemvowel_message(message: str) -> str:
        return Constants.remove_letters(message, 'aeiou')

    @staticmethod
    def disemconsonant_message(message: str) -> str:
        return Constants.remove_letters(message, 'bcdfghjklmnpqrstvwxyz')

    @staticmethod
    def fix_and_setify(csv_values: str) -> Set[str]:
        """
        For the area parameters that include lists of comma-separated values, parse them
        appropiately before turning them into sets.
        """

        split_values = csv_values.split(', ')
        # Ah, escape characters... again...
        for (i, split_value) in enumerate(split_values):
            split_values[i] = split_value.replace(',\\', ',')

        if split_values in [list(), ['']]:
            return set()
        return set(split_values)

    @staticmethod
    def gagged_message() -> str:
        length = random.randint(5, 9)
        letters = ['g', 'h', 'm', 'r']
        starters = ['G', 'M']
        message = random.choice(
            starters) + "".join([random.choice(letters) for _ in range(length)])
        return message

    @staticmethod
    def cjoin(structure: Iterable, the: bool = False, sort: bool = True) -> str:
        if not structure:
            return ''

        connector = 'the ' if the else ''
        new_structure = sorted(structure) if sort else list(structure)

        info = '{}{}'.format(connector, new_structure[0])
        if len(new_structure) > 1:
            for i in range(1, len(new_structure) - 1):
                info += ', {}{}'.format(connector, new_structure[i])
            info += ' and {}{}'.format(connector, new_structure[-1])
        return info

    @staticmethod
    def parse_area_names(client: ClientManager.Client,
                         areas: List[str]) -> List[AreaManager.Area]:
        """
        Convert a list of area names or IDs into area objects.
        """

        area_list = list()
        # Replace arguments with proper area objects
        for i in range(len(areas)):
            # The escape character combination for areas that have commas in their name is ',\'
            # (yes, I know it's inverted)
            # This double try block takes into account the possibility that some weird person
            # wants ',\' as part of their actual area name. If you are that person... just... why
            try:
                target = areas[i].replace(',\\', ',')
                area_list.append(
                    client.hub.area_manager.get_area_by_name(target))
            except AreaError:
                try:
                    area_list.append(
                        client.hub.area_manager.get_area_by_name(areas[i]))
                except AreaError:
                    try:
                        area_list.append(
                            client.hub.area_manager.get_area_by_id(int(areas[i])))
                    except Exception:
                        raise ArgumentError(
                            'Could not parse area `{}`.'.format(areas[i]))
        return area_list

    @staticmethod
    def parse_effects(client: ClientManager.Client, effects: List[str]) -> Set[str]:
        """
        Convert a sequence of characters to their associated effect names.
        """

        if not effects:
            raise ArgumentError('Expected effects.')
        if len({x.lower() for x in effects}) != len([x.lower() for x in effects]):
            raise ArgumentError(
                'Effect list cannot contained repeated characters.')

        parsed_effects = set()
        for effect_letter in effects:
            try:
                parsed_effects.add(Effects[effect_letter.capitalize()])
            except KeyError:
                raise ArgumentError(
                    'Invalid effect letter `{}`.'.format(effect_letter))

        return parsed_effects

    @staticmethod
    def parse_id(client: ClientManager.Client, identifier: str) -> ClientManager.Client:
        """
        Given a client ID, returns the client that matches this identifier.
        """

        if identifier == '':
            raise ArgumentError('Expected client ID.')
        if not identifier.isdigit():
            raise ArgumentError(
                '`{}` does not look like a valid client ID.'.format(identifier))

        targets = client.server.client_manager.get_targets(client, TargetType.ID,
                                                           int(identifier), False)

        if not targets:
            raise ClientError('No targets found.')

        return targets[0]

    @staticmethod
    def parse_id_or_ipid(client: ClientManager.Client,
                         identifier: str) -> List[ClientManager.Client]:
        """
        Given either a client ID or IPID, returns all clients that match this identifier.

        First tries to match by ID, then by IPID. IPID can be of the same length as client ID and
        thus be mismatched, but it is extremely unlikely (1 in 100,000,000 chance).
        """

        if identifier == '':
            raise ArgumentError('Expected client ID or IPID.')
        if not identifier.isdigit() or len(identifier) > 10:
            raise ArgumentError('{} does not look like a valid client ID or IPID.'
                                .format(identifier))

        idnt = int(identifier)
        # First try and match by ID
        targets = client.server.client_manager.get_targets(
            client, TargetType.ID, idnt, False)
        if targets:
            return targets

        # Otherwise, try and match by IPID
        # PROVIDED the client is CM or mod
        if client.is_officer():
            targets = client.server.client_manager.get_targets(
                client, TargetType.IPID, idnt, False)
            if targets:
                return targets

        raise ArgumentError('No targets found.')

    @staticmethod
    def parse_time_length(time_length: str) -> float:
        """
        Convert seconds into a formatted string representing timelength.
        """
        TIMER_LIMIT = 21600  # 6 hours in seconds
        # Check if valid length and convert to seconds
        raw_length = time_length.split(':')
        try:
            length = [int(entry) for entry in raw_length]
        except ValueError:
            raise ClientError('Expected length of time.')

        if len(length) == 1:
            length = length[0]
        elif len(length) == 2:
            length = length[0] * 60 + length[1]
        elif len(length) == 3:
            length = length[0] * 3600 + length[1] * 60 + length[2]
        else:
            raise ClientError('Expected length of time.')

        if length > TIMER_LIMIT:
            raise ClientError('Suggested timer length exceeds server limit.')
        if length <= 0:
            raise ClientError('Expected positive time length.')
        return length

    @staticmethod
    def parse_two_area_names(client: ClientManager.Client,
                             raw_areas: List[AreaManager.Area],
                             area_duplicate: bool = True,
                             check_valid_range: bool = True) -> List[AreaManager.Area]:
        """
        Convert the area passage commands inputs into inputs for parse_area_names.
        and check for the different cases it needs to possibly handle
        """

        # Convert to two-area situation
        if len(raw_areas) == 0:
            raw_areas = [client.area.name, client.area.name]
        elif len(raw_areas) == 1:
            if area_duplicate:
                raw_areas.append(raw_areas[0])
            else:
                raw_areas.insert(0, client.area.name)
        elif len(raw_areas) > 2:
            raise ArgumentError('Expected at most two area names.')

        # Replace arguments with proper area objects
        areas = Constants.parse_area_names(client, raw_areas)

        if check_valid_range and areas[0].id > areas[1].id:
            raise ArgumentError('The ID of the first area must be lower than the ID of the second '
                                'area.')
        if not area_duplicate and areas[0].id == areas[1].id:
            raise ArgumentError('Areas must be different.')

        return areas

    @staticmethod
    def remove_h_message(message: str) -> str:
        return Constants.remove_letters(message, 'h')

    @staticmethod
    def remove_letters(message: str, target: str) -> str:
        message = re.sub("[{}]".format(target), "",
                         message, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", message)

    @staticmethod
    def format_area_ranges(areas: Iterable[AreaManager.Area]) -> str:
        # Obtain area ranges from an iterable containing area objects
        # Ex. If areas contains area 1, 2, 3, 5, 6 and 8, this will return "1-3, 5-6 and 8"
        # If areas is None or empty, returns None
        if not areas:
            return 'None'

        raw_area_ids = sorted([area.id for area in areas])
        last_area = raw_area_ids[0]
        area_ranges = list()
        current_range = [last_area, last_area]

        def add_range():
            if current_range[0] != current_range[1]:
                area_ranges.append(
                    '{}-{}'.format(current_range[0], current_range[1]))
            else:
                area_ranges.append('{}'.format(current_range[0]))

        for area_id in raw_area_ids[1:]:
            if area_id != last_area + 1:
                add_range()
                current_range = [area_id, area_id]
            else:
                current_range[1] = area_id
            last_area = area_id

        add_range()
        return Constants.cjoin(area_ranges)

    @staticmethod
    def create_fragile_task(coro_or_future: Awaitable, client: ClientManager.Client = None,
                            exception_cleanup: Callable[[], None] = None):
        """
        Schedule the execution of a coroutine object in a spawned task with a done callback that
        checks if an exception was raised after the coroutine finished.
        If there was no exception, do no further actions.
        If there was an exception other than asyncio.CancelledError, reraise the exception in
        the callback accordingly.
        If there was an asyncio.CancelledError or KeyboardInterrupt, do no further actions.

        Parameters
        ----------
        coro : coroutine
            Coroutine to schedule.
        client : ClientManager.Client, optional
            Client to notify in the callback if a caught exception during the coroutine was of type
            server.exceptions.TsuserverException. If such notification happens, the exception is
            not further propagated. Defaults to None.
        exception_cleanup : typing.types.FunctionType, optional
            Function to execute an exception is retrieved, but before it is propagated.
            Defaults to None.

        Raises
        ------
        exception
            The exception raised by `coro_or_future`, if any was raised.

        Returns
        -------
        task : Task.
            Task where the coroutine object is scheduled to be executed.

        """

        def check_exception(_client, _future):
            try:
                exception = _future.exception()
            except asyncio.CancelledError:
                return

            if not exception:
                return
            if isinstance(exception, (KeyboardInterrupt,)):
                return

            try:
                if not (_client and isinstance(exception, TsuserverException)):
                    raise exception

                _client.send_ooc(exception)
            finally:
                if exception_cleanup:
                    exception_cleanup()

        loop = asyncio.get_event_loop()
        task = loop.create_task(coro_or_future)
        task.add_done_callback(functools.partial(check_exception, client))
        return task

    @staticmethod
    def cancel_and_await_task(task: asyncio.Task):
        """
        Function that schedules the cancellation of `task` and awaiting it until it is able to
        properly retrieve the cancellation exception from `task`. This function assumes the task
        has not been cancelled yet.

        Parameters
        ----------
        task : asyncio.Task
            Task to cancel

        Returns
        -------
        None.
        """

        async def _do():
            try:
                task.cancel()
                await task
            except asyncio.CancelledError:
                pass

        Constants.create_fragile_task(_do())

    @staticmethod
    def complete_partial_arguments(original_partial, *overwriting_args, **overwriting_keywords):
        if isinstance(original_partial, functools.partial):
            new_func = original_partial.func
            new_args = overwriting_args  # original_partial.args
            new_keywords = overwriting_keywords.copy()  # original_partial.keywords.copy()
        else:
            new_func = original_partial
            new_args = tuple()
            new_keywords = dict()
        if original_partial.args:
            new_args = original_partial.args
        new_keywords.update(original_partial.keywords)
        return functools.partial(new_func, *new_args, **new_keywords)

    @staticmethod
    def make_partial_from(current_type, default_type: type, *args, **kwargs) -> Callable:
        """
        Make a merged functools.partial function based on current_type if it is also a partial
        function by returning self.complete_partial_arguments(current_type, *args, **kwargs).
        If current_type is None or the default type, create a partial function with a default type
        by returning self.complete_partial_arguments(default_type, *args, **kwargs).

        Parameters
        ----------
        current_type : functools.partial, type(default_type) or None
            Function or class to base the merged functions upon.
        default_type : type
            Default type to build a partial function upon.
        *args : iterable of Any
            Positional arguments to pass to self.complete_partial_arguments.
        **kwargs : TYPE
            Keywords arguments to pass to self.complete_partial_arguments.

        Raises
        ------
        ValueError
            If current_type is not a partial function, default_type or None.

        Returns
        -------
        functools.partial
            Merged partial function.

        """

        if isinstance(current_type, functools.partial):
            return Constants.complete_partial_arguments(current_type, *args, **kwargs)
        if current_type in [None, default_type]:
            return functools.partial(default_type, *args, **kwargs)
        raise ValueError(current_type, type(current_type))

    @staticmethod
    def contains_illegal_characters(text: str) -> bool:
        """
        Returns True if `text` contains a zero-width character, False otherwise.

        Parameters
        ----------
        text : str
            Text to check.
        Returns
        -------
        bool
            True if `text` contains a zero-width character, False otherwise.
        """

        illegal_characters = [
            '\u200b',
            '\u200c',
            '\u200d',
            '\u2060',
            '\ufeff',
        ]

        for char in illegal_characters:
            if char in text:
                return True
        return False

    @staticmethod
    def get_first_area_list_item(view_name: str, hub: _Hub, area: AreaManager.Area) -> str:
        if view_name == 'AREA':
            return (f'|| GO TO {view_name} VIEW\n'
                    f'|| YOU ARE HERE:\n'
                    f'|| Hub {hub.get_id()[1:]}, Area {area.id}\n')
        elif view_name == 'HUB':
            return (f'|| GO TO {view_name} VIEW')
        else:
            raise RuntimeError(f'Invalid view {view_name}')

    @staticmethod
    def secure_eq(a: str, b: str) -> bool:
        """
        Return whether a and b are the same, such that timing attacks are difficult to perform.

        Parameters
        ----------
        a : str
            First element.
        b : str
            Second element.

        Returns
        -------
        bool
            Whether `a == b`.
        """

        key = secrets.token_hex(16)
        byte_key = bytes(key, 'utf-8')

        mes_a = a.encode('utf-8')
        mes_b = b.encode('utf-8')

        enc_a = hmac.new(byte_key, mes_a, hashlib.sha256)
        enc_b = hmac.new(byte_key, mes_b, hashlib.sha256)

        return hmac.compare_digest(
            enc_a.hexdigest(),
            enc_b.hexdigest()
        )

    @staticmethod
    def get_ip_of_transport(transport: Union[_ProactorSocketTransport, None]) -> str:
        if not transport:
            return "127.0.0.1"

        return transport.get_extra_info('peername')[0]

    @staticmethod
    async def await_cancellation(old_task: asyncio.Task):
        # Wait until it is able to properly retrieve the cancellation exception
        try:
            await old_task
        except asyncio.CancelledError:
            pass

    @staticmethod
    async def do_nothing():
        while True:
            try:
                await asyncio.sleep(1)
            except KeyboardInterrupt:
                raise
