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

class EvidenceList:
    class Evidence:
        def __init__(self, name, desc, image, pos):
            self.name = name
            self.desc = desc
            self.image = image
            self.public = False
            self.pos = pos

        def set_name(self, name):
            self.name = name

        def set_desc(self, desc):
            self.desc = desc

        def set_image(self, image):
            self.image = image

        def to_string(self):
            sequence = (self.name, self.desc, self.image)
            return '&'.join(sequence)

    def __init__(self):
        self.evidences = []
        self.poses = {'def': ['def', 'hld'], 'pro': ['pro', 'hlp'], 'wit': ['wit'], 'hlp': ['hlp', 'pro'], 'hld': [
            'hld', 'def'], 'jud': ['jud'], 'all': ['hlp', 'hld', 'wit', 'jud', 'pro', 'def', ''], 'pos': []}

    def login(self, client):
        if client.area.evidence_mod == 'FFA':
            pass
        if client.area.evidence_mod == 'Mods':
            if not client.is_cm:
                return False
        if client.area.evidence_mod == 'CM':
            if not client.is_cm and not client.is_mod:
                return False
        if client.area.evidence_mod == 'HiddenCM':
            if not client.is_cm and not client.is_mod:
                return False
        return True

    def correct_format(self, client, desc):
        if client.area.evidence_mod != 'HiddenCM':
            return True
        else:
            # correct format: <owner = pos>\ndesc
            if desc[:9] == '<owner = ' and desc[9:12] in self.poses and desc[12:14] == '>\n':
                return True
            return False

    def add_evidence(self, client, name, description, image, pos='all'):
        if self.login(client):
            if client.area.evidence_mod == 'HiddenCM':
                pos = 'pos'
            self.evidences.append(self.Evidence(name, description, image, pos))

    def evidence_swap(self, client, id1, id2):
        if self.login(client):
            self.evidences[id1], self.evidences[id2] = self.evidences[id2], self.evidences[id1]

    def create_evi_list(self, client):
        evi_list = []
        nums_list = [0]
        for i in range(len(self.evidences)):
            if client.area.evidence_mod == 'HiddenCM' and self.login(client):
                nums_list.append(i + 1)
                evi = self.evidences[i]
                evi_list.append(self.Evidence(evi.name, '<owner = {}>\n{}'.format(
                    evi.pos, evi.desc), evi.image, evi.pos).to_string())
            elif client.pos in self.poses[self.evidences[i].pos]:
                nums_list.append(i + 1)
                evi_list.append(self.evidences[i].to_string())
        return nums_list, evi_list

    def del_evidence(self, client, evi_id):
        if self.login(client):
            self.evidences.pop(evi_id)

    def edit_evidence(self, client, evi_id, arg):
        if self.login(client):
            if client.area.evidence_mod == 'HiddenCM' and self.correct_format(client, arg[1]):
                self.evidences[evi_id] = self.Evidence(arg[0], arg[1][14:], arg[2], arg[1][9:12])
                return
            if client.area.evidence_mod == 'HiddenCM':
                client.send_ooc('You entered a wrong pos.')
                return
            self.evidences[evi_id] = self.Evidence(arg[0], arg[1], arg[2], arg[3])
