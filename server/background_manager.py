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
        self._backgrounds = []
        self._source_file = 'backgrounds.yaml'
        self._default_background = None

        self._prev_backgrounds = []
        self._prev_source_file = 'backgrounds.yaml'
        self._prev_default_background = None

    def get_backgrounds(self) -> List[str]:
        return self._backgrounds.copy()

    def get_source_file(self) -> str:
        return self._source_file

    def get_default_background(self) -> Union[str, None]:
        return self._default_background

    def set_default_background(self, background: Union[str, None]):
        if not self.is_background(background):
            raise BackgroundError.BackgroundNotFoundError

        self._default_background = background
        self._check_structure()

    def load_backgrounds_from_file(self, source_file: str) -> List[str]:
        backgrounds = ValidateBackgrounds().validate(f'config/{source_file}')
        output = self._load_backgrounds(backgrounds, f'config/{source_file}')
        self._check_structure()
        return output

    def _load_backgrounds(self, new_list: List[str], source_file: str) -> List[str]:
        self._prev_backgrounds = self._backgrounds.copy()
        self._prev_source_file = self._source_file
        self._prev_default_background = self._default_background

        lower = [name.lower() for name in new_list]
        self._backgrounds = lower
        self._source_file = source_file
        if not self.is_background(self._default_background):
            self._default_background = None

        return lower.copy()

    def is_background(self, background: Union[str, None]) -> bool:
        return background is None or background in self._backgrounds

    def restore_backgrounds(self):
        self._backgrounds = self._prev_backgrounds.copy()
        self._source_file = self._prev_source_file
        self._default_background = self._prev_default_background
        self._check_structure()

    def _check_structure(self):
        assert self.is_background(self._default_background)

        assert (
            self._prev_default_background is None
            or self._prev_default_background in self._prev_backgrounds
        )
