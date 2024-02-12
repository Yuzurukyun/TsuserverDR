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

# tbh idk what i should add here but this is custom by Yuzuru ig

import requests
import pathlib
import os


class Downloader:
    def __init__(self, _name: str, _type: str, _link: str):
        self.name = _name
        self.link = _link
        self.file_type = _type
        self.dirs = ("bg", "char", "music", "area")
        self.current_dir = os.getcwd()

    def dir_path(self, _type: str) -> str:
        dir_path_name = {
            "bg": "bg_lists",
            "char": "char_lists",
            "area": "area_lists",
            "music": "music_lists"
        }
        return str(pathlib.Path().joinpath("config").joinpath(
            dir_path_name[self.file_type.lower()]).joinpath(f"{self.name}.yaml"))

    def filter_string(self) -> str:
        new_link = self.link
        new_link = new_link.split("?")

        if len(new_link) > 1:
            new_link = new_link[0]
        else:
            new_link = self.link

        if not new_link.endswith("yaml"):
            return ""
        if "cdn.discordapp.com/attachments/" not in new_link:
            return ""

        return new_link

    def validate(self):
        if self.file_type.lower() not in self.dirs:
            return None
        if not self.filter_string():
            return None

        return True

    def download(self):
        if not self.validate():
            return None

        r = requests.get(self.filter_string())
        with open(self.dir_path(self.file_type.lower()), "wb") as file:
            file.write(r.content)

        return True
