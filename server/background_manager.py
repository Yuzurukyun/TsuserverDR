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
        self._source_file = 'config/backgrounds.yaml'
        self._default_background = None

    @property
    def backgrounds(self) -> List[str]:
        return self._backgrounds.copy()

    @property
    def source_file(self) -> str:
        return self._source_file

    @property
    def default_background(self) -> Union[str, None]:
        return self._default_background

    @property.setter
    def default_background(self, background: Union[str, None]):
        if not self.is_background(background):
            raise BackgroundError.BackgroundNotFoundError

        self._default_background = background
        self._check_structure()

    def load_backgrounds(self, new_list: List[str]) -> List[str]:
        output = self._load_backgrounds(new_list, 'config/backgrounds.yaml')
        self._check_structure()
        return output

    def load_backgrounds_from_file(self, source_file: str) -> List[str]:
        backgrounds = ValidateBackgrounds().validate(f'config/{source_file}')
        output = self._load_backgrounds(backgrounds, f'config/{source_file}')
        self._check_structure()
        return output

    def _load_backgrounds(self, new_list: List[str], source_file: str) -> List[str]:
        self._backgrounds = new_list.copy()
        self._source_file = source_file
        if not self.is_background(self.default_background):
            self.default_background = None

        return new_list.copy()

    def is_background(self, background: Union[str, None]) -> bool:
        return background is None or background in self._backgrounds

    def _check_structure(self):
        assert self.is_background(self.default_background)
