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
Module that contains the base hubbed game class.
"""

from __future__ import annotations

import typing
from typing import Callable, Dict, Set, Any, Tuple, Type, Union

from server.exceptions import HubbedGameError, GameWithAreasError
from server.gamewithareas_manager import _GameWithAreas, GameWithAreasManager
from server.timer_manager import Timer

if typing.TYPE_CHECKING:
    # Avoid circular referencing
    from server.area_manager import AreaManager
    from server.client_manager import ClientManager
    from server.game_manager import _Team
    from server.hub_manager import _Hub
    from server.timer_manager import Timer
    from server.tsuserver import TsuserverDR


class _HubbedGameTrivialInherited(_GameWithAreas):
    """
    This class should not be instantiated.
    """

    def get_id(self) -> str:
        """
        Return the ID of this hubbed game.

        Returns
        -------
        str
            The ID.

        """

        return super().get_id()

    def get_numerical_id(self) -> int:
        """
        Return the numerical portion of the ID of this hubbed game.

        Returns
        -------
        int
            Numerical portion of the ID.
        """

        return super().get_numerical_id()

    def get_name(self) -> str:
        """
        Get the name of the hubbed game.

        Returns
        -------
        str
            Name.
        """

        return super().get_name()

    def set_name(self, name: str):
        """
        Set the name of the hubbed game.

        Parameters
        ----------
        name : str
            Name.
        """

        self.unchecked_set_name(name)
        self.manager._check_structure()

    def unchecked_set_name(self, name: str):
        """
        Set the name of the hubbed game.

        This method does not assert structural integrity.

        Parameters
        ----------
        name : str
            Name.
        """

        super().unchecked_set_name(name)

    def get_player_limit(self) -> Union[int, None]:
        """
        Return the player membership limit of this hubbed game.

        Returns
        -------
        Union[int, None]
            The player membership limit.

        """

        return super().get_player_limit()

    def get_player_concurrent_limit(self) -> Union[int, None]:
        """
        Return the concurrent player membership limit of this hubbed game.

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
        Return (a shallow copy of) the set of players of this hubbed game that satisfy a
        condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all players returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) players of this hubbed game.

        """

        return super().get_players(cond=cond)

    def is_player(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is a player of the hubbed game.

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
        Make a user a player of the hubbed game. By default this player will not be a leader,
        unless the hubbed game has no leaders and it requires a leader.
        It will also subscribe the hubbed game to the player so it can listen to its updates.

        Parameters
        ----------
        user : ClientManager.Client
            User to add to the hubbed game. They must be in an area part of the hubbed game.

        Raises
        ------
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.UserNotInAreaError
            If the user is not in an area part of the hubbed game.
        HubbedGameError.UserHasNoCharacterError
            If the user has no character but the hubbed game requires that all players have
            characters.
        HubbedGameError.UserNotInvitedError
            If the hubbed game requires players be invited to be added and the user is not
            invited.
        HubbedGameError.UserAlreadyPlayerError
            If the user to add is already a user of the hubbed game.
        HubbedGameError.UserHitGameConcurrentLimitError
            If the player has reached the concurrent player membership of any of the hubbed game
            managed by the manager of this hubbed game, or by virtue of joining this
            hubbed game they would violate this hubbed game's concurrent player membership
            limit.
        HubbedGameError.GameIsFullError
            If the hubbed game reached its player limit.

        """

        self.unchecked_add_player(user)
        self.manager._check_structure()

    def unchecked_add_player(self, user: ClientManager.Client):
        """
        Make a user a player of the hubbed game. By default this player will not be a leader,
        unless the hubbed game has no leaders and it requires a leader.
        It will also subscribe the hubbed game to the player so it can listen to its updates.

        Parameters
        ----------
        user : ClientManager.Client
            User to add to the hubbed game. They must be in an area part of the hubbed game.

        Raises
        ------
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.UserNotInAreaError
            If the user is not in an area part of the hubbed game.
        HubbedGameError.UserHasNoCharacterError
            If the user has no character but the hubbed game requires that all players have
            characters.
        HubbedGameError.UserNotInvitedError
            If the hubbed game requires players be invited to be added and the user is not
            invited.
        HubbedGameError.UserAlreadyPlayerError
            If the user to add is already a user of the hubbed game.
        HubbedGameError.UserHitGameConcurrentLimitError
            If the player has reached the concurrent player membership of any of the hubbed game
            managed by the manager of this hubbed game, or by virtue of joining this
            hubbed game they would violate this hubbed game's concurrent player membership
            limit.
        HubbedGameError.GameIsFullError
            If the hubbed game reached its player limit.

        """

        try:
            super().unchecked_add_player(user)
        except GameWithAreasError.GameIsUnmanagedError:
            raise HubbedGameError.GameIsUnmanagedError
        except GameWithAreasError.UserNotInAreaError:
            raise HubbedGameError.UserNotInAreaError
        except GameWithAreasError.UserHasNoCharacterError:
            raise HubbedGameError.UserHasNoCharacterError
        except GameWithAreasError.UserNotInvitedError:
            raise HubbedGameError.UserNotInvitedError
        except GameWithAreasError.UserAlreadyPlayerError:
            raise HubbedGameError.UserAlreadyPlayerError
        except GameWithAreasError.UserHitGameConcurrentLimitError:
            raise HubbedGameError.UserHitGameConcurrentLimitError
        except GameWithAreasError.GameIsFullError:
            raise HubbedGameError.GameIsFullError

    def remove_player(self, user: ClientManager.Client):
        """
        Make a user be no longer a player of this hubbed game. If they were part of a team
        managed by this hubbed game, they will also be removed from said team. It will also
        unsubscribe the hubbed game from the player so it will no longer listen to its updates.

        If the hubbed game required that there it always had players and by calling this method
        the hubbed game had no more players, the hubbed game will automatically be scheduled
        for deletion.

        Parameters
        ----------
        user : ClientManager.Client
            User to remove.

        Raises
        ------
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.UserNotPlayerError
            If the user to remove is already not a player of this hubbed game.

        """

        self.unchecked_remove_player(user)
        self.manager._check_structure()

    def unchecked_remove_player(self, user: ClientManager.Client):
        """
        Make a user be no longer a player of this hubbed game. If they were part of a team
        managed by this hubbed game, they will also be removed from said team. It will also
        unsubscribe the hubbed game from the player so it will no longer listen to its updates.

        If the hubbed game required that there it always had players and by calling this method
        the hubbed game had no more players, the hubbed game will automatically be scheduled
        for deletion.

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to remove.

        Raises
        ------
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.UserNotPlayerError
            If the user to remove is already not a player of this hubbed game.

        """
        try:
            super().unchecked_remove_player(user)
        except GameWithAreasError.GameIsUnmanagedError:
            raise HubbedGameError.GameIsUnmanagedError
        except GameWithAreasError.UserNotPlayerError:
            raise HubbedGameError.UserNotPlayerError

    def requires_players(self) -> bool:
        """
        Return whether the hubbed game requires players at all times.

        Returns
        -------
        bool
            Whether the hubbed game requires players at all times.
        """

        return super().requires_players()

    def get_invitations(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
        ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of invited users of this hubbed game that satisfy a
        condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all invited users returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) invited users of this hubbed game.

        """

        return super().get_invitations(cond=cond)

    def is_invited(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is invited to the hubbed game.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Raises
        ------
        HubbedGameError.UserAlreadyPlayerError
            If the user is a player of this hubbed game.

        Returns
        -------
        bool
            True if the user is invited, False otherwise.

        """

        try:
            return super().is_invited(user)
        except GameWithAreasError.UserAlreadyPlayerError:
            raise HubbedGameError.UserAlreadyPlayerError

    def add_invitation(self, user: ClientManager.Client):
        """
        Mark a user as invited to this hubbed game.

        Parameters
        ----------
        user : ClientManager.Client
            User to invite to the hubbed game.

        Raises
        ------
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.GameDoesNotTakeInvitationsError
            If the hubbed game does not require users be invited to the hubbed game.
        HubbedGameError.UserAlreadyInvitedError
            If the player to invite is already invited to the hubbed game.
        HubbedGameError.UserAlreadyPlayerError
            If the player to invite is already a player of the hubbed game.

        """

        self.unchecked_add_invitation(user)
        self.manager._check_structure()

    def unchecked_add_invitation(self, user: ClientManager.Client):
        """
        Mark a user as invited to this hubbed game.

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to invite to the hubbed game.

        Raises
        ------
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.GameDoesNotTakeInvitationsError
            If the hubbed game does not require users be invited to the hubbed game.
        HubbedGameError.UserAlreadyInvitedError
            If the player to invite is already invited to the hubbed game.
        HubbedGameError.UserAlreadyPlayerError
            If the player to invite is already a player of the hubbed game.

        """

        try:
            super().unchecked_add_invitation(user)
        except GameWithAreasError.GameIsUnmanagedError:
            raise HubbedGameError.GameIsUnmanagedError
        except GameWithAreasError.GameDoesNotTakeInvitationsError:
            raise HubbedGameError.GameDoesNotTakeInvitationsError
        except GameWithAreasError.UserAlreadyInvitedError:
            raise HubbedGameError.UserAlreadyInvitedError
        except GameWithAreasError.UserAlreadyPlayerError:
            raise HubbedGameError.UserAlreadyPlayerError

    def remove_invitation(self, user: ClientManager.Client):
        """
        Mark a user as no longer invited to this hubbed game (uninvite).

        Parameters
        ----------
        user : ClientManager.Client
            User to uninvite.

        Raises
        ------
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.GameDoesNotTakeInvitationsError
            If the hubbed game does not require users be invited to the hubbed game.
        HubbedGameError.UserNotInvitedError
            If the user to uninvite is already not invited to this hubbed game.

        """

        self.unchecked_remove_invitation(user)
        self.manager._check_structure()

    def unchecked_remove_invitation(self, user: ClientManager.Client):
        """
        Mark a user as no longer invited to this hubbed game (uninvite).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to uninvite.

        Raises
        ------
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.GameDoesNotTakeInvitationsError
            If the hubbed game does not require users be invited to the hubbed game.
        HubbedGameError.UserNotInvitedError
            If the user to uninvite is already not invited to this hubbed game.

        """

        try:
            super().unchecked_remove_invitation(user)
        except GameWithAreasError.GameIsUnmanagedError:
            raise HubbedGameError.GameIsUnmanagedError
        except GameWithAreasError.GameDoesNotTakeInvitationsError:
            raise HubbedGameError.GameDoesNotTakeInvitationsError
        except GameWithAreasError.UserNotInvitedError:
            raise HubbedGameError.UserNotInvitedError

    def requires_invitations(self):
        """
        Return True if the hubbed game requires players be invited before being allowed to join
        the hubbed game, False otherwise.

        Returns
        -------
        bool
            True if the hubbed game requires players be invited before being allowed to join
            the hubbed game, False otherwise.
        """

        return super().requires_invitations()

    def get_leaders(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
        ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of leaders of this hubbed game that satisfy a condition
        if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all leaders returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) leaders of this hubbed game.

        """

        return super().get_leaders(cond=cond)

    def get_regulars(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
        ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of players of this hubbed game that are regulars and
        satisfy a condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all regulars returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) regulars of this hubbed game.

        """

        return super().get_regulars(cond=cond)

    def is_leader(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is a leader of the hubbed game.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Raises
        ------
        HubbedGameError.UserNotPlayerError
            If the player to test is not a player of this hubbed game.

        Returns
        -------
        bool
            True if the player is a user, False otherwise.

        """

        try:
            return super().is_leader(user)
        except GameWithAreasError.UserNotPlayerError:
            raise HubbedGameError.UserNotPlayerError

    def add_leader(self, user: ClientManager.Client):
        """
        Set a user as leader of this hubbed game (promote to leader).

        Parameters
        ----------
        user : ClientManager.Client
            Player to promote to leader.

        Raises
        ------
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.UserNotPlayerError
            If the player to promote is not a player of this hubbed game.
        HubbedGameError.UserAlreadyLeaderError
            If the player to promote is already a leader of this hubbed game.

        """

        self.unchecked_add_leader(user)
        self.manager._check_structure()

    def unchecked_add_leader(self, user: ClientManager.Client):
        """
        Set a user as leader of this hubbed game (promote to leader).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            Player to promote to leader.

        Raises
        ------
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.UserNotPlayerError
            If the player to promote is not a player of this hubbed game.
        HubbedGameError.UserAlreadyLeaderError
            If the player to promote is already a leader of this hubbed game.

        """

        try:
            super().unchecked_add_leader(user)
        except GameWithAreasError.GameIsUnmanagedError:
            raise HubbedGameError.GameIsUnmanagedError
        except GameWithAreasError.UserNotPlayerError:
            raise HubbedGameError.UserNotPlayerError
        except GameWithAreasError.UserAlreadyLeaderError:
            raise HubbedGameError.UserAlreadyLeaderError

    def remove_leader(self, user: ClientManager.Client):
        """
        Make a user no longer leader of this hubbed game (demote).

        Parameters
        ----------
        user : ClientManager.Client
            User to demote.

        Raises
        ------
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.UserNotPlayerError
            If the player to demote is not a player of this hubbed game.
        HubbedGameError.UserNotLeaderError
            If the player to demote is already not a leader of this hubbed game.

        """

        self.unchecked_remove_leader(user)
        self.manager._check_structure()

    def unchecked_remove_leader(self, user: ClientManager.Client):
        """
        Make a user no longer leader of this hubbed game (demote).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to demote.

        Raises
        ------
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.UserNotPlayerError
            If the player to demote is not a player of this hubbed game.
        HubbedGameError.UserNotLeaderError
            If the player to demote is already not a leader of this hubbed game.

        """

        try:
            super().unchecked_remove_leader(user)
        except GameWithAreasError.GameIsUnmanagedError:
            raise HubbedGameError.GameIsUnmanagedError
        except GameWithAreasError.UserNotPlayerError:
            raise HubbedGameError.UserNotPlayerError
        except GameWithAreasError.UserNotLeaderError:
            raise HubbedGameError.UserNotLeaderError

    def has_ever_had_players(self) -> bool:
        """
        Return True if a player has ever been added to this hubbed game, False otherwise.

        Returns
        -------
        bool
            True if the hubbed game has ever had a player added, False otherwise.

        """

        return super().has_ever_had_players()

    def requires_leaders(self) -> bool:
        """
        Return whether the hubbed game requires leaders at all times.

        Returns
        -------
        bool
            Whether the hubbed game requires leaders at all times.
        """

        return super().requires_leaders()

    def has_ever_had_players(self):
        """
        Return True if a player has ever been added to this hubbed game, False otherwise.

        Returns
        -------
        bool
            True if the hubbed game has ever had a player added, False otherwise.

        """

        return super().has_ever_had_players()

    def requires_characters(self) -> bool:
        """
        Return whether the hubbed game requires players have a character at all times.

        Returns
        -------
        bool
            Whether the hubbed game requires players have a character at all times.
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
        Create a new timer managed by this hubbed game with given parameters.

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
            If True, the hubbed game will automatically delete the timer once it is terminated
            by it ticking out or manual termination. If False, no such automatic deletion will take
            place. Defaults to True.

        Returns
        -------
        Timer
            The created timer.

        Raises
        ------
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.GameTooManyTimersError
            If the hubbed game is already managing its maximum number of timers.

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
        Create a new timer managed by this hubbed game with given parameters.

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
            If True, the hubbed game will automatically delete the timer once it is terminated
            by it ticking out or manual termination. If False, no such automatic deletion will take
            place. Defaults to True.

        Returns
        -------
        Timer
            The created timer.

        Raises
        ------
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.GameTooManyTimersError
            If the hubbed game is already managing its maximum number of timers.

        """

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
        except GameWithAreasError.GameIsUnmanagedError:
            raise HubbedGameError.GameIsUnmanagedError
        except GameWithAreasError.GameTooManyTimersError:
            raise HubbedGameError.GameTooManyTimersError

    def delete_timer(self, timer: Timer) -> str:
        """
        Delete a timer managed by this hubbed game, terminating it first if needed.

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
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.GameDoesNotManageTimerError
            If the hubbed game does not manage the target timer.

        """

        timer_id = self.unchecked_delete_timer(timer)
        self.manager._check_structure()
        return timer_id

    def unchecked_delete_timer(self, timer: Timer) -> str:
        """
        Delete a timer managed by this hubbed game, terminating it first if needed.

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
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.GameDoesNotManageTimerError
            If the hubbed game does not manage the target timer.

        """

        try:
            return super().unchecked_delete_timer(timer)
        except GameWithAreasError.GameIsUnmanagedError:
            raise HubbedGameError.GameIsUnmanagedError
        except GameWithAreasError.GameDoesNotManageTimerError:
            raise HubbedGameError.GameDoesNotManageTimerError

    def get_timers(self) -> Set[Timer]:
        """
        Return (a shallow copy of) the timers this hubbed game manages.

        Returns
        -------
        Set[Timer]
            Timers this hubbed game manages.

        """

        return super().get_timers()

    def get_timer_by_id(self, timer_id: str) -> Timer:
        """
        If `timer_tag` is the ID of a timer managed by this hubbed game, return that timer.

        Parameters
        ----------
        timer_id: str
            ID of timer this hubbed game manages.

        Returns
        -------
        Timer
            The timer whose ID matches the given ID.

        Raises
        ------
        HubbedGameError.GameInvalidTimerIDError:
            If `timer_tag` is a str and it is not the ID of a timer this hubbed game manages.

        """

        try:
            return super().get_timer_by_id(timer_id)
        except GameWithAreasError.GameInvalidTimerIDError:
            raise HubbedGameError.GameInvalidTimerIDError

    def get_timer_limit(self) -> Union[int, None]:
        """
        Return the timer limit of this hubbed game.

        Returns
        -------
        Union[int, None]
            Timer limit.

        """

        return super().get_timer_limit()

    def get_timer_ids(self) -> Set[str]:
        """
        Return (a shallow copy of) the IDs of all timers managed by this hubbed game.

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
        Create a new team managed by this hubbed game.

        Parameters
        ----------
        team_type : _Team
            Class of team that will be produced. Defaults to None (and converted to the
            default team created by games, namely, _Team).
        creator : ClientManager.Client, optional
            The player who created this team. If set, they will also be added to the team if
            possible. The creator must be a player of this hubbed game. Defaults to None.
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
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.GameTooManyTeamsError
            If the hubbed game is already managing its maximum number of teams.
        HubbedGameError.UserInAnotherTeamError
            If `creator` is not None and already part of a team managed by this hubbed game.

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
        Create a new team managed by this hubbed game.

        This method does not assert structural integrity.

        Parameters
        ----------
        team_type : _Team
            Class of team that will be produced. Defaults to None (and converted to the
            default team created by games, namely, _Team).
        creator : ClientManager.Client, optional
            The player who created this team. If set, they will also be added to the team if
            possible. The creator must be a player of this hubbed game. Defaults to None.
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
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.GameTooManyTeamsError
            If the hubbed game is already managing its maximum number of teams.
        HubbedGameError.UserInAnotherTeamError
            If `creator` is not None and already part of a team managed by this hubbed game.

        """

        try:
            return super().unchecked_new_team(
                team_type=team_type,
                creator=creator,
                player_limit=player_limit,
                require_invitations=require_invitations,
                require_players=require_players,
                require_leaders=require_leaders,
            )
        except GameWithAreasError.GameIsUnmanagedError:
            raise HubbedGameError.GameIsUnmanagedError
        except GameWithAreasError.GameTooManyTeamsError:
            raise HubbedGameError.GameTooManyTeamsError
        except GameWithAreasError.UserInAnotherTeamError:
            raise HubbedGameError.UserInAnotherTeamError

    def delete_team(self, team: _Team) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a team managed by this hubbed game.

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
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.GameDoesNotManageTeamError
            If the hubbed game does not manage the target team.

        """

        team_id, players = self.unchecked_delete_team(team)
        self.manager._check_structure()
        return team_id, players

    def unchecked_delete_team(self, team: _Team) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a team managed by this hubbed game.

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
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.GameDoesNotManageTeamError
            If the hubbed game does not manage the target team.

        """

        try:
            return super().unchecked_delete_team(team)
        except GameWithAreasError.GameIsUnmanagedError:
            raise HubbedGameError.GameIsUnmanagedError
        except GameWithAreasError.GameDoesNotManageTeamError:
            raise HubbedGameError.GameDoesNotManageTeamError

    def manages_team(self, team: _Team) -> bool:
        """
        Return True if the team is managed by this hubbed game, False otherwise.

        Parameters
        ----------
        team : _Team
            The team to check.

        Returns
        -------
        bool
            True if the hubbed game manages this team, False otherwise.

        """

        return super().manages_team(team)

    def get_teams(self) -> Set[_Team]:
        """
        Return (a shallow copy of) the teams this hubbed game manages.

        Returns
        -------
        Set[_Team]
            Teams this hubbed game manages.

        """

        return super().get_teams()

    def get_team_by_id(self, team_id: str) -> _Team:
        """
        If `team_id` is the ID of a team managed by this hubbed game, return the team.

        Parameters
        ----------
        team_id : str
            ID of the team this hubbed game manages.

        Returns
        -------
        _Team
            The team that matches the given ID.

        Raises
        ------
        HubbedGameError.GameInvalidTeamIDError:
            If `team_id` is not the ID of a team this hubbed game manages.

        """

        try:
            return super().get_team_by_id(team_id)
        except GameWithAreasError.GameInvalidTeamIDError:
            raise HubbedGameError.GameInvalidTeamIDError

    def get_team_limit(self) -> Union[int, None]:
        """
        Return the team limit of this hubbed game.

        Returns
        -------
        Union[int, None]
            Team limit.

        """

        return super().get_team_limit()

    def get_team_ids(self) -> Set[str]:
        """
        Return (a shallow copy of) the IDs of all teams managed by this hubbed game.

        Returns
        -------
        Set[str]
            The IDs of all managed teams.

        """

        return super().get_team_ids()

    def get_teams_of_user(self, user: ClientManager.Client) -> Set[_Team]:
        """
        Return (a shallow copy of) the teams managed by this hubbed game user `user` is a player
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
        HubbedGameError.GameTooManyTeamsError
            If the hubbed game is already managing its maximum number of teams.

        """

        try:
            return super().get_available_team_id()
        except GameWithAreasError.GameTooManyTeamsError:
            raise HubbedGameError.GameTooManyTeamsError

    def get_autoadd_on_client_enter(self) -> bool:
        """
        Return True if the hubbed game will always attempt to add nonplayer users who enter an
        area part of the hubbed game, False otherwise.

        Returns
        -------
        bool
            True if the hubbed game will always attempt to add nonplayer users who enter an area
            part of the hubbed game, False otherwise.
        """

        return super().get_autoadd_on_client_enter()

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

        super().unchecked_set_autoadd_on_client_enter(new_value)

    def add_area(self, area: AreaManager.Area):
        """
        Add an area to this hubbed game's set of areas.

        Parameters
        ----------
        area : AreaManager.Area
            Area to add.

        Raises
        ------
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.AreaAlreadyInGameError
            If the area is already part of the hubbed game.
        HubbedGameError.AreaHitGameConcurrentLimitError.
            If `area` has reached the concurrent area membership limit of any of the games with
            areas it belongs to managed by this manager, or by virtue of adding this area it will
            violate this hubbed game's concurrent area membership limit.

        """

        self.unchecked_add_area(area)
        self.manager._check_structure()

    def remove_area(self, area: AreaManager.Area):
        """
        Remove an area from this hubbed game's set of areas.
        If the area is already a part of the hubbed game, do nothing.
        If any player of the hubbed game is in this area, they are removed from the
        hubbed game.
        If the hubbed game has no areas remaining, it will be automatically destroyed.

        Parameters
        ----------
        area : AreaManager.Area
            Area to remove.

        Raises
        ------
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.AreaNotInGameError
            If the area is already not part of the hubbed game.

        """

        self.unchecked_remove_area(area)
        self.manager._check_structure()

    def unchecked_remove_area(self, area: AreaManager.Area):
        """
        Remove an area from this hubbed game's set of areas.
        If the area is already a part of the hubbed game, do nothing.
        If any player of the hubbed game is in this area, they are removed from the
        hubbed game.
        If the hubbed game has no areas remaining, it will be automatically destroyed.

        This method does not assert structural integrity.

        Parameters
        ----------
        area : AreaManager.Area
            Area to remove.

        Raises
        ------
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.AreaNotInGameError
            If the area is already not part of the hubbed game.

        """

        try:
            super().unchecked_remove_area(area)
        except GameWithAreasError.GameIsUnmanagedError:
            raise HubbedGameError.GameIsUnmanagedError
        except GameWithAreasError.AreaNotInGameError:
            raise HubbedGameError.AreaNotInGameError

    def requires_areas(self) -> bool:
        """
        Return whether the hubbed game requires areas at all times.

        Returns
        -------
        bool
            Whether the hubbed game requires areas at all times.
        """

        return super().requires_areas()

    def has_area(self, area: AreaManager.Area) -> bool:
        """
        If the area is part of this hubbed game's set of areas, return True; otherwise, return
        False.

        Parameters
        ----------
        area : AreaManager.Area
            Area to check.

        Returns
        -------
        bool
            True if the area is part of the hubbed game's set of areas, False otherwise.

        """

        return super().has_area(area)

    def get_areas(self) -> Set[AreaManager.Area]:
        """
        Return (a shallow copy of) the set of areas of this hubbed game.

        Returns
        -------
        Set[AreaManager.Area]
            Set of areas of the hubbed game.

        """

        return super().get_areas()

    def get_area_concurrent_limit(self) -> Union[int, None]:
        """
        Return the concurrent area membership limit of this hubbed game.

        Returns
        -------
        Union[int, None]
            The concurrent area membership limit.

        """

        return super().get_area_concurrent_limit()

    def get_users_in_areas(self) -> Set[ClientManager.Client]:
        """
        Return all users in areas part of the hubbed game, even those that are not players of
        the hubbed game.

        Returns
        -------
        Set[ClientManager.Client]
            All users in areas part of the hubbed game.

        """

        return super().get_users_in_areas()

    def get_nonleader_users_in_areas(self) -> Set[ClientManager.Client]:
        """
        Return all users in areas part of the hubbed game, even those that are not players of
        the hubbed game, such that they are not leaders of the hubbed game.

        Returns
        -------
        Set[ClientManager.Client]
            All users in areas part of the hubbed game that are not leaders of the hubbed game.

        """

        return super().get_nonleader_users_in_areas()

    def get_nonplayer_users_in_areas(self) -> Set[ClientManager.Client]:
        """
        Return all users in areas part of the hubbed game that are not players of the
        hubbed game.

        Returns
        -------
        Set[ClientManager.Client]
            All users in areas part of the hubbed game that are not players of the
            hubbed game.

        """

        return super().get_nonplayer_users_in_areas()

    def is_unmanaged(self):
        """
        Return True if this hubbed game is unmanaged, False otherwise.

        Returns
        -------
        bool
            True if unmanaged, False otherwise.

        """

        return super().is_unmanaged()

    def destroy(self):
        """
        Mark this hubbed game as destroyed and notify its manager so that it is deleted.
        If the hubbed game is already destroyed, this function does nothing.
        A hubbed game marked for destruction will delete all of its timers, teams, remove all
        its players and unsubscribe it from updates of its former players.

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
        Mark this hubbed game as destroyed and notify its manager so that it is deleted.
        If the hubbed game is already destroyed, this function does nothing.

        This method is reentrant (it will do nothing though).

        Returns
        -------
        None.

        """
        super().unchecked_destroy()

    def _on_client_inbound_ms_check(
        self,
        player: ClientManager.Client,
        contents: Dict[str, Any] = None
        ):
        """
        Default callback for hubbed game player signaling it wants to check if sending an IC
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
        Default callback for hubbed game player signaling it has sent an IC message.
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
        Default callback for hubbed game player signaling it has changed character.

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
        Default callback for hubbed game player signaling it was destroyed, for example, as a
        result of a disconnection.

        By default it only removes the player from the hubbed game. If the hubbed game is
        already unmanaged or the player is not in the hubbed game, this callback does nothing.

        Parameters
        ----------
        player : ClientManager.Client
            Player that signaled it was destroyed.

        Returns
        -------
        None.

        """

        super()._on_client_destroyed(player)

    def _on_area_client_left_final(
        self,
        area: AreaManager.Area,
        client: ClientManager.Client = None,
        old_displayname: str = None,
        ignore_bleeding: bool = False,
        ignore_autopass: bool = False,
        ):
        """
        Default callback for hubbed game area signaling a client left. This is executed after
        all other actions related to moving the player to a new area have been executed:
        in particular, client.area holds the new area of the client.

        By default it removes the player from the hubbed game if their new area is not part of
        the hubbed game.

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

        super()._on_area_client_left_final(
            area,
            client=client,
            old_displayname=old_displayname,
            ignore_bleeding=ignore_bleeding,
            ignore_autopass=ignore_autopass,
        )

    def _on_area_client_entered_final(
        self,
        area: AreaManager.Area,
        client: ClientManager.Client = None,
        old_area: Union[AreaManager.Area, None] = None,
        old_displayname: str = None,
        ignore_bleeding: bool = False,
        ignore_autopass: bool = False,
        ):
        """
        Default callback for hubbed game area signaling a client entered.

        By default adds a user to the hubbed game if the hubbed game is meant to
        automatically add users that enter an area part of the hubbed game.

        Parameters
        ----------
        area : AreaManager.Area
            Area that signaled a client has entered.
        client : ClientManager.Client, optional
            The client that has entered. The default is None.
        old_area : AreaManager.Area
            The old area the client has come from (possibly None for a newly connected user). The
            default is None.
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

        super()._on_area_client_entered_final(
            area,
            client=client,
            old_area=old_area,
            old_displayname=old_displayname,
            ignore_bleeding=ignore_bleeding,
            ignore_autopass=ignore_autopass,
        )

    def _on_area_client_inbound_ms_check(
        self,
        area: AreaManager.Area,
        client: ClientManager.Client = None,
        contents: Dict[str, Any] = None
        ):
        """
        Default callback for hubbed game area signaling a client in the area sent an IC message.
        Unlike the ClientManager.Client callback for send_ic_check, this one is triggered
        regardless of whether the sender is part of the hubbed game or not. This is useful for
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

        super()._on_area_client_inbound_ms_check(
            area,
            client=client,
            contents=contents,
        )

    def _on_area_destroyed(self, area: AreaManager.Area):
        """
        Default callback for hubbed game area signaling it was destroyed.

        By default it calls self.unchecked_remove_area(area).

        Parameters
        ----------
        area : AreaManager.Area
            Area that signaled it was destroyed.

        Returns
        -------
        None.

        """

        super()._on_area_destroyed(area)

    def _on_areas_loaded(self, area_manager: AreaManager):
        """
        Default callback for server area manager signaling it loaded new areas.

        By default it does nothing.

        Parameters
        ----------
        area_manager : AreaManager
            AreaManager that signaled the areas load.

        Returns
        -------
        None.

        """

        super()._on_areas_loaded(area_manager)



class _HubbedGame(_HubbedGameTrivialInherited):
    """
    A hubbed game is a game that manages and subscribes to its areas' updates.
    Any player of such a hubbed game must be in an area of the hubbed game. If a player of
    the hubbed game goes to an area not part of the hubbed game, they are removed
    automatically from the hubbed game.

    If an area is removed from the set of areas of the hubbed game, all players in that area
    are removed in some unspecified order.

    Each of these hubbed games may also impose a concurrent area membership limit, so that
    every area part of a hubbed game is at most an area of that many hubbed games managed
    by this games's manager.

    Each of these hubbed games may also set an autoadd on client enter flag. If set, nonplayer
    clients who enter an area part of the hubbed game will be added to the hubbed game if
    possible; if this fails, no action is taken and no errors are propagated.

    Attributes
    ----------
    server : TsuserverDR
        Server the hubbed game belongs to.
    manager : HubbedGameManager
        Manager for this hubbed game.
    hub: _Hub
        Hub for this hubbed game.
    listener : Listener
        Standard listener of the hubbed game.

    Callback Methods
    ----------------
    _on_area_client_left_final
        Method to perform once a client left an area of the hubbed game.
    _on_area_client_entered_final
        Method to perform once a client entered an area of the hubbed game.
    _on_area_destroyed
        Method to perform once an area of the hubbed game is marked for destruction.
    _on_client_inbound_ms_check
        Method to perform once a player of the hubbed game wants to send an IC message.
    _on_client_inbound_ms_final
        Method to perform once a player of the hubbed game sends an IC message.
    _on_client_change_character
        Method to perform once a player of the hubbed game has changed character.
    _on_client_destroyed
        Method to perform once a player of the hubbed game is destroyed.

    """

    # (Private) Attributes
    # --------------------
    # _areas : Set[AreaManager.Area]
    #   Areas of the hubbed game.
    # _area_concurrent_limit : Union[int, None]
    #   The maximum number of hubbed games managed by `manager` that any
    #   area of this hubbed game may belong to, including this hubbed game.
    # _autoadd_on_client_enter : bool
    #   Whether nonplayer users that enter an area part of the hubbed game will be
    #   automatically added if permitted by the conditions of the hubbed game.
    #
    # Invariants
    # ----------
    # 1. For each player of the hubbed game, they are in an area part of the hubbed game.
    # 2. It is not true that the hubbed game requires invitations and automatically adds users
    #    that join an area part of the hubbed game.
    # 3. The invariants from the parent class _Game are satisfied.

    def __init__(
        self,
        server: TsuserverDR,
        manager: HubbedGameManager,
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
        require_areas: bool = True,
        # new
        hub: _Hub = None,
    ):
        """
        Create a new hubbed game. A hubbed game should not be fully initialized anywhere
        else other than some manager code, as otherwise the manager will not recognize the
        hubbed game.

        Parameters
        ----------
        server : TsuserverDR
            Server the hubbed game belongs to.
        manager : HubbedGameManager
            Manager for this hubbed game.
        game_id : str
            Identifier of the hubbed game.
        player_limit : Union[int, None], optional
            If an int, it is the maximum number of players the hubbed game supports. If None, it
            indicates the hubbed game has no player limit. Defaults to None.
        player_concurrent_limit : Union[int, None], optional
            If an int, it is the maximum number of hubbed games managed by `manager` that any
            player of this hubbed game may belong to, including this hubbed game. If None,
            it indicates that this hubbed game does not care about how many other games with
            areas managed by `manager` each of its players belongs to. Defaults to None.
        require_invitation : bool, optional
            If True, players can only be added to the hubbed game if they were previously
            invited. If False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the hubbed game has no players left, the hubbed game
            will automatically be deleted. If False, no such automatic deletion will happen.
            Defaults to True.
        require_leaders : bool, optional
            If True, if at any point the hubbed game has no leaders left, the hubbed game
            will choose a leader among any remaining players left; if no players are left, the next
            player added will be made leader. If False, no such automatic assignment will happen.
            Defaults to True.
        require_character : bool, optional
            If False, players without a character will not be allowed to join the hubbed game,
            and players that switch to something other than a character will be automatically
            removed from the hubbed game. If False, no such checks are made. A player without a
            character is considered one where player.has_character() returns False. Defaults to
            False.
        team_limit : Union[int, None], optional
            If an int, it is the maximum number of teams the hubbed game supports. If None, it
            indicates the hubbed game has no team limit. Defaults to None.
        timer_limit : Union[int, None], optional
            If an int, it is the maximum number of timers the hubbed game supports. If None, it
            indicates the hubbed game has no timer limit. Defaults to None.
        area_concurrent_limit : Union[int, None], optional
            If an int, it is the maximum number of hubbed games managed by `manager` that any
            area of this hubbed game may belong to, including this hubbed game. If None, it
            indicates that this hubbed game does not care about how many other hubbed game
            managed by `manager` each of its areas belongs to. Defaults to 1 (an area may not be a
            part of another hubbed game managed by `manager` while being an area of this game).
        autoadd_on_client_enter : bool, optional
            If True, nonplayer users that enter an area part of the hubbed game will be
            automatically added if permitted by the conditions of the hubbed game. If False, no
            such adding will take place. Defaults to False.
        require_areas : bool, optional
            If True, if at any point the hubbed game has no areas left, the game with areas
            will automatically be deleted. If False, no such automatic deletion will happen.
            Defaults to True.
        hub : _Hub, optional
            Hub the hubbed game belongs to. Defaults to None.

        """

        self.hub = hub

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
            timer_limit=timer_limit,
            area_concurrent_limit=area_concurrent_limit,
            autoadd_on_client_enter=autoadd_on_client_enter,
            require_areas=require_areas,
        )

        self.listener.subscribe(self.hub.area_manager)
        self.listener.update_events({
            'areas_loaded': self._on_areas_loaded,
            })
        self.manager: HubbedGameManager  # Setting for typing

    def get_type_name(self) -> str:
        """
        Return the type name of the hubbed game. Names are fully lowercase.
        Implementations of the class should replace this with a human readable name of the hubbed
        game.

        Returns
        -------
        str
            Type name of the hubbed game.

        """

        return "hubbed game"

    def unchecked_add_area(self, area: AreaManager.Area):
        """
        Add an area to this hubbed game's set of areas.

        This method does not assert structural integrity.

        Parameters
        ----------
        area : AreaManager.Area
            Area to add.

        Raises
        ------
        HubbedGameError.GameIsUnmanagedError
            If the hubbed game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubbedGameError.AreaAlreadyInGameError
            If the area is already part of the hubbed game.
        HubbedGameError.AreaHitGameConcurrentLimitError.
            If `area` has reached the concurrent area membership limit of any of the games with
            areas it belongs to managed by this manager, or by virtue of adding this area it will
            violate this hubbed game's concurrent area membership limit.

        """

        if self.is_unmanaged():
            raise HubbedGameError.GameIsUnmanagedError
        if area.hub != self.hub:
            raise HubbedGameError.AreaNotInHubError

        try:
            return super().unchecked_add_area(area)
        except GameWithAreasError.GameIsUnmanagedError:
            raise RuntimeError(self)
        except GameWithAreasError.AreaAlreadyInGameError:
            raise HubbedGameError.AreaAlreadyInGameError
        except GameWithAreasError.AreaHitGameConcurrentLimitError:
            raise HubbedGameError.AreaHitGameConcurrentLimitError

    def _check_structure(self):
        """
        Assert that all invariants specified in the class description are maintained.

        Raises
        ------
        AssertionError
            If any of the invariants are not maintained.

        """

        # 1.
        for area in self.get_areas():
            assert area.hub == self.hub, (
                f'For hubbed game {self}, expected all its areas belong to hub {self.hub}, '
                f'found area {area} belonged to hub {area.hub} instead'
                )

        # 2.
        super()._check_structure()

    def __str__(self) -> str:
        """
        Return a string representation of this hubbed game.

        Returns
        -------
        str
            Representation.

        """

        return (f"HubbedGame::{self.get_id()}:{self.hub}"
                f"{self.get_players()}:{self.get_leaders()}:{self.get_invitations()}"
                f"{self.get_timers()}:"
                f"{self.get_teams()}:"
                f"{self.get_areas()}")

    def __repr__(self) -> str:
        """
        Return a representation of this hubbed game.

        Returns
        -------
        str
            Printable representation.

        """

        return (f'GameWithAreas(server, {self.hub}, {self.manager.get_id()}, "{self.get_id()}", '
                f'player_limit={self.get_player_limit()}, '
                f'player_concurrent_limit={self.get_player_concurrent_limit()}, '
                f'require_players={self.requires_players()}, '
                f'require_invitations={self.requires_invitations()}, '
                f'require_leaders={self.requires_leaders()}, '
                f'require_character={self.requires_characters()}, '
                f'team_limit={self.get_team_limit()}, '
                f'timer_limit={self.get_timer_limit()}, '
                f'areas={self.get_areas()}), '
                f'|| '
                f'players={self.get_players()}, '
                f'invitations={self.get_invitations()}, '
                f'leaders={self.get_leaders()}, '
                f'timers={self.get_timers()}, '
                f'teams={self.get_teams()}, '
                f'unmanaged={self.is_unmanaged()}), '
                f')')

