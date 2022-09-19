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
Module that contains the AssetManager class.

Assets are representations of the contents in the `config` folder of a running server.
This is roughly an ABC for each asset manager.
"""

from __future__ import annotations

import typing

from abc import ABC, abstractmethod

from typing import Any, Callable, List, Union

from server.exceptions import ServerError
from server.subscriber import Publisher

if typing.TYPE_CHECKING:
    from server.client_manager import ClientManager
    from server.hub_manager import _Hub
    from server.tsuserver import TsuserverDR


class AssetManager(ABC):
    """
    A quasi-abstract base class for managers of assets.
    """

    def __init__(self, server: TsuserverDR, hub: Union[_Hub, None] = None):
        """
        Create an asset manager.

        Parameters
        ----------
        server : TsuserverDR
            The server this asset manager belongs to.
        hub : _Hub, optional
            The hub this asset manager belongs to. Defaults to None.
        """

        self.server = server
        self.hub = hub
        self.publisher = Publisher(self)

    @abstractmethod
    def get_name(self) -> str:
        """
        Return a brief human-readable description of the manager.

        Returns
        -------
        str
            Brief human-readable description of the class.
        """

        raise NotImplementedError

    @abstractmethod
    def get_default_file(self) -> str:
        """
        Return the location of the default asset file the manager will use relative to the root
        server directory.

        Returns
        -------
        str
            Location.
        """

        raise NotImplementedError

    @abstractmethod
    def get_loader(self) -> Callable[[str, ], Any]:
        """
        Return the function the manager uses to load an asset file and parse it into a
        representation the server software can understand.

        Returns
        -------
        Callable[[str, ], Any]
            Function.
        """

        raise NotImplementedError

    @abstractmethod
    def get_source_file(self) -> Union[str, None]:
        """
        Return the source file of the last asset the manager successfully loaded relative to the
        root directory of the server, or None if the latest loaded asset was loaded raw.

        Returns
        -------
        Union[str, None]
            Source file or None.
        """

        raise NotImplementedError

    @abstractmethod
    def get_custom_folder(self) -> str:
        """
        Return the location of the folder relative to the server root directory where custom assets
        will be loaded from.

        Returns
        -------
        str
            Location.
        """

        raise NotImplementedError

    @abstractmethod
    def load_file(source_file: str) -> List:
        """
        Load assets from a file relative to the server root directory.

        Parameters
        ----------
        source_file : str
            File to load.

        Returns
        -------
        List
            List of generated assets.
        """

        raise NotImplementedError

    @abstractmethod
    def load_raw(raw: Any) -> List:
        """
        Load assets from a Python representation.

        Parameters
        ----------
        raw : Any
            Assets to load

        Returns
        -------
        List
            List of generated assets.
        """

        raise NotImplementedError

    def command_list_load(self, client: ClientManager.Client, file: str,
                          notify_others: bool = True):
        """
        Load an asset given by the player and notify the player and others if indicated.

        Parameters
        ----------
        client : ClientManager.Client
            Player who requested the loading.
        file : str
            Location of the file relative to the server root folder.
        notify_others : bool, optional
            If other players of the server should be notified if the asset is successfully loaded,
            by default True.

        Raises
        ------
        ServerError.FileInvalidNameError
            If `file` includes relative directories.
        ServerError.FileNotFoundError
            If the file was not found.
        ServerError.FileOSError
            If there was an operating system error when opening the file.
        ServerError.YAMLInvalidError
            If the file was empty, had a YAML syntax error, or could not be decoded using UTF-8.
        ServerError.FileSyntaxError
            If the file failed verification for its asset type.
        """

        if not file:
            source_file = self.get_default_file()
            msg = f'the default {self.get_name()} file'
        else:
            source_file = f'{self.get_custom_folder()}/{file}.yaml'
            msg = f'the custom {self.get_name()} file `{source_file}`'
        fail_msg = f'Unable to load {msg}'

        try:
            self.get_loader()(source_file)
        except ServerError.FileInvalidNameError:
            raise ServerError(f'{fail_msg}: '
                              f'File names may not contain relative directories.')
        except ServerError.FileNotFoundError:
            raise ServerError(f'{fail_msg}: '
                              f'File not found.')
        except ServerError.FileOSError as exc:
            raise ServerError(f'{fail_msg}: '
                              f'An OS error occurred: `{exc}`.')
        except ServerError.YAMLInvalidError as exc:
            raise ServerError(f'{fail_msg}: '
                              f'`{exc}`.')
        except ServerError.FileSyntaxError as exc:
            raise ServerError(f'{fail_msg}: '
                              f'An asset syntax error occurred: `{exc}`.')
        else:
            client.send_ooc(f'You have loaded {msg}.')
            if notify_others:
                client.send_ooc_others(f'{msg[0].upper()}{msg[1:]} has been loaded.',
                                       is_officer=False)
                client.send_ooc_others(f'{client.name} [{client.id}] has loaded {msg}.',
                                       is_officer=True)

    def command_list_info(self, client: ClientManager.Client):
        """
        Return information about the current list loaded by the manager to the player.

        Parameters
        ----------
        client : ClientManager.Client
            Player who requested the information.
        """

        raw_name = self.get_source_file()
        if raw_name is None:
            name = 'a non-standard list'
        elif raw_name.startswith(self.get_custom_folder()):
            name = (f'the custom list '
                    f'`{raw_name[len(self.get_custom_folder())+1:-len(".yaml")]}`')
        else:
            name = 'the default list'

        client.send_ooc(f'The current {self.get_name()} is {name}.')

    @abstractmethod
    def _check_structure(self):
        """
        Assert that all invariants specified in the class description are maintained.

        Raises
        ------
        AssertionError
            If any of the invariants are not maintained.

        """

        raise NotImplementedError
