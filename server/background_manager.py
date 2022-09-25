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
Module that contains the BackgroundManager class.
"""

from __future__ import annotations

import typing

from typing import Callable, List, Union

from server.asset_manager import AssetManager
from server.exceptions import BackgroundError
from server.validate.backgrounds import ValidateBackgrounds

if typing.TYPE_CHECKING:
    from server.hub_manager import _Hub
    from server.tsuserver import TsuserverDR

class BackgroundManager(AssetManager):
    """
    A manager for backgrounds. Background managers store a list of backgrounds either from a
    loaded file or an adequate Python representation.
    """

    def __init__(self, server: TsuserverDR, hub: Union[_Hub, None] = None):
        """
        Create a background manager object.

        Parameters
        ----------
        server: TsuserverDR
            The server this background manager belongs to.
        hub : _Hub, optional
            The hub this area manager belongs to. Defaults to None.
        """

        super().__init__(server, hub=hub)
        self._backgrounds = ['default']
        self._source_file = 'config/backgrounds.yaml'
        self._default_background = self._backgrounds[0]

    def get_type_name(self) -> str:
        """
        Return `'background list'`.

        Returns
        -------
        str
            `'background list'`.
        """

        return 'background list'

    def get_default_file(self) -> str:
        """
        Return `'config/backgrounds.yaml'`.

        Returns
        -------
        str
            `'config/backgrounds.yaml'`.
        """

        return 'config/backgrounds.yaml'

    def get_loader(self) -> Callable[[str, ], str]:
        """
        Return `self.hub.load_backgrounds`.

        Returns
        -------
        Callable[[str, ], str]
            `self.hub.load_backgrounds`.
        """

        return self.hub.load_backgrounds

    def get_backgrounds(self) -> List[str]:
        """
        Return a copy of the backgrounds managed by this manager.

        Returns
        -------
        List[str]
            Backgrounds managed.
        """

        return self._backgrounds.copy()

    def get_source_file(self) -> Union[str, None]:
        """
        Return the source file of the last background list the manager successfully loaded relative
        to the root directory of the server, or None if the latest loaded background list was
        loaded raw.

        Returns
        -------
        Union[str, None]
            Source file or None.
        """

        return self._source_file

    def get_custom_folder(self) -> str:
        """
        Return `'config/background_lists'`.

        Returns
        -------
        str
            `'config/background_lists'`.
        """

        return 'config/background_lists'

    def get_default_background(self) -> str:
        return self._default_background

    def set_default_background(self, background: str):
        if not self.is_background(background):
            raise BackgroundError.BackgroundNotFoundError

        self._default_background = background
        self._check_structure()

    def validate_file(self, source_file: Union[str, None] = None) -> List[str]:
        if source_file is None:
            source_file = self._source_file

        backgrounds = ValidateBackgrounds().validate(source_file)
        return backgrounds

    def load_file(self, source_file: str) -> List[str]:
        """
        Set the background list from a given file.

        Parameters
        ----------
        source_file : str
            Relative path from server root folder to background file.

        Returns
        -------
        List[str]
            Backgrounds.

        Raises
        ------
        ServerError.FileInvalidNameError
            If `source_file` includes relative directories.
        ServerError.FileNotFoundError
            If the file was not found.
        ServerError.FileOSError
            If there was an operating system error when opening the file.
        ServerError.YAMLInvalidError
            If the file was empty, had a YAML syntax error, or could not be decoded using UTF-8.
        ServerError.FileSyntaxError
            If the file failed verification for its asset type.
        """

        backgrounds = self.validate_file(source_file)
        output = self._load_backgrounds(backgrounds, source_file)
        self._check_structure()
        return output

    def load_raw(self, yaml_contents: List) -> List[str]:
        """
        Load a background list from a YAML representation.

        Parameters
        ----------
        yaml_contents: Dict
            YAML representation.

        Returns
        -------
        List[str]
            Backgrounds.

        Raises
        ------
        ServerError.FileNotFoundError
            If the file was not found.
        ServerError.FileOSError
            If there was an operating system error when opening the file.
        ServerError.YAMLInvalidError
            If the file was empty, had a YAML syntax error, or could not be decoded using UTF-8.
        ServerError.FileSyntaxError
            If the file failed verification for backgrounds.
        """

        backgrounds = ValidateBackgrounds().validate_contents(yaml_contents)
        output = self._load_backgrounds(backgrounds, None)
        self._check_structure()

        return output

    def _load_backgrounds(self, new_list: List[str], source_file: Union[str, None]) -> List[str]:
        lower = [name.lower() for name in new_list]
        self._backgrounds = lower
        self._source_file = source_file
        if not self.is_background(self._default_background):
            self._default_background = lower[0]

        return lower.copy()

    def is_background(self, background: str) -> bool:
        return background.lower() in self._backgrounds

    def _check_structure(self):
        """
        Assert that all invariants specified in the class description are maintained.

        Raises
        ------
        AssertionError
            If any of the invariants are not maintained.

        """

        # At least one background
        assert self._backgrounds

        # The default background is actually a background
        assert self.is_background(self._default_background)
