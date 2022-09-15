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

"""
Module that contains the base game with areas class.
"""

from __future__ import annotations

import functools
import typing
from typing import Callable, Dict, Set, Any, Union

from server.exceptions import GameWithAreasError, GameError
from server.game_manager import _Game, GameManager

if typing.TYPE_CHECKING:
    # Avoid circular referencing
    from server.area_manager import AreaManager
    from server.client_manager import ClientManager
    from server.tsuserver import TsuserverDR


class _GameWithAreasTrivialInherited(_Game):
    """
    This class should not be instantiated.
    """

    def get_id(self) -> str:
        """
        Return the ID of this game with areas.

        Returns
        -------
        str
            The ID.

        """

        return super().get_id()

    def get_player_limit(self) -> Union[int, None]:
        """
        Return the player membership limit of this game with areas.

        Returns
        -------
        Union[int, None]
            The player membership limit.

        """

        return super().get_player_limit()

    def get_player_concurrent_limit(self) -> Union[int, None]:
        """
        Return the concurrent player membership limit of this game with areas.

        Returns
        -------
        Union[int, None]
            The concurrent player membership limit.

        """

        return super().get_player_concurrent_limit()

    def get_players(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
        ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of players of this game with areas that satisfy a
        condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all players returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) players of this game with areas.

        """

        return super().get_players(cond=cond)

    def is_player(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is a player of the game with areas.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Returns
        -------
        bool
            True if the user is a player, False otherwise.

        """

        return super().is_player(user)

    def add_player(self, user: ClientManager.Client):
        """
        Make a user a player of the game with areas. By default this player will not be a leader,
        unless the game with areas has no leaders and it requires a leader.
        It will also subscribe the game with areas to the player so it can listen to its updates.

        Parameters
        ----------
        user : ClientManager.Client
            User to add to the game with areas. They must be in an area part of the game with areas.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areaswas scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.UserNotInAreaError
            If the user is not in an area part of the game with areas.
        GameWithAreasError.UserHasNoCharacterError
            If the user has no character but the game with areas requires that all players have
            characters.
        GameWithAreasError.UserNotInvitedError
            If the game with areasrequires players be invited to be added and the user is not
            invited.
        GameWithAreasError.UserAlreadyPlayerError
            If the user to add is already a user of the game with areas.
        GameWithAreasError.UserHitGameConcurrentLimitError
            If the player has reached the concurrent player membership of any of the game with areas
            managed by the manager of this game with area, or by virtue of joining this game with
            areas they would violate this game with areas's concurrent player membership limit.
        GameWithAreasError.GameIsFullError
            If the game with areas reached its player limit.

        """

        super().unchecked_add_player(user)
        self._check_structure()

    def remove_player(self, user: ClientManager.Client):
        """
        Make a user be no longer a player of this game with areas. If they were part of a team
        managed by this game with areas, they will also be removed from said team. It will also
        unsubscribe the game with areas from the player so it will no longer listen to its updates.

        If the game with areas required that there it always had players and by calling this method
        the game with areas had no more players, the game will automatically be scheduled for
        deletion.

        Parameters
        ----------
        user : ClientManager.Client
            User to remove.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.UserNotPlayerError
            If the user to remove is already not a player of this game with areas.

        """

        self.unchecked_remove_player(user)
        self.manager._check_structure()

    def unchecked_remove_player(self, user: ClientManager.Client):
        """
        Make a user be no longer a player of this game with areas. If they were part of a team
        managed by this game with areas, they will also be removed from said team. It will also
        unsubscribe the game with areas from the player so it will no longer listen to its updates.

        If the game with areas required that there it always had players and by calling this method
        the game with areas had no more players, the game will automatically be scheduled for
        deletion.

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to remove.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.UserNotPlayerError
            If the user to remove is already not a player of this game with areas.

        """

        if self.is_unmanaged():
           raise GameWithAreasError.GameIsUnmanagedError

        try:
            super().unchecked_remove_player(user)
        except GameError.GameIsUnmanagedError:
            # Should not have made it here as we already asserted the game is not unmmanaged
            raise RuntimeError(self, user)
        except GameError.UserNotPlayerError:
            raise GameWithAreasError.UserNotPlayerError

    def requires_players(self) -> bool:
        """
        Return whether the game with areas requires players at all times.

        Returns
        -------
        bool
            Whether the game with areas requires players at all times.
        """

        return super().requires_players()

    def get_invitations(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
        ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of invited users of this game with areas that satisfy a
        condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all invited users returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) invited users of this game with areas.

        """

        return super().get_invitations(cond=cond)

    def is_invited(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is invited to the game with areas.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Raises
        ------
        GameWithAreasError.UserAlreadyPlayerError
            If the user is a player of this game with areas.

        Returns
        -------
        bool
            True if the user is invited, False otherwise.

        """

        try:
            return super().is_invited(user)
        except GameError.UserAlreadyPlayerError:
            raise GameWithAreasError.UserAlreadyPlayerError

    def add_invitation(self, user: ClientManager.Client):
        """
        Mark a user as invited to this game with areas.

        Parameters
        ----------
        user : ClientManager.Client
            User to invite to the game with areas.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.GameDoesNotTakeInvitationsError
            If the game with areas does not require users be invited to the game with areas.
        GameWithAreasError.UserAlreadyInvitedError
            If the player to invite is already invited to the game with areas.
        GameWithAreasError.UserAlreadyPlayerError
            If the player to invite is already a player of the game with areas.

        """

        self.unchecked_add_invitation(user)
        self.manager._check_structure()

    def unchecked_add_invitation(self, user: ClientManager.Client):
        """
        Mark a user as invited to this game with areas.

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to invite to the game with areas.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.GameDoesNotTakeInvitationsError
            If the game with areas does not require users be invited to the game with areas.
        GameWithAreasError.UserAlreadyInvitedError
            If the player to invite is already invited to the game with areas.
        GameWithAreasError.UserAlreadyPlayerError
            If the player to invite is already a player of the game with areas.

        """

        if self.is_unmanaged():
            raise GameWithAreasError.GameIsUnmanagedError

        try:
            super().unchecked_add_invitation(user)
        except GameError.GameIsUnmanagedError:
            # Should not have made it here as we already asserted the game is not unmmanaged
            raise RuntimeError(self, user)
        except GameError.GameDoesNotTakeInvitationsError:
            raise GameWithAreasError.GameDoesNotTakeInvitationsError
        except GameError.UserAlreadyInvitedError:
            raise GameWithAreasError.UserAlreadyInvitedError
        except GameError.UserAlreadyPlayerError:
            raise GameWithAreasError.UserAlreadyPlayerError

    def remove_invitation(self, user: ClientManager.Client):
        """
        Mark a user as no longer invited to this game with areas (uninvite).

        Parameters
        ----------
        user : ClientManager.Client
            User to uninvite.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.GameDoesNotTakeInvitationsError
            If the game with areas does not require users be invited to the game with areas.
        GameWithAreasError.UserNotInvitedError
            If the user to uninvite is already not invited to this game with areas.

        """

        self.unchecked_remove_invitation(user)
        self.manager._check_structure()

    def unchecked_remove_invitation(self, user: ClientManager.Client):
        """
        Mark a user as no longer invited to this game (uninvite).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to uninvite.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.GameDoesNotTakeInvitationsError
            If the game with areas does not require users be invited to the game with areas.
        GameWithAreasError.UserNotInvitedError
            If the user to uninvite is already not invited to this game with areas.

        """

        if self.is_unmanaged():
            raise GameWithAreasError.GameIsUnmanagedError

        try:
            super().unchecked_remove_invitation(user)
        except GameError.GameIsUnmanagedError:
            # Should not have made it here as we already asserted the game is not unmmanaged
            raise RuntimeError(self, user)
        except GameError.GameDoesNotTakeInvitationsError:
            raise GameWithAreasError.GameDoesNotTakeInvitationsError
        except GameError.UserNotInvitedError:
            raise GameWithAreasError.UserNotInvitedError

    def requires_invitations(self):
        """
        Return True if the game with areas requires players be invited before being allowed to join
        the game, False otherwise.

        Returns
        -------
        bool
            True if the game with areas requires players be invited before being allowed to join
            the game, False otherwise.
        """

        return super().requires_invitations()

    def get_leaders(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
        ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of leaders of this game with areas that satisfy a condition
        if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all leaders returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) leaders of this game with areas.

        """

        return super().get_leaders(cond=cond)

    def get_regulars(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
        ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of players of this game with areas that are regulars and
        satisfy a condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all regulars returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) regulars of this game with areas.

        """

        return super().get_regulars(cond=cond)

    def is_leader(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is a leader of the game with areas.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Raises
        ------
        GameWithAreasError.UserNotPlayerError
            If the player to test is not a player of this game with areas.

        Returns
        -------
        bool
            True if the player is a user, False otherwise.

        """

        try:
            return super().is_leader(user)
        except GameError.UserNotPlayerError:
            raise GameWithAreasError.UserNotPlayerError

    def add_leader(self, user: ClientManager.Client):
        """
        Set a user as leader of this game with areas (promote to leader).

        Parameters
        ----------
        user : ClientManager.Client
            Player to promote to leader.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.UserNotPlayerError
            If the player to promote is not a player of this game with areas.
        GameWithAreasError.UserAlreadyLeaderError
            If the player to promote is already a leader of this game with areas.

        """

        self.unchecked_add_leader(user)
        self.manager._check_structure()

    def unchecked_add_leader(self, user: ClientManager.Client):
        """
        Set a user as leader of this game with areas (promote to leader).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            Player to promote to leader.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.UserNotPlayerError
            If the player to promote is not a player of this gamewith areas .
        GameWithAreasError.UserAlreadyLeaderError
            If the player to promote is already a leader of this gamewith areas .

        """

        if self.is_unmanaged():
            raise GameWithAreasError.GameIsUnmanagedError

        try:
            super().unchecked_add_leader(user)
        except GameError.GameIsUnmanagedError:
            # Should not have made it here as we already asserted the game with areas is not
            # unmmanaged
            raise RuntimeError(self, user)
        except GameError.UserNotPlayerError:
            raise GameWithAreasError.UserNotPlayerError
        except GameError.UserAlreadyLeaderError:
            raise GameWithAreasError.UserAlreadyLeaderError

    def remove_leader(self, user: ClientManager.Client):
        """
        Make a user no longer leader of this game with areas (demote).

        Parameters
        ----------
        user : ClientManager.Client
            User to demote.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.UserNotPlayerError
            If the player to demote is not a player of this game with areas.
        GameWithAreasError.UserNotLeaderError
            If the player to demote is already not a leader of this game with areas.

        """

        self.unchecked_remove_leader(user)
        self.manager._check_structure()

    def unchecked_remove_leader(self, user: ClientManager.Client):
        """
        Make a user no longer leader of this game with areas (demote).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to demote.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.UserNotPlayerError
            If the player to demote is not a player of this game with areas.
        GameWithAreasError.UserNotLeaderError
            If the player to demote is already not a leader of this game with areas.

        """

        if self.is_unmanaged():
            raise GameWithAreasError.GameIsUnmanagedError

        try:
            super().unchecked_remove_leader(user)
        except GameError.GameIsUnmanagedError:
            # Should not have made it here as we already asserted the game is not unmmanaged
            raise RuntimeError(self, user)
        except GameError.UserNotPlayerError:
            raise GameWithAreasError.UserNotPlayerError
        except GameError.UserNotLeaderError:
            raise GameWithAreasError.UserNotLeaderError

    def has_ever_had_players(self) -> bool:
        """
        Return True if a player has ever been added to this game with areas, False otherwise.

        Returns
        -------
        bool
            True if the game with areas has ever had a player added, False otherwise.

        """

        return super().has_ever_had_players()

    def requires_leaders(self) -> bool:
        """
        Return whether the game with areas requires leaders at all times.

        Returns
        -------
        bool
            Whether the game with areas requires leaders at all times.
        """

        return super().requires_leaders()

    def has_ever_had_players(self):
        """
        Return True if a player has ever been added to this game with areas, False otherwise.

        Returns
        -------
        bool
            True if the game with areas has ever had a player added, False otherwise.

        """

        return super().has_ever_had_players()

    def is_unmanaged(self):
        """
        Return True if this game with areas is unmanaged, False otherwise.

        Returns
        -------
        bool
            True if unmanaged, False otherwise.

        """

        return super().is_unmanaged()


class _GameWithAreas(_GameWithAreasTrivialInherited):
    """
    A game with areas is a game that manages and subscribes to its areas' updates.
    Any player of such a game with areas must be in an area of the game with areas. If a player of
    the game with areas goes to an area not part of the game with areas, they are removed
    automatically from the game with areas.
    If an area is removed from the set of areas of the game with areas, all players in that area
    are removed in some unspecified order.
    Each of these games with areas may also impose a concurrent area membership limit, so that
    every area part of a game with areas is at most an area of that many games with areas managed
    by this games's manager.
    Each of these games with areas may also set an autoadd on client enter flag. If set, nonplayer
    clients who enter an area part of the game with areas will be added to the game with areas if
    possible; if this fails, no action is taken and no errors are propagated.

    Attributes
    ----------
    server : TsuserverDR
        Server the game with areas belongs to.
    manager : GameWithAreasManager
        Manager for this game with areas.
    team_manager : PlayerGroupManager
        Internal manager that handles the teams of the game with areas.
    timer_manager: TimerManager
        Internal manager that handles the timers of the game with areas.
    listener : Listener
        Standard listener of the game with areas.

    Callback Methods
    ----------------
    _on_area_client_left_final
        Method to perform once a client left an area of the game with areas.
    _on_area_client_entered_final
        Method to perform once a client entered an area of the game with areas.
    _on_area_destroyed
        Method to perform once an area of the game with areas is marked for destruction.
    _on_client_inbound_ms_check
        Method to perform once a player of the game with areas wants to send an IC message.
    _on_client_inbound_ms_final
        Method to perform once a player of the game with areas sends an IC message.
    _on_client_change_character
        Method to perform once a player of the game with areas has changed character.
    _on_client_destroyed
        Method to perform once a player of the game with areas is destroyed.

    """

    # (Private) Attributes
    # --------------------
    # _areas : Set[AreaManager.Area]
    #   Areas of the game with areas.
    # _area_concurrent_limit : Union[int, None]
    #   The maximum number of games with areas managed by `manager` that any
    #   area of this game with areas may belong to, including this game with areas.
    # _autoadd_on_client_enter : bool
    #   Whether nonplayer users that enter an area part of the game with areas will be
    #   automatically added if permitted by the conditions of the game with areas.
    #
    # Invariants
    # ----------
    # 1. For each player of the game with areas, they are in an area part of the game with areas.
    # 2. It is not true that the game with areas requires invitations and automatically adds users
    #    that join an area part of the game with areas.
    # 3. The invariants from the parent class _Game are satisfied.

    def __init__(
        self,
        server: TsuserverDR,
        manager: GameWithAreasManager,
        game_id: str,
        player_limit: Union[int, None] = None,
        player_concurrent_limit: Union[int, None] = None,
        require_invitations: bool = False,
        require_players: bool = True,
        require_leaders: bool = True,
        require_character: bool = False,
        team_limit: Union[int, None] = None,
        timer_limit: Union[int, None] = None,
        area_concurrent_limit: Union[int, None] = None,
        autoadd_on_client_enter: bool = False,
    ):
        """
        Create a new game with areas. A game with areas should not be fully initialized anywhere
        else other than some manager code, as otherwise the manager will not recognize the game with
        areas.

        Parameters
        ----------
        server : TsuserverDR
            Server the game with areas belongs to.
        manager : GameWithAreasManager
            Manager for this game with areas.
        game_id : str
            Identifier of the game with areas.
        player_limit : int or None, optional
            If an int, it is the maximum number of players the game with areas supports. If None, it
            indicates the game with areas has no player limit. Defaults to None.
        player_concurrent_limit : int or None, optional
            If an int, it is the maximum number of games with areas managed by `manager` that any
            player of this game with areas may belong to, including this game with areas. If None,
            it indicates that this game with areas does not care about how many other games with
            areas managed by `manager` each of its players belongs to. Defaults to None.
        require_invitation : bool, optional
            If True, players can only be added to the game with areas if they were previously
            invited. If False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the game with areas has no players left, the game with areas
            will automatically be deleted. If False, no such automatic deletion will happen.
            Defaults to True.
        require_leaders : bool, optional
            If True, if at any point the game with areas has no leaders left, the game with areas
            will choose a leader among any remaining players left; if no players are left, the next
            player added will be made leader. If False, no such automatic assignment will happen.
            Defaults to True.
        require_character : bool, optional
            If False, players without a character will not be allowed to join the game with areas,
            and players that switch to something other than a character will be automatically
            removed from the game with areas. If False, no such checks are made. A player without a
            character is considered one where player.has_character() returns False. Defaults to
            False.
        team_limit : int or None, optional
            If an int, it is the maximum number of teams the game with areas supports. If None, it
            indicates the game with areas has no team limit. Defaults to None.
        timer_limit : int or None, optional
            If an int, it is the maximum number of timers the game with areas supports. If None, it
            indicates the game with areas has no timer limit. Defaults to None.
        area_concurrent_limit : int or None, optional
            If an int, it is the maximum number of games with areas managed by `manager` that any
            area of this game with areas may belong to, including this game with areas. If None, it
            indicates that this game with areas does not care about how many other game with areas
            managed by `manager` each of its areas belongs to. Defaults to 1 (an area may not be a
            part of another game with areas managed by `manager` while being an area of this game).
        autoadd_on_client_enter : bool, optional
            If True, nonplayer users that enter an area part of the game with areas will be
            automatically added if permitted by the conditions of the game with areas. If False, no
            such adding will take place. Defaults to False.

        """

        self._areas = set()
        self._area_concurrent_limit = area_concurrent_limit
        self._autoadd_on_client_enter = autoadd_on_client_enter

        super().__init__(
            server,
            manager,
            game_id,
            player_limit=player_limit,
            player_concurrent_limit=player_concurrent_limit,
            require_invitations=require_invitations,
            require_players=require_players,
            require_leaders=require_leaders,
            require_character=require_character,
            team_limit=team_limit,
            timer_limit=timer_limit
        )

        self.listener.subscribe(self.server.area_manager)
        self.listener.update_events({
            'area_client_left_final': self._on_area_client_left_final,
            'area_client_entered_final': self._on_area_client_entered_final,
            'area_client_inbound_ms_check': self._on_area_client_inbound_ms_check,
            'area_destroyed': self._on_area_destroyed,
            'areas_loaded': self._on_areas_loaded,
            })

    def get_name(self) -> str:
        """
        Return the name of the game with areas. Names are fully lowercase.
        Implementations of the class should replace this with a human readable name of the game
        with areas.

        Returns
        -------
        str
            Name of the game with areas.

        """

        return "game with areas"

    def get_autoadd_on_client_enter(self) -> bool:
        """
        Return True if the game with areas will always attempt to add nonplayer users who enter an
        area part of the game with areas, False otherwise.

        Returns
        -------
        bool
            True if the game with areas will always attempt to add nonplayer users who enter an area
            part of the game with areas, False otherwise.
        """

        return self._autoadd_on_client_enter

    def set_autoadd_on_client_enter(self, new_value: bool):
        """
        Set the new status of the autoadd on client enter flag.

        Parameters
        ----------
        new_value : bool
            New value.

        """

        self.unchecked_set_autoadd_on_client_enter(new_value)
        self.manager._check_structure()

    def unchecked_set_autoadd_on_client_enter(self, new_value: bool):
        """
        Set the new status of the autoadd on client enter flag.

        This method does not assert structural integrity.

        Parameters
        ----------
        new_value : bool
            New value.

        """

        self._autoadd_on_client_enter = new_value

    def unchecked_add_player(self, user: ClientManager.Client):
        """
        Make a user a player of the game with areas. By default this player will not be a leader,
        unless the game with areas has no leaders and it requires a leader.
        It will also subscribe the game with areas to the player so it can listen to its updates.

        Parameters
        ----------
        user : ClientManager.Client
            User to add to the game with areas. They must be in an area part of the game with areas.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areaswas scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.UserNotInAreaError
            If the user is not in an area part of the game with areas.
        GameWithAreasError.UserHasNoCharacterError
            If the user has no character but the game with areas requires that all players have
            characters.
        GameWithAreasError.UserNotInvitedError
            If the game with areasrequires players be invited to be added and the user is not
            invited.
        GameWithAreasError.UserAlreadyPlayerError
            If the user to add is already a user of the game with areas.
        GameWithAreasError.UserHitGameConcurrentLimitError
            If the player has reached the concurrent player membership of any of the game with areas
            managed by the manager of this game with area, or by virtue of joining this game with
            areas they would violate this game with areas's concurrent player membership limit.
        GameWithAreasError.GameIsFullError
            If the game with areas reached its player limit.

        """

        if self.is_unmanaged():
            raise GameWithAreasError.GameIsUnmanagedError
        # Check user in area before doing the rest of the add player code.
        if user.area not in self._areas:
            raise GameWithAreasError.UserNotInAreaError

        try:
            super().unchecked_add_player(user)
        except GameError.GameIsUnmanagedError:
            raise RuntimeError(self)
        except GameError.UserNotInvitedError:
            raise GameWithAreasError.UserNotInvitedError
        except GameError.UserAlreadyPlayerError:
            raise GameWithAreasError.UserAlreadyPlayerError
        except GameError.UserHitGameConcurrentLimitError:
            raise GameWithAreasError.UserHitGameConcurrentLimitError
        except GameError.GameIsFullError:
            raise GameWithAreasError.GameIsFullError

    def add_area(self, area: AreaManager.Area):
        """
        Add an area to this game's set of areas.

        Parameters
        ----------
        area : AreaManager.Area
            Area to add.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.AreaAlreadyInGameError
            If the area is already part of the game with areas.
        GameWithAreasError.AreaHitGameConcurrentLimitError.
            If `area` has reached the concurrent area membership limit of any of the games with areas it
            belongs to managed by this manager, or by virtue of adding this area it will violate
            this game's concurrent area membership limit.

        """

        if self.is_unmanaged():
            raise GameWithAreasError.GameIsUnmanagedError
        if area in self._areas:
            raise GameWithAreasError.AreaAlreadyInGameError

        self._areas.add(area)
        self.listener.subscribe(area)
        try:
            self.manager._add_area_to_mapping(area, self)
        except GameWithAreasError.AreaHitGameConcurrentLimitError as ex:
            self._areas.discard(area)
            self.listener.unsubscribe(area)
            raise ex

        self._check_structure()

    def remove_area(self, area: AreaManager.Area):
        """
        Remove an area from this game's set of areas.
        If the area is already a part of the game with areas, do nothing.
        If any player of the game with areas is in this area, they are removed from the game with
        areas.
        If the game with areas has no areas remaining, it will be automatically destroyed.

        Parameters
        ----------
        area : AreaManager.Area
            Area to remove.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.AreaNotInGameError
            If the area is already not part of the game with areas.

        """

        if self.is_unmanaged():
            raise GameWithAreasError.GameIsUnmanagedError
        if area not in self._areas:
            raise GameWithAreasError.AreaNotInGameError

        # Implementation detail: we may not simply check if client.area == area. That is because it
        # may be the case a player was moved as a result of the area being destroyed, which is one
        # of the events that triggers this method. Moreover, as the change_area code in area reloads
        # does not trigger the publishers, we cannot necessarily assume that _on_area_client_left
        # will do our checks.
        # However, we can check ourselves manually: if a player of the game with areas is in an
        # area not part of the game with areas, remove them.
        # As area is in self._areas (by earlier check), we do not need to check
        faulty_players = self.get_players(cond=lambda client: client.area == area)
        for player in faulty_players:
            self.remove_player(player)
        # Remove area only after removing all players to prevent structural checks failing
        self._areas.discard(area)
        self.listener.unsubscribe(area)
        self.manager._remove_area_from_mapping(area, self)
        if not self._areas:
            self.destroy()

        self._check_structure()

    def has_area(self, area: AreaManager.Area) -> bool:
        """
        If the area is part of this game's set of areas, return True; otherwise, return False.

        Parameters
        ----------
        area : AreaManager.Area
            Area to check.

        Returns
        -------
        bool
            True if the area is part of the game's set of areas, False otherwise.

        """

        return area in self._areas

    def get_areas(self) -> Set[AreaManager.Area]:
        """
        Return (a shallow copy of) the set of areas of this game with areas.

        Returns
        -------
        Set[AreaManager.Area]
            Set of areas of the game with areas.

        """

        return self._areas.copy()

    def get_area_concurrent_limit(self) -> Union[int, None]:
        """
        Return the concurrent area membership limit of this game with areas.

        Returns
        -------
        Union[int, None]
            The concurrent area membership limit.

        """

        return self._area_concurrent_limit

    def get_users_in_areas(self) -> Set[ClientManager.Client]:
        """
        Return all users in areas part of the game with areas, even those that are not players of
        the game with areas.

        Returns
        -------
        Set[ClientManager.Client]
            All users in areas part of the game with areas.

        """

        clients = list()
        for area in self._areas:
            clients.extend(area.clients)
        return set(clients)

    def get_nonleader_users_in_areas(self) -> Set[ClientManager.Client]:
        """
        Return all users in areas part of the game with areas, even those that are not players of
        the game with areas, such that they are not leaders of the game with areas.

        Returns
        -------
        Set[ClientManager.Client]
            All users in areas part of the game with areas that are not leaders of the game with areas.

        """

        return {client for client in self.get_users_in_areas()
                if not (self.is_player(client) and self.is_leader(client))}

    def get_nonplayer_users_in_areas(self) -> Set[ClientManager.Client]:
        """
        Return all users in areas part of the game with areas that are not players of the game
        with areas.

        Returns
        -------
        Set[ClientManager.Client]
            All users in areas part of the game with areas that are not players of the game with
            areas.

        """

        return {client for client in self.get_users_in_areas() if not self.is_player(client)}

    def destroy(self):
        """
        Mark this game with areas as destroyed and notify its manager so that it is deleted.
        If the game with areas is already destroyed, this function does nothing.

        This method is reentrant (it will do nothing though).

        Returns
        -------
        None.

        """

        # Remove areas too. This is done first so that structural checks can take place after
        # areas are removed.
        for area in self.get_areas():
            self.remove_area(area)
        super().destroy()  # Also calls _check_structure()

    def __str__(self) -> str:
        """
        Return a string representation of this game with areas.

        Returns
        -------
        str
            Representation.

        """

        return (f"GameWithAreas::{self.get_id()}:"
                f"{self.get_players()}:{self.get_leaders()}:{self.get_invitations()}"
                f"{self.get_timers()}:"
                f"{self.get_teams()}:"
                f"{self.get_areas()}")

    def __repr__(self) -> str:
        """
        Return a representation of this game with areas.

        Returns
        -------
        str
            Printable representation.

        """

        return (f'GameWithAreas(server, {self.manager.get_id()}, "{self.get_id()}", '
                f'player_limit={self.get_player_limit()}, '
                f'player_concurrent_limit={self.get_player_concurrent_limit()}, '
                f'require_players={self.requires_players()}, '
                f'require_invitations={self.requires_invitations()}, '
                f'require_leaders={self.requires_leaders()}, '
                f'require_character={self.requires_characters()}, '
                f'team_limit={self.team_manager.get_managee_limit()}, '
                f'timer_limit={self.timer_manager.get_timer_limit()}, '
                f'areas={self.get_areas()}) || '
                f'players={self.get_players()}, '
                f'invitations={self.get_invitations()}, '
                f'leaders={self.get_leaders()}, '
                f'timers={self.get_timers()}, '
                f'teams={self.get_teams()}')

    def _on_area_client_left_final(self, area, client=None, old_displayname=None,
                                   ignore_bleeding=False, ignore_autopass=False):
        """
        Default callback for game with areas area signaling a client left. This is executed after
        all other actions related to moving the player to a new area have been executed:
        in particular, client.area holds the new area of the client.

        By default it removes the player from the game with areas if their new area is not part of
        the game with areas.

        Parameters
        ----------
        area : AreaManager.Area
            Area that signaled a client has left.
        client : ClientManager.Client, optional
            The client that has left. The default is None.
        new_area : AreaManager.Area
            The new area the client has gone to. The default is None.
        old_displayname : str, optional
            The old displayed name of the client before they changed area. This will typically
            change only if the client's character or showname are taken. The default is None.
        ignore_bleeding : bool, optional
            If the code should ignore actions regarding bleeding. The default is False.
        ignore_autopass : bool, optional
            If the code should ignore actions regarding autopass. The default is False.

        Returns
        -------
        None.

        """

        # print('Received LEFT', area, client, client.area, old_displayname, ignore_bleeding)
        if client in self.get_players() and client.area not in self._areas:
            self.remove_player(client)

        self._check_structure()

    def _on_area_client_entered_final(self, area: AreaManager.Area,
                                      client: ClientManager.Client = None,
                                      old_area: AreaManager.Area = None,
                                      old_displayname: str = None,
                                      ignore_bleeding: bool = False,
                                      ignore_autopass: bool = False):
        """
        Default callback for game with areas area signaling a client entered.

        By default adds a user to the game with areas if the game with areas is meant to
        automatically add users that enter an area part of the game with areas.

        Parameters
        ----------
        area : AreaManager.Area
            Area that signaled a client has entered.
        client : ClientManager.Client, optional
            The client that has entered. The default is None.
        old_area : AreaManager.Area
            The old area the client has come from. The default is None.
        old_displayname : str, optional
            The old displayed name of the client before they changed area. This will typically
            change only if the client's character or showname are taken. The default is None.
        ignore_bleeding : bool, optional
            If the code should ignore actions regarding bleeding. The default is False.
        ignore_autopass : bool, optional
            If the code should ignore actions regarding autopass. The default is False.

        Returns
        -------
        None.

        """

        # print('Received ENTERED', area, client, old_area, old_displayname, ignore_bleeding)
        if client not in self.get_players() and self.get_autoadd_on_client_enter():
            self.add_player(client)

        self._check_structure()

    def _on_area_client_inbound_ms_check(self, area: AreaManager.Area,
                                         client: ClientManager.Client = None,
                                         contents: Dict[str, Any] = None):
        """
        Default callback for game with areas area signaling a client in the area sent an IC message.
        Unlike the ClientManager.Client callback for send_ic_check, this one is triggered
        regardless of whether the sender is part of the game with areas or not. This is useful for
        example, to filter out messages sent by non-players.

        By default does nothing.

        Parameters
        ----------
        area : AreaManager.Area
            Area that signaled a client has entered.
        client : ClientManager.Client, optional
            The client that has send the IC message. The default is None.
        contents : dict of str to Any
            Arguments of the IC message as indicated in AOProtocol.

        Returns
        -------
        None.

        """

        # print('User', client, 'in area', area, 'wants to check sent', contents)

        self._check_structure()

    def _on_area_destroyed(self, area: AreaManager.Area):
        """
        Default callback for game with areas area signaling it was destroyed.

        By default it calls self.remove_area(area).

        Parameters
        ----------
        area : AreaManager.Area
            Area that signaled it was destroyed.

        Returns
        -------
        None.

        """

        # print('Received DESTRUCTION', area)
        self.remove_area(area)

        self._check_structure()

    def _on_areas_loaded(self, area_manager: AreaManager):
        """
        Default callback for server area manager signaling it loaded new areas.

        By default it calls self.destroy().

        Parameters
        ----------
        area_manager : AreaManager
            AreaManager that signaled the area loads

        Returns
        -------
        None.

        """

        self.destroy()

    def _check_structure(self):
        """
        Assert that all invariants specified in the class description are maintained.

        Raises
        ------
        AssertionError
            If any of the invariants are not maintained.

        """

        # 1.
        for player in self.get_players():
            err = (f'For game with areas {self}, expected that its player {player} was in an area '
                   f'part of the game with areas, found they were in area {player.area} instead.')
            assert player.area in self._areas, err

        # 2.
        if self._autoadd_on_client_enter and self.requires_invitations():
            err = (f'For game with areas {self}, expected that it did not simultaneously require '
                   f'invitations for users to join while mandating users be automatically added '
                   f'if they enter an area of the game with areas, found it did.')
            raise AssertionError(err)

        # 2.
        super()._check_structure()


class GameWithAreasManager(GameManager):
    """
    A game with areas manager is a game manager with dedicated area management functions.

    """

    # TODO: Enforce GameWithAreasManager to only take game with areas when calling
    # new_game with areas, or when initialized. Also do it in check_structure()

    def __init__(self, server, game_limit=None, default_game_type=None,
                 available_id_producer=None):
        """
        Create a game with areas manager object.

        Parameters
        ----------
        server : TsuserverDR
            The server this game with areas manager belongs to.
        game_limit : int, optional
            The maximum number of games with areas this manager can handle. Defaults to None (no limit).
        default_game_type : GameWithAreas, optional
            The default type of game with areas this manager will create. Defaults to None (and then
            converted to GameWithAreas).
        available_id_producer : typing.types.FunctionType, optional
            Function to produce available game with areas IDs. It will override the built-in class method
            get_available_game_id. Defaults to None (and then converted to the built-in
            get_available_game_id).

        """

        if default_game_type is None:
            default_game_type = _GameWithAreas
        self._area_to_games = dict()

        super().__init__(server, managee_limit=game_limit, default_managee_type=default_game_type,
                         available_id_producer=available_id_producer)

    def new_managee(self, game_type=None, creator=None, player_limit=None,
                 player_concurrent_limit=1, require_invitations=False, require_players=True,
                 require_leaders=True, require_character=False, team_limit=None, timer_limit=None,
                 areas=None, area_concurrent_limit=None,
                 autoadd_on_client_enter=False) -> _GameWithAreas:
        """
        Create a new game with areas managed by this manager.

        Parameters
        ----------
        game_type : _Game or functools.partial
            Class of game with areas that will be produced. Defaults to None (and converted to the default
            game with areas created by this game with areas manager).
        creator : ClientManager.Client, optional
            The player who created this game with areas. If set, they will also be added to the game with areas.
            Defaults to None.
        player_limit : int or None, optional
            If an int, it is the maximum number of players the game with areas supports. If None, it
            indicates the game with areas has no player limit. Defaults to None.
        player_concurrent_limit : int or None, optional
            If an int, it is the maximum number of games with areas managed by `self` that any player
            of this game with areas to create may belong to, including this game with areas to create. If None, it
            indicates that this game with areas does not care about how many other games with areas managed by `self`
            each of its players belongs to. Defaults to 1 (a player may not be in another game
            managed by `self` while in this game).
        require_invitations : bool, optional
            If True, users can only be added to the game with areas if they were previously invited. If
            False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the game with areas loses all its players, the game with areas will automatically
            be deleted. If False, no such automatic deletion will happen. Defaults to True.
        require_leaders : bool, optional
            If True, if at any point the game with areas has no leaders left, the game with areas will choose a leader
            among any remaining players left; if no players are left, the next player added will
            be made leader. If False, no such automatic assignment will happen. Defaults to True.
        require_character : bool, optional
            If False, players without a character will not be allowed to join the game with areas, and players
            that switch to something other than a character will be automatically removed from the
            game with areas. If False, no such checks are made. A player without a character is considered
            one where player.has_character() returns False. Defaults to False.
        team_limit : int or None, optional
            If an int, it is the maximum number of teams the game with areas will support. If None, it
            indicates the game with areas will have no team limit. Defaults to None.
        timer_limit : int or None, optional
            If an int, it is the maximum number of timers the game with areas will support. If None, it
            indicates the game with areas will have no timer limit. Defaults to None.
        areas : set of AreaManager.Area, optional
            Areas the game with areas starts with. Defaults to None (and converted to an empty set).
        area_concurrent_limit : int or None, optional
            If an int, it is the maximum number of games with areas managed by `manager` that any
            area of this game with areas may belong to, including this game with areas. If None, it indicates
            that this game with areas does not care about how many other game with areas managed by
            `manager` each of its areas belongs to. Defaults to 1 (an area may not be a part of
            another game with areas managed by `manager` while being an area of this game).
        autoadd_on_client_enter : bool, optional
            If True, nonplayer users that enter an area part of the game with areas will be automatically
            added if permitted by the conditions of the game with areas. If False, no such adding will take
            place. Defaults to False.

        Returns
        -------
        GameWithAreas
            The created game with areas.

        Raises
        ------
        GameError.ManagerTooManyGamesError
            If the manager is already managing its maximum number of games.
        Any error from the created game's add_player(creator)
            If the game with areas cannot add `creator` as a player if given one.

        """

        if game_type is None:
            game_type = self.get_managee_type()

        new_game_type = functools.partial(game_type,
                                          area_concurrent_limit=area_concurrent_limit,
                                          autoadd_on_client_enter=autoadd_on_client_enter)

        game = super().new_managee(managee_type=new_game_type, creator=None, player_limit=player_limit,
                                player_concurrent_limit=player_concurrent_limit,
                                require_invitations=require_invitations,
                                require_players=require_players,
                                require_leaders=require_leaders,
                                require_character=require_character,
                                team_limit=team_limit,
                                timer_limit=timer_limit)

        try:
            for area in areas:
                game.add_area(area)
        except GameError as ex:
            # Discard game
            self.delete_managee(game)
            raise ex

        # Add creator manually. This is because adding it via .new_game will yield errors because
        # the areas are not added until the section before.
        try:
            if creator:
                game.add_player(creator)
        except GameError as ex:
            # Discard game
            self.delete_managee(game)
            raise ex

        return game

    def get_games_in_area(self, area) -> Set[_GameWithAreas]:
        """
        Return (a shallow copy of) the all games with areas managed by this manager that contain the given
        area.

        Parameters
        ----------
        area : AreaManager.Area
            Area that all returned games with areas must contain.

        Returns
        -------
        set of GameWithAreas
            Games that contain the given area.

        """

        try:
            return self._area_to_games[area].copy()
        except KeyError:
            return set()

    def _find_area_concurrent_limiting_game(self, area: AreaManager.Area):
        """
        For area `area`, find a game with areas `most_restrictive_game` managed by this manager
        such that, if `area` were to be added to another game with areas managed by this manager, they would
        violate `most_restrictive_game`'s concurrent area membership limit.
        If no such game with areas exists (or the area is not an area of any game with areas managed by this
        manager), return None.
        If multiple such games with areas exist, any one of them may be returned.

        Parameters
        ----------
        area : AreaManager.Area
            Area to test.

        Returns
        -------
        GameWithAreas or None
            Limiting game with areas as previously described if it exists, None otherwise.

        """

        games = self.get_games_in_area(area)
        if not games:
            return None

        # We only care about groups that establish a concurrent area membership limit
        games_with_limit = {game for game in games
                            if game.get_area_concurrent_limit() is not None}
        if not games_with_limit:
            return None

        # It just suffices to analyze the game with the smallest limit, because:
        # 1. If the area is part of at least as many games with areas as this game's limit, this game
        # is an example game that can be returned.
        # 2. Otherwise, no other games with areas exist due to the minimality condition.
        most_restrictive_game = min(games_with_limit,
                                    key=lambda game: game.get_area_concurrent_limit())
        if len(games) < most_restrictive_game.get_area_concurrent_limit():
            return None
        return most_restrictive_game

    def _add_area_to_mapping(self, area: AreaManager.Area, game: _GameWithAreas):
        """
        Update the area to game with areas mapping with the information that `area` was added to
        `game`.

        Parameters
        ----------
        area : AreaManager.Area
            Area that was added.
        game : GameWithAreas
            Game with areas that `area` was added to.

        Raises
        ------
        GameWithAreasError.AreaHitGameConcurrentLimitError.
            If `area` has reached the concurrent area membership limit of any of the games with areas it
            belongs to managed by this manager, or by virtue of adding this area to `game` it
            will violate this game's concurrent area membership limit.

        Returns
        -------
        None.

        """

        if self._find_area_concurrent_limiting_game(area):
            raise GameWithAreasError.AreaHitGameConcurrentLimitError

        try:
            self._area_to_games[area].add(game)
        except KeyError:
            self._area_to_games[area] = {game}

    def _remove_area_from_mapping(self, area: AreaManager.Area, game: _GameWithAreas):
        """
        Update the area to game with areas mapping with the information that `area` was removed
        from `game`.
        If the area is already not associated with that game with areas, or is not part of the mapping,
        this method will not do anything.

        Parameters
        ----------
        area : AreaManager.Area
            Area that was removed.
        game : GameWithAreas
            Game with areas that `area` was removed from.

        Returns
        -------
        None.

        """

        try:
            self._area_to_games[area].remove(game)
        except (KeyError, ValueError):
            return

        if not self._area_to_games[area]:
            self._area_to_games.pop(area)

    def _check_structure(self):
        """
        Assert that all invariants specified in the class description are maintained.

        Raises
        ------
        AssertionError
            If any of the invariants are not maintained.

        """

        # 1.
        for area in self._area_to_games:
            games = self._area_to_games[area]

            # a.
            err = (f'For game with areas manager {self}, expected that area {area} to only appear '
                   f'in the area to game with areas mapping if it was a area of any game with '
                   f'areas managed by this manager, but found it appeared while not belonging to '
                   f'any game with areas. || {self}')
            assert games, err

            for game in games:
                # b.
                err = (f'For game with areas manager {self}, expected that game with areas {game} '
                       f'that appears in the area to game with areas mapping for area {area} '
                       f'also appears in the game with areas ID to game with areas mapping, but '
                       f'found it did not. || {self}')
                assert game in self.get_managees(), err

                # c.
                err = (f'For game with areas manager {self}, expected that area {area} in the area '
                       f'to game with areas mapping be a area of its associated game with areas {game}, but '
                       f'found that was not the case. || {self}')
                assert area in game.get_areas(), err

        # 2.
        for area in self._area_to_games:
            games = self._area_to_games[area]
            membership = len(games)

            for game in games:
                limit = game.get_area_concurrent_limit()

                if limit is None:
                    continue
                err = (f'For game with areas manager {self}, expected that area {area} in game '
                       f'{game} belonged to at most the concurrent area membership limit of '
                       f'that game of {limit} game{"s" if limit != 1 else ""}, found it '
                       f'belonged to {membership} game{"s" if membership != 1 else ""}. || {self}')
                assert membership <= limit, err

        # Last
        super()._check_structure()

    def __repr__(self) -> str:
        """
        Return a representation of this game with areas manager.

        Returns
        -------
        str
            Printable representation.

        """

        return (f"GameWithAreasManager(server, game_limit={self.get_managee_limit()}, "
                f"|| "
                f"_area_to_games={self._area_to_games}, "
                f"id={hex(id(self))})")
