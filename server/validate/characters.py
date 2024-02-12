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

from typing import List

import sys
if r'../..' not in sys.path:
    sys.path.append(r'../..')

from server.exceptions import ServerError
from server.validate_assets import Validate


class ValidateCharacters(Validate):
    def validate_contents(self, contents, extra_parameters=None) -> List[str]:
        # Check characters contents is indeed a list of strings
        if not isinstance(contents, list):
            msg = (f'Expected the characters list to be a list, got a '
                   f'{type(contents).__name__}: {contents}.')
            raise ServerError.FileSyntaxError(msg)

        for (i, character) in enumerate(contents.copy()):
            if character is None:
                msg = (f'Expected all character names to be defined, but character {i} was not.')
                raise ServerError.FileSyntaxError(msg)
            if not isinstance(character, (str, float, int, bool, complex)):
                msg = (f'Expected all character names to be strings or numbers, but character '
                       f'{i}: {character} was not a string or number.')
                raise ServerError.FileSyntaxError(msg)

            # Otherwise, character i is valid. Cast it as string to deal with YAML doing
            # potential casting of its own
            contents[i] = str(character)

        return contents


if __name__ == '__main__':
    ValidateCharacters().read_sysargv_and_validate(default='characters.yaml')
