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

from __future__ import annotations

import typing

from typing import Any, Callable, Dict, List, Tuple, Union

from server.asset_manager import AssetManager
from server.exceptions import MusicError
from server.validate.music import ValidateMusic

if typing.TYPE_CHECKING:
    from server.hub_manager import _Hub
    from server.tsuserver import TsuserverDR

class MusicManager(AssetManager):
    """
    A manager for music. Music managers store a list of music either from a
    loaded file or an adequate Python representation.
    """

    def __init__(self, server: TsuserverDR, hub: Union[_Hub, None] = None):
        """
        Create a music manager object.

        Parameters
        ----------
        server: TsuserverDR
            The server this music manager belongs to.
        hub : _Hub, optional
            The hub this music manager belongs to. Defaults to None.
        """

        super().__init__(server, hub=hub)
        self._music = []
        self._source_file = 'config/music.yaml'

    def get_type_name(self) -> str:
        """
        Return `'music list'`.

        Returns
        -------
        str
            `'music list'`.
        """

        return 'music list'

    def get_default_file(self) -> str:
        """
        Return `'config/music.yaml'`.

        Returns
        -------
        str
            `'config/music.yaml'`.
        """

        return 'config/music.yaml'

    def get_loader(self) -> Callable[[str, ], str]:
        """
        Return `self.server.load_characters`.

        Returns
        -------
        Callable[[str, ], str]
            `self.server.load_characters`.
        """

        return self.load_file

    def get_music(self) -> List[Dict[str, Any]]:
        """
        Return a copy of the music managed by this manager.

        Returns
        -------
        List[Dict[str, Any]]
            Music managed.
        """

        return self._music.copy()

    def get_source_file(self) -> Union[str, None]:
        """
        Return the source file of the last music list the manager successfully loaded relative to
        the root directory of the server, or None if the latest loaded music list was loaded raw.

        Returns
        -------
        Union[str, None]
            Source file or None.
        """

        return self._source_file

    def get_custom_folder(self) -> str:
        """
        Return `'config/music_lists'`.

        Returns
        -------
        str
            `'config/music_lists'`.
        """

        return 'config/music_lists'

    def validate_file(self, source_file: Union[str, None] = None) -> List[Dict[str, Any]]:
        if source_file is None:
            source_file = self._source_file

        music = ValidateMusic().validate(source_file)
        return music

    def load_file(self, source_file: str) -> List[Dict[str, Any]]:
        """
        Set the music list from a given file.

        Parameters
        ----------
        source_file : str
            Relative path from server root folder to music file.

        Returns
        -------
        List[str]
            Music.

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

        music = self.validate_file(source_file)
        output = self._load_music(music, source_file)
        self._check_structure()

        return output

    def load_raw(self, yaml_contents: List) -> List[Dict[str, Any]]:
        """
        Load a music list from a YAML representation.

        Parameters
        ----------
        yaml_contents: Dict
            YAML representation.

        Returns
        -------
        List[Dict[str, Any]]:
            Music.

        Raises
        ------
        ServerError.FileNotFoundError
            If the file was not found.
        ServerError.FileOSError
            If there was an operating system error when opening the file.
        ServerError.YAMLInvalidError
            If the file was empty, had a YAML syntax error, or could not be decoded using UTF-8.
        ServerError.FileSyntaxError
            If the file failed verification for music.
        """

        music = ValidateMusic().validate_contents(yaml_contents)
        output = self._load_music(music, None)
        self._check_structure()

        return output

    def transfer_contents_from_manager(self, other: MusicManager) -> List[Dict[str, Any]]:
        music = other.get_music()
        source_file = other.get_source_file()
        output = self._load_music(music, source_file)
        self._check_structure()

        return output

    def _load_music(self, new_list: List[Dict[str, Any]], source_file: Union[str, None]) -> List[Dict[str, Any]]:
        self._music = new_list.copy()
        self._source_file = source_file

        return new_list.copy()

    def get_music_data(self, music: str) -> Tuple[str, int, str]:
        for item in self.get_music():
            if item['category'] == music:
                return item['category'], -1, ''
            for song in item['songs']:
                if song['name'] == music:
                    name = song['name']
                    length = song['length'] if 'length' in song else -1
                    source = song['source'] if 'source' in song else ''
                    return name, length, source
        raise MusicError.MusicNotFoundError

    def is_music(self, music: str) -> bool:
        try:
            self.get_music_data(music)
            return True
        except MusicError.MusicNotFoundError:
            return False

    def get_client_view(self) -> List[str]:
        prepared_music_list = list()
        for item in self._music:
            category = item['category']
            songs = item['songs']
            prepared_music_list.append(category)
            for song in songs:
                name = song['name']
                prepared_music_list.append(name)

        return prepared_music_list

    def _check_structure(self):
        """
        Assert that all invariants specified in the class description are maintained.

        Raises
        ------
        AssertionError
            If any of the invariants are not maintained.

        """

        # At least one music track
        assert self._music
