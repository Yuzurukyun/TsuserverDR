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
from typing import Callable, Dict, Set, Any, Tuple, Type, Union

from server.exceptions import GameWithAreasError, GameError
from server.game_manager import _Game, _Team, GameManager
from server.timer_manager import Timer

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
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.UserNotInAreaError
            If the user is not in an area part of the game with areas.
        GameWithAreasError.UserHasNoCharacterError
            If the user has no character but the game with areas requires that all players have
            characters.
        GameWithAreasError.UserNotInvitedError
            If the game with areas requires players be invited to be added and the user is not
            invited.
        GameWithAreasError.UserAlreadyPlayerError
            If the user to add is already a user of the game with areas.
        GameWithAreasError.UserHitGameConcurrentLimitError
            If the player has reached the concurrent player membership of any of the game with areas
            managed by the manager of this game with areas, or by virtue of joining this
            game with areas they would violate this game with areas's concurrent player membership
            limit.
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
        the game with areas had no more players, the game with areas will automatically be scheduled
        for deletion.

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
        the game with areas had no more players, the game with areas will automatically be scheduled
        for deletion.

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
        Mark a user as no longer invited to this game with areas (uninvite).

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
        the game with areas, False otherwise.

        Returns
        -------
        bool
            True if the game with areas requires players be invited before being allowed to join
            the game with areas, False otherwise.
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
            If the player to promote is not a player of this game with areas.
        GameWithAreasError.UserAlreadyLeaderError
            If the player to promote is already a leader of this game with areas.

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

    def requires_characters(self) -> bool:
        """
        Return whether the game with areas requires players have a character at all times.

        Returns
        -------
        bool
            Whether the game with areas requires players have a character at all times.
        """

        return super().requires_characters()

    def new_timer(
        self,
        timer_type: Type[Timer] = None,
        start_value: Union[float, None] = None,
        tick_rate: float = 1,
        min_value: Union[float, None] = None,
        max_value: Union[float, None] = None,
        auto_restart: bool = False,
        auto_destroy: bool = True
        ) -> Timer:
        """
        Create a new timer managed by this game with areas with given parameters.

        Parameters
        ----------
        timer_type : Type[Timer], optional
            Class of timer that will be produced. Defaults to None (and converted to Timer).
        start_value : float, optional
            Number of seconds the apparent timer the timer will initially have. Defaults
            to None (will use the default from `timer_type`).
        tick_rate : float, optional
            Starting rate in timer seconds/IRL seconds at which the timer will tick. Defaults to 1.
        min_value : float, optional
            Minimum value the apparent timer may take. If the timer ticks below this, it will
            end automatically. It must be a non-negative number. Defaults to None (will use the
            default from `timer_type`.)
        max_value : float, optional
            Maximum value the apparent timer may take. If the timer ticks above this, it will
            end automatically. Defaults to None (will use the default from `timer_type`).
        auto_restart : bool, optional
            If True, the timer will reset without terminating back to its max value if the tick rate
            was non-negative and the timer went below its min value, or back to its max value if
            the tick rate was negative and the timer went above its max value. If False, the
            timer will terminate once either of the two conditions is satisfied without restarting.
            Defaults to False.
        auto_destroy : bool, optional
            If True, the game with areas will automatically delete the timer once it is terminated
            by it ticking out or manual termination. If False, no such automatic deletion will take
            place. Defaults to True.

        Returns
        -------
        Timer
            The created timer.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.GameTooManyTimersError
            If the game with areas is already managing its maximum number of timers.

        """

        timer = self.unchecked_new_timer(
            timer_type=timer_type,
            start_value=start_value,
            tick_rate=tick_rate,
            min_value=min_value,
            max_value=max_value,
            auto_restart=auto_restart,
            auto_destroy=auto_destroy,
        )
        self.manager._check_structure()
        return timer

    def unchecked_new_timer(
        self,
        timer_type: Type[Timer] = None,
        start_value: Union[float, None] = None,
        tick_rate: float = 1,
        min_value: Union[float, None] = None,
        max_value: Union[float, None] = None,
        auto_restart: bool = False,
        auto_destroy: bool = True
        ) -> Timer:
        """
        Create a new timer managed by this game with areas with given parameters.

        This method does not assert structural integrity.

        Parameters
        ----------
        timer_type : Type[Timer], optional
            Class of timer that will be produced. Defaults to None (and converted to Timer).
        start_value : float, optional
            Number of seconds the apparent timer the timer will initially have. Defaults
            to None (will use the default from `timer_type`).
        tick_rate : float, optional
            Starting rate in timer seconds/IRL seconds at which the timer will tick. Defaults to 1.
        min_value : float, optional
            Minimum value the apparent timer may take. If the timer ticks below this, it will
            end automatically. It must be a non-negative number. Defaults to None (will use the
            default from `timer_type`.)
        max_value : float, optional
            Maximum value the apparent timer may take. If the timer ticks above this, it will
            end automatically. Defaults to None (will use the default from `timer_type`).
        auto_restart : bool, optional
            If True, the timer will reset without terminating back to its max value if the tick rate
            was non-negative and the timer went below its min value, or back to its max value if
            the tick rate was negative and the timer went above its max value. If False, the
            timer will terminate once either of the two conditions is satisfied without restarting.
            Defaults to False.
        auto_destroy : bool, optional
            If True, the game with areas will automatically delete the timer once it is terminated
            by it ticking out or manual termination. If False, no such automatic deletion will take
            place. Defaults to True.

        Returns
        -------
        Timer
            The created timer.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.GameTooManyTimersError
            If the game with areas is already managing its maximum number of timers.

        """

        if self.is_unmanaged():
            raise GameError.GameIsUnmanagedError

        try:
            return super().unchecked_new_timer(
                timer_type=timer_type,
                start_value=start_value,
                tick_rate=tick_rate,
                min_value=min_value,
                max_value=max_value,
                auto_restart=auto_restart,
                auto_destroy=auto_destroy,
            )
        except GameError.GameIsUnmanagedError:
            raise RuntimeError(self)
        except GameError.GameTooManyTimersError:
            raise GameWithAreasError.GameTooManyTimersError

    def delete_timer(self, timer: Timer) -> str:
        """
        Delete a timer managed by this game with areas, terminating it first if needed.

        Parameters
        ----------
        timer : Timer
            The timer to delete.

        Returns
        -------
        str
            The ID of the timer that was deleted.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.GameDoesNotManageTimerError
            If the game with areas does not manage the target timer.

        """

        timer_id = self.unchecked_delete_timer(timer)
        self.manager._check_structure()
        return timer_id

    def unchecked_delete_timer(self, timer: Timer) -> str:
        """
        Delete a timer managed by this game with areas, terminating it first if needed.

        This method does not assert structural integrity.

        Parameters
        ----------
        timer : Timer
            The timer to delete.

        Returns
        -------
        str
            The ID of the timer that was deleted.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.GameDoesNotManageTimerError
            If the game with areas does not manage the target timer.

        """

        if self.is_unmanaged():
            raise GameWithAreasError.GameIsUnmanagedError

        try:
            return super().unchecked_delete_timer(timer)
        except GameError.GameIsUnmanagedError:
            raise RuntimeError(self)
        except GameError.GameDoesNotManageTimerError:
            raise GameWithAreasError.GameDoesNotManageTimerError

    def get_timers(self) -> Set[Timer]:
        """
        Return (a shallow copy of) the timers this game with areas manages.

        Returns
        -------
        Set[Timer]
            Timers this game with areas manages.

        """

        return super().get_timers()

    def get_timer_by_id(self, timer_id: str) -> Timer:
        """
        If `timer_tag` is the ID of a timer managed by this game with areas, return that timer.

        Parameters
        ----------
        timer_id: str
            ID of timer this game with areas manages.

        Returns
        -------
        Timer
            The timer whose ID matches the given ID.

        Raises
        ------
        GameWithAreasError.GameInvalidTimerIDError:
            If `timer_tag` is a str and it is not the ID of a timer this game with areas manages.

        """

        try:
            return super().get_timer_by_id(timer_id)
        except GameError.GameInvalidTimerIDError:
            raise GameWithAreasError.GameInvalidTimerIDError

    def get_timer_limit(self) -> Union[int, None]:
        """
        Return the timer limit of this game with areas.

        Returns
        -------
        Union[int, None]
            Timer limit.

        """

        return super().get_timer_limit()

    def get_timer_ids(self) -> Set[str]:
        """
        Return (a shallow copy of) the IDs of all timers managed by this game with areas.

        Returns
        -------
        Set[str]
            The IDs of all managed timers.

        """

        return super().get_timer_ids()

    def new_team(
        self,
        team_type: Type[_Team],
        creator: ClientManager.Client = None,
        player_limit: Union[int, None] = None,
        require_invitations: bool = False,
        require_players: bool = True,
        require_leaders: bool = True
        ) -> _Team:
        """
        Create a new team managed by this game with areas.

        Parameters
        ----------
        team_type : _Team
            Class of team that will be produced. Defaults to None (and converted to the
            default team created by games, namely, _Team).
        creator : ClientManager.Client, optional
            The player who created this team. If set, they will also be added to the team if
            possible. The creator must be a player of this game with areas. Defaults to None.
        player_limit : int, optional
            The maximum number of players the team may have. Defaults to None (no limit).
        require_invitations : bool, optional
            If True, users can only be added to the team if they were previously invited. If
            False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the team has no players left, the team will automatically
            be deleted. If False, no such automatic deletion will happen. Defaults to True.
        require_leaders : bool, optional
            If True, if at any point the team has no leaders left, the team will choose a
            leader among any remaining players left; if no players are left, the next player
            added will be made leader. If False, no such automatic assignment will happen.
            Defaults to True.

        Returns
        -------
        _Team
            The created team.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.GameTooManyTeamsError
            If the game with areas is already managing its maximum number of teams.
        GameWithAreasError.UserInAnotherTeamError
            If `creator` is not None and already part of a team managed by this game with areas.

        """

        team = self.unchecked_new_team(
            team_type=team_type,
            creator=creator,
            player_limit=player_limit,
            require_invitations=require_invitations,
            require_players=require_players,
            require_leaders=require_leaders,
        )
        self.manager._check_structure()
        return team

    def unchecked_new_team(
        self,
        team_type: Type[_Team],
        creator: ClientManager.Client = None,
        player_limit: Union[int, None] = None,
        require_invitations: bool = False,
        require_players: bool = True,
        require_leaders: bool = True
        ) -> _Team:
        """
        Create a new team managed by this game with areas.

        This method does not assert structural integrity.

        Parameters
        ----------
        team_type : _Team
            Class of team that will be produced. Defaults to None (and converted to the
            default team created by games, namely, _Team).
        creator : ClientManager.Client, optional
            The player who created this team. If set, they will also be added to the team if
            possible. The creator must be a player of this game with areas. Defaults to None.
        player_limit : int, optional
            The maximum number of players the team may have. Defaults to None (no limit).
        require_invitations : bool, optional
            If True, users can only be added to the team if they were previously invited. If
            False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the team has no players left, the team will automatically
            be deleted. If False, no such automatic deletion will happen. Defaults to True.
        require_leaders : bool, optional
            If True, if at any point the team has no leaders left, the team will choose a
            leader among any remaining players left; if no players are left, the next player
            added will be made leader. If False, no such automatic assignment will happen.
            Defaults to True.

        Returns
        -------
        _Team
            The created team.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.GameTooManyTeamsError
            If the game with areas is already managing its maximum number of teams.
        GameWithAreasError.UserInAnotherTeamError
            If `creator` is not None and already part of a team managed by this game with areas.

        """

        if self.is_unmanaged():
            raise GameWithAreasError.GameIsUnmanagedError

        try:
            return super().unchecked_new_team(
                team_type=team_type,
                creator=creator,
                player_limit=player_limit,
                require_invitations=require_invitations,
                require_players=require_players,
                require_leaders=require_leaders,
            )
        except GameError.GameIsUnmanagedError:
            raise RuntimeError(self)
        except GameError.GameTooManyTeamsError:
            raise GameWithAreasError.GameTooManyTeamsError
        except GameError.UserInAnotherTeamError:
            raise GameWithAreasError.UserInAnotherTeamError

    def delete_team(self, team: _Team) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a team managed by this game with areas.

        Parameters
        ----------
        team : _Team
            The team to delete.

        Returns
        -------
        Tuple[str, Set[ClientManager.Client]]
            The ID and players of the team that was deleted.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.GameDoesNotManageTeamError
            If the game with areas does not manage the target team.

        """

        team_id, players = self.unchecked_delete_team(team)
        self.manager._check_structure()
        return team_id, players

    def unchecked_delete_team(self, team: _Team) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a team managed by this game with areas.

        This method does not assert structural integrity.

        Parameters
        ----------
        team : _Team
            The team to delete.

        Returns
        -------
        Tuple[str, Set[ClientManager.Client]]
            The ID and players of the team that was deleted.

        Raises
        ------
        GameWithAreasError.GameIsUnmanagedError
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.GameDoesNotManageTeamError
            If the game with areas does not manage the target team.

        """

        if self.is_unmanaged():
            raise GameWithAreasError.GameIsUnmanagedError

        try:
            return super().unchecked_delete_team(team)
        except GameError.GameIsUnmanagedError:
            raise RuntimeError(self)
        except GameError.GameDoesNotManageTeamError:
            raise GameWithAreasError.GameDoesNotManageTeamError

    def manages_team(self, team: _Team) -> bool:
        """
        Return True if the team is managed by this game with areas, False otherwise.

        Parameters
        ----------
        team : _Team
            The team to check.

        Returns
        -------
        bool
            True if the game with areas manages this team, False otherwise.

        """

        return super().manages_team(team)

    def get_teams(self) -> Set[_Team]:
        """
        Return (a shallow copy of) the teams this game with areas manages.

        Returns
        -------
        Set[_Team]
            Teams this game with areas manages.

        """

        return super().get_teams()

    def get_team_by_id(self, team_id: str) -> _Team:
        """
        If `team_id` is the ID of a team managed by this game with areas, return the team.

        Parameters
        ----------
        team_id : str
            ID of the team this game with areas manages.

        Returns
        -------
        _Team
            The team that matches the given ID.

        Raises
        ------
        GameWithAreasError.GameInvalidTeamIDError:
            If `team_id` is not the ID of a team this game with areas manages.

        """

        try:
            return super().get_team_by_id(team_id)
        except GameError.GameInvalidTeamIDError:
            raise GameWithAreasError.GameInvalidTeamIDError

    def get_team_limit(self) -> Union[int, None]:
        """
        Return the team limit of this game with areas.

        Returns
        -------
        Union[int, None]
            Team limit.

        """

        return super().get_team_limit()

    def get_team_ids(self) -> Set[str]:
        """
        Return (a shallow copy of) the IDs of all teams managed by this game with areas.

        Returns
        -------
        Set[str]
            The IDs of all managed teams.

        """

        return super().get_team_ids()

    def get_teams_of_user(self, user: ClientManager.Client) -> Set[_Team]:
        """
        Return (a shallow copy of) the teams managed by this game with areas user `user` is a player
        of. If the user is part of no such team, an empty set is returned.

        Parameters
        ----------
        user : ClientManager.Client
            User whose teams will be returned.

        Returns
        -------
        Set[_Team]
            Teams the player belongs to.

        """

        return super().get_teams_of_user(user)

    def get_users_in_some_team(self):
        """
        Return (a shallow copy of) all the users that are part of some team managed by this game
        with areas.

        Returns
        -------
        Set[ClientManager.Client]
            Users in some managed team.

        """

        return super().get_users_in_some_team()

    def get_available_team_id(self) -> str:
        """
        Get a team ID that no other team managed by this team has.

        Returns
        -------
        str
            A unique team ID.

        Raises
        ------
        GameWithAreasError.GameTooManyTeamsError
            If the game with areas is already managing its maximum number of teams.

        """

        try:
            return super().get_available_team_id()
        except GameError.GameTooManyTeamsError:
            return GameWithAreasError.GameTooManyTeamsError

    def is_unmanaged(self):
        """
        Return True if this game with areas is unmanaged, False otherwise.

        Returns
        -------
        bool
            True if unmanaged, False otherwise.

        """

        return super().is_unmanaged()

    def destroy(self):
        """
        Mark this game with areas as destroyed and notify its manager so that it is deleted.
        If the game with areas is already destroyed, this function does nothing.
        A game with areas marked for destruction will delete all of its timers, teams, remove all
        its players and unsubscribe it from updates of its former players.

        This method is reentrant (it will do nothing though).

        Returns
        -------
        None.

        """

        self.unchecked_destroy()
        self.manager._check_structure()
        self._check_structure()  # Manager will not check this otherwise.

    def _on_client_inbound_ms_check(
        self,
        player: ClientManager.Client,
        contents: Dict[str, Any] = None
        ):
        """
        Default callback for game with areas player signaling it wants to check if sending an IC
        message is appropriate. The IC arguments can be passed by reference, so this also serves as
        an opportunity to modify the IC message if neeeded.

        To indicate a message should not be sent, some TsuserverException can be raised. The
        message of the exception will be sent to the client.

        Parameters
        ----------
        player : ClientManager.Client
            Player that wants to send the IC message.
        contents : Dict[str, Any], optional
            Arguments of the IC message as indicated in AOProtocol.

        Returns
        -------
        None.

        """

        super()._on_client_inbound_ms_check(player, contents=contents)

    def _on_client_inbound_ms_final(
        self,
        player: ClientManager.Client,
        contents: Dict[str, Any] = None
        ):
        """
        Default callback for game with areas player signaling it has sent an IC message.
        This callback is executed after the server is done making all modifications to the MS packet
        sent by the server.

        By default does nothing.

        Parameters
        ----------
        player : ClientManager.Client
            Player that signaled it has sent an IC message.
        contents : Dict[str, Any], optional
            Arguments of the IC message as indicated in AOProtocol.

        Returns
        -------
        None.

        """

        super()._on_client_inbound_ms_final(player, contents=contents)

    def _on_client_change_character(
        self,
        player: ClientManager.Client,
        old_char_id: Union[int, None] = None,
        new_char_id: Union[int, None] = None
        ):
        """
        Default callback for game with areas player signaling it has changed character.

        By default it only checks if the player is now no longer having a character. If that is
        the case and the game requires all players have characters, the player is automatically
        removed.

        Parameters
        ----------
        player : ClientManager.Client
            Player that signaled it has changed character.
        old_char_id : int, optional
            Previous character ID. The default is None.
        new_char_id : int, optional
            New character ID. The default is None.

        Returns
        -------
        None.

        """

        super()._on_client_change_character(
            player,
            old_char_id=old_char_id,
            new_char_id=new_char_id
        )

    def _on_client_destroyed(self, player: ClientManager.Client):
        """
        Default callback for game with areas player signaling it was destroyed, for example, as a
        result of a disconnection.

        By default it only removes the player from the game with areas. If the game with areas is
        already unmanaged or the player is not in the game with areas, this callback does nothing.

        Parameters
        ----------
        player : ClientManager.Client
            Player that signaled it was destroyed.

        Returns
        -------
        None.

        """

        super()._on_client_destroyed(player)

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
        else other than some manager code, as otherwise the manager will not recognize the
        game with areas.

        Parameters
        ----------
        server : TsuserverDR
            Server the game with areas belongs to.
        manager : GameWithAreasManager
            Manager for this game with areas.
        game_id : str
            Identifier of the game with areas.
        player_limit : Union[int, None], optional
            If an int, it is the maximum number of players the game with areas supports. If None, it
            indicates the game with areas has no player limit. Defaults to None.
        player_concurrent_limit : Union[int, None], optional
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
        team_limit : Union[int, None], optional
            If an int, it is the maximum number of teams the game with areas supports. If None, it
            indicates the game with areas has no team limit. Defaults to None.
        timer_limit : Union[int, None], optional
            If an int, it is the maximum number of timers the game with areas supports. If None, it
            indicates the game with areas has no timer limit. Defaults to None.
        area_concurrent_limit : Union[int, None], optional
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
            If the game with areas was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameWithAreasError.UserNotInAreaError
            If the user is not in an area part of the game with areas.
        GameWithAreasError.UserHasNoCharacterError
            If the user has no character but the game with areas requires that all players have
            characters.
        GameWithAreasError.UserNotInvitedError
            If the game with areas requires players be invited to be added and the user is not
            invited.
        GameWithAreasError.UserAlreadyPlayerError
            If the user to add is already a user of the game with areas.
        GameWithAreasError.UserHitGameConcurrentLimitError
            If the player has reached the concurrent player membership of any of the game with areas
            managed by the manager of this game with areas, or by virtue of joining this
            game with areas they would violate this game with areas's concurrent player membership limit.
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
        Add an area to this game with areas's set of areas.

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
            If `area` has reached the concurrent area membership limit of any of the games with
            areas it belongs to managed by this manager, or by virtue of adding this area it will
            violate this game with areas's concurrent area membership limit.

        """

        self.unchecked_add_area(area)
        self._check_structure()

    def unchecked_add_area(self, area: AreaManager.Area):
        """
        Add an area to this game with area's set of areas.

        This method does not assert structural integrity.

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
            If `area` has reached the concurrent area membership limit of any of the games with
            areas it belongs to managed by this manager, or by virtue of adding this area it will
            violate this game with areas's concurrent area membership limit.

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

    def remove_area(self, area: AreaManager.Area):
        """
        Remove an area from this game with area's set of areas.
        If the area is already a part of the game with areas, do nothing.
        If any player of the game with areas is in this area, they are removed from the
        game with areas.
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

        self.unchecked_remove_area(area)
        self._check_structure()

    def unchecked_remove_area(self, area: AreaManager.Area):
        """
        Remove an area from this game with area's set of areas.
        If the area is already a part of the game with areas, do nothing.
        If any player of the game with areas is in this area, they are removed from the
        game with areas.
        If the game with areas has no areas remaining, it will be automatically destroyed.

        This method does not assert structural integrity.

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
            self.unchecked_remove_player(player)
        # Remove area only after removing all players to prevent structural checks failing
        self._areas.discard(area)
        self.listener.unsubscribe(area)
        self.manager._remove_area_from_mapping(area, self)
        if not self._areas:
            self.unchecked_destroy()

    def has_area(self, area: AreaManager.Area) -> bool:
        """
        If the area is part of this game with areas's set of areas, return True; otherwise, return
        False.

        Parameters
        ----------
        area : AreaManager.Area
            Area to check.

        Returns
        -------
        bool
            True if the area is part of the game with areas's set of areas, False otherwise.

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
        Return all users in areas part of the game with areas that are not players of the
        game with areas.

        Returns
        -------
        Set[ClientManager.Client]
            All users in areas part of the game with areas that are not players of the
            game with areas.

        """

        return {client for client in self.get_users_in_areas() if not self.is_player(client)}

    def unchecked_destroy(self):
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
            self.unchecked_remove_area(area)
        super().unchecked_destroy()

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
                f'team_limit={self.get_team_limit()}, '
                f'timer_limit={self.get_timer_limit()}, '
                f'areas={self.get_areas()}) || '
                f'players={self.get_players()}, '
                f'invitations={self.get_invitations()}, '
                f'leaders={self.get_leaders()}, '
                f'timers={self.get_timers()}, '
                f'teams={self.get_teams()}')

    def _on_area_client_left_final(
        self,
        area: AreaManager.Area,
        client: ClientManager.Client = None,
        old_displayname: str = None,
        ignore_bleeding: bool = False,
        ignore_autopass: bool = False,
        ):
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
            self.unchecked_remove_player(client)

        self._check_structure()

    def _on_area_client_entered_final(
        self,
        area: AreaManager.Area,
        client: ClientManager.Client = None,
        old_area: AreaManager.Area = None,
        old_displayname: str = None,
        ignore_bleeding: bool = False,
        ignore_autopass: bool = False,
        ):
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
            self.unchecked_add_player(client)

        self._check_structure()

    def _on_area_client_inbound_ms_check(
        self,
        area: AreaManager.Area,
        client: ClientManager.Client = None,
        contents: Dict[str, Any] = None
        ):
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
        contents : Dict[str, Any]
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

        By default it calls self.unchecked_remove_area(area).

        Parameters
        ----------
        area : AreaManager.Area
            Area that signaled it was destroyed.

        Returns
        -------
        None.

        """

        # print('Received DESTRUCTION', area)
        self.unchecked_remove_area(area)

        self._check_structure()

    def _on_areas_loaded(self, area_manager: AreaManager):
        """
        Default callback for server area manager signaling it loaded new areas.

        By default it calls self.destroy().

        Parameters
        ----------
        area_manager : AreaManager
            AreaManager that signaled the areas load.

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