class _HubbedGameManagerTrivialInherited(GameWithAreasManager):
    """
    This class should not be instantiated.
    """

    def new_managee(
        self,
        managee_type: Type[_HubbedGame] = None,
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
        autoadd_on_creation_existing_users: bool = False,
        require_areas: bool = True,
        hub: Union[_Hub, None] = None,
        **kwargs: Any,
        ) -> _HubbedGame:
        """
        Create a new hubbed game managed by this manager.

        Parameters
        ----------
        managee_type : Type[_HubbedGame], optional
            Class of hubbed game that will be produced. Defaults to None (and converted to the
            default hubbed game created by this hubbed game manager).
        creator : Union[ClientManager.Client, None], optional
            The player who created this hubbed game. If set, they will also be added to the
            hubbed game. Defaults to None.
        player_limit : Union[int, None], optional
            If an int, it is the maximum number of players the hubbed game supports. If None, it
            indicates the hubbed game has no player limit. Defaults to None.
        player_concurrent_limit : Union[int, None], optional
            If an int, it is the maximum number of hubbed games managed by `self` that any
            player of this hubbed game to create may belong to, including this hubbed game
            to create. If None, it indicates that this hubbed game does not care about how many
            other hubbed games managed by `self` each of its players belongs to. Defaults to 1
            (a player may not be in another game managed by `self` while in this game).
        require_invitations : bool, optional
            If True, users can only be added to the hubbed game if they were previously invited.
            If False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the hubbed game loses all its players, the hubbed game
            will automatically be deleted. If False, no such automatic deletion will happen.
            Defaults to True.
        require_leaders : bool, optional
            If True, if at any point the hubbed game has no leaders left, the hubbed game
            will choose a leader among any remaining players left; if no players are left, the next
            player added will be made leader. If False, no such automatic assignment will happen.
            Defaults to True.
        require_character : bool, optional
            If False, players without a character will not be allowed to join the hubbed game,
            and players that switch to something other than a character will be automatically
            removed from the hubbed game. If False, no such checks are made. A player without a
            character is considered one where player.has_character() returns False. Defaults to
            False.
        team_limit : Union[int, None], optional
            If an int, it is the maximum number of teams the hubbed game will support. If None,
            it indicates the hubbed game will have no team limit. Defaults to None.
        timer_limit : Union[int, None], optional
            If an int, it is the maximum number of timers the hubbed game will support. If None,
            it indicates the hubbed game will have no timer limit. Defaults to None.
        areas : Set[AreaManager.Area], optional
            The areas to add to the hubbed game when creating it. Defaults to None (and
            converted to a set containing the creator's area if given a creator, and the empty set
            otherwise).
        area_concurrent_limit : Union[int, None]
            The concurrent area membership limit of this hubbed game. Defaults to None.
        autoadd_on_client_enter : bool
            If the hubbed game will always attempt to add nonplayer users who enter an area
            part of the hubbed game. Defaults to False.
        autoadd_on_creation_existing_users : bool
            If the hubbed game will attempt to add nonplayer users who were in an area added
            to the hubbed game on creation. Defaults to False.
        require_areas : bool, optional
            If True, if at any point the hubbed game has no areas left, the game with areas
            will automatically be deleted. If False, no such automatic deletion will happen.
            Defaults to True.
        hub : _Hub, optional
            Hub of the hubbed game. Defaults to None (and converted to the creator's hub if given a
            creator, and None otherwise).
        **kwargs : Any
            Additional arguments to consider when producing the hubbed game.

        Returns
        -------
        _HubbedGame
            The created hubbed game.

        Raises
        ------
        HubbedGameError.ManagerTooManyGamesError
            If the manager is already managing its maximum number of games.
        Any error from the created hubbed game's add_player(creator)
            If the hubbed game cannot add `creator` as a player if given one.

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
            autoadd_on_creation_existing_users=autoadd_on_creation_existing_users,
            require_areas=require_areas,
            hub=hub,
            **kwargs,
            )
        self._check_structure()
        return game

    def get_managee_type(self) -> Type[_HubbedGame]:
        """
        Return the type of the hubbed game that will be constructed by default with a call of
        `new_managee`.

        Returns
        -------
        Type[_HubbedGame]
            Type of the hubbed game.

        """

        return super().get_managee_type()

    def delete_managee(self, managee: _HubbedGame) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a hubbed game managed by this manager, so all its players no longer belong to
        this hubbed game.

        Parameters
        ----------
        managee : _HubbedGame
            The hubbed game to delete.

        Returns
        -------
        Tuple[str, Set[ClientManager.Client]]
            The ID and players of the hubbed game that was deleted.

        Raises
        ------
        HubbedGameError.ManagerDoesNotManageGameError
            If the manager does not manage the target hubbed game.

        """

        game_id, game_players = self.unchecked_delete_managee(managee)
        self._check_structure()
        return game_id, game_players

    def unchecked_delete_managee(
        self,
        managee: _HubbedGame
        ) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a hubbed game managed by this manager, so all its players no longer belong to
        this hubbed game.

        Parameters
        ----------
        managee : _HubbedGame
            The hubbed game to delete.

        Returns
        -------
        Tuple[str, Set[ClientManager.Client]]
            The ID and players of the hubbed game that was deleted.

        Raises
        ------
        HubbedGameError.ManagerDoesNotManageGameError
            If the manager does not manage the target hubbed game.

        """

        try:
            return super().unchecked_delete_managee(managee)
        except GameWithAreasError.ManagerDoesNotManageGameError:
            raise HubbedGameError.ManagerDoesNotManageGameError

    def manages_managee(self, game: _HubbedGame):
        """
        Return True if the hubbed game is managed by this manager, False otherwise.

        Parameters
        ----------
        game : _HubbedGame
            The game to check.

        Returns
        -------
        bool
            True if the manager manages this hubbed game, False otherwise.

        """

        return super().manages_managee(game)

    def get_managees(self) -> Set[_HubbedGame]:
        """
        Return (a shallow copy of) the hubbed games this manager manages.

        Returns
        -------
        Set[_HubbedGame]
            Hubbed games this manager manages.

        """

        return super().get_managees()

    def get_managee_by_id(self, managee_id: str) -> _HubbedGame:
        """
        If `managee_id` is the ID of a hubbed game managed by this manager, return that.

        Parameters
        ----------
        managee_id : str
            ID of the hubbed game this manager manages.

        Returns
        -------
        _HubbedGame
            The hubbed game with that ID.

        Raises
        ------
        HubbedGameError.ManagerInvalidGameIDError
            If `game_id` is not the ID of a hubbed game this manager manages.

        """

        try:
            return super().get_managee_by_id(managee_id)
        except GameWithAreasError.ManagerInvalidGameIDError:
            raise HubbedGameError.ManagerInvalidGameIDError

    def get_managee_by_numerical_id(self, managee_numerical_id: int) -> _HubbedGame:
        """
        If `managee_numerical_id` is the numerical ID of a hubbed game managed by this manager,
        return the hubbed game.

        Parameters
        ----------
        managee_numerical_id : int
            Numerical ID of the hubbed game this manager manages.

        Returns
        -------
        _HubbedGame
            The hubbed game with that ID.

        Raises
        ------
        HubbedGameError.ManagerInvalidGameIDError:
            If `managee_numerical_id` is not the numerical ID of a hubbed game
            this manager manages.

        """

        try:
            return super().get_managee_by_numerical_id(managee_numerical_id)
        except GameWithAreasError.ManagerInvalidGameIDError:
            raise HubbedGameError.ManagerInvalidGameIDError

    def get_managee_limit(self) -> Union[int, None]:
        """
        Return the hubbed game limit of this manager.

        Returns
        -------
        Union[int, None]
            Hubbed game limit.

        """

        return super().get_managee_limit()

    def get_managee_ids(self) -> Set[str]:
        """
        Return (a shallow copy of) the IDs of all hubbed games managed by this manager.

        Returns
        -------
        Set[str]
            The IDs of all managed hubbed games.

        """

        return super().get_managee_ids()

    def get_managee_ids_to_managees(self) -> Dict[str, _HubbedGame]:
        """
        Return a mapping of the IDs of all hubbed games managed by this manager to their
        associated hubbed game.

        Returns
        -------
        Dict[str, _HubbedGame]
            Mapping.
        """

        return super().get_managee_ids_to_managees()

    def get_managee_numerical_ids_to_managees(self) -> Dict[int, _HubbedGame]:
        """
        Return a mapping of the numerical IDs of all hubbed game managed by this manager to
        their associated hubbed game.

        Returns
        -------
        Dict[int, _HubbedGame]
            Mapping.
        """

        return super().get_managee_numerical_ids_to_managees()

    def get_managees_of_user(self, user: ClientManager.Client):
        """
        Return (a shallow copy of) the hubbed games managed by this manager user `user` is a
        player of. If the user is part of no such hubbed game, an empty set is returned.

        Parameters
        ----------
        user : ClientManager.Client
            User whose hubbed games will be returned.

        Returns
        -------
        Set[_HubbedGame]
            Hubbed games the player belongs to.

        """

        return super().get_managees_of_user(user)

    def get_player_to_managees_map(self) -> Dict[ClientManager.Client, Set[_HubbedGame]]:
        """
        Return a mapping of the players part of any hubbed game managed by this manager to the
        hubbed game managed by this manager such players belong to.

        Returns
        -------
        Dict[ClientManager.Client, Set[_HubbedGame]]
            Mapping.
        """

        return super().get_player_to_managees_map()

    def get_users_in_some_managee(self) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) all the users that are part of some hubbed game managed by
        this manager.

        Returns
        -------
        Set[ClientManager.Client]
            Users in some managed hubbed game.

        """

        return super().get_users_in_some_managee()

    def is_managee_creatable(self) -> bool:
        """
        Return whether a new hubbed game can currently be created without creating one.

        Returns
        -------
        bool
            True if a hubbed game can be currently created, False otherwise.
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

    def get_managees_in_area(self, area: AreaManager.Area) -> Set[_HubbedGame]:
        """
        Return (a shallow copy of) all hubbed games managed by this manager that contain
        the given area.

        Parameters
        ----------
        area : AreaManager.Area
            Area that all returned hubbed games must contain.

        Returns
        -------
        Set[_HubbedGame]
            Hubbed games that contain the given area.

        """

        return super().get_managees_in_area(area)

    def find_area_concurrent_limiting_managee(
        self,
        area: AreaManager.Area
        ) -> Union[_HubbedGame, None]:
        """
        For area `area`, find a hubbed game `most_restrictive_game` managed by this manager
        such that, if `area` were to be added to another hubbed game managed by this manager,
        they would violate `most_restrictive_game`'s concurrent area membership limit.
        If no such hubbed game exists (or the area is not an area of any hubbed game
        managed by this  manager), return None.
        If multiple such hubbed games exist, any one of them may be returned.

        Parameters
        ----------
        area : AreaManager.Area
            Area to test.

        Returns
        -------
        Union[_HubbedGame, None]
            Limiting hubbed game as previously described if it exists, None otherwise.

        """

        return super().find_area_concurrent_limiting_managee(area)

    def find_player_concurrent_limiting_managee(
        self,
        user: ClientManager.Client
        ) -> Union[_HubbedGame, None]:
        """
        For user `user`, find a hubbed game `most_restrictive_game` managed by this manager such
        that, if `user` were to join another hubbed game managed by this manager, they would
        violate `most_restrictive_game`'s concurrent player membership limit.
        If no such hubbed game exists (or the player is not member of any hubbed game
        managed by this manager), return None.
        If multiple such hubbed games exist, any one of them may be returned.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Returns
        -------
        Union[_HubbedGame, None]
            Limiting hubbed game as previously described if it exists, None otherwise.

        """

        return super().find_player_concurrent_limiting_managee(user)

    def get_areas_to_managees_map(self) -> Dict[ClientManager.Client, Set[_HubbedGame]]:
        """
        Return a mapping of the areas part of any hubbed game managed by this manager to the
        hubbed game managed by this manager such players belong to.

        Returns
        -------
        Dict[ClientManager.Client, Set[_HubbedGame]]
            Mapping.
        """

        return super().get_areas_to_managees_map()

class HubbedGameManager(_HubbedGameManagerTrivialInherited):
    """
    A hubbed game manager is a game manager with dedicated area management functions.

    Attributes
    ----------
    server : TsuserverDR
        Server the hubbed game manager belongs to.
    """

    # Invariants
    # ----------
    # 1. The invariants of the parent class are maintained.

    def __init__(
        self,
        server: TsuserverDR,
        managee_limit: Union[int, None] = None,
        default_managee_type: Type[_HubbedGame] = None,
        ):
        """
        Create a hubbed game manager object.

        Parameters
        ----------
        server : TsuserverDR
            The server this hubbed game manager belongs to.
        managee_limit : int, optional
            The maximum number of hubbed games this manager can handle. Defaults to None
            (no limit).
        default_managee_type : Type[_HubbedGame], optional
            The default type of hubbed game this manager will create. Defaults to None (and then
            converted to _HubbedGame).

        """

        if default_managee_type is None:
            default_managee_type = _HubbedGame

        super().__init__(
            server,
            managee_limit=managee_limit,
            default_managee_type=default_managee_type
        )

    def unchecked_new_managee(
        self,
        managee_type: Type[_HubbedGame] = None,
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
        autoadd_on_creation_existing_users: bool = False,
        require_areas: bool = True,
        hub: Union[_Hub, None] = None,
        **kwargs: Any,
        ) -> _HubbedGame:

        """
        Create a new hubbed game managed by this manager.

        This method does not assert structural integrity.

        Parameters
        ----------
        managee_type : Type[_HubbedGame], optional
            Class of hubbed game that will be produced. Defaults to None (and converted to the
            default hubbed game created by this hubbed game manager).
        creator : Union[ClientManager.Client, None], optional
            The player who created this hubbed game. If set, they will also be added to the
            hubbed game. Defaults to None.
        player_limit : Union[int, None], optional
            If an int, it is the maximum number of players the hubbed game supports. If None, it
            indicates the hubbed game has no player limit. Defaults to None.
        player_concurrent_limit : Union[int, None], optional
            If an int, it is the maximum number of hubbed games managed by `self` that any
            player of this hubbed game to create may belong to, including this hubbed game
            to create. If None, it indicates that this hubbed game does not care about how many
            other hubbed games managed by `self` each of its players belongs to. Defaults to 1
            (a player may not be in another game managed by `self` while in this game).
        require_invitations : bool, optional
            If True, users can only be added to the hubbed game if they were previously invited.
            If False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the hubbed game loses all its players, the hubbed game
            will automatically be deleted. If False, no such automatic deletion will happen.
            Defaults to True.
        require_leaders : bool, optional
            If True, if at any point the hubbed game has no leaders left, the hubbed game
            will choose a leader among any remaining players left; if no players are left, the next
            player added will be made leader. If False, no such automatic assignment will happen.
            Defaults to True.
        require_character : bool, optional
            If False, players without a character will not be allowed to join the hubbed game,
            and players that switch to something other than a character will be automatically
            removed from the hubbed game. If False, no such checks are made. A player without a
            character is considered one where player.has_character() returns False. Defaults to
            False.
        team_limit : Union[int, None], optional
            If an int, it is the maximum number of teams the hubbed game will support. If None,
            it indicates the hubbed game will have no team limit. Defaults to None.
        timer_limit : Union[int, None], optional
            If an int, it is the maximum number of timers the hubbed game will support. If None,
            it indicates the hubbed game will have no timer limit. Defaults to None.
        areas : Set[AreaManager.Area], optional
            The areas to add to the hubbed game when creating it. Defaults to None (and
            converted to a set containing the creator's area if given a creator, and the empty set
            otherwise).
        area_concurrent_limit : Union[int, None]
            The concurrent area membership limit of this hubbed game. Defaults to None.
        autoadd_on_client_enter: bool, optional
            If the hubbed game will always attempt to add nonplayer users who enter an area
            part of the hubbed game. Defaults to False.
        autoadd_on_creation_existing_users : bool, optional
            If the hubbed game will attempt to add nonplayer users who were in an area added
            to the hubbed game on creation. Defaults to False.
        require_areas : bool, optional
            If True, if at any point the hubbed game has no areas left, the game with areas
            will automatically be deleted. If False, no such automatic deletion will happen.
            Defaults to True.
        hub : _Hub, optional
            Hub of the hubbed game. Defaults to None (and converted to the creator's hub if given a
            creator, and None otherwise).
        **kwargs : Any
            Additional arguments to consider when producing the hubbed game.

        Returns
        -------
        _HubbedGame
            The created hubbed game.

        Raises
        ------
        HubbedGameError.ManagerTooManyGamesError
            If the manager is already managing its maximum number of games.
        Any error from the created hubbed game's add_player(creator)
            If the hubbed game cannot add `creator` as a player if given one.

        """

        if managee_type is None:
            managee_type = self.get_managee_type()
        if not hub:
            hub = creator.hub if creator else None

        try:
            game: _HubbedGame = super().unchecked_new_managee(
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
                area_concurrent_limit=area_concurrent_limit,
                autoadd_on_client_enter=autoadd_on_client_enter,
                require_areas=require_areas,
                # kwargs
                hub=hub,
                **kwargs,
            )
        except GameWithAreasError.ManagerTooManyGamesError:
            raise HubbedGameError.ManagerTooManyGamesError

        areas = game.get_areas()
        try:
            for area in areas:
                game.unchecked_add_area(area)
        except HubbedGameError as ex:
            # Discard game
            self.unchecked_delete_managee(game)
            raise ex

        # Add creator manually. This is because adding it via .new_game will yield errors because
        # the areas are not added until the section before.
        try:
            if creator:
                game.unchecked_add_player(creator)
        except HubbedGameError as ex:
            # Discard game
            self.unchecked_delete_managee(game)
            raise ex

        if autoadd_on_creation_existing_users:
            clients_to_add = {client for area in areas for client in area.clients}
            if creator:
                clients_to_add.discard(creator)
            for client in clients_to_add:
                try:
                    game.add_player(client)
                except HubbedGameError as ex:
                    # Discard game
                    self.unchecked_delete_managee(game)
                    raise ex

        return game

    def get_available_managee_id(self):
        """
        Get a hubbed game ID that no other hubbed game managed by this manager has.

        Returns
        -------
        str
            A unique hubbed game ID.

        Raises
        ------
        HubbedGameError.ManagerTooManyGamesError
            If the manager is already managing its maximum number of games.

        """

        game_number = 0
        game_limit = self.get_managee_limit()
        while game_limit is None or game_number < game_limit:
            new_game_id = "hg{}".format(game_number)
            if new_game_id not in self.get_managee_ids():
                return new_game_id
            game_number += 1
        raise HubbedGameError.ManagerTooManyGamesError

    def _check_structure(self):
        """
        Assert that all invariants specified in the class description are maintained.

        Raises
        ------
        AssertionError
            If any of the invariants are not maintained.

        """

        super()._check_structure()

    def __repr__(self) -> str:
        """
        Return a representation of this hubbed game manager.

        Returns
        -------
        str
            Printable representation.

        """

        return (f"HubbedGameManager(server, managee_limit={self.get_managee_limit()}, "
                f"default_managee_type={self.get_managee_type()}, "
                f"|| "
                f"_id_to_managee={self.get_managee_ids_to_managees()}, "
                f"_user_to_managees={self.get_player_to_managees_map()}, "
                f"_area_to_managees={self.get_areas_to_managees_map()}, "
                f"id={self.get_id()}, "
                f')')
