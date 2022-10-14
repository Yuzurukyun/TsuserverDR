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
Module that contains the trial minigame class.

"""

from __future__ import annotations

import typing
from typing import Callable, Dict, Set, Any, Tuple, Type, Union

import enum

from server.exceptions import HubbedGameError, TrialMinigameError
from server.hubbedgame_manager import _HubbedGame

if typing.TYPE_CHECKING:
    # Avoid circular referencing
    from server.area_manager import AreaManager
    from server.client_manager import ClientManager
    from server.game_manager import _Team
    from server.hub_manager import _Hub
    from server.hubbedgame_manager import HubbedGameManager
    from server.timer_manager import Timer
    from server.trial_manager import _Trial
    from server.tsuserver import TsuserverDR

class TRIALMINIGAMES(enum.Enum):
    """
    All supported trial minigames.
    """

    NONSTOP_DEBATE = enum.auto()

class _TrialMinigameTrivialInherited(_HubbedGame):
    """
    This class should not be instantiated.
    """

    def get_id(self) -> str:
        """
        Return the ID of this trial minigame.

        Returns
        -------
        str
            The ID.

        """

        return super().get_id()

    def get_numerical_id(self) -> int:
        """
        Return the numerical portion of the ID of this trial minigame.

        Returns
        -------
        int
            Numerical portion of the ID.
        """

        return super().get_numerical_id()

    def get_name(self) -> str:
        """
        Get the name of the trial minigame.

        Returns
        -------
        str
            Name.
        """

        return super().get_name()

    def set_name(self, name: str):
        """
        Set the name of the trial minigame.

        Parameters
        ----------
        name : str
            Name.
        """

        self.unchecked_set_name(name)
        self.manager._check_structure()

    def unchecked_set_name(self, name: str):
        """
        Set the name of the trial minigame.

        This method does not assert structural integrity.

        Parameters
        ----------
        name : str
            Name.
        """

        super().unchecked_set_name(name)

    def get_player_limit(self) -> Union[int, None]:
        """
        Return the player membership limit of this trial minigame.

        Returns
        -------
        Union[int, None]
            The player membership limit.

        """

        return super().get_player_limit()

    def get_player_concurrent_limit(self) -> Union[int, None]:
        """
        Return the concurrent player membership limit of this trial minigame.

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
        Return (a shallow copy of) the set of players of this trial minigame that satisfy a
        condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all players returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) players of this trial minigame.

        """

        return super().get_players(cond=cond)

    def is_player(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is a player of the trial minigame.

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
        Make a user a player of the trial minigame. By default this player will not be a leader,
        unless the trial minigame has no leaders and it requires a leader.
        It will also subscribe the trial minigame to the player so it can listen to its updates.

        Newly added players will be ordered to switch to a 'trial minigame' variant.

        Parameters
        ----------
        user : ClientManager.Client
            User to add to the trial minigame. They must be in an area part of the trial minigame.

        Raises
        ------
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.UserNotInAreaError
            If the user is not in an area part of the trial minigame.
        TrialMinigameError.UserHasNoCharacterError
            If the user has no character but the trial minigame requires that all players have
            characters.
        TrialMinigameError.UserNotInvitedError
            If the trial minigame requires players be invited to be added and the user is not
            invited.
        TrialMinigameError.UserAlreadyPlayerError
            If the user to add is already a user of the trial minigame.
        TrialMinigameError.UserHitGameConcurrentLimitError
            If the player has reached the concurrent player membership of any of the trial minigame
            managed by the manager of this trial minigame, or by virtue of joining this
            trial minigame they would violate this trial minigame's concurrent player membership
            limit.
        TrialMinigameError.GameIsFullError
            If the trial minigame reached its player limit.

        """

        self.unchecked_add_player(user)
        self.manager._check_structure()

    def remove_player(self, user: ClientManager.Client):
        """
        Make a user be no longer a player of this trial minigame. If they were part of a team
        managed by this trial minigame, they will also be removed from said team. It will also
        unsubscribe the trial minigame from the player so it will no longer listen to its updates.

        If the trial minigame required that there it always had players and by calling this method
        the trial minigame had no more players, the trial minigame will automatically be scheduled
        for deletion.

        Parameters
        ----------
        user : ClientManager.Client
            User to remove.

        Raises
        ------
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.UserNotPlayerError
            If the user to remove is already not a player of this trial minigame.

        """

        self.unchecked_remove_player(user)
        self.manager._check_structure()

    def unchecked_remove_player(self, user: ClientManager.Client):
        """
        Make a user be no longer a player of this trial minigame. If they were part of a team
        managed by this trial minigame, they will also be removed from said team. It will also
        unsubscribe the trial minigame from the player so it will no longer listen to its updates.

        If the trial minigame required that there it always had players and by calling this method
        the trial minigame had no more players, the trial minigame will automatically be scheduled
        for deletion.

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to remove.

        Raises
        ------
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.UserNotPlayerError
            If the user to remove is already not a player of this trial minigame.

        """

        try:
            super().unchecked_remove_player(user)
        except HubbedGameError.GameIsUnmanagedError:
            raise TrialMinigameError.GameIsUnmanagedError
        except HubbedGameError.UserNotPlayerError:
            raise TrialMinigameError.UserNotPlayerError

    def requires_players(self) -> bool:
        """
        Return whether the trial minigame requires players at all times.

        Returns
        -------
        bool
            Whether the trial minigame requires players at all times.
        """

        return super().requires_players()

    def get_invitations(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
        ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of invited users of this trial minigame that satisfy a
        condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all invited users returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) invited users of this trial minigame.

        """

        return super().get_invitations(cond=cond)

    def is_invited(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is invited to the trial minigame.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Raises
        ------
        TrialMinigameError.UserAlreadyPlayerError
            If the user is a player of this trial minigame.

        Returns
        -------
        bool
            True if the user is invited, False otherwise.

        """

        try:
            return super().is_invited(user)
        except HubbedGameError.UserAlreadyPlayerError:
            raise TrialMinigameError.UserAlreadyPlayerError

    def add_invitation(self, user: ClientManager.Client):
        """
        Mark a user as invited to this trial minigame.

        Parameters
        ----------
        user : ClientManager.Client
            User to invite to the trial minigame.

        Raises
        ------
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.GameDoesNotTakeInvitationsError
            If the trial minigame does not require users be invited to the trial minigame.
        TrialMinigameError.UserAlreadyInvitedError
            If the player to invite is already invited to the trial minigame.
        TrialMinigameError.UserAlreadyPlayerError
            If the player to invite is already a player of the trial minigame.

        """

        self.unchecked_add_invitation(user)
        self.manager._check_structure()

    def unchecked_add_invitation(self, user: ClientManager.Client):
        """
        Mark a user as invited to this trial minigame.

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to invite to the trial minigame.

        Raises
        ------
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.GameDoesNotTakeInvitationsError
            If the trial minigame does not require users be invited to the trial minigame.
        TrialMinigameError.UserAlreadyInvitedError
            If the player to invite is already invited to the trial minigame.
        TrialMinigameError.UserAlreadyPlayerError
            If the player to invite is already a player of the trial minigame.

        """

        try:
            super().unchecked_add_invitation(user)
        except HubbedGameError.GameIsUnmanagedError:
            raise TrialMinigameError.GameIsUnmanagedError
        except HubbedGameError.GameDoesNotTakeInvitationsError:
            raise TrialMinigameError.GameDoesNotTakeInvitationsError
        except HubbedGameError.UserAlreadyInvitedError:
            raise TrialMinigameError.UserAlreadyInvitedError
        except HubbedGameError.UserAlreadyPlayerError:
            raise TrialMinigameError.UserAlreadyPlayerError

    def remove_invitation(self, user: ClientManager.Client):
        """
        Mark a user as no longer invited to this trial minigame (uninvite).

        Parameters
        ----------
        user : ClientManager.Client
            User to uninvite.

        Raises
        ------
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.GameDoesNotTakeInvitationsError
            If the trial minigame does not require users be invited to the trial minigame.
        TrialMinigameError.UserNotInvitedError
            If the user to uninvite is already not invited to this trial minigame.

        """

        self.unchecked_remove_invitation(user)
        self.manager._check_structure()

    def unchecked_remove_invitation(self, user: ClientManager.Client):
        """
        Mark a user as no longer invited to this trial minigame (uninvite).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to uninvite.

        Raises
        ------
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.GameDoesNotTakeInvitationsError
            If the trial minigame does not require users be invited to the trial minigame.
        TrialMinigameError.UserNotInvitedError
            If the user to uninvite is already not invited to this trial minigame.

        """

        try:
            super().unchecked_remove_invitation(user)
        except HubbedGameError.GameIsUnmanagedError:
            raise TrialMinigameError.GameIsUnmanagedError
        except HubbedGameError.GameDoesNotTakeInvitationsError:
            raise TrialMinigameError.GameDoesNotTakeInvitationsError
        except HubbedGameError.UserNotInvitedError:
            raise TrialMinigameError.UserNotInvitedError

    def requires_invitations(self):
        """
        Return True if the trial minigame requires players be invited before being allowed to join
        the trial minigame, False otherwise.

        Returns
        -------
        bool
            True if the trial minigame requires players be invited before being allowed to join
            the trial minigame, False otherwise.
        """

        return super().requires_invitations()

    def get_leaders(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
        ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of leaders of this trial minigame that satisfy a condition
        if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all leaders returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) leaders of this trial minigame.

        """

        return super().get_leaders(cond=cond)

    def get_regulars(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
        ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of players of this trial minigame that are regulars and
        satisfy a condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all regulars returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) regulars of this trial minigame.

        """

        return super().get_regulars(cond=cond)

    def is_leader(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is a leader of the trial minigame.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Raises
        ------
        TrialMinigameError.UserNotPlayerError
            If the player to test is not a player of this trial minigame.

        Returns
        -------
        bool
            True if the player is a user, False otherwise.

        """

        try:
            return super().is_leader(user)
        except HubbedGameError.UserNotPlayerError:
            raise TrialMinigameError.UserNotPlayerError

    def add_leader(self, user: ClientManager.Client):
        """
        Set a user as leader of this trial minigame (promote to leader).

        Parameters
        ----------
        user : ClientManager.Client
            Player to promote to leader.

        Raises
        ------
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.UserNotPlayerError
            If the player to promote is not a player of this trial minigame.
        TrialMinigameError.UserAlreadyLeaderError
            If the player to promote is already a leader of this trial minigame.

        """

        self.unchecked_add_leader(user)
        self.manager._check_structure()

    def unchecked_add_leader(self, user: ClientManager.Client):
        """
        Set a user as leader of this trial minigame (promote to leader).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            Player to promote to leader.

        Raises
        ------
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.UserNotPlayerError
            If the player to promote is not a player of this trial minigame.
        TrialMinigameError.UserAlreadyLeaderError
            If the player to promote is already a leader of this trial minigame.

        """

        try:
            super().unchecked_add_leader(user)
        except HubbedGameError.GameIsUnmanagedError:
            raise TrialMinigameError.GameIsUnmanagedError
        except HubbedGameError.UserNotPlayerError:
            raise TrialMinigameError.UserNotPlayerError
        except HubbedGameError.UserAlreadyLeaderError:
            raise TrialMinigameError.UserAlreadyLeaderError

    def remove_leader(self, user: ClientManager.Client):
        """
        Make a user no longer leader of this trial minigame (demote).

        Parameters
        ----------
        user : ClientManager.Client
            User to demote.

        Raises
        ------
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.UserNotPlayerError
            If the player to demote is not a player of this trial minigame.
        TrialMinigameError.UserNotLeaderError
            If the player to demote is already not a leader of this trial minigame.

        """

        self.unchecked_remove_leader(user)
        self.manager._check_structure()

    def unchecked_remove_leader(self, user: ClientManager.Client):
        """
        Make a user no longer leader of this trial minigame (demote).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to demote.

        Raises
        ------
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.UserNotPlayerError
            If the player to demote is not a player of this trial minigame.
        TrialMinigameError.UserNotLeaderError
            If the player to demote is already not a leader of this trial minigame.

        """

        try:
            super().unchecked_remove_leader(user)
        except HubbedGameError.GameIsUnmanagedError:
            raise TrialMinigameError.GameIsUnmanagedError
        except HubbedGameError.UserNotPlayerError:
            raise TrialMinigameError.UserNotPlayerError
        except HubbedGameError.UserNotLeaderError:
            raise TrialMinigameError.UserNotLeaderError

    def has_ever_had_players(self) -> bool:
        """
        Return True if a player has ever been added to this trial minigame, False otherwise.

        Returns
        -------
        bool
            True if the trial minigame has ever had a player added, False otherwise.

        """

        return super().has_ever_had_players()

    def requires_leaders(self) -> bool:
        """
        Return whether the trial minigame requires leaders at all times.

        Returns
        -------
        bool
            Whether the trial minigame requires leaders at all times.
        """

        return super().requires_leaders()

    def has_ever_had_players(self):
        """
        Return True if a player has ever been added to this trial minigame, False otherwise.

        Returns
        -------
        bool
            True if the trial minigame has ever had a player added, False otherwise.

        """

        return super().has_ever_had_players()

    def requires_characters(self) -> bool:
        """
        Return whether the trial minigame requires players have a character at all times.

        Returns
        -------
        bool
            Whether the trial minigame requires players have a character at all times.
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
        Create a new timer managed by this trial minigame with given parameters.

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
            If True, the trial minigame will automatically delete the timer once it is terminated
            by it ticking out or manual termination. If False, no such automatic deletion will take
            place. Defaults to True.

        Returns
        -------
        Timer
            The created timer.

        Raises
        ------
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.GameTooManyTimersError
            If the trial minigame is already managing its maximum number of timers.

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
        Create a new timer managed by this trial minigame with given parameters.

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
            If True, the trial minigame will automatically delete the timer once it is terminated
            by it ticking out or manual termination. If False, no such automatic deletion will take
            place. Defaults to True.

        Returns
        -------
        Timer
            The created timer.

        Raises
        ------
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.GameTooManyTimersError
            If the trial minigame is already managing its maximum number of timers.

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
        except HubbedGameError.GameIsUnmanagedError:
            raise TrialMinigameError.GameIsUnmanagedError
        except HubbedGameError.GameTooManyTimersError:
            raise TrialMinigameError.GameTooManyTimersError

    def delete_timer(self, timer: Timer) -> str:
        """
        Delete a timer managed by this trial minigame, terminating it first if needed.

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
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.GameDoesNotManageTimerError
            If the trial minigame does not manage the target timer.

        """

        timer_id = self.unchecked_delete_timer(timer)
        self.manager._check_structure()
        return timer_id

    def unchecked_delete_timer(self, timer: Timer) -> str:
        """
        Delete a timer managed by this trial minigame, terminating it first if needed.

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
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.GameDoesNotManageTimerError
            If the trial minigame does not manage the target timer.

        """

        try:
            return super().unchecked_delete_timer(timer)
        except HubbedGameError.GameIsUnmanagedError:
            raise TrialMinigameError.GameIsUnmanagedError
        except HubbedGameError.GameDoesNotManageTimerError:
            raise TrialMinigameError.GameDoesNotManageTimerError

    def get_timers(self) -> Set[Timer]:
        """
        Return (a shallow copy of) the timers this trial minigame manages.

        Returns
        -------
        Set[Timer]
            Timers this trial minigame manages.

        """

        return super().get_timers()

    def get_timer_by_id(self, timer_id: str) -> Timer:
        """
        If `timer_tag` is the ID of a timer managed by this trial minigame, return that timer.

        Parameters
        ----------
        timer_id: str
            ID of timer this trial minigame manages.

        Returns
        -------
        Timer
            The timer whose ID matches the given ID.

        Raises
        ------
        TrialMinigameError.GameInvalidTimerIDError:
            If `timer_tag` is a str and it is not the ID of a timer this trial minigame manages.

        """

        try:
            return super().get_timer_by_id(timer_id)
        except HubbedGameError.GameInvalidTimerIDError:
            raise TrialMinigameError.GameInvalidTimerIDError

    def get_timer_limit(self) -> Union[int, None]:
        """
        Return the timer limit of this trial minigame.

        Returns
        -------
        Union[int, None]
            Timer limit.

        """

        return super().get_timer_limit()

    def get_timer_ids(self) -> Set[str]:
        """
        Return (a shallow copy of) the IDs of all timers managed by this trial minigame.

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
        Create a new team managed by this trial minigame.

        Parameters
        ----------
        team_type : _Team
            Class of team that will be produced. Defaults to None (and converted to the
            default team created by games, namely, _Team).
        creator : ClientManager.Client, optional
            The player who created this team. If set, they will also be added to the team if
            possible. The creator must be a player of this trial minigame. Defaults to None.
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
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.GameTooManyTeamsError
            If the trial minigame is already managing its maximum number of teams.
        TrialMinigameError.UserInAnotherTeamError
            If `creator` is not None and already part of a team managed by this trial minigame.

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
        Create a new team managed by this trial minigame.

        This method does not assert structural integrity.

        Parameters
        ----------
        team_type : _Team
            Class of team that will be produced. Defaults to None (and converted to the
            default team created by games, namely, _Team).
        creator : ClientManager.Client, optional
            The player who created this team. If set, they will also be added to the team if
            possible. The creator must be a player of this trial minigame. Defaults to None.
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
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.GameTooManyTeamsError
            If the trial minigame is already managing its maximum number of teams.
        TrialMinigameError.UserInAnotherTeamError
            If `creator` is not None and already part of a team managed by this trial minigame.

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
        except HubbedGameError.GameIsUnmanagedError:
            raise TrialMinigameError.GameIsUnmanagedError
        except HubbedGameError.GameTooManyTeamsError:
            raise TrialMinigameError.GameTooManyTeamsError
        except HubbedGameError.UserInAnotherTeamError:
            raise TrialMinigameError.UserInAnotherTeamError

    def delete_team(self, team: _Team) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a team managed by this trial minigame.

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
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.GameDoesNotManageTeamError
            If the trial minigame does not manage the target team.

        """

        team_id, players = self.unchecked_delete_team(team)
        self.manager._check_structure()
        return team_id, players

    def unchecked_delete_team(self, team: _Team) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a team managed by this trial minigame.

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
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.GameDoesNotManageTeamError
            If the trial minigame does not manage the target team.

        """

        try:
            return super().unchecked_delete_team(team)
        except HubbedGameError.GameIsUnmanagedError:
            raise TrialMinigameError.GameIsUnmanagedError
        except HubbedGameError.GameDoesNotManageTeamError:
            raise TrialMinigameError.GameDoesNotManageTeamError

    def manages_team(self, team: _Team) -> bool:
        """
        Return True if the team is managed by this trial minigame, False otherwise.

        Parameters
        ----------
        team : _Team
            The team to check.

        Returns
        -------
        bool
            True if the trial minigame manages this team, False otherwise.

        """

        return super().manages_team(team)

    def get_teams(self) -> Set[_Team]:
        """
        Return (a shallow copy of) the teams this trial minigame manages.

        Returns
        -------
        Set[_Team]
            Teams this trial minigame manages.

        """

        return super().get_teams()

    def get_team_by_id(self, team_id: str) -> _Team:
        """
        If `team_id` is the ID of a team managed by this trial minigame, return the team.

        Parameters
        ----------
        team_id : str
            ID of the team this trial minigame manages.

        Returns
        -------
        _Team
            The team that matches the given ID.

        Raises
        ------
        TrialMinigameError.GameInvalidTeamIDError:
            If `team_id` is not the ID of a team this trial minigame manages.

        """

        try:
            return super().get_team_by_id(team_id)
        except HubbedGameError.GameInvalidTeamIDError:
            raise TrialMinigameError.GameInvalidTeamIDError

    def get_team_limit(self) -> Union[int, None]:
        """
        Return the team limit of this trial minigame.

        Returns
        -------
        Union[int, None]
            Team limit.

        """

        return super().get_team_limit()

    def get_team_ids(self) -> Set[str]:
        """
        Return (a shallow copy of) the IDs of all teams managed by this trial minigame.

        Returns
        -------
        Set[str]
            The IDs of all managed teams.

        """

        return super().get_team_ids()

    def get_teams_of_user(self, user: ClientManager.Client) -> Set[_Team]:
        """
        Return (a shallow copy of) the teams managed by this trial minigame user `user` is a player
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
        Return (a shallow copy of) all the users that are part of some team managed by this
        trial minigame.

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
        TrialMinigameError.GameTooManyTeamsError
            If the trial minigame is already managing its maximum number of teams.

        """

        try:
            return super().get_available_team_id()
        except HubbedGameError.GameTooManyTeamsError:
            raise TrialMinigameError.GameTooManyTeamsError

    def get_autoadd_on_client_enter(self) -> bool:
        """
        Return True if the trial minigame will always attempt to add nonplayer users who enter an
        area part of the trial minigame, False otherwise.

        Returns
        -------
        bool
            True if the trial minigame will always attempt to add nonplayer users who enter an area
            part of the trial minigame, False otherwise.
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
        Add an area to this trial minigame's set of areas.

        Parameters
        ----------
        area : AreaManager.Area
            Area to add.

        Raises
        ------
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.AreaDisallowsBulletsError
            If the area to add disallows bullets.
        TrialMinigameError.AreaAlreadyInGameError
            If the area is already part of the trial minigame.
        TrialMinigameError.AreaHitGameConcurrentLimitError.
            If `area` has reached the concurrent area membership limit of any of the games with
            areas it belongs to managed by this manager, or by virtue of adding this area it will
            violate this trial minigame's concurrent area membership limit.

        """

        self.unchecked_add_area(area)
        self.manager._check_structure()

    def remove_area(self, area: AreaManager.Area):
        """
        Remove an area from this trial minigame's set of areas.
        If the area is already a part of the trial minigame, do nothing.
        If any player of the trial minigame is in this area, they are removed from the
        trial minigame.
        If the trial minigame has no areas remaining, it will be automatically destroyed.

        Parameters
        ----------
        area : AreaManager.Area
            Area to remove.

        Raises
        ------
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.AreaNotInGameError
            If the area is already not part of the trial minigame.

        """

        self.unchecked_remove_area(area)
        self.manager._check_structure()

    def unchecked_remove_area(self, area: AreaManager.Area):
        """
        Remove an area from this trial minigame's set of areas.
        If the area is already a part of the trial minigame, do nothing.
        If any player of the trial minigame is in this area, they are removed from the
        trial minigame.
        If the trial minigame has no areas remaining, it will be automatically destroyed.

        This method does not assert structural integrity.

        Parameters
        ----------
        area : AreaManager.Area
            Area to remove.

        Raises
        ------
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.AreaNotInGameError
            If the area is already not part of the trial minigame.

        """

        try:
            super().unchecked_remove_area(area)
        except HubbedGameError.GameIsUnmanagedError:
            raise TrialMinigameError.GameIsUnmanagedError
        except HubbedGameError.AreaNotInGameError:
            raise TrialMinigameError.AreaNotInGameError

    def requires_areas(self) -> bool:
        """
        Return whether the trial minigame requires areas at all times.

        Returns
        -------
        bool
            Whether the trial minigame requires areas at all times.
        """

        return super().requires_areas()

    def has_area(self, area: AreaManager.Area) -> bool:
        """
        If the area is part of this trial minigame's set of areas, return True; otherwise, return
        False.

        Parameters
        ----------
        area : AreaManager.Area
            Area to check.

        Returns
        -------
        bool
            True if the area is part of the trial minigame's set of areas, False otherwise.

        """

        return super().has_area(area)

    def get_areas(self) -> Set[AreaManager.Area]:
        """
        Return (a shallow copy of) the set of areas of this trial minigame.

        Returns
        -------
        Set[AreaManager.Area]
            Set of areas of the trial minigame.

        """

        return super().get_areas()

    def get_area_concurrent_limit(self) -> Union[int, None]:
        """
        Return the concurrent area membership limit of this trial minigame.

        Returns
        -------
        Union[int, None]
            The concurrent area membership limit.

        """

        return super().get_area_concurrent_limit()

    def get_users_in_areas(self) -> Set[ClientManager.Client]:
        """
        Return all users in areas part of the trial minigame, even those that are not players of
        the trial minigame.

        Returns
        -------
        Set[ClientManager.Client]
            All users in areas part of the trial minigame.

        """

        return super().get_users_in_areas()

    def get_nonleader_users_in_areas(self) -> Set[ClientManager.Client]:
        """
        Return all users in areas part of the trial minigame, even those that are not players of
        the trial minigame, such that they are not leaders of the trial minigame.

        Returns
        -------
        Set[ClientManager.Client]
            All users in areas part of the trial minigame that are not leaders of the trial minigame.

        """

        return super().get_nonleader_users_in_areas()

    def get_nonplayer_users_in_areas(self) -> Set[ClientManager.Client]:
        """
        Return all users in areas part of the trial minigame that are not players of the
        trial minigame.

        Returns
        -------
        Set[ClientManager.Client]
            All users in areas part of the trial minigame that are not players of the trial minigame.

        """

        return super().get_nonplayer_users_in_areas()

    def is_unmanaged(self):
        """
        Return True if this trial minigame is unmanaged, False otherwise.

        Returns
        -------
        bool
            True if unmanaged, False otherwise.

        """

        return super().is_unmanaged()

    def destroy(self):
        """
        Mark this trial minigame as destroyed and notify its manager so that it is deleted.
        If the trial minigame is already destroyed, this function does nothing.
        A trial minigame marked for destruction will delete all of its timers, teams, remove all
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
        Default callback for trial minigame player signaling it wants to check if sending an IC
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
        Default callback for trial minigame player signaling it has sent an IC message.
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
        Default callback for trial minigame player signaling it has changed character.

        By default it only checks if the player is now no longer having a character. If that is
        the case and the trial minigamerequires all players have characters, the player is automatically
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
        Default callback for trial minigame player signaling it was destroyed, for example, as a
        result of a disconnection.

        By default it only removes the player from the trial minigame If the trial minigame is
        already unmanaged or the player is not in the trial minigame, this callback does nothing.

        Parameters
        ----------
        player : ClientManager.Client
            Player that signaled it was destroyed.

        Returns
        -------
        None.

        """

        super()._on_client_destroyed(player)

    def _on_area_client_inbound_ms_check(
        self,
        area: AreaManager.Area,
        client: ClientManager.Client = None,
        contents: Dict[str, Any] = None
        ):
        """
        Default callback for trial minigame area signaling a client in the area sent an IC message.
        Unlike the ClientManager.Client callback for send_ic_check, this one is triggered
        regardless of whether the sender is part of the trial minigame or not. This is useful for
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

        super()._on_area_client_inbound_ms_check(area, client=client, contents=contents)

    def _on_area_destroyed(self, area: AreaManager.Area):
        """
        Default callback for trial minigame area signaling it was destroyed.

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
        Default callback for hub area manager signaling it loaded new areas.

        By default it calls self.destroy().

        Parameters
        ----------
        area_manager : AreaManager
            AreaManager that signaled the areas load.

        Returns
        -------
        None.

        """

        super()._on_areas_loaded(area_manager)


class _TrialMinigame(_TrialMinigameTrivialInherited):
    """
    A trial minigame is a hubbed game that is part of a trial. Any players of the trial minigame
    must be players of the trial, and any areas of the trial minigame must be areas of the trial.

    Each of these trial minigames may also set an autoadd on trial adding player flag. If set, if
    the parent trial adds a player, they will also be added to the trial minigame if possible; if
    this fails, no action is taken and no errors are propagated.

    Attributes
    ----------
    server : TsuserverDR
        Server the trial minigame belongs to.
    manager : HubbedGameManager
        Manager for this trial minigame.
    hub: _Hub
        Hub for this hubbed game.
    listener : Listener
        Standard listener of the trial minigame.

    Callback Methods
    ----------------
    _on_client_inbound_ms_check
        Method to perform once a player of the trial minigame wants to send an IC message.
    _on_client_inbound_ms_final
        Method to perform once a player of the trial minigame sends an IC message.
    _on_client_change_character
        Method to perform once a player of the trial minigame has changed character.
    _on_client_destroyed
        Method to perform once a player of the trial minigame is destroyed.
    _on_area_client_left_final
        Method to perform once a client left an area of the trial minigame.
    _on_area_client_entered_final
        Method to perform once a client entered an area of the trial minigame.
    _on_area_destroyed
        Method to perform once an area of the trial minigame is marked for destruction.

    """

    # (Private) Attributes
    # --------------------
    # _trial : _Trial
    #   Trial of the trial minigame
    # __autoadd_on_trial_player_add : bool
    #   Whether players that are added to the trial minigame will be automatically added if
    #   permitted by the conditions of the trial minigame.

    # Invariants
    # ----------
    # 1. The invariants from the parent class TrialMinigame are satisfied.

    def __init__(
        self,
        server: TsuserverDR,
        manager: HubbedGameManager,
        minigame_id: str,
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
        hub: _Hub = None,
        # new
        trial: _Trial = None,
        autoadd_on_trial_player_add: bool = False,
    ):
        """
        Create a trial minigame. A trial minigame should not be fully initialized anywhere
        else other than some manager code, as otherwise the manager will not recognize the
        trial minigame.

        Parameters
        ----------
        server : TsuserverDR
            Server the trial minigame belongs to.
        manager : GameManager
            Manager for this trial minigame.
        minigame_id : str
            Identifier of the trial minigame.
        player_limit : int or None, optional
            If an int, it is the maximum number of players the trial minigame supports. If None, it
            indicates the trial minigame has no player limit. Defaults to None.
        player_concurrent_limit : int or None, optional
            If an int, it is the maximum number of games managed by `manager` that any
            player of this trial minigame may belong to, including this trial minigame. If None, it
            indicates that this trial minigame does not care about how many other games managed by
            `manager` each of its players belongs to. Defaults to None.
        require_invitation : bool, optional
            If True, players can only be added to the trial minigame if they were previously
            invited. If False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the trial minigame has no players left, the trial minigame will
            automatically be deleted. If False, no such automatic deletion will happen.
            Defaults to True.
        require_leaders : bool, optional
            If True, if at any point the trial minigame has no leaders left, the trial minigame will
            choose a leader among any remaining players left; if no players are left, the next
            player added will be made leader. If False, no such automatic assignment will happen.
            Defaults to True.
        require_character : bool, optional
            If False, players without a character will not be allowed to join the trial minigame,
            and players that switch to something other than a character will be automatically
            removed from the trial minigame. If False, no such checks are made. A player without a
            character is considered one where player.has_participant_character() returns False. Defaults to
            False.
        team_limit : int or None, optional
            If an int, it is the maximum number of teams the trial minigame supports. If None, it
            indicates the trial minigame has no team limit. Defaults to None.
        timer_limit : int or None, optional
            If an int, it is the maximum number of timers the trial minigame supports. If None,
            it indicates the trial minigame has no timer limit. Defaults to None.
        area_concurrent_limit : int or None, optional
            If an int, it is the maximum number of trial minigames managed by `manager` that any
            area of this trial minigames may belong to, including this trial. If None, it indicates
            that this trial minigamedoes not care about how many other trial minigames managed by
            `manager` each of its areas belongs to. Defaults to 1 (an area may not be a part of
            another trial minigame managed by `manager` while being an area of this trial).
        autoadd_on_client_enter : bool, optional
            If True, nonplayer users that enter an area part of the trial minigame will be
            automatically added if permitted by the conditions of the trial minigame. If False, no
            such adding will take place. Defaults to False.
        require_areas : bool, optional
            If True, if at any point the trial minigame has no areas left, the game with areas
            will automatically be deleted. If False, no such automatic deletion will happen.
            Defaults to True.
        hub : _Hub, optional
            Hub the trial belongs to. Defaults to None.
        trial : _Trial, optional
            Trial the trial minigame is a part of.
        autoadd_on_trial_player_add : bool, optional
            If True, players that are added to the trial minigame will be automatically added if
            permitted by the conditions of the trial minigame. If False, no such adding will take
            place. Defaults to False.

        """

        self._trial = trial
        self._autoadd_on_trial_player_add = autoadd_on_trial_player_add

        super().__init__(
            server,
            manager,
            minigame_id,
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
            hub=hub,
        )

        self.listener.subscribe(trial)
        self.listener.update_events({
            'trial_player_added': self._on_trial_player_added,
            })

    def get_type_name(self) -> str:
        """
        Return the type name of the trial minigame. Names are fully lowercase.
        Implementations of the class should replace this with a human readable name of the trial
        minigame.

        Returns
        -------
        str
            Type name of the trial minigame.

        """

        return "trial minigame"

    def unchecked_add_player(self, user: ClientManager.Client):
        """
        Make a user a player of the trial minigame. By default this player will not be a leader,
        unless the trial minigame has no leaders and it requires a leader.
        It will also subscribe the trial minigame to the player so it can listen to its updates.

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to add to the trial minigame. They must be in an area part of the trial minigame.

        Raises
        ------
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.UserNotPlayerError
            If the user is not a player of the trial.
        TrialMinigameError.UserNotInAreaError
            If the user is not in an area part of the trial minigame.
        TrialMinigameError.UserHasNoCharacterError
            If the user has no character but the trial minigame requires that all players have
            characters.
        TrialMinigameError.UserNotInvitedError
            If the trial minigame requires players be invited to be added and the user is not
            invited.
        TrialMinigameError.UserAlreadyPlayerError
            If the user to add is already a user of the trial minigame.
        TrialMinigameError.UserHitGameConcurrentLimitError
            If the player has reached the concurrent player membership of any of the trial minigames
            managed by the manager of this trial minigame, or by virtue of joining this
            trial minigame they would violate this trial minigame's concurrent player membership
            limit.
        TrialMinigameError.GameIsFullError
            If the trial minigame reached its player limit.

        """

        if self.is_unmanaged():
            raise TrialMinigameError.GameIsUnmanagedError
        if not self._trial.is_player(user):
            raise TrialMinigameError.UserNotPlayerError

        try:
            super().unchecked_add_player(user)
        except HubbedGameError.GameIsUnmanagedError:
            raise RuntimeError(self)
        except HubbedGameError.UserNotInAreaError:
            raise TrialMinigameError.UserNotInAreaError
        except HubbedGameError.UserHasNoCharacterError:
            raise TrialMinigameError.UserHasNoCharacterError
        except HubbedGameError.UserNotInvitedError:
            raise TrialMinigameError.UserNotInvitedError
        except HubbedGameError.UserAlreadyPlayerError:
            raise TrialMinigameError.UserAlreadyPlayerError
        except HubbedGameError.UserHitGameConcurrentLimitError:
            raise TrialMinigameError.UserHitGameConcurrentLimitError
        except HubbedGameError.GameIsFullError:
            raise TrialMinigameError.GameIsFullError

    def unchecked_add_area(self, area):
        """
        Add an area to this trial minigame's set of areas.

        This method does not assert structural integrity.

        Parameters
        ----------
        area : AreaManager.Area
            Area to add.

        Raises
        ------
        TrialMinigameError.GameIsUnmanagedError
            If the trial minigame was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialMinigameError.AreaNotInGameError
            If the area is not part of the trial of the trial minigame.
        TrialMinigameError.AreaAlreadyInGameError
            If the area is already part of the trial minigame.
        TrialMinigameError.AreaHitGameConcurrentLimitError.
            If `area` has reached the concurrent area membership limit of any of the games it
            belongs to managed by this manager, or by virtue of adding this area it will violate
            this trial minigame's concurrent area membership limit.

        """

        if self.is_unmanaged():
            raise TrialMinigameError.GameIsUnmanagedError
        if not self._trial.has_area(area):
            raise TrialMinigameError.AreaNotInGameError

        try:
            super().unchecked_add_area(area)
        except HubbedGameError.GameIsUnmanagedError:
            raise RuntimeError(self)
        except HubbedGameError.AreaAlreadyInGameError:
            raise TrialMinigameError.AreaAlreadyInGameError
        except HubbedGameError.AreaHitGameConcurrentLimitError:
            raise TrialMinigameError.AreaHitGameConcurrentLimitError

    def get_trial(self) -> _Trial:
        """
        Return the trial of the trial minigame.

        Returns
        -------
        _Trial
            Trial of the trial minigame.

        """

        return self._trial

    def get_autoadd_on_trial_player_add(self) -> bool:
        """
        Return whether the trial minigame will attempt to add players to it if the parent trial
        added it as player.

        Returns
        -------
        bool.
            True if an attempt will be made automatically, False otherwise.
        """

        return self._autoadd_on_trial_player_add

    def set_autoadd_on_trial_player_add(self, new_value: bool):
        """
        Set the new value of the autoadd on trial adding a player flag.

        Parameters
        ----------
        new_value : bool
            New value.

        """

        self.unchecked_set_autoadd_on_trial_player_add(new_value)
        self.manager._check_structure()

    def unchecked_set_autoadd_on_trial_player_add(self, new_value: bool):
        """
        Set the new value of the autoadd on trial adding a player flag.

        Parameters
        ----------
        new_value : bool
            New value.

        """

        self._autoadd_on_trial_player_add = new_value

    def get_type(self) -> TRIALMINIGAMES:
        """
        Return the type of the trial minigame.

        Returns
        -------
        TRIALMINIGAMES
            Type of trial minigame.

        """

        # Should be overriden in child class.
        raise NotImplementedError

    def unchecked_destroy(self):
        """
        Mark this trial minigameas destroyed and notify its manager so that it is deleted.
        If the trial minigameis already destroyed, this function does nothing.

        This method is reentrant (it will do nothing though).

        This method does not assert structural integrity.

        Returns
        -------
        None.

        """

        # Keep track of areas for later
        areas = self.get_areas()

        # Then carry on
        super().unchecked_destroy()

        # Force every user in the former areas of the trial minigame to switch to trial gamemode
        for area in areas:
            for user in area.clients:
                user.send_gamemode(name='trial')

    def _on_area_client_left_final(
        self,
        area: AreaManager.Area,
        client: ClientManager.Client = None,
        old_displayname: str = None,
        ignore_bleeding: bool = False,
        ignore_autopass: bool = False,
        ):
        """
        If a player left to an area not part of the trial minigame, remove the player and warn them
        and the leaders of the trial minigame.

        If a non-plyer left to an area not part of the trial minigame, warn them and the leaders of
        the trial minigame.

        Parameters
        ----------
        area : AreaManager.Area
            Area that signaled a client has left.
        client : ClientManager.Client, optional
            The client that has left. The default is None.
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

        was_leader = self.is_leader(client) if self.is_player(client) else False
        if client in self.get_players() and client.area not in self.get_areas():
            client.send_ooc(f'You have left to an area not part of trial minigame '
                            f'`{self.get_id()}` and thus were automatically removed from the '
                            f'minigame.')
            client.send_ooc_others(f'(X) Player {old_displayname} [{client.id}] has left to '
                                   f'an area not part of your trial minigame and thus was '
                                   f'automatically removed from it '
                                   f'({area.id}->{client.area.id}).',
                                   pred=lambda c: c in self.get_leaders(), in_hub=area.hub)

            self.remove_player(client)
            if self.is_unmanaged():
                if was_leader:
                    client.send_ooc(f'Your trial minigame `{self.get_id()}` was automatically '
                                    f'ended as it lost all its players.')
                client.send_ooc_others(f'(X) Trial minigame `{self.get_id()}` was automatically '
                                       f'ended as it lost all its players.',
                                       is_zstaff_flex=True, in_hub=area.hub)

        elif client.area not in self.get_areas():
            client.send_ooc(f'You have left to an area not part of trial minigame '
                            f'`{self.get_id()}`.')
            client.send_ooc_others(f'(X) Player {old_displayname} [{client.id}] has left to an '
                                   f'area not part of your trial minigame '
                                   f'({area.id}->{client.area.id}).',
                                   pred=lambda c: c in self.get_leaders(), in_hub=area.hub)

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
        If a non-player entered, warn them and the leaders of the trial minigame.

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

        if client not in self.get_players() and old_area not in self.get_areas():
            old_area_id = str(old_area.id) if old_area else "SERVER_SELECT"
            client.send_ooc(f'You have entered an area part of trial minigame `{self.get_id()}`.')
            client.send_ooc_others(f'(X) Non-player {client.displayname} [{client.id}] has entered '
                                   f'an area part of your trial minigame '
                                   f'({old_area_id}->{area.id}).',
                                   pred=lambda c: c in self.get_leaders())

    def _on_trial_player_added(
        self,
        trial: _Trial,
        player: ClientManager.Client = None
        ):

        """
        Default callback when the parent trial adds a player.
        If a player was added to the trial of the trial minigame, attempt to add the player to the
        trial minigame as well. If unsuccessful, do nothing.
        Do note the player may already be part of the trial minigame by this point: if another
        thread was also listening to this callback and acted upon it before the current thread by
        adding the player to the trial minigame.

        Parameters
        ----------
        trial : TrialManager._Trial
            Trial that generated the callback. Typically is self.get_trial().
        player : ClientManager.Client, optional
            Player that was added to the trial.

        Returns
        -------
        None.

        """

        if self.get_autoadd_on_trial_player_add():
            try:
                self.add_player(player)
            except TrialMinigameError:
                pass

    def __str__(self):
        """
        Return a string representation of this trial minigame.

        Returns
        -------
        str
            Representation.

        """

        return (f"TrialMinigame::{self.get_id()}:{self.get_trial()}"
                f"{self.get_players()}:{self.get_leaders()}:{self.get_invitations()}"
                f"{self.get_timers()}:"
                f"{self.get_teams()}:"
                f"{self.get_areas()}")

    def __repr__(self):
        """
        Return a representation of this trial minigame.

        Returns
        -------
        str
            Printable representation.

        """

        return (f'TrialMinigame(server, {self.manager.get_id()}, "{self.get_id()}", '
                f'player_limit={self.get_player_limit()}, '
                f'player_concurrent_limit={self.get_player_concurrent_limit()}, '
                f'require_players={self.requires_players()}, '
                f'require_invitations={self.requires_invitations()}, '
                f'require_leaders={self.requires_leaders()}, '
                f'require_character={self.requires_characters()}, '
                f'team_limit={self._team_manager.get_managee_limit()}, '
                f'timer_limit={self._timer_manager.get_timer_limit()}, '
                f'areas={self.get_areas()}, '
                f'trial_id={self.get_trial().get_id()}), '
                f'|| '
                f'players={self.get_players()}, '
                f'invitations={self.get_invitations()}, '
                f'leaders={self.get_leaders()}, '
                f'timers={self.get_timers()}, '
                f'teams={self.get_teams()}, '
                f'unmanaged={self.is_unmanaged()}), '
                f')')
