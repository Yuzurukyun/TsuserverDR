from __future__ import annotations

import typing

from typing import List, Union

from server.validate.characters import ValidateCharacters

if typing.TYPE_CHECKING:
    from server.tsuserver import TsuserverDR

class CharacterManager:
    def __init__(self, server: TsuserverDR):
        self._server = server
        self._characters = []
        self._source_file = 'config/characters.yaml'

    def get_characters(self) -> List[str]:
        return self._characters.copy()

    def get_source_file(self) -> str:
        return self._source_file

    def validate_file(self, source_file: Union[str, None] = None) -> List[str]:
        if source_file is None:
            source_file = self._source_file

        characters = ValidateCharacters().validate(source_file)
        return characters

    def load_characters_from_file(self, source_file: str) -> List[str]:
        """
        Set the character list from a given file.

        Parameters
        ----------
        source_file : str
            Relative path from server root folder to character file.

        Returns
        -------
        List[str]
            Characters.

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

        characters = self.validate_file(source_file)
        output = self._load_characters(characters, source_file)
        self._check_structure()
        return output

    def _load_characters(self, new_list: List[str], source_file: str) -> List[str]:
        lower = [name.lower() for name in new_list]
        self._characters = lower
        self._source_file = source_file

        return lower.copy()

    def is_character(self, character: str) -> bool:
        return character.lower() in self._characters

    def _check_structure(self):
        # At least one character
        assert self._characters
