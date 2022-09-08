from __future__ import annotations

import typing

from typing import List, Union

from server.exceptions import BackgroundError
from server.validate.backgrounds import ValidateBackgrounds

if typing.TYPE_CHECKING:
    from server.tsuserver import TsuserverDR

class BackgroundManager:
    def __init__(self, server: TsuserverDR):
        self._server = server
        self._backgrounds = ['default']
        self._source_file = 'backgrounds.yaml'
        self._default_background = self._backgrounds[0]

    def get_backgrounds(self) -> List[str]:
        return self._backgrounds.copy()

    def get_source_file(self) -> str:
        return self._source_file

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

    def load_backgrounds_from_file(self, source_file: str) -> List[str]:
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

    def _load_backgrounds(self, new_list: List[str], source_file: str) -> List[str]:
        lower = [name.lower() for name in new_list]
        self._backgrounds = lower
        self._source_file = source_file
        if not self.is_background(self._default_background):
            self._default_background = lower[0]

        return lower.copy()

    def is_background(self, background: str) -> bool:
        return background.lower() in self._backgrounds

    def _check_structure(self):
        # At least one background
        assert self._backgrounds

        # The default background is actually a background
        assert self.is_background(self._default_background)
