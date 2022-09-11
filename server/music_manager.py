from __future__ import annotations

import typing

from typing import Any, Callable, Dict, List, Tuple, Union

from server.asset_manager import AssetManager
from server.exceptions import MusicError
from server.validate.music import ValidateMusic

if typing.TYPE_CHECKING:
    from server.tsuserver import TsuserverDR

class MusicManager(AssetManager):
    def __init__(self, server: TsuserverDR):
        super().__init__(server)
        self._music = []
        self._source_file = 'config/music.yaml'

    def get_name(self) -> str:
        return 'music list'

    def get_default_file(self) -> str:
        return 'config/music.yaml'

    def get_loader(self) -> Callable[[str, ], str]:
        return self.load_music

    def get_music(self) -> List[Dict[str, Any]]:
        return self._music.copy()

    def get_source_file(self) -> Union[str, None]:
        return self._source_file

    def validate_file(self, source_file: Union[str, None] = None) -> List[Dict[str, Any]]:
        if source_file is None:
            source_file = self._source_file

        music = ValidateMusic().validate(source_file)
        return music

    def load_music(self, source_file: str) -> List[Dict[str, Any]]:
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

    def load_music_raw(self, yaml_contents: List) -> List[str]:
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
        # At least one music track
        assert self._music
