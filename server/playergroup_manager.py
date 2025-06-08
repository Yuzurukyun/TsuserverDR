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

"""
Module that contains the PlayerGroupManager class and the _PlayerGroup subclass.

"""

from __future__ import annotations

import random
import typing

from typing import Callable, Dict, Tuple, Type, Union, Set

from server.exceptions import PlayerGroupError

if typing.TYPE_CHECKING:
    from server.client_manager import ClientManager
    from server.tsuserver import TsuserverDR


class _PlayerGroup:
    """
    A mutable data type for player groups.

    Player groups are groups of users (called players) with an ID, where some players
    (possibly none) are leaders.

    Each player group may have a player limit (beyond which no new players may be added), may
    require that it never loses all its players as soon as it gets its first one (or else it
    is automatically deleted) and may require that if it has at least one player, then that
    there is at least one leader (or else one is automatically chosen between all players).
    Each of these player groups may also impose a concurrent player membership limit, so that every
    user that is a player of it is at most a player of that many player groups managed by this
    player group's manager.

    Once a player group is scheduled for deletion, its manager will no longer recognize it as a
    player group it is managing (it will unmanage it), so no further mutator public method calls
    would be allowed on the player group.

    Attributes
    ----------
    server : TsuserverDR
        Server the player group belongs to.
    manager : PlayerGroupManager
        Manager for this player group.

    """

    # (Private) Attributes
    # --------------------
    # _playergroup_id : str
    #     Identifier for this player group.
    # _player_limit : Union[int, None].
    #     If an int, it is the maximum number of players the player group supports. If None, the
    #     player group may have an arbitrary number of players.
    # _player_concurrent_limit : Union[int, None].
    #     If an int, it is the maximum number of player groups managed by the same manager as
    #     this player group that any player part of this player group may belong to, including this
    #     player group. If None, no such restriction is considered.
    # _players : Set[ClientManager.Client]
    #     Players of the player group.
    # _leaders : Set[ClientManager.Client]
    #     Leaders of the player group.
    # _invitations : Set[ClientManager.Client]
    #     Users invited to (but not part of of) the player group.
    # _require_players : bool
    #     If True, the player group will be destroyed automatically if it loses all its players (but
    #     it may start with no players).
    # _require_leaders : bool
    #     If True and the player group has no leaders but at least one player, it will randomly
    #     choose one player to be a leader.
    # _ever_had_players : bool
    #    If True, at least once has a player been added successfully the player group;
    #    otherwise False.
    # _unmanaged : bool
    #     If True, the manager this player group claims is its manager no longer recognizes it is
    #     managing this player group, thus no further mutator public method calls would be allowed.

    # Invariants
    # ----------
    # 1. Each player is a client of the server.
    # 2. `self._unmanaged` is False if and only if `self` is in
    #    `self.manager.get_managees()`.
    # 3. If `self._unmanaged`, then `self._players`, `self._invitations`, `self._leaders` are
    #    all empty sets.
    # 4. For every player `player` in `self._players`, `self.manager.get_managees_of_user()[player]`
    #    exists and contains `self`.
    # 5. If `self._player_limit` is not None, then `len(self._players) <= player_limit`.
    # 6. For every player in `self._leaders`, they also belong in `self._players`.
    # 7. If `len(self._players) >= 1`, then `self._ever_had_players is True`.
    # 8. If `self._require_players` is True, then `len(self._players) >= 1 or self._unmanaged`.
    # 9. If `self._require_leaders` is True and `len(self._players) >= 1`, then
    #    `len(self._leaders) >= 1`.
    # 10. `self._invitations` and `self._players` are disjoint sets.
    # 11. If `self._require_invitations` is False, then `self._invitations` is the empty set.

    def __init__(
        self,
        server: TsuserverDR,
        manager: PlayerGroupManager,
        playergroup_id: str,
        player_limit: Union[int, None] = None,
        player_concurrent_limit: Union[int, None] = 1,
        require_invitations: bool = False,
        require_players: bool = True,
        require_leaders: bool = True,
    ):
        """
        Create a new player group. A player group should not be created outside some manager code.

        Parameters
        ----------
        server : TsuserverDR
            Server the player group belongs to.
        manager : PlayerGroupManager
            Manager for this player group.
        playergroup_id : str
            Identifier of the player group.
        player_limit : Union[int, None], optional
            If an int, it is the maximum number of players the player group supports. If None,
            it indicates the player group has no player limit. Defaults to None.
        player_concurrent_limit : Union[int, None], optional
            If an int, it is the maximum number of player groups managed by `manager` that any
            player of this player group may belong to, including this player group. If None, it
            indicates that this player group does not care about how many other player groups
            managed by `manager` each of its players belongs to. Defaults to 1 (a player may not be
            in another player group managed by `manager` while in this player group).
        require_invitation : bool, optional
            If True, players can only be added to the player group if they were previously invited.
            If False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the player group has no players left, the player group will
            automatically be deleted. If False, no such automatic deletion will happen.
            Defaults to True.
        require_leaders : bool, optional
            If True, if at any point the player group has no leaders left, the player group will
            choose a leader among any remaining players left; if no players are left, the next
            player added will be made leader. If False, no such automatic assignment will happen.
            Defaults to True.

        """

        self.server = server
        self.manager = manager
        self._playergroup_id = playergroup_id
        self._player_limit = player_limit
        self._player_concurrent_limit = player_concurrent_limit
        self._require_invitations = require_invitations
        self._require_players = require_players
        self._require_leaders = require_leaders

        self._name = playergroup_id
        self._players = set()
        self._leaders = set()
        self._invitations = set()
        self._ever_had_players = False
        self._unmanaged = False

    def get_id(self) -> str:
        """
        Return the ID of this player group.

        Returns
        -------
        str
            The ID.

        """

        return self._playergroup_id

    def get_numerical_id(self) -> int:
        """
        Return the numerical portion of the ID of this player group.

        Returns
        -------
        int
            Numerical portion of the ID.
        """

        digits = [x for x in self._playergroup_id if x.isdigit()]
        number = ''.join(digits)
        return int(number)

    def get_type_name(self) -> str:
        """
        Return the type name of the player group. Names are fully lowercase.
        Implementations of the class should replace this with a human readable name of the player
        group.

        Returns
        -------
        str
            Type name of the player group.

        """

        return "player group"

    def get_name(self) -> str:
        """
        Get the name of the player group.

        Returns
        -------
        str
            Name.
        """

        return self._name

    def set_name(self, name: str):
        """
        Set the name of the player group.

        Parameters
        ----------
        name : str
            Name.
        """

        self.unchecked_set_name(name)
        self.manager._check_structure()

    def unchecked_set_name(self, name: str):
        """
        Set the name of the player group.

        This method does not assert structural integrity.

        Parameters
        ----------
        name : str
            Name.
        """

        self._name = name

    def get_player_limit(self) -> Union[int, None]:
        """
        Return the player membership limit of this player group.

        Returns
        -------
        Union[int, None]
            The player membership limit.

        """

        return self._player_concurrent_limit

    def get_player_concurrent_limit(self) -> Union[int, None]:
        """
        Return the concurrent player membership limit of this player group.

        Returns
        -------
        Union[int, None]
            The concurrent player membership limit.

        """

        return self._player_concurrent_limit

    def get_players(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
    ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of players of this player group that satisfy a
        condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all players returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) players of this player group.

        """

        if cond is None:
            def cond(c): return True

        filtered_players = {player for player in self._players if cond(player)}
        return filtered_players

    def is_player(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is a player of the player group.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Returns
        -------
        bool
            True if the user is a player, False otherwise.

        """

        return user in self._players

    def add_player(self, user: ClientManager.Client):
        """
        Make a user a player of the player group. By default this player will not be a
        leader, unless the player group has no leaders and the player group requires a leader.

        Parameters
        ----------
        user : ClientManager.Client
            User to add to the player group.

        Raises
        ------
        PlayerGroupError.GroupIsUnmanagedError:
            If the player group was scheduled for deletion and thus does not accept any mutator
            public method calls.
        PlayerGroupError.UserNotInvitedError
            If the player group requires players be invited to be added and the user is not invited.
        PlayerGroupError.UserAlreadyPlayerError
            If the user to add is already a user of the player group.
        PlayerGroupError.UserInAnotherGroupError
            If the player is already in another player group managed by this manager.
        PlayerGroupError.UserHitGroupConcurrentLimitError
            If the player has reached the concurrent player membership of any of the player groups
            managed by the manager of this player group, or by virtue of joining this player group
            they would violate this player group's concurrent player membership limit.
        PlayerGroupError.GroupIsFullError
            If the player group reached its player limit.

        """

        self.unchecked_add_player(user)
        self.manager._check_structure()

    def unchecked_add_player(self, user: ClientManager.Client):
        """
        Make a user a player of the player group. By default this player will not be a
        leader, unless the player group has no leaders and the player group requires a leader.

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to add to the player group.

        Raises
        ------
        PlayerGroupError.GroupIsUnmanagedError:
            If the player group was scheduled for deletion and thus does not accept any mutator
            public method calls.
        PlayerGroupError.UserNotInvitedError
            If the player group requires players be invited to be added and the user is not invited.
        PlayerGroupError.UserAlreadyPlayerError
            If the user to add is already a user of the player group.
        PlayerGroupError.UserInAnotherGroupError
            If the player is already in another player group managed by this manager.
        PlayerGroupError.UserHitGroupConcurrentLimitError
            If the player has reached the concurrent player membership of any of the player groups
            managed by the manager of this player group, or by virtue of joining this player group
            they would violate this player group's concurrent player membership limit.
        PlayerGroupError.GroupIsFullError
            If the player group reached its player limit.

        """

        if self._unmanaged:
            raise PlayerGroupError.GroupIsUnmanagedError
        if self._require_invitations and user not in self._invitations:
            raise PlayerGroupError.UserNotInvitedError
        if user in self._players:
            raise PlayerGroupError.UserAlreadyPlayerError
        if self._player_limit is not None and len(self._players) >= self._player_limit:
            raise PlayerGroupError.GroupIsFullError
        if self.manager.find_player_concurrent_limiting_managee(user):
            raise PlayerGroupError.UserHitGroupConcurrentLimitError
        groups_of_user = self.manager.get_managees_of_user(user)
        if len(groups_of_user) >= self._player_concurrent_limit:
            raise PlayerGroupError.UserHitGroupConcurrentLimitError

        self._ever_had_players = True
        self._players.add(user)

        if self._require_invitations:
            self._invitations.remove(user)

        self._choose_leader_if_needed()

    def remove_player(self, user: ClientManager.Client):
        """
        Make a user be no longer a player of this player group.

        If the player group required that there it always had players and by calling this method the
        group had no more players, the player group will automatically be scheduled for deletion.

        Parameters
        ----------
        user : ClientManager.Client
            User to remove.

        Raises
        ------
        PlayerGroupError.GroupIsUnmanagedError:
            If the player group was scheduled for deletion and thus does not accept any mutator
            public method calls.
        PlayerGroupError.UserNotPlayerError
            If the user to remove is already not a player of this player group.

        """

        self.unchecked_remove_player(user)
        self.manager._check_structure()

    def unchecked_remove_player(self, user: ClientManager.Client):
        """
        Make a user be no longer a player of this player group.

        If the player group required that there it always had players and by calling this method the
        group had no more players, the player group will automatically be scheduled for deletion.

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to remove.

        Raises
        ------
        PlayerGroupError.GroupIsUnmanagedError:
            If the player group was scheduled for deletion and thus does not accept any mutator
            public method calls.
        PlayerGroupError.UserNotPlayerError
            If the user to remove is already not a player of this player group.

        """

        if self._unmanaged:
            raise PlayerGroupError.GroupIsUnmanagedError
        if user not in self._players:
            raise PlayerGroupError.UserNotPlayerError

        self._players.remove(user)
        self._leaders.discard(user)

        # Check updated leadership requirement
        self._choose_leader_if_needed()
        # Check if no players, and disassemble if appropriate
        if self._require_players and not self._players:
            self.manager.delete_managee(self)

    def requires_players(self) -> bool:
        """
        Return whether the player group requires players at all times.

        Returns
        -------
        bool
            Whether the player group requires players at all times.
        """

        return self._require_players

    def get_invitations(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
    ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of invited users of this player group that satisfy
        a condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all invited users returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) invited users of this player group.

        """

        if cond is None:
            def cond(c): return True

        filtered_invited = {invited for invited in self._invitations if cond(invited)}
        return filtered_invited

    def is_invited(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is invited to the player group.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Raises
        ------
        PlayerGroupError.UserAlreadyPlayerError
            If the user is a player of this player group.

        Returns
        -------
        bool
            True if the user is invited, False otherwise.

        """

        if user in self._players:
            raise PlayerGroupError.UserAlreadyPlayerError

        return user in self._invitations

    def add_invitation(self, user: ClientManager.Client):
        """
        Mark a user as invited to this player group.

        Parameters
        ----------
        user : ClientManager.Client
            User to invite to the player group.

        Raises
        ------
        PlayerGroupError.GroupIsUnmanagedError:
            If the player group was scheduled for deletion and thus does not accept any mutator
            public method calls.
        PlayerGroupError.GroupDoesNotTakeInvitationsError
            If the player group does not require users be invited to the player group.
        PlayerGroupError.UserAlreadyInvitedError
            If the player to invite is already invited to the player group.
        PlayerGroupError.UserAlreadyPlayerError
            If the player to invite is already a player of the player group.

        """

        self.unchecked_add_invitation(user)
        self.manager._check_structure()

    def unchecked_add_invitation(self, user: ClientManager.Client):
        """
        Mark a user as invited to this player group.

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to invite to the player group.

        Raises
        ------
        PlayerGroupError.GroupIsUnmanagedError:
            If the player group was scheduled for deletion and thus does not accept any mutator
            public method calls.
        PlayerGroupError.GroupDoesNotTakeInvitationsError
            If the player group does not require users be invited to the player group.
        PlayerGroupError.UserAlreadyInvitedError
            If the player to invite is already invited to the player group.
        PlayerGroupError.UserAlreadyPlayerError
            If the player to invite is already a player of the player group.

        """
        if self._unmanaged:
            raise PlayerGroupError.GroupIsUnmanagedError
        if not self._require_invitations:  # By design check if invitations are required first
            raise PlayerGroupError.GroupDoesNotTakeInvitationsError
        if user in self._invitations:
            raise PlayerGroupError.UserAlreadyInvitedError
        if user in self._players:
            raise PlayerGroupError.UserAlreadyPlayerError

        self._invitations.add(user)

    def remove_invitation(self, user: ClientManager.Client) -> bool:
        """
        Mark a user as no longer invited to this player group (uninvite).

        Parameters
        ----------
        user : ClientManager.Client
            User to uninvite.

        Raises
        ------
        PlayerGroupError.GroupIsUnmanagedError:
            If the player group was scheduled for deletion and thus does not accept any mutator
            public method calls.
        PlayerGroupError.GroupDoesNotTakeInvitationsError
            If the player group does not require users be invited to the player group.
        PlayerGroupError.UserNotInvitedError
            If the user to uninvite is already not invited to this player group.

        """

        self.unchecked_remove_invitation(user)
        self.manager._check_structure()

    def unchecked_remove_invitation(self, user: ClientManager.Client):
        """
        Mark a user as no longer invited to this player group (uninvite).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to uninvite.

        Raises
        ------
        PlayerGroupError.GroupIsUnmanagedError:
            If the player group was scheduled for deletion and thus does not accept any mutator
            public method calls.
        PlayerGroupError.GroupDoesNotTakeInvitationsError
            If the player group does not require users be invited to the player group.
        PlayerGroupError.UserNotInvitedError
            If the user to uninvite is already not invited to this player group.

        """

        if self._unmanaged:
            raise PlayerGroupError.GroupIsUnmanagedError
        if not self._require_invitations:  # By design check if invitations are required first
            raise PlayerGroupError.GroupDoesNotTakeInvitationsError
        if user not in self._invitations:
            raise PlayerGroupError.UserNotInvitedError

        self._invitations.remove(user)

    def requires_invitations(self) -> bool:
        """
        Return True if the player group requires players be invited before being allowed to join
        the player group, False otherwise.

        Returns
        -------
        bool
            True if the player group requires players be invited before being allowed to join
            the player group, False otherwise.
        """

        return self._require_invitations

    def get_leaders(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
    ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of leaders of this player group that satisfy a
        condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all leaders returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) leaders of this player group.

        """

        if cond is None:
            def cond(c): return True

        filtered_leaders = {leader for leader in self._leaders if cond(leader)}
        return filtered_leaders

    def get_regulars(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
    ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of players of this player group that are not leaders
        (regulars) and satisfy a condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all regulars returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) regulars of this player group.

        """

        if cond is None:
            def cond(c): return True

        regulars = {player for player in self._players if player not in self._leaders}
        filtered_regulars = {regular for regular in regulars if cond(regular)}
        return filtered_regulars

    def is_leader(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is a leader of the player group.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Raises
        ------
        PlayerGroupError.UserNotPlayerError
            If the player to test is not a player of this player group.

        Returns
        -------
        bool
            True if the player is a user, False otherwise.

        """

        if user not in self._players:
            raise PlayerGroupError.UserNotPlayerError

        return user in self._leaders

    def add_leader(self, user: ClientManager.Client):
        """
        Set a user as leader of this player group (promote to leader).

        Parameters
        ----------
        user : ClientManager.Client
            Player to promote to leader.

        Raises
        ------
        PlayerGroupError.GroupIsUnmanagedError:
            If the player group was scheduled for deletion and thus does not accept any mutator
            public method calls.
        PlayerGroupError.UserNotPlayerError
            If the player to promote is not a player of this player group.
        PlayerGroupError.UserAlreadyLeaderError
            If the player to promote is already a leader of this player group.

        """

        self.unchecked_add_leader(user)
        self.manager._check_structure()

    def unchecked_add_leader(self, user: ClientManager.Client):
        """
        Set a user as leader of this player group (promote to leader).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            Player to promote to leader.

        Raises
        ------
        PlayerGroupError.GroupIsUnmanagedError:
            If the player group was scheduled for deletion and thus does not accept any mutator
            public method calls.
        PlayerGroupError.UserNotPlayerError
            If the player to promote is not a player of this player group.
        PlayerGroupError.UserAlreadyLeaderError
            If the player to promote is already a leader of this player group.

        """

        if self._unmanaged:
            raise PlayerGroupError.GroupIsUnmanagedError
        if user not in self._players:
            raise PlayerGroupError.UserNotPlayerError
        if user in self._leaders:
            raise PlayerGroupError.UserAlreadyLeaderError

        self._leaders.add(user)

    def remove_leader(self, user: ClientManager.Client):
        """
        Make a user no longer leader of this player group (demote).

        Parameters
        ----------
        user : ClientManager.Client
            User to demote.

        Raises
        ------
        PlayerGroupError.GroupIsUnmanagedError:
            If the player group was scheduled for deletion and thus does not accept any mutator
            public method calls.
        PlayerGroupError.UserNotPlayerError
            If the player to demote is not a player of this player group.
        PlayerGroupError.UserNotLeaderError
            If the player to demote is already not a leader of this player group.

        """

        self.unchecked_remove_leader(user)
        self.manager._check_structure()

    def unchecked_remove_leader(self, user: ClientManager.Client):
        """
        Make a user no longer leader of this player group (demote).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to demote.

        Raises
        ------
        PlayerGroupError.GroupIsUnmanagedError:
            If the player group was scheduled for deletion and thus does not accept any mutator
            public method calls.
        PlayerGroupError.UserNotPlayerError
            If the player to demote is not a player of this player group.
        PlayerGroupError.UserNotLeaderError
            If the player to demote is already not a leader of this player group.

        """

        if self._unmanaged:
            raise PlayerGroupError.GroupIsUnmanagedError
        if user not in self._players:
            raise PlayerGroupError.UserNotPlayerError
        if user not in self._leaders:
            raise PlayerGroupError.UserNotLeaderError

        self._leaders.remove(user)
        # Check leadership requirement
        self._choose_leader_if_needed()

    def requires_leaders(self) -> bool:
        """
        Return whether the player group requires leaders at all times.

        Returns
        -------
        bool
            Whether the player group requires leaders at all times.
        """

        return self._require_leaders

    def is_unmanaged(self) -> bool:
        """
        Return True if this player group is unmanaged, False otherwise.

        Returns
        -------
        bool
            True if unmanaged, False otherwise.

        """

        return self._unmanaged

    def has_ever_had_players(self) -> bool:
        """
        Return True if a player has ever been added to this player group, False otherwise.

        Returns
        -------
        bool
            True if the player group has ever had a player added, False otherwise.

        """

        return self._ever_had_players

    def destroy(self):
        """
        Mark this player group as destroyed and notify its manager so that it is deleted.
        If the player group is already destroyed, this function does nothing.

        This method is reentrant (it will do nothing though).

        Returns
        -------
        None.

        """

        self.unchecked_destroy()
        self.manager._check_structure()
        self._check_structure()  # Manager will not check this otherwise.

    def unchecked_destroy(self):
        """
        Mark this player group as destroyed and notify its manager so that it is deleted.
        If the player group is already destroyed, this function does nothing.

        This method is reentrant (it will do nothing though).

        Returns
        -------
        None.

        """

        # Implementation detail: To make this safely reentrant and allow this code to be ran
        # multiple times, we do the following:
        # At the very beginning we check if self._unmanaged is True.
        # * If yes, we abort execution of this method.
        # * If no, we continue execution and mark self._unmanaged as True
        # Thus there cannot be more than one call of destroy that is not immediately aborted.

        if self._unmanaged:
            return
        self._unmanaged = True

        if self.manager.manages_managee(self):
            # If manager still recognizes, remove
            self.manager.unchecked_delete_managee(self)
            # Don't use errors because exceptions thrown may not be PlayerGroupError

        # While only clearing internal variables here means that structural integrity won't be
        # maintained in time for the manager's structural checks, as the manager will no longer
        # list this player group as a managee, no structural checks will be performed
        # on this object anymore by outside entities, so this code is safe.

        self._players = set()
        self._invitations = set()
        self._leaders = set()

    def _choose_leader_if_needed(self):
        """
        If the player group requires that the player group always have a leader if there is at least
        one player, one leader will randomly be chosen among all players. If this condition is
        already true, no new leaders are chosen.
        """

        if not self._require_leaders:
            return
        if self._leaders:
            return
        if not self._players:
            return

        new_leader = random.choice(list(self.get_players()))
        self.unchecked_add_leader(new_leader)

    def _check_structure(self):
        """
        Assert that all invariants specified in the class description are maintained.

        Parameters
        ----------
        do_earliest_ancestor_check : bool, optional
            If True, the structural checks will only be performed if the instance is of type this
            class rather than some inherited class. If False, this pre-emptive check is ignored.
            Defaults to True.
        Raises
        ------
        AssertionError
            If any of the invariants are not maintained.

        """

        # 1.
        for player in self._players:
            if not self.server.is_client(player):
                print(f'For player group {self._playergroup_id}, expected that player {player} was a '
                      f'client of its server {self.server}, but found that was not the case. || {self}')

        # 2.
        assert self._unmanaged or self in self.manager.get_managees(), (
            f'For player group {self._playergroup_id} that is not unmanaged that also claims '
            f'that it is managed by manager {self.manager}, expected that it recognized that '
            f'it managed it, but found it did not. || {self}'
        )

        # 3.
        if self._unmanaged:
            assert not self._players, (
                f'For player group {self._playergroup_id} that is unmanaged, expected that it had '
                f'no players, but found it had these players: {self._players} || {self}'
            )

            assert not self._invitations, (
                f'For player group {self._playergroup_id} that is unmanaged, expected that it had '
                f'no invitations, but found it had these invitations: {self._invitations} '
                f'|| {self}')

            assert not self._leaders, (
                f'For player group {self._playergroup_id} that is unmanaged, expected that it had '
                f'no leaders, but found it had these leaders: {self._leaders} || {self}'
            )

        # 4.
        for player in self._players:
            assert (
                player in self.manager.get_users_in_some_managee()
                and self in self.manager.get_managees_of_user(player)
            ), (
                f'For player group {self._playergroup_id}, expected that its player {player} is '
                f'properly recognized in the player to player group mapping of the manager of '
                f'the player group {self.manager}, but found that was not the case. || {self}'
            )

        # 5.
        if self._player_limit is not None:
            assert len(self._players) <= self._player_limit, (
                f'For player group {self._playergroup_id}, expected that there were at most '
                f'{self._player_limit} players, but found it had {len(self._players)} players. '
                f'|| {self}'
            )

        # 6.
        for leader in self._leaders:
            assert leader in self._players, (
                f'For player group {self._playergroup_id}, expected that leader {leader} was a '
                f'player of it too, but found it was not. || {self}'
            )

        # 7.
        if self._players:
            assert self._ever_had_players, (
                f'For player group {self._playergroup_id}, expected it knew it ever had some '
                f'players, but found it did not. || {self}'
            )

        # 8.
        if self._require_players and self._ever_had_players:
            assert self._players or self._unmanaged, (
                f'For player group {self._playergroup_id}, expected that it was scheduled for '
                f'deletion after losing all its players, but found it was not. || {self}'
            )

        # 9.
        if self._require_leaders:
            assert not self._players or self._leaders, (
                f'For player group {self._playergroup_id} with some players, expected that '
                f'there was a leader, but found it had none. || {self}'
            )

        # 10.
        players_also_invited = self._players.intersection(self._invitations)
        assert not players_also_invited, (
            f'For player group {self._playergroup_id}, expected that all users in the '
            f'invitation list of the player group were not players, but found the following '
            f'players who were in the invitation list: {players_also_invited}. || {self}'
        )

        # 11.
        assert self._require_invitations or not self._invitations, (
            f'For player group {self._playergroup_id} that does not require invitations, '
            f'expected that no player was invited to the player group, but found the following '
            f'users who were in the invitation list: {self._invitations}. || {self}'
        )

    def __repr__(self) -> str:
        """
        Return a representation of this player group.

        Returns
        -------
        str
            Printable representation.

        """

        return (f'PlayerGroup(server, {self.get_id()}, "{self.get_id()}", '
                f'player_limit={self.get_player_limit()}, '
                f'player_concurrent_limit={self.get_player_concurrent_limit()}, '
                f'require_players={self.requires_players()}, '
                f'require_invitations={self.requires_invitations()}, '
                f'require_leaders={self.requires_leaders()}, '
                f'|| '
                f'players={self.get_players()}, '
                f'invitations={self.get_invitations()}, '
                f'leaders={self.get_leaders()}, '
                f'unmanaged={self.is_unmanaged()}), '
                f')')


class PlayerGroupManager:
    """
    A mutable data type for a manager for player groups.

    Each player group is managed by a player group manager. Only this manager is allowed to execute
    any public methods on them. Each manager may also have a player group limit (beyond which it
    will not manage any more player groups).

    Contains the player group object definition, methods for creating and deleting them, as well as
    some observer methods.

    Attributes
    ----------
    server : TsuserverDR
        Server the player group manager belongs to.

    """

    # (Private) Attributes
    # --------------------
    # _managee_limit : Union[int, None]
    #     If an int, it is the maximum number of player groups this manager supports. If None, the
    #     manager may manage an arbitrary number of player groups.
    # _default_managee_type : _PlayerGroup
    #     The type of player group this player group manager will create by default when ordered
    #     to create a new one.
    # _user_to_managees : dict of ClientManager.Client to set of _PlayerGroup
    #     Mapping of users to the player groups managed by this manager they belong to.
    # _id_to_managee : dict of str to _PlayerGroup
    #     Mapping of player group IDs to player groups that this manager manages.

    # Invariants
    # ----------
    # 1. If `self._managee_limit` is an int, then `len(self._id_to_managee) <=
    #    self._managee_limit`.
    # 2. For every player group `(playergroup_id, _PlayerGroup)` in `self._id_to_managee.items()`:
    #     a. `playergroup._playergroup_id == playergroup_id`.
    #     b. `playergroup.is_unmanaged()` is False.
    # 3. For all pairs of distinct player groups `group1` and `group2` in
    #    `self._id_to_managee.values()`:
    #     a. `group1._playergroup_id != group2._playergroup_id`.
    # 4. For every player and player groups pair (`player`, `playergroups`) in
    #    `self.get_managees_of_user().items()`:
    #     a. For every player group `playergroup` in `playergroups`:
    #           1. `playergroup` has no player concurrent membership limit, or it is at least the
    #               length of `playergroups`.
    # 5. Each player group it manages also satisfies its structural invariants.

    def __init__(
        self,
        server: TsuserverDR,
        managee_limit: Union[int, None] = None,
        default_managee_type: Type[_PlayerGroup] = None,
    ):
        """
        Create a player group manager object.

        Parameters
        ----------
        server : TsuserverDR
            The server this player group manager belongs to.
        managee_limit : int, optional
            The maximum number of player groups this manager can handle. Defaults to None (no
            limit).
        default_managee_type : Type[_PlayerGroup], optional
            The default type of player group this manager will create. Defaults to None (and then
            converted to _PlayerGroup).

        """

        self._id = hex(id(self))

        if default_managee_type is None:
            default_managee_type = _PlayerGroup

        self.server = server
        self._default_group_type = default_managee_type
        self._group_limit = managee_limit
        self._id_to_group: Dict[str, _PlayerGroup] = dict()

    def get_managee_type(self) -> Type[_PlayerGroup]:
        """
        Return the type of the player group that will be constructed by default with a call of
        `new_managee`.

        Returns
        -------
        Type[_PlayerGroup]
            Type of the player group.
        """

        return self._default_group_type

    def new_managee(
        self,
        managee_type: Type[_PlayerGroup] = None,
        creator: Union[ClientManager.Client, None] = None,
        player_limit: Union[int, None] = None,
        player_concurrent_limit: Union[int, None] = 1,
        require_invitations: bool = False,
        require_players: bool = True,
        require_leaders: bool = True,
        **kwargs,
    ) -> _PlayerGroup:
        """
        Create a new player group managed by this manager.

        Parameters
        ----------
        managee_type : Type[_PlayerGroup], optional
            Class of player group that will be produced. Defaults to None (and converted to the
            default player group created by this player group manager).
        creator : Union[ClientManager.Client, None], optional
            The player who created this player group. If set, they will also be added to the player
            group. Defaults to None.
        player_limit : Union[int, None], optional
            If an int, it is the maximum number of players the player group supports. If None, it
            indicates the player group has no player limit. Defaults to None.
        player_concurrent_limit : Union[int, None], optional
            If an int, it is the maximum number of player groups managed by `self` that any player
            of this player group to create may belong to, including this player group to create. If
            None, it indicates that this player group does not care about how many other player
            groups managed by `self` each of its players belongs to. Defaults to 1 (a player may
            not be in another player group managed by `self` while in this new player group).
        require_invitations : bool, optional
            If True, users can only be added to the player group if they were previously invited. If
            False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the player group loses all its players, the player group will
            automatically be deleted. If False, no such automatic deletion will happen. Defaults to
            True.
        require_leaders : bool, optional
            If True, if at any point the player group has no leaders left, the player group will
            choose a leader among any remaining players left; if no players are left, the next
            player added will be made leader. If False, no such automatic assignment will happen.
            Defaults to True.
        **kwargs : Any
            Additional arguments to consider when producing the player group.

        Returns
        -------
        _PlayerGroup
            The created player group.

        Raises
        ------
        PlayerGroupError.ManagerTooManyGroupsError
            If the manager is already managing its maximum number of player groups.
        PlayerGroupError.UserHitGroupConcurrentLimitError.
            If `creator` has reached the concurrent player membership limit of any of the player
            groups it belongs to managed by this manager, or by virtue of joining this player group
            the creator they would violate this player group's concurrent player membership limit.

        """

        playergroup = self.unchecked_new_managee(
            managee_type=managee_type,
            creator=creator,
            player_limit=player_limit,
            player_concurrent_limit=player_concurrent_limit,
            require_invitations=require_invitations,
            require_players=require_players,
            require_leaders=require_leaders,
            **kwargs,
        )
        self._check_structure()
        return playergroup

    def unchecked_new_managee(
        self,
        managee_type: Type[_PlayerGroup] = None,
        creator: Union[ClientManager.Client, None] = None,
        player_limit: Union[int, None] = None,
        player_concurrent_limit: Union[int, None] = 1,
        require_invitations: bool = False,
        require_players: bool = True,
        require_leaders: bool = True,
        **kwargs,
    ) -> _PlayerGroup:
        """
        Create a new player group managed by this manager.

        Parameters
        ----------
        managee_type : Type[_PlayerGroup], optional
            Class of player group that will be produced. Defaults to None (and converted to the
            default player group created by this player group manager).
        creator : Union[ClientManager.Client, None], optional
            The player who created this player group. If set, they will also be added to the player
            group. Defaults to None.
        player_limit : Union[int, None], optional
            If an int, it is the maximum number of players the player group supports. If None, it
            indicates the player group has no player limit. Defaults to None.
        player_concurrent_limit : Union[int, None], optional
            If an int, it is the maximum number of player groups managed by `self` that any player
            of this player group to create may belong to, including this player group to create. If
            None, it indicates that this player group does not care about how many other player
            groups managed by `self` each of its players belongs to. Defaults to 1 (a player may
            not be in another player group managed by `self` while in this new player group).
        require_invitations : bool, optional
            If True, users can only be added to the player group if they were previously invited. If
            False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the player group loses all its players, the player group will
            automatically be deleted. If False, no such automatic deletion will happen. Defaults to
            True.
        require_leaders : bool, optional
            If True, if at any point the player group has no leaders left, the player group will
            choose a leader among any remaining players left; if no players are left, the next
            player added will be made leader. If False, no such automatic assignment will happen.
            Defaults to True.
        **kwargs : Any
            Additional arguments to consider when producing the player group.

        Returns
        -------
        _PlayerGroup
            The created player group.

        Raises
        ------
        PlayerGroupError.ManagerTooManyGroupsError
            If the manager is already managing its maximum number of player groups.
        PlayerGroupError.UserHitGroupConcurrentLimitError.
            If `creator` has reached the concurrent player membership limit of any of the player
            groups it belongs to managed by this manager, or by virtue of joining this player group
            the creator they would violate this player group's concurrent player membership limit.

        """

        if managee_type is None:
            managee_type = self.get_managee_type()

        if not self.is_managee_creatable():
            raise PlayerGroupError.ManagerTooManyGroupsError
        if creator:
            # Check if adding the creator to this new player group would cause any concurrent
            # membership limits being reached.
            if self.find_player_concurrent_limiting_managee(creator):
                raise PlayerGroupError.UserHitGroupConcurrentLimitError
            groups_of_user = self.get_managees_of_user(creator)
            if groups_of_user is not None and len(groups_of_user) >= player_concurrent_limit:
                raise PlayerGroupError.UserHitGroupConcurrentLimitError

        group_id = self.get_available_managee_id()

        # At this point, we are committed to creating this player group.
        playergroup = managee_type(
            self.server,
            self,
            group_id,
            player_limit=player_limit,
            player_concurrent_limit=player_concurrent_limit,
            require_invitations=require_invitations,
            require_players=require_players,
            require_leaders=require_leaders,
            **kwargs,
        )

        self._id_to_group[group_id] = playergroup

        try:
            if creator:
                playergroup.unchecked_add_player(creator)
        except PlayerGroupError as ex:
            # Discard player group
            self.unchecked_delete_managee(playergroup)
            raise ex

        return playergroup

    def delete_managee(self, managee: _PlayerGroup) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a player group managed by this manager, so all its players no longer belong to this
        player group.

        Parameters
        ----------
        managee : _PlayerGroup
            The player group to delete.

        Returns
        -------
        Tuple[str, Set[ClientManager.Client]]
            The ID and players of the player group that was deleted.

        Raises
        ------
        PlayerGroupError.ManagerDoesNotManageGroupError
            If the manager does not manage the target player group.

        """

        playergroup_id, former_players = self.unchecked_delete_managee(managee)
        self._check_structure()
        return playergroup_id, former_players

    def unchecked_delete_managee(
        self,
        managee: _PlayerGroup
    ) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a player group managed by this manager, so all its players no longer belong to this
        player group.

        Parameters
        ----------
        managee : _PlayerGroup
            The player group to delete.

        Returns
        -------
        Tuple[str, Set[ClientManager.Client]]
            The ID and players of the player group that was deleted.

        Raises
        ------
        PlayerGroupError.ManagerDoesNotManageGroupError
            If the manager does not manage the target player group.

        """

        if not self.manages_managee(managee):
            raise PlayerGroupError.ManagerDoesNotManageGroupError

        playergroup_id = managee.get_id()
        self._id_to_group.pop(playergroup_id)

        former_players = managee.get_players()

        managee.unchecked_destroy()

        return playergroup_id, former_players

    def manages_managee(self, managee: _PlayerGroup) -> bool:
        """
        Return True if the player group is managed by this manager, False otherwise.

        Parameters
        ----------
        managee : _PlayerGroup
            The player group to check.

        Returns
        -------
        bool
            True if the manager manages this player group, False otherwise.

        """

        return managee in self._id_to_group.values()

    def get_managees(self) -> Set[_PlayerGroup]:
        """
        Return (a shallow copy of) the player groups this manager manages.

        Returns
        -------
        Set[_PlayerGroup]
            Player groups this manager manages.

        """

        return set(self._id_to_group.values())

    def get_managee_by_id(self, managee_id: str) -> _PlayerGroup:
        """
        If `managee_id` is the ID of a player group managed by this manager, return the player
        group.

        Parameters
        ----------
        managee_id : str
            ID of the player group this manager manages.

        Returns
        -------
        _PlayerGroup
            The player group with that ID.

        Raises
        ------
        PlayerGroupError.ManagerInvalidGroupIDError:
            If `managee_id` is not the ID of a player group this manager manages.

        """

        try:
            return self._id_to_group[managee_id]
        except KeyError:
            raise PlayerGroupError.ManagerInvalidGroupIDError

    def get_managee_by_numerical_id(self, managee_numerical_id: Union[str, int]) -> _PlayerGroup:
        """
        If `managee_numerical_id` is the numerical ID of a player group managed by this manager,
        return the player group.

        Parameters
        ----------
        managee_numerical_id : Union[str, int]
            Numerical ID of the player group this manager manages.

        Returns
        -------
        _PlayerGroup
            The player group with that ID.

        Raises
        ------
        PlayerGroupError.ManagerInvalidGroupIDError:
            If `managee_numerical_id` is not the numerical ID of a player group
            this manager manages.

        """

        try:
            managee_numerical_id = int(managee_numerical_id)
        except ValueError:
            raise PlayerGroupError.ManagerInvalidGroupIDError

        for group in self._id_to_group.values():
            if group.get_numerical_id() == managee_numerical_id:
                return group
        raise PlayerGroupError.ManagerInvalidGroupIDError

    def get_managee_limit(self) -> Union[int, None]:
        """
        Return the player group limit of this manager.

        Returns
        -------
        Union[int, None]
            Player group limit.

        """

        return self._group_limit

    def get_managee_ids(self) -> Set[str]:
        """
        Return (a shallow copy of) the IDs of all player groups managed by this manager.

        Returns
        -------
        Set[str]
            The IDs of all player groups this manager manages.

        """

        return set(self._id_to_group.keys())

    def get_managee_ids_to_managees(self) -> Dict[str, _PlayerGroup]:
        """
        Return a mapping of the IDs of all player groups managed by this manager to their associated
        player group.

        Returns
        -------
        Dict[str, _PlayerGroup]
            Mapping.
        """

        return self._id_to_group.copy()

    def get_managee_numerical_ids_to_managees(self) -> Dict[int, _PlayerGroup]:
        """
        Return a mapping of the numerical IDs of all player groups managed by this manager to their
        associated player group.

        Returns
        -------
        Dict[int, _PlayerGroup]
            Mapping.
        """

        temp = dict()
        for group in self._id_to_group.values():
            temp[group.get_numerical_id()] = group

        output = dict()
        for num_id in sorted(temp.keys()):
            output[num_id] = temp[num_id]

        return output

    def get_managees_of_user(self, user: ClientManager.Client) -> Set[_PlayerGroup]:
        """
        Return (a shallow copy of) the player groups managed by this manager user `user` is a
        player of. If the user is part of no such player group, an empty set is returned.

        Parameters
        ----------
        user : ClientManager.Client
            User whose player groups will be returned.

        Returns
        -------
        Set[_PlayerGroup]
            Player groups the player belongs to.

        """

        users_to_managees = self.get_player_to_managees_map()

        try:
            return users_to_managees[user].copy()
        except KeyError:
            return set()

    def get_player_to_managees_map(self) -> Dict[ClientManager.Client, Set[_PlayerGroup]]:
        """
        Return a mapping of the players part of any player group managed by this manager to the
        player groups managed by this manager such players belong to.

        Returns
        -------
        Dict[ClientManager.Client, Set[_PlayerGroup]]
            Mapping.
        """

        output = dict()
        for group in self._id_to_group.values():
            for player in group.get_players():
                if player not in output:
                    output[player] = set()
                output[player].add(group)

        return output

    def get_users_in_some_managee(self) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) all the users that are part of some player group managed by
        this manager.

        Returns
        -------
        Set[ClientManager.Client]
            Users in some managed player group.

        """

        return set(self.get_player_to_managees_map().keys())

    def is_managee_creatable(self) -> bool:
        """
        Return whether a new player group can currently be created without creating one.

        Returns
        -------
        bool
            True if a player group can be currently created, False otherwise.
        """

        limit = self.get_managee_limit()
        if limit is None:
            return True
        return len(self._id_to_group) < limit

    def get_available_managee_id(self) -> str:
        """
        Get a player group ID that no other player group managed by this manager has.

        Returns
        -------
        str
            A unique player group ID.

        Raises
        ------
        PlayerGroupError.ManagerTooManyGroupsError
            If the manager is already managing its maximum number of player groups.

        """

        group_number = 0
        limit = self.get_managee_limit()
        while limit is None or group_number < limit:
            new_managee_id = f'pg{group_number}'
            if new_managee_id not in self._id_to_group:
                return new_managee_id
            group_number += 1
        raise PlayerGroupError.ManagerTooManyGroupsError

    def get_id(self) -> str:
        """
        Return the ID of this manager. This ID is guaranteed to be unique among
        simultaneously existing Python objects.

        Returns
        -------
        str
            ID.

        """

        return self._id

    def find_player_concurrent_limiting_managee(
        self,
        user: ClientManager.Client
    ) -> Union[_PlayerGroup, None]:
        """
        For user `user`, find a player group `most_restrictive_group` managed by this manager such
        that, if `user` were to join another player group managed by this manager, they would
        violate `most_restrictive_group`'s concurrent player membership limit.
        If no such player group exists (or the player is not member of any player group managed by
        this manager), return None.
        If multiple such player groups exist, any one of them may be returned.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Returns
        -------
        Union[_PlayerGroup, None]
            Limiting player group as previously described if it exists, None otherwise.

        """

        groups = self.get_managees_of_user(user)
        if not groups:
            return None

        # We only care about groups that establish a concurrent player membership limit
        groups_with_limit = {group for group in groups
                             if group.get_player_concurrent_limit() is not None}
        if not groups_with_limit:
            return None

        # It just suffices to analyze the group with the smallest limit, because:
        # 1. If the player is member of at least as many groups as this group's limit, this group
        # is an example group that can be returned.
        # 2. Otherwise, no other groups exist due to the minimality condition.
        most_restrictive_group: _PlayerGroup = min(
            groups_with_limit,
            key=lambda group: group.get_player_concurrent_limit()
        )
        if len(groups) < most_restrictive_group.get_player_concurrent_limit():
            return None
        return most_restrictive_group

    def _check_structure(self):
        """
        Assert that all invariants specified in the class description are maintained.

        Raises
        ------
        AssertionError
            If any of the invariants are not maintained.

        """

        # 1.
        if self._group_limit is not None:
            assert len(self._id_to_group) <= self._group_limit, (
                f'For player group manager {self._id}, expected that it managed at most '
                f'{self._group_limit} player groups, but found it managed '
                f'{len(self._id_to_group)} player groups. || {self}'
            )

        # 2.
        for (playergroup_id, playergroup) in self._id_to_group.items():
            # 2a.
            assert playergroup.get_id() == playergroup_id, (
                f'For player group manager {self._id}, expected that player group {playergroup} '
                f'that appears in the ID to player group mapping has the same ID as in the '
                f'mapping, but found it did not. || {self}'
            )

            # 2b.
            assert not playergroup.is_unmanaged(), (
                f'For player group manager {self._id}, expected that managed player group '
                f'{playergroup} recognized that it was not unmanaged, but found it did.'
            )

        # 3.
        for playergroup1 in self._id_to_group.values():
            for playergroup2 in self._id_to_group.values():
                if playergroup1 == playergroup2:
                    continue

                # 3a.
                assert playergroup1.get_id() != playergroup2.get_id(), (
                    f'For player group manager {self._id}, expected that its two managed player '
                    f'groups {playergroup1}, {playergroup2} had unique player group IDs, but '
                    f'found they did not. || {self}'
                )

        # 4.
        user_to_groups = self.get_player_to_managees_map()
        for (user, playergroups) in user_to_groups.items():
            membership = len(playergroups)

            for group in playergroups:
                limit = group.get_player_concurrent_limit()

                if limit is None:
                    continue
                assert membership <= limit, (
                    f'For player group manager {self}, expected that user {user} in player '
                    f'group {group} belonged to at most the concurrent player membership limit '
                    f'of that player group of {limit} player group{"s" if limit != 1 else ""}, '
                    f'found they belonged to {membership} player '
                    f'group{"s" if membership != 1 else ""}. || {self}'
                )

        # Last.
        for playergroup in self._id_to_group.values():
            playergroup._check_structure()

    def __repr__(self):
        """
        Return a representation of this player group manager.

        Returns
        -------
        str
            Printable representation.

        """

        return (f"PlayerGroupManager(server, managee_limit={self.get_managee_limit()}, "
                f"default_managee_type={self.get_managee_type()}, "
                f"|| "
                f"_user_to_managees={self.get_player_to_managees_map()}, "
                f"_id_to_managee={self.get_managee_ids_to_managees()}, "
                f"id={self.get_id()}, "
                f')')


if __name__ == '__main__':
    import sys
    if r'..' not in sys.path:
        sys.path.append(r'..')