class _GameWithAreasManagerTrivialInherited(GameManager):
    """
    This class should not be instantiated.
    """

    def get_managee_type(self) -> Type[_GameWithAreas]:
        """
        Return the type of the game with areas that will be constructed by default with a call of
        `new_managee`.

        Returns
        -------
        Type[_GameWithAreas]
            Type of the game with areas.

        """

        return super().get_managee_type()

    def delete_managee(self, managee: _GameWithAreas) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a game with areas managed by this manager, so all its players no longer belong to
        this game with areas.

        Parameters
        ----------
        managee : _GameWithAreas
            The game with areas to delete.

        Returns
        -------
        Tuple[str, Set[ClientManager.Client]]
            The ID and players of the game with areas that was deleted.

        Raises
        ------
        GameWithAreasError.ManagerDoesNotManageGameError
            If the manager does not manage the target game with areas.

        """

        game_id, game_players = self.unchecked_delete_managee(managee)
        self._check_structure()
        return game_id, game_players

    def unchecked_delete_managee(
        self,
        managee: _GameWithAreas
        ) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a game with areas managed by this manager, so all its players no longer belong to
        this game with areas.

        Parameters
        ----------
        managee : _GameWithAreas
            The game with areas to delete.

        Returns
        -------
        Tuple[str, Set[ClientManager.Client]]
            The ID and players of the game with areas that was deleted.

        Raises
        ------
        GameWithAreasError.ManagerDoesNotManageGameError
            If the manager does not manage the target game with areas.

        """

        try:
            return super().unchecked_delete_managee(managee)
        except GameError.ManagerDoesNotManageGameError:
            raise GameWithAreasError.ManagerDoesNotManageGameError

    def manages_managee(self, game: _GameWithAreas):
        """
        Return True if the game with areas is managed by this manager, False otherwise.

        Parameters
        ----------
        game : _GameWithAreas
            The game to check.

        Returns
        -------
        bool
            True if the manager manages this game with areas, False otherwise.

        """

        return super().manages_managee(game)

    def get_managees(self):
        """
        Return (a shallow copy of) the games with areas this manager manages.

        Returns
        -------
        Set[_GameWithAreas]
            Games with areas this manager manages.

        """

        return super().get_managees()

    def get_managee_by_id(self, managee_id: str) -> _GameWithAreas:
        """
        If `managee_id` is the ID of a game with areas managed by this manager, return that.

        Parameters
        ----------
        managee_id : str
            ID of the game with areas this manager manages.

        Returns
        -------
        _GameWithAreas
            The game with areas with that ID.

        Raises
        ------
        GameWithAreasError.ManagerInvalidGameIDError
            If `game_id` is not the ID of a game with areas this manager manages.

        """

        try:
            return super().get_managee_by_id(managee_id)
        except GameError.ManagerInvalidGameIDError:
            raise GameWithAreasError.ManagerInvalidGameIDError

    def get_managee_limit(self) -> Union[int, None]:
        """
        Return the game with areas limit of this manager.

        Returns
        -------
        Union[int, None]
            Game with areas limit.

        """

        return super().get_managee_limit()

    def get_managee_ids(self) -> Set[str]:
        """
        Return (a shallow copy of) the IDs of all games with areas managed by this manager.

        Returns
        -------
        Set[str]
            The IDs of all managed games with areas.

        """

        return super().get_managee_ids()

    def get_managee_ids_to_managees(self) -> Dict[str, _GameWithAreas]:
        """
        Return a mapping of the IDs of all games with areas managed by this manager to their
        associated game with areas.

        Returns
        -------
        Dict[str, _GameWithAreas]
            Mapping.
        """

        return super().get_managee_ids_to_managees()

    def get_managees_of_user(self, user: ClientManager.Client):
        """
        Return (a shallow copy of) the games with areas managed by this manager user `user` is a
        player of. If the user is part of no such game with areas, an empty set is returned.

        Parameters
        ----------
        user : ClientManager.Client
            User whose games with areas will be returned.

        Returns
        -------
        Set[_GameWithAreas]
            Games with areas the player belongs to.

        """

        return super().get_managees_of_user(user)

    def get_managees_of_players(self) -> Dict[ClientManager.Client, Set[_GameWithAreas]]:
        """
        Return a mapping of the players part of any game with areas managed by this manager to the
        game with areas managed by this manager such players belong to.

        Returns
        -------
        Dict[ClientManager.Client, Set[_GameWithAreas]]
            Mapping.
        """

        return super().get_managees_of_players()

    def get_users_in_some_managee(self) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) all the users that are part of some game with areas managed by
        this manager.

        Returns
        -------
        Set[ClientManager.Client]
            Users in some managed game with areas.

        """

        return super().get_users_in_some_managee()

    def is_managee_creatable(self) -> bool:
        """
        Return whether a new game with areas can currently be created without creating one.

        Returns
        -------
        bool
            True if a game with areas can be currently created, False otherwise.
        """

        return super().is_managee_creatable()

    def get_id(self) -> str:
        """
        Return the ID of this manager. This ID is guaranteed to be unique among
        simultaneously existing Python objects.

        Returns
        -------
        str
            ID.

        """

        return super().get_id()

    def find_player_concurrent_limiting_managee(
        self,
        user: ClientManager.Client
        ) -> Union[_GameWithAreas, None]:
        """
        For user `user`, find a game with areas `most_restrictive_game` managed by this manager such
        that, if `user` were to join another game with areas managed by this manager, they would
        violate `most_restrictive_game`'s concurrent player membership limit.
        If no such game with areas exists (or the player is not member of any game with areas
        managed by this manager), return None.
        If multiple such games with areas exist, any one of them may be returned.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Returns
        -------
        Union[_GameWithAreas, None]
            Limiting game with areas as previously described if it exists, None otherwise.

        """

        return super().find_player_concurrent_limiting_managee(user)

class GameWithAreasManager(_GameWithAreasManagerTrivialInherited):
    """
    A game with areas manager is a game manager with dedicated area management functions.

    Attributes
    ----------
    server : TsuserverDR
        Server the game manager belongs to.
    """

    # (Private) Attributes
    # --------------------
    # _area_to_games : Dict[AreaManager.Area, Set[_GameWithAreas]]
    #   Mapping of areas to games with areas that this manager manages.

    # Invariants
    # ----------
    # 1. For every area `area` in `self._area_to_games.keys()`:
    #     a. `self._area_to_games[area]` is a non-empty set.
    #     b. `self._area_to_games[area]` is a subset of `self.get_managees()
    #     c. For every game with areas `game` in `self._area_to_games[area]`, `area` belongs to
    #        `game`.
    # 2. For every area `area` in `self._area_to_games.keys()`:
    #     a. For every game with areas `game` in `self._area_to_games[area]`:
    #           1. `game` has no area concurrent membership limit, or it is at least the length
    #               of `self._area_to_games[area]`.
    # 3. The invariants of the parent class are maintained.

    def __init__(
        self,
        server: TsuserverDR,
        managee_limit: Union[int, None] = None,
        default_managee_type: Type[_GameWithAreas] = None,
        ):
        """
        Create a game with areas manager object.

        Parameters
        ----------
        server : TsuserverDR
            The server this game manager belongs to.
        managee_limit : int, optional
            The maximum number of games with areas this manager can handle. Defaults to None
            (no limit).
        default_managee_type : Type[_GameWithAreas], optional
            The default type of game with areas this manager will create. Defaults to None (and then
            converted to _GameWithAreas).

        """

        if default_managee_type is None:
            default_managee_type = _GameWithAreas
        self._area_to_games: Dict[AreaManager.Area, Set[_GameWithAreas]] = dict()

        super().__init__(
            server,
            managee_limit=managee_limit,
            default_managee_type=default_managee_type
        )

    def new_managee(
        self,
        managee_type: Type[_GameWithAreas] = None,
        creator: Union[ClientManager.Client, None] = None,
        player_limit: Union[int, None] = None,
        player_concurrent_limit: Union[int, None] = 1,
        require_invitations: bool = False,
        require_players: bool = True,
        require_leaders: bool = True,
        require_character: bool = False,
        team_limit: Union[int, None] = None,
        timer_limit: Union[int, None] = None,
        areas: Set[AreaManager.Area] = None,
        area_concurrent_limit: Union[int, None] = None,
        autoadd_on_client_enter: bool = False,
        **kwargs: Any,
        ) -> _GameWithAreas:
        """
        Create a new game with areas managed by this manager.

        Parameters
        ----------
        managee_type : Type[_GameWithAreas], optional
            Class of game with areas that will be produced. Defaults to None (and converted to the
            default game with areas created by this game with areas manager).
        creator : Union[ClientManager.Client, None], optional
            The player who created this game with areas. If set, they will also be added to the
            game with areas. Defaults to None.
        player_limit : Union[int, None], optional
            If an int, it is the maximum number of players the game with areas supports. If None, it
            indicates the game with areas has no player limit. Defaults to None.
        player_concurrent_limit : Union[int, None], optional
            If an int, it is the maximum number of games with areas managed by `self` that any
            player of this game with areas to create may belong to, including this game with areas
            to create. If None, it indicates that this game with areas does not care about how many
            other games with areas managed by `self` each of its players belongs to. Defaults to 1
            (a player may not be in another game managed by `self` while in this game).
        require_invitations : bool, optional
            If True, users can only be added to the game with areas if they were previously invited.
            If False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the game with areas loses all its players, the game with areas
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
        team_limit : Union[int, None], optional
            If an int, it is the maximum number of teams the game with areas will support. If None,
            it indicates the game with areas will have no team limit. Defaults to None.
        timer_limit : Union[int, None], optional
            If an int, it is the maximum number of timers the game with areas will support. If None,
            it indicates the game with areas will have no timer limit. Defaults to None.
        areas : Set[AreaManager.Area], optional
            The areas to add to the game with areas when creating it. Defaults to None (and
            converted to an empty set).
        area_concurrent_limit : Union[int, None]
            The concurrent area membership limit of this game with areas. Defaults to None.
        autoadd_on_client_enter: bool
            If the game with areas will always attempt to add nonplayer users who enter an area
            part of the game with areas. Defaults to False.
        **kwargs : Any
            Additional arguments to consider when producing the game with areas.

        Returns
        -------
        _GameWithAreas
            The created game with areas.

        Raises
        ------
        GameWithAreasError.ManagerTooManyGamesError
            If the manager is already managing its maximum number of games.
        Any error from the created game with areas's add_player(creator)
            If the game with areas cannot add `creator` as a player if given one.

        """

        game = self.unchecked_new_managee(
            managee_type=managee_type,
            creator=creator,
            player_limit=player_limit,
            player_concurrent_limit=player_concurrent_limit,
            require_invitations=require_invitations,
            require_players=require_players,
            require_leaders=require_leaders,
            # kwargs
            require_character=require_character,
            team_limit=team_limit,
            timer_limit=timer_limit,
            areas=areas,
            area_concurrent_limit=area_concurrent_limit,
            autoadd_on_client_enter=autoadd_on_client_enter,
            **kwargs,
            )
        self._check_structure()
        return game

    def unchecked_new_managee(
        self,
        managee_type: Type[_GameWithAreas] = None,
        creator: Union[ClientManager.Client, None] = None,
        player_limit: Union[int, None] = None,
        player_concurrent_limit: Union[int, None] = 1,
        require_invitations: bool = False,
        require_players: bool = True,
        require_leaders: bool = True,
        require_character: bool = False,
        team_limit: Union[int, None] = None,
        timer_limit: Union[int, None] = None,
        areas: Set[AreaManager.Area] = None,
        area_concurrent_limit: Union[int, None] = None,
        autoadd_on_client_enter: bool = False,
        **kwargs: Any,
        ) -> _GameWithAreas:

        """
        Create a new game with areas managed by this manager.

        Parameters
        ----------
        managee_type : Type[_GameWithAreas], optional
            Class of game with areas that will be produced. Defaults to None (and converted to the
            default game with areas created by this game with areas manager).
        creator : Union[ClientManager.Client, None], optional
            The player who created this game with areas. If set, they will also be added to the
            game with areas. Defaults to None.
        player_limit : Union[int, None], optional
            If an int, it is the maximum number of players the game with areas supports. If None, it
            indicates the game with areas has no player limit. Defaults to None.
        player_concurrent_limit : Union[int, None], optional
            If an int, it is the maximum number of games with areas managed by `self` that any
            player of this game with areas to create may belong to, including this game with areas
            to create. If None, it indicates that this game with areas does not care about how many
            other games with areas managed by `self` each of its players belongs to. Defaults to 1
            (a player may not be in another game managed by `self` while in this game).
        require_invitations : bool, optional
            If True, users can only be added to the game with areas if they were previously invited.
            If False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the game with areas loses all its players, the game with areas
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
        team_limit : Union[int, None], optional
            If an int, it is the maximum number of teams the game with areas will support. If None,
            it indicates the game with areas will have no team limit. Defaults to None.
        timer_limit : Union[int, None], optional
            If an int, it is the maximum number of timers the game with areas will support. If None,
            it indicates the game with areas will have no timer limit. Defaults to None.
        areas : Set[AreaManager.Area], optional
            The areas to add to the game with areas when creating it. Defaults to None (and
            converted to an empty set).
        area_concurrent_limit : Union[int, None]
            The concurrent area membership limit of this game with areas. Defaults to None.
        autoadd_on_client_enter: bool
            If the game with areas will always attempt to add nonplayer users who enter an area
            part of the game with areas. Defaults to False.
        **kwargs : Any
            Additional arguments to consider when producing the game with areas.

        Returns
        -------
        _GameWithAreas
            The created game with areas.

        Raises
        ------
        GameWithAreasError.ManagerTooManyGamesError
            If the manager is already managing its maximum number of games.
        Any error from the created game with areas's add_player(creator)
            If the game with areas cannot add `creator` as a player if given one.

        """

        if managee_type is None:
            managee_type = self.get_managee_type()

        if not self.is_managee_creatable():
            raise GameWithAreasError.ManagerTooManyGamesError

        game: _GameWithAreas = super().new_managee(
            managee_type=managee_type,
            creator=None,  # Manually none
            player_limit=player_limit,
            player_concurrent_limit=player_concurrent_limit,
            require_invitations=require_invitations,
            require_players=require_players,
            require_leaders=require_leaders,
            require_character=require_character,
            team_limit=team_limit,
            timer_limit=timer_limit,
            # kwargs
            area_concurrent_limit=area_concurrent_limit,
            autoadd_on_client_enter=autoadd_on_client_enter,
            **kwargs,
        )

        try:
            for area in areas:
                game.unchecked_add_area(area)
        except GameWithAreasError as ex:
            # Discard game
            self.unchecked_delete_managee(game)
            raise ex

        # Add creator manually. This is because adding it via .new_game will yield errors because
        # the areas are not added until the section before.
        try:
            if creator:
                game.unchecked_add_player(creator)
        except GameWithAreasError as ex:
            # Discard game
            self.unchecked_delete_managee(game)
            raise ex

        return game

    def get_available_managee_id(self):
        """
        Get a game with areas ID that no other game with areas managed by this manager has.

        Returns
        -------
        str
            A unique game with areas ID.

        Raises
        ------
        GameWithAreasError.ManagerTooManyGamesError
            If the manager is already managing its maximum number of games.

        """

        game_number = 0
        game_limit = self.get_managee_limit()
        while game_limit is None or game_number < game_limit:
            new_game_id = "gwa{}".format(game_number)
            if new_game_id not in self.get_managee_ids():
                return new_game_id
            game_number += 1
        raise GameWithAreasError.ManagerTooManyGamesError

    def get_managees_in_area(self, area) -> Set[_GameWithAreas]:
        """
        Return (a shallow copy of) the all games with areas managed by this manager that contain
        the given area.

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

    def find_area_concurrent_limiting_managee(
        self,
        area: AreaManager.Area
        ) -> Union[_GameWithAreas, None]:
        """
        For area `area`, find a game with areas `most_restrictive_game` managed by this manager
        such that, if `area` were to be added to another game with areas managed by this manager,
        they would violate `most_restrictive_game`'s concurrent area membership limit.
        If no such game with areas exists (or the area is not an area of any game with areas
        managed by this  manager), return None.
        If multiple such games with areas exist, any one of them may be returned.

        Parameters
        ----------
        area : AreaManager.Area
            Area to test.

        Returns
        -------
        Union[_GameWithAreas, None]
            Limiting game with areas as previously described if it exists, None otherwise.

        """

        games = self.get_managees_in_area(area)
        if not games:
            return None

        # We only care about games that establish a concurrent area membership limit
        games_with_limit = {game for game in games
                            if game.get_area_concurrent_limit() is not None}
        if not games_with_limit:
            return None

        # It just suffices to analyze the game with the smallest limit, because:
        # 1. If the area is part of at least as many games with areas as this game with area's
        #    limit, this game with areas is an example game with areas that can be returned.
        # 2. Otherwise, no other games with areas exist due to the minimality condition.
        most_restrictive_game: _GameWithAreas = min(
            games_with_limit, key=lambda game: game.get_area_concurrent_limit())
        if len(games) < most_restrictive_game.get_area_concurrent_limit():
            return None
        return most_restrictive_game

    def get_managees_of_areas(self) -> Dict[ClientManager.Client, Set[_GameWithAreas]]:
        """
        Return a mapping of the areas part of any game with areas managed by this manager to the
        game with areas managed by this manager such players belong to.

        Returns
        -------
        Dict[ClientManager.Client, Set[_GameWithAreas]]
            Mapping.
        """

        # Implementation detail
        # This is essentially a public view of self._area_to_games

        output = dict()
        for (area, games) in self._area_to_games.items():
            output[area] = games.copy()

        return output

    def _add_area_to_mapping(self, area: AreaManager.Area, game: _GameWithAreas):
        """
        Update the area to game with areas mapping with the information that `area` was added to
        `game`.

        Parameters
        ----------
        area : AreaManager.Area
            Area that was added.
        game : _GameWithAreas
            Game with areas that `area` was added to.

        Raises
        ------
        GameWithAreasError.AreaHitGameConcurrentLimitError.
            If `area` has reached the concurrent area membership limit of any of the games with areas it
            belongs to managed by this manager, or by virtue of adding this area to `game` it
            will violate this game with area's concurrent area membership limit.

        """

        if self.find_area_concurrent_limiting_managee(area):
            raise GameWithAreasError.AreaHitGameConcurrentLimitError

        try:
            self._area_to_games[area].add(game)
        except KeyError:
            self._area_to_games[area] = {game}

    def _remove_area_from_mapping(self, area: AreaManager.Area, game: _GameWithAreas):
        """
        Update the area to game with areas mapping with the information that `area` was removed
        from `game`.
        If the area is already not associated with that game with areas, or is not part of the
        mapping, this method will not do anything.

        Parameters
        ----------
        area : AreaManager.Area
            Area that was removed.
        game : _GameWithAreas
            Game with areas that `area` was removed from.

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
                       f'to game with areas mapping be a area of its associated game with areas '
                       f'{game}, but found that was not the case. || {self}')
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
                       f'with areas {game} belonged to at most the concurrent area membership '
                       f'limit of that game with areas of {limit} game{"s" if limit != 1 else ""} '
                       f'with areas, found it belonged to {membership} '
                       f'game{"s" if membership != 1 else ""} with areas. || {self}')
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

        return (f"GameWithAreasManager(server, managee_limit={self.get_managee_limit()}, "
                f"default_managee_type={self.get_managee_type()}, "
                f"|| "
                f"_user_to_managees={self.get_managees_of_players()}, "
                f"_id_to_managee={self.get_managee_ids_to_managees()}, "
                f"_area_to_games={self.get_managees_of_areas()}, "
                f"id={self.get_id()}")
