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
Module that contains the nonstop debate game.

"""

from __future__ import annotations

from enum import Enum, auto

import functools
import typing
from typing import Callable, Dict, Set, Any, Tuple, Type, Union

from server import logger
from server.exceptions import NonStopDebateError, TrialMinigameError
from server.exceptions import ClientError, TimerError
from server.trialminigame import _TrialMinigame, TRIALMINIGAMES

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


class NSDMode(Enum):
    """
    Modes for a nonstop debate.
    """

    PRERECORDING = auto()
    RECORDING = auto()
    LOOPING = auto()
    INTERMISSION = auto()
    INTERMISSION_POSTBREAK = auto()
    INTERMISSION_TIMERANOUT = auto()


class _NonStopDebateTrivialInherited(_TrialMinigame):
    """
    This class should not be instantiated.
    """

    def get_id(self) -> str:
        """
        Return the ID of this nonstop debate.

        Returns
        -------
        str
            The ID.

        """

        return super().get_id()

    def get_numerical_id(self) -> int:
        """
        Return the numerical portion of the ID of this nonstop debate.

        Returns
        -------
        int
            Numerical portion of the ID.
        """

        return super().get_numerical_id()

    def get_name(self) -> str:
        """
        Get the name of the nonstop debate.

        Returns
        -------
        str
            Name.
        """

        return super().get_name()

    def set_name(self, name: str):
        """
        Set the name of the nonstop debate.

        Parameters
        ----------
        name : str
            Name.
        """

        self.unchecked_set_name(name)
        self.manager._check_structure()

    def unchecked_set_name(self, name: str):
        """
        Set the name of the nonstop debate.

        This method does not assert structural integrity.

        Parameters
        ----------
        name : str
            Name.
        """

        super().unchecked_set_name(name)

    def get_player_limit(self) -> Union[int, None]:
        """
        Return the player membership limit of this nonstop debate.

        Returns
        -------
        Union[int, None]
            The player membership limit.

        """

        return super().get_player_limit()

    def get_player_concurrent_limit(self) -> Union[int, None]:
        """
        Return the concurrent player membership limit of this nonstop debate.

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
        Return (a shallow copy of) the set of players of this nonstop debate that satisfy a
        condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all players returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) players of this nonstop debate.

        """

        return super().get_players(cond=cond)

    def is_player(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is a player of the nonstop debate.

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
        Make a user a player of the nonstop debate. By default this player will not be a leader,
        unless the nonstop debate has no leaders and it requires a leader.
        It will also subscribe the nonstop debate to the player so it can listen to its updates.

        Newly added players will be ordered to switch to a 'nonstop debate' variant.

        Parameters
        ----------
        user : ClientManager.Client
            User to add to the nonstop debate. They must be in an area part of the nonstop debate.

        Raises
        ------
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.UserNotPlayerError
            If the user is not a player of the trial.
        NonStopDebateError.UserNotInAreaError
            If the user is not in an area part of the nonstop debate.
        NonStopDebateError.UserHasNoCharacterError
            If the user has no character but the nonstop debate requires that all players have
            characters.
        NonStopDebateError.UserNotInvitedError
            If the nonstop debate requires players be invited to be added and the user is not
            invited.
        NonStopDebateError.UserAlreadyPlayerError
            If the user to add is already a user of the nonstop debate.
        NonStopDebateError.UserHitGameConcurrentLimitError
            If the player has reached the concurrent player membership of any of the nonstop debate
            managed by the manager of this nonstop debate, or by virtue of joining this
            nonstop debate they would violate this nonstop debate's concurrent player membership
            limit.
        NonStopDebateError.GameIsFullError
            If the nonstop debate reached its player limit.

        """

        self.unchecked_add_player(user)
        self.manager._check_structure()

    def remove_player(self, user: ClientManager.Client):
        """
        Make a user be no longer a player of this nonstop debate. If they were part of a team
        managed by this nonstop debate, they will also be removed from said team. It will also
        unsubscribe the nonstop debate from the player so it will no longer listen to its updates.

        If the nonstop debate required that there it always had players and by calling this method
        the nonstop debate had no more players, the nonstop debate will automatically be scheduled
        for deletion.

        Parameters
        ----------
        user : ClientManager.Client
            User to remove.

        Raises
        ------
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.UserNotPlayerError
            If the user to remove is already not a player of this nonstop debate.

        """

        self.unchecked_remove_player(user)
        self.manager._check_structure()

    def requires_players(self) -> bool:
        """
        Return whether the nonstop debate requires players at all times.

        Returns
        -------
        bool
            Whether the nonstop debate requires players at all times.
        """

        return super().requires_players()

    def get_invitations(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
    ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of invited users of this nonstop debate that satisfy a
        condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all invited users returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) invited users of this nonstop debate.

        """

        return super().get_invitations(cond=cond)

    def is_invited(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is invited to the nonstop debate.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Raises
        ------
        NonStopDebateError.UserAlreadyPlayerError
            If the user is a player of this nonstop debate.

        Returns
        -------
        bool
            True if the user is invited, False otherwise.

        """

        try:
            return super().is_invited(user)
        except TrialMinigameError.UserAlreadyPlayerError:
            raise NonStopDebateError.UserAlreadyPlayerError

    def add_invitation(self, user: ClientManager.Client):
        """
        Mark a user as invited to this nonstop debate.

        Parameters
        ----------
        user : ClientManager.Client
            User to invite to the nonstop debate.

        Raises
        ------
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.GameDoesNotTakeInvitationsError
            If the nonstop debate does not require users be invited to the nonstop debate.
        NonStopDebateError.UserAlreadyInvitedError
            If the player to invite is already invited to the nonstop debate.
        NonStopDebateError.UserAlreadyPlayerError
            If the player to invite is already a player of the nonstop debate.

        """

        self.unchecked_add_invitation(user)
        self.manager._check_structure()

    def unchecked_add_invitation(self, user: ClientManager.Client):
        """
        Mark a user as invited to this nonstop debate.

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to invite to the nonstop debate.

        Raises
        ------
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.GameDoesNotTakeInvitationsError
            If the nonstop debate does not require users be invited to the nonstop debate.
        NonStopDebateError.UserAlreadyInvitedError
            If the player to invite is already invited to the nonstop debate.
        NonStopDebateError.UserAlreadyPlayerError
            If the player to invite is already a player of the nonstop debate.

        """

        try:
            super().unchecked_add_invitation(user)
        except TrialMinigameError.GameIsUnmanagedError:
            raise NonStopDebateError.GameIsUnmanagedError
        except TrialMinigameError.GameDoesNotTakeInvitationsError:
            raise NonStopDebateError.GameDoesNotTakeInvitationsError
        except TrialMinigameError.UserAlreadyInvitedError:
            raise NonStopDebateError.UserAlreadyInvitedError
        except TrialMinigameError.UserAlreadyPlayerError:
            raise NonStopDebateError.UserAlreadyPlayerError

    def remove_invitation(self, user: ClientManager.Client):
        """
        Mark a user as no longer invited to this nonstop debate (uninvite).

        Parameters
        ----------
        user : ClientManager.Client
            User to uninvite.

        Raises
        ------
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.GameDoesNotTakeInvitationsError
            If the nonstop debate does not require users be invited to the nonstop debate.
        NonStopDebateError.UserNotInvitedError
            If the user to uninvite is already not invited to this nonstop debate.

        """

        self.unchecked_remove_invitation(user)
        self.manager._check_structure()

    def unchecked_remove_invitation(self, user: ClientManager.Client):
        """
        Mark a user as no longer invited to this nonstop debate (uninvite).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to uninvite.

        Raises
        ------
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.GameDoesNotTakeInvitationsError
            If the nonstop debate does not require users be invited to the nonstop debate.
        NonStopDebateError.UserNotInvitedError
            If the user to uninvite is already not invited to this nonstop debate.

        """

        try:
            super().unchecked_remove_invitation(user)
        except TrialMinigameError.GameIsUnmanagedError:
            raise NonStopDebateError.GameIsUnmanagedError
        except TrialMinigameError.GameDoesNotTakeInvitationsError:
            raise NonStopDebateError.GameDoesNotTakeInvitationsError
        except TrialMinigameError.UserNotInvitedError:
            raise NonStopDebateError.UserNotInvitedError

    def requires_invitations(self):
        """
        Return True if the nonstop debate requires players be invited before being allowed to join
        the nonstop debate, False otherwise.

        Returns
        -------
        bool
            True if the nonstop debate requires players be invited before being allowed to join
            the nonstop debate, False otherwise.
        """

        return super().requires_invitations()

    def get_leaders(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
    ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of leaders of this nonstop debate that satisfy a condition
        if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all leaders returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) leaders of this nonstop debate.

        """

        return super().get_leaders(cond=cond)

    def get_regulars(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
    ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of players of this nonstop debate that are regulars and
        satisfy a condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all regulars returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) regulars of this nonstop debate.

        """

        return super().get_regulars(cond=cond)

    def is_leader(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is a leader of the nonstop debate.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Raises
        ------
        NonStopDebateError.UserNotPlayerError
            If the player to test is not a player of this nonstop debate.

        Returns
        -------
        bool
            True if the player is a user, False otherwise.

        """

        try:
            return super().is_leader(user)
        except TrialMinigameError.UserNotPlayerError:
            raise NonStopDebateError.UserNotPlayerError

    def add_leader(self, user: ClientManager.Client):
        """
        Set a user as leader of this nonstop debate (promote to leader).

        Parameters
        ----------
        user : ClientManager.Client
            Player to promote to leader.

        Raises
        ------
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.UserNotPlayerError
            If the player to promote is not a player of this nonstop debate.
        NonStopDebateError.UserAlreadyLeaderError
            If the player to promote is already a leader of this nonstop debate.

        """

        self.unchecked_add_leader(user)
        self.manager._check_structure()

    def unchecked_add_leader(self, user: ClientManager.Client):
        """
        Set a user as leader of this nonstop debate (promote to leader).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            Player to promote to leader.

        Raises
        ------
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.UserNotPlayerError
            If the player to promote is not a player of this nonstop debate.
        NonStopDebateError.UserAlreadyLeaderError
            If the player to promote is already a leader of this nonstop debate.

        """

        try:
            super().unchecked_add_leader(user)
        except TrialMinigameError.GameIsUnmanagedError:
            raise NonStopDebateError.GameIsUnmanagedError
        except TrialMinigameError.UserNotPlayerError:
            raise NonStopDebateError.UserNotPlayerError
        except TrialMinigameError.UserAlreadyLeaderError:
            raise NonStopDebateError.UserAlreadyLeaderError

    def remove_leader(self, user: ClientManager.Client):
        """
        Make a user no longer leader of this nonstop debate (demote).

        Parameters
        ----------
        user : ClientManager.Client
            User to demote.

        Raises
        ------
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.UserNotPlayerError
            If the player to demote is not a player of this nonstop debate.
        NonStopDebateError.UserNotLeaderError
            If the player to demote is already not a leader of this nonstop debate.

        """

        self.unchecked_remove_leader(user)
        self.manager._check_structure()

    def unchecked_remove_leader(self, user: ClientManager.Client):
        """
        Make a user no longer leader of this nonstop debate (demote).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to demote.

        Raises
        ------
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.UserNotPlayerError
            If the player to demote is not a player of this nonstop debate.
        NonStopDebateError.UserNotLeaderError
            If the player to demote is already not a leader of this nonstop debate.

        """

        try:
            super().unchecked_remove_leader(user)
        except TrialMinigameError.GameIsUnmanagedError:
            raise NonStopDebateError.GameIsUnmanagedError
        except TrialMinigameError.UserNotPlayerError:
            raise NonStopDebateError.UserNotPlayerError
        except TrialMinigameError.UserNotLeaderError:
            raise NonStopDebateError.UserNotLeaderError

    def has_ever_had_players(self) -> bool:
        """
        Return True if a player has ever been added to this nonstop debate, False otherwise.

        Returns
        -------
        bool
            True if the nonstop debate has ever had a player added, False otherwise.

        """

        return super().has_ever_had_players()

    def requires_leaders(self) -> bool:
        """
        Return whether the nonstop debate requires leaders at all times.

        Returns
        -------
        bool
            Whether the nonstop debate requires leaders at all times.
        """

        return super().requires_leaders()

    def requires_participant_characters(self) -> bool:
        """
        Return whether the nonstop debate requires players have a participant character at all times.

        Returns
        -------
        bool
            Whether the nonstop debate requires players have a participant character at all times.
        """

        return super().requires_participant_characters()

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
        Create a new timer managed by this nonstop debate with given parameters.

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
            If True, the nonstop debate will automatically delete the timer once it is terminated
            by it ticking out or manual termination. If False, no such automatic deletion will take
            place. Defaults to True.

        Returns
        -------
        Timer
            The created timer.

        Raises
        ------
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.GameTooManyTimersError
            If the nonstop debate is already managing its maximum number of timers.

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
        Create a new timer managed by this nonstop debate with given parameters.

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
            If True, the nonstop debate will automatically delete the timer once it is terminated
            by it ticking out or manual termination. If False, no such automatic deletion will take
            place. Defaults to True.

        Returns
        -------
        Timer
            The created timer.

        Raises
        ------
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.GameTooManyTimersError
            If the nonstop debate is already managing its maximum number of timers.

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
        except TrialMinigameError.GameIsUnmanagedError:
            raise NonStopDebateError.GameIsUnmanagedError
        except TrialMinigameError.GameTooManyTimersError:
            raise NonStopDebateError.GameTooManyTimersError

    def delete_timer(self, timer: Timer) -> str:
        """
        Delete a timer managed by this nonstop debate, terminating it first if needed.

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
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.GameDoesNotManageTimerError
            If the nonstop debate does not manage the target timer.

        """

        timer_id = self.unchecked_delete_timer(timer)
        self.manager._check_structure()
        return timer_id

    def unchecked_delete_timer(self, timer: Timer) -> str:
        """
        Delete a timer managed by this nonstop debate, terminating it first if needed.

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
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.GameDoesNotManageTimerError
            If the nonstop debate does not manage the target timer.

        """

        try:
            return super().unchecked_delete_timer(timer)
        except TrialMinigameError.GameIsUnmanagedError:
            raise NonStopDebateError.GameIsUnmanagedError
        except TrialMinigameError.GameDoesNotManageTimerError:
            raise NonStopDebateError.GameDoesNotManageTimerError

    def get_timers(self) -> Set[Timer]:
        """
        Return (a shallow copy of) the timers this nonstop debate manages.

        Returns
        -------
        Set[Timer]
            Timers this nonstop debate manages.

        """

        return super().get_timers()

    def get_timer_by_id(self, timer_id: str) -> Timer:
        """
        If `timer_tag` is the ID of a timer managed by this nonstop debate, return that timer.

        Parameters
        ----------
        timer_id: str
            ID of timer this nonstop debate manages.

        Returns
        -------
        Timer
            The timer whose ID matches the given ID.

        Raises
        ------
        NonStopDebateError.GameInvalidTimerIDError:
            If `timer_tag` is a str and it is not the ID of a timer this nonstop debate manages.

        """

        try:
            return super().get_timer_by_id(timer_id)
        except TrialMinigameError.GameInvalidTimerIDError:
            raise NonStopDebateError.GameInvalidTimerIDError

    def get_timer_limit(self) -> Union[int, None]:
        """
        Return the timer limit of this nonstop debate.

        Returns
        -------
        Union[int, None]
            Timer limit.

        """

        return super().get_timer_limit()

    def get_timer_ids(self) -> Set[str]:
        """
        Return (a shallow copy of) the IDs of all timers managed by this nonstop debate.

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
        Create a new team managed by this nonstop debate.

        Parameters
        ----------
        team_type : _Team
            Class of team that will be produced. Defaults to None (and converted to the
            default team created by games, namely, _Team).
        creator : ClientManager.Client, optional
            The player who created this team. If set, they will also be added to the team if
            possible. The creator must be a player of this nonstop debate. Defaults to None.
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
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.GameTooManyTeamsError
            If the nonstop debate is already managing its maximum number of teams.
        NonStopDebateError.UserInAnotherTeamError
            If `creator` is not None and already part of a team managed by this nonstop debate.

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
        Create a new team managed by this nonstop debate.

        This method does not assert structural integrity.

        Parameters
        ----------
        team_type : _Team
            Class of team that will be produced. Defaults to None (and converted to the
            default team created by games, namely, _Team).
        creator : ClientManager.Client, optional
            The player who created this team. If set, they will also be added to the team if
            possible. The creator must be a player of this nonstop debate. Defaults to None.
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
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.GameTooManyTeamsError
            If the nonstop debate is already managing its maximum number of teams.
        NonStopDebateError.UserInAnotherTeamError
            If `creator` is not None and already part of a team managed by this nonstop debate.

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
        except TrialMinigameError.GameIsUnmanagedError:
            raise NonStopDebateError.GameIsUnmanagedError
        except TrialMinigameError.GameTooManyTeamsError:
            raise NonStopDebateError.GameTooManyTeamsError
        except TrialMinigameError.UserInAnotherTeamError:
            raise NonStopDebateError.UserInAnotherTeamError

    def delete_team(self, team: _Team) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a team managed by this nonstop debate.

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
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.GameDoesNotManageTeamError
            If the nonstop debate does not manage the target team.

        """

        team_id, players = self.unchecked_delete_team(team)
        self.manager._check_structure()
        return team_id, players

    def unchecked_delete_team(self, team: _Team) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a team managed by this nonstop debate.

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
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.GameDoesNotManageTeamError
            If the nonstop debate does not manage the target team.

        """

        try:
            return super().unchecked_delete_team(team)
        except TrialMinigameError.GameIsUnmanagedError:
            raise NonStopDebateError.GameIsUnmanagedError
        except TrialMinigameError.GameDoesNotManageTeamError:
            raise NonStopDebateError.GameDoesNotManageTeamError

    def manages_team(self, team: _Team) -> bool:
        """
        Return True if the team is managed by this nonstop debate, False otherwise.

        Parameters
        ----------
        team : _Team
            The team to check.

        Returns
        -------
        bool
            True if the nonstop debate manages this team, False otherwise.

        """

        return super().manages_team(team)

    def get_teams(self) -> Set[_Team]:
        """
        Return (a shallow copy of) the teams this nonstop debate manages.

        Returns
        -------
        Set[_Team]
            Teams this nonstop debate manages.

        """

        return super().get_teams()

    def get_team_by_id(self, team_id: str) -> _Team:
        """
        If `team_id` is the ID of a team managed by this nonstop debate, return the team.

        Parameters
        ----------
        team_id : str
            ID of the team this nonstop debate manages.

        Returns
        -------
        _Team
            The team that matches the given ID.

        Raises
        ------
        NonStopDebateError.GameInvalidTeamIDError:
            If `team_id` is not the ID of a team this nonstop debate manages.

        """

        try:
            return super().get_team_by_id(team_id)
        except TrialMinigameError.GameInvalidTeamIDError:
            raise NonStopDebateError.GameInvalidTeamIDError

    def get_team_limit(self) -> Union[int, None]:
        """
        Return the team limit of this nonstop debate.

        Returns
        -------
        Union[int, None]
            Team limit.

        """

        return super().get_team_limit()

    def get_team_ids(self) -> Set[str]:
        """
        Return (a shallow copy of) the IDs of all teams managed by this nonstop debate.

        Returns
        -------
        Set[str]
            The IDs of all managed teams.

        """

        return super().get_team_ids()

    def get_teams_of_user(self, user: ClientManager.Client) -> Set[_Team]:
        """
        Return (a shallow copy of) the teams managed by this nonstop debate user `user` is a player
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
        nonstop debate.

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
        NonStopDebateError.GameTooManyTeamsError
            If the nonstop debate is already managing its maximum number of teams.

        """

        try:
            return super().get_available_team_id()
        except TrialMinigameError.GameTooManyTeamsError:
            raise NonStopDebateError.GameTooManyTeamsError

    def get_autoadd_on_client_enter(self) -> bool:
        """
        Return True if the nonstop debate will always attempt to add nonplayer users who enter an
        area part of the nonstop debate, False otherwise.

        Returns
        -------
        bool
            True if the nonstop debate will always attempt to add nonplayer users who enter an area
            part of the nonstop debate, False otherwise.
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
        Add an area to this nonstop debate's set of areas.

        Parameters
        ----------
        area : AreaManager.Area
            Area to add.

        Raises
        ------
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.AreaDisallowsBulletsError
            If the area to add disallows bullets.
        NonStopDebateError.AreaAlreadyInGameError
            If the area is already part of the nonstop debate.
        NonStopDebateError.AreaHitGameConcurrentLimitError.
            If `area` has reached the concurrent area membership limit of any of the games with
            areas it belongs to managed by this manager, or by virtue of adding this area it will
            violate this nonstop debate's concurrent area membership limit.

        """

        self.unchecked_add_area(area)
        self.manager._check_structure()

    def unchecked_add_area(self, area):
        """
        Add an area to this nonstop debate's set of areas.

        This method does not assert structural integrity.

        Parameters
        ----------
        area : AreaManager.Area
            Area to add.

        Raises
        ------
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.AreaNotInGameError
            If the area is not part of the trial of the nonstop debate.
        NonStopDebateError.AreaAlreadyInGameError
            If the area is already part of the nonstop debate.
        NonStopDebateError.AreaHitGameConcurrentLimitError.
            If `area` has reached the concurrent area membership limit of any of the games it
            belongs to managed by this manager, or by virtue of adding this area it will violate
            this nonstop debate's concurrent area membership limit.

        """

        try:
            super().unchecked_add_area(area)
        except TrialMinigameError.AreaNotInGameError:
            raise NonStopDebateError.AreaNotInGameError
        except TrialMinigameError.GameIsUnmanagedError:
            raise NonStopDebateError.GameIsUnmanagedError
        except TrialMinigameError.AreaAlreadyInGameError:
            raise NonStopDebateError.AreaAlreadyInGameError
        except TrialMinigameError.AreaHitGameConcurrentLimitError:
            raise NonStopDebateError.AreaHitGameConcurrentLimitError

    def remove_area(self, area: AreaManager.Area):
        """
        Remove an area from this nonstop debate's set of areas.
        If the area is already a part of the nonstop debate, do nothing.
        If any player of the nonstop debate is in this area, they are removed from the
        nonstop debate.
        If the nonstop debate has no areas remaining, it will be automatically destroyed.

        Parameters
        ----------
        area : AreaManager.Area
            Area to remove.

        Raises
        ------
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.AreaNotInGameError
            If the area is already not part of the nonstop debate.

        """

        self.unchecked_remove_area(area)
        self.manager._check_structure()

    def unchecked_remove_area(self, area: AreaManager.Area):
        """
        Remove an area from this nonstop debate's set of areas.
        If the area is already a part of the nonstop debate, do nothing.
        If any player of the nonstop debate is in this area, they are removed from the
        nonstop debate.
        If the nonstop debate has no areas remaining, it will be automatically destroyed.

        This method does not assert structural integrity.

        Parameters
        ----------
        area : AreaManager.Area
            Area to remove.

        Raises
        ------
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.AreaNotInGameError
            If the area is already not part of the nonstop debate.

        """

        try:
            super().unchecked_remove_area(area)
        except TrialMinigameError.GameIsUnmanagedError:
            raise NonStopDebateError.GameIsUnmanagedError
        except TrialMinigameError.AreaNotInGameError:
            raise NonStopDebateError.AreaNotInGameError

    def requires_areas(self) -> bool:
        """
        Return whether the nonstop debate requires areas at all times.

        Returns
        -------
        bool
            Whether the nonstop debate requires areas at all times.
        """

        return super().requires_areas()

    def has_area(self, area: AreaManager.Area) -> bool:
        """
        If the area is part of this nonstop debate's set of areas, return True; otherwise, return
        False.

        Parameters
        ----------
        area : AreaManager.Area
            Area to check.

        Returns
        -------
        bool
            True if the area is part of the nonstop debate's set of areas, False otherwise.

        """

        return super().has_area(area)

    def get_areas(self) -> Set[AreaManager.Area]:
        """
        Return (a shallow copy of) the set of areas of this nonstop debate.

        Returns
        -------
        Set[AreaManager.Area]
            Set of areas of the nonstop debate.

        """

        return super().get_areas()

    def get_area_concurrent_limit(self) -> Union[int, None]:
        """
        Return the concurrent area membership limit of this nonstop debate.

        Returns
        -------
        Union[int, None]
            The concurrent area membership limit.

        """

        return super().get_area_concurrent_limit()

    def get_users_in_areas(self) -> Set[ClientManager.Client]:
        """
        Return all users in areas part of the nonstop debate, even those that are not players of
        the nonstop debate.

        Returns
        -------
        Set[ClientManager.Client]
            All users in areas part of the nonstop debate.

        """

        return super().get_users_in_areas()

    def get_nonleader_users_in_areas(self) -> Set[ClientManager.Client]:
        """
        Return all users in areas part of the nonstop debate, even those that are not players of
        the nonstop debate, such that they are not leaders of the nonstop debate.

        Returns
        -------
        Set[ClientManager.Client]
            All users in areas part of the nonstop debate that are not leaders of the nonstop debate.

        """

        return super().get_nonleader_users_in_areas()

    def get_nonplayer_users_in_areas(self) -> Set[ClientManager.Client]:
        """
        Return all users in areas part of the nonstop debate that are not players of the
        nonstop debate.

        Returns
        -------
        Set[ClientManager.Client]
            All users in areas part of the nonstop debate that are not players of the nonstop debate.

        """

        return super().get_nonplayer_users_in_areas()

    def get_trial(self) -> _Trial:
        """
        Return the trial of the nonstop debate.

        Returns
        -------
        _Trial
            Trial of the nonstop debate.

        """

        return super().get_trial()

    def get_autoadd_on_trial_player_add(self) -> bool:
        """
        Return whether the nonstop debate will attempt to add players to it if the parent trial
        added it as player.

        Returns
        -------
        bool.
            True if an attempt will be made automatically, False otherwise.
        """

        return super().get_autoadd_on_trial_player_add()

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

        super().unchecked_set_autoadd_on_trial_player_add(new_value)

    def is_unmanaged(self):
        """
        Return True if this nonstop debate is unmanaged, False otherwise.

        Returns
        -------
        bool
            True if unmanaged, False otherwise.

        """

        return super().is_unmanaged()

    def destroy(self):
        """
        Mark this nonstop debate as destroyed and notify its manager so that it is deleted.
        If the nonstop debate is already destroyed, this function does nothing.
        A nonstop debate marked for destruction will delete all of its timers, teams, remove all
        its players and unsubscribe it from updates of its former players.

        This method is reentrant (it will do nothing though).

        Returns
        -------
        None.

        """

        self.unchecked_destroy()
        self.manager._check_structure()
        self._check_structure()  # Manager will not check this otherwise.

    def _on_area_destroyed(self, area: AreaManager.Area):
        """
        Default callback for nonstop debate area signaling it was destroyed.

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

    def _on_trial_player_added(
        self,
        trial: _Trial,
        player: ClientManager.Client = None
    ):
        """
        Default callback when the parent trial adds a player.
        If a player was added to the trial of the nonstop debate, attempt to add the player to the
        nonstop debate as well. If unsuccessful, do nothing.
        Do note the player may already be part of the nonstop debate by this point: if another
        thread was also listening to this callback and acted upon it before the current thread by
        adding the player to the nonstop debate.

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

        super()._on_trial_player_added(trial, player=player)


class _NonStopDebate(_NonStopDebateTrivialInherited):
    """
    A nonstop debate is a trial game based in its Danganronpa counterpart.

    Attributes
    ----------
    server : TsuserverDR
        Server the nonstop debate belongs to.
    manager : HubbedGameManager
        Manager for this nonstop debate.
    hub: _Hub
        Hub for this hubbed game.
    listener : Listener
        Standard listener of the nonstop debate.

    Callback Methods
    ----------------
    _on_client_inbound_ms_check
        Method to perform once a player of the nonstop debate wants to send an IC message.
    _on_client_inbound_ms_final
        Method to perform once a player of the nonstop debate sends an IC message.
    _on_client_change_character
        Method to perform once a player of the nonstop debate has changed character.
    _on_client_destroyed
        Method to perform once a player of the nonstop debate is destroyed.
    _on_area_client_left_final
        Method to perform once a client left an area of the nonstop debate.
    _on_area_client_entered_final
        Method to perform once a client entered an area of the nonstop debate.
    _on_area_destroyed
        Method to perform once an area of the nonstop debate is marked for destruction.

    """

    # (Private) Attributes
    # --------------------
    # _mode : NSDMode
    #   Current mode of the NSD.
    # _messages : List of Dict of str to Any
    #   Recorded messages to loop
    #
    # Invariants
    # ----------
    # 1. The invariants from the parent class TrialMinigame are satisfied.

    def __init__(
        self,
        server: TsuserverDR,
        manager: HubbedGameManager,
        nsd_id: str,
        player_limit: Union[int, None] = None,
        player_concurrent_limit: Union[int, None] = None,
        require_invitations: bool = False,
        require_players: bool = True,
        require_leaders: bool = True,
        require_participant_character: bool = False,
        team_limit: Union[int, None] = None,
        timer_limit: Union[int, None] = None,
        area_concurrent_limit: Union[int, None] = None,
        autoadd_on_client_enter: bool = False,
        require_areas: bool = True,
        hub: _Hub = None,
        trial: _Trial = None,
        autoadd_on_trial_player_add: bool = False,
        # new
        timer_start_value: int = 300,
    ):
        """
        Create a new nonstop debate (NSD) game. An NSD should not be fully initialized anywhere
        else other than some manager code, as otherwise the manager will not recognize the NSD.

        Parameters
        ----------
        server : TsuserverDR
            Server the NSD belongs to.
        manager : HubbedGameManager
            Manager for this NSD.
        nsd_id : str
            Identifier of the NSD.
        player_limit : int or None, optional
            If an int, it is the maximum number of players the NSD supports. If None, it
            indicates the NSD has no player limit. Defaults to None.
        player_concurrent_limit : int or None, optional
            If an int, it is the maximum number of games managed by `manager` that any
            player of this NSD may belong to, including this NSD. If None, it indicates
            that this NSD does not care about how many other games managed by `manager` each
            of its players belongs to. Defaults to None.
        require_invitation : bool, optional
            If True, players can only be added to the NSD if they were previously invited. If
            False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the NSD has no players left, the NSD will
            automatically be deleted. If False, no such automatic deletion will happen.
            Defaults to True.
        require_leaders : bool, optional
            If True, if at any point the NSD has no leaders left, the NSD will choose a
            leader among any remaining players left; if no players are left, the next player
            added will be made leader. If False, no such automatic assignment will happen.
            Defaults to True.
        require_participant_character : bool, optional
            If False, players without a participant character will not be allowed to join the
            NSD, and players that switch to something other than a participant character
            will be automatically removed from the NSD. If False, no such checks are
            made. A player without a participant character is considered one where
            player.has_participant_character() returns False. Defaults to False.
        team_limit : int or None, optional
            If an int, it is the maximum number of teams the NSD supports. If None, it
            indicates the NSD has no team limit. Defaults to None.
        timer_limit : int or None, optional
            If an int, it is the maximum number of timers the NSD supports. If None, it
            indicates the NSD has no timer limit. Defaults to None.
        areas : set of AreaManager.Area, optional
            Areas the NSD starts with. Defaults to None.
        area_concurrent_limit : int or None, optional
            If an int, it is the maximum number of trials managed by `manager` that any
            area of this trial may belong to, including this trial. If None, it indicates
            that this nonstop debate does not care about how many other trials managed by
            `manager` each of its areas belongs to. Defaults to 1 (an area may not be a part of
            another trial managed by `manager` while being an area of this trial).
        autoadd_on_client_enter : bool, optional
            If True, nonplayer users that enter an area part of the nonstop debate will be
            automatically added if permitted by the conditions of the nonstop debate. If False, no
            such adding will take place. Defaults to False.
        require_areas : bool, optional
            If True, if at any point the nonstop debate has no areas left, the game with areas
            will automatically be deleted. If False, no such automatic deletion will happen.
            Defaults to True.
        hub : _Hub, optional
            Hub the nonstop debate belongs to. Defaults to None.
        trial : _Trial, optional
            Trial the nonstop debate is a part of. Defaults to None.
        autoadd_on_trial_player_add : bool, optional
            If True, players that are added to the trial will be automatically added if permitted
            by the conditions of the nonstop debate. If False, no such adding will take place.
            Defaults to False.
        timer_start_value : float, optional
            In seconds, the length of time the main timer of this nonstop debate will have at the
            start. It must be a positive number. Defaults to 300 (5 minutes).

        """

        self._mode = NSDMode.PRERECORDING
        self._preintermission_mode = NSDMode.PRERECORDING
        self._messages = list()
        self._message_index = -1

        self._timer = None
        self._message_timer = None
        self._player_refresh_timer = None
        self._mode_switch_lockout_timer = None

        self._timer_start_value = timer_start_value
        self._message_refresh_rate = 7
        self._mode_switch_timeout_length = 5
        self._client_timer_id = 0
        self._breaker = None
        self._timers_are_setup = False
        self._mode_switch_lockout_lock = True
        self._intermission_messages = 0

        super().__init__(
            server,
            manager,
            nsd_id,
            player_limit=player_limit,
            player_concurrent_limit=player_concurrent_limit,
            require_invitations=require_invitations,
            require_players=require_players,
            require_leaders=require_leaders,
            require_participant_character=require_participant_character,
            team_limit=team_limit,
            timer_limit=timer_limit,
            area_concurrent_limit=area_concurrent_limit,
            autoadd_on_client_enter=autoadd_on_client_enter,
            require_areas=require_areas,
            hub=hub,
            trial=trial,
            autoadd_on_trial_player_add=autoadd_on_trial_player_add,
        )

    def get_type_name(self) -> str:
        """
        Return the type name of the nonstop debate. Names are fully lowercase.
        Implementations of the class should replace this with a human readable name of the nonstop
        debate.

        Returns
        -------
        str
            Type name of the nonstop debate.

        """

        return "nonstop debate"

    def unchecked_add_player(self, user: ClientManager.Client):
        """
        Make a user a player of the nonstop debate. By default this player will not be a leader,
        unless the nonstop debate has no leaders and it requires a leader.
        It will also subscribe the nonstop debate ot the player so it can listen to its updates.

        It will also send a gamemode change order to the new player that aligns with the current
        mode of the NSD.

        Parameters
        ----------
        user : ClientManager.Client
            User to add to the nonstop debate. They must be in an area part of the nonstop debate.

        Raises
        ------
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.UserNotPlayerError
            If the user is not a player of the trial.
        NonStopDebateError.UserNotInAreaError
            If the user is not in an area part of the nonstop debate.
        NonStopDebateError.UserHasNoCharacterError
            If the user has no character but the nonstop debate requires that all players have
            characters.
        NonStopDebateError.UserNotInvitedError
            If the nonstop debate requires players be invited to be added and the user is not
            invited.
        NonStopDebateError.UserAlreadyPlayerError
            If the user to add is already a user of the nonstop debate.
        NonStopDebateError.UserHitGameConcurrentLimitError
            If the player has reached the concurrent player membership of any of the nonstop debates
            managed by the manager of this nonstop debate, or by virtue of joining this
            nonstop debate they would violate this nonstop debate's concurrent player membership
            limit.
        NonStopDebateError.GameIsFullError
            If the nonstop debate reached its player limit.

        """

        try:
            super().unchecked_add_player(user)
        except TrialMinigameError.GameIsUnmanagedError:
            raise NonStopDebateError.GameIsUnmanagedError
        except TrialMinigameError.UserNotPlayerError:
            raise NonStopDebateError.UserNotPlayerError
        except TrialMinigameError.UserNotInAreaError:
            raise NonStopDebateError.UserNotInAreaError
        except TrialMinigameError.UserHasNoCharacterError:
            raise NonStopDebateError.UserHasNoCharacterError
        except TrialMinigameError.UserNotInvitedError:
            raise NonStopDebateError.UserNotInvitedError
        except TrialMinigameError.UserAlreadyPlayerError:
            raise NonStopDebateError.UserAlreadyPlayerError
        except TrialMinigameError.UserHitGameConcurrentLimitError:
            raise NonStopDebateError.UserHitGameConcurrentLimitError
        except TrialMinigameError.GameIsFullError:
            raise NonStopDebateError.GameIsFullError

        self.introduce_user(user)

    def unchecked_remove_player(self, user: ClientManager.Client):
        """
        Make a user be no longer a player of this nonstop debate. If they were part of a team
        managed by this nonstop debate, they will also be removed from said team. It will also
        unsubscribe the nonstop debate  from the player so it will no longer listen to its updates.
        It will also send an order to the player to go back to its default theme gamemode.

        If the nonstop debate required that there it always had players and by calling this method
        the nonstop debate had no more players, the nonstop debate will automatically be scheduled
        for deletion.

        Parameters
        ----------
        user : ClientManager.Client
            User to remove.

        Raises
        ------
        NonStopDebateError.GameIsUnmanagedError
            If the nonstop debate was scheduled for deletion and thus does not accept any mutator
            public method calls.
        NonStopDebateError.UserNotPlayerError
            If the user to remove is already not a player of this nonstop debate.

        """

        try:
            super().unchecked_remove_player(user)
        except TrialMinigameError.GameIsUnmanagedError:
            raise NonStopDebateError.GameIsUnmanagedError
        except TrialMinigameError.UserNotPlayerError:
            raise NonStopDebateError.UserNotPlayerError

        self.dismiss_user(user)

    def introduce_user(self, user: ClientManager.Client):
        """
        Broadcast information relevant for a user entering an area of the NSD, namely current
        gamemode and status of timers.
        Note the user needs not be in the same area as the NSD, nor be a player of the NSD.

        Parameters
        ----------
        user : ClientManager.Client
            User to introduce.

        """

        if self._mode in [NSDMode.LOOPING, NSDMode.RECORDING, NSDMode.PRERECORDING]:
            user.send_gamemode(name='nsd')
        elif self._mode in [NSDMode.INTERMISSION, NSDMode.INTERMISSION_POSTBREAK,
                            NSDMode.INTERMISSION_TIMERANOUT]:
            user.send_gamemode(name='trial')
        else:
            raise RuntimeError(f'Unrecognized mode {self._mode}')

        # Nonstop debate splash
        user.send_splash(name='testimony4')

        # Timer stuff
        if self._timer and self._timer.started() and not self._timer.paused():
            user.send_timer_resume(timer_id=self._client_timer_id)
        else:
            user.send_timer_pause(timer_id=self._client_timer_id)
        self._send_current_timers(user)

    def dismiss_user(self, user: ClientManager.Client):
        """
        Broadcast information relevant for a user that has left the NSD, namely modify the
        gamemode and timers as follows:
        * If the user is still part of an area of the NSD, no action is taken.
        * Otherwise, if they are still part of an area of the NSD's trial, their gamemode is set
        to trial and the timers are cleared.
        * Otherwise, the gamemode is cleared and so are the timers.
        Note the user needs not be in the same area as the NSD, nor be a player of the NSD.
        If the NSD has never had any players, this method does nothing.

        Parameters
        ----------
        user : ClientManager.Client
            User to dismiss.

        """

        if not self.has_ever_had_players():
            return

        # We use .new_area rather than .area as this function may have been called as a result
        # of the user moving, in which case .area still points to the user's old area.

        # If the user is still part of an area of the NSD, do nothing
        # Otherwise, ...
        if user.new_area not in self.get_areas():
            # If the user is still part of an area part of the NSD's trial, make them
            # switch to the trial gamemode
            if user.new_area in self._trial.get_areas():
                user.send_gamemode(name='trial')
            # Otherwise, fully clear out gamemode
            else:
                user.send_gamemode(name='')

        # Update the timers only if the player is not in an area part of the NSD
        if user.new_area not in self.get_areas():
            user.send_timer_pause(timer_id=self._client_timer_id)
            user.send_timer_set_time(timer_id=self._client_timer_id, new_time=0)
            user.send_timer_set_step_length(timer_id=self._client_timer_id,
                                            new_step_length=0)
            user.send_timer_set_firing_interval(timer_id=self._client_timer_id,
                                                new_firing_interval=0)

    def get_type(self) -> TRIALMINIGAMES:
        """
        Return the type of the minigame (NonStopDebate).

        Returns
        -------
        TRIALMINIGAMES
            Type of minigame.

        """

        return TRIALMINIGAMES.NONSTOP_DEBATE

    def get_mode(self) -> NSDMode:
        """
        Return the current mode of the nonstop debate.

        Returns
        -------
        NSDMode
            Current mode.

        """

        return self._mode

    def set_prerecording(self):
        """
        Set the NSD to be in prerecording mode (equivalent to recording but before the first
        message is sent, so timer is not unpaused).

        Raises
        ------
        NonStopDebateError.NSDAlreadyInModeError
            If the nonstop debate is already in recording mode.

        """

        if self._mode == NSDMode.PRERECORDING:
            raise NonStopDebateError.NSDAlreadyInModeError('Nonstop debate is already in this '
                                                           'mode.')
        if self._mode not in [NSDMode.INTERMISSION, NSDMode.INTERMISSION_POSTBREAK,
                              NSDMode.INTERMISSION_TIMERANOUT]:
            raise NonStopDebateError.NSDNotInModeError('You may not set your nonstop debate to be '
                                                       'prerecording at this moment.')

        self._mode = NSDMode.PRERECORDING
        self._preintermission_mode = NSDMode.PRERECORDING
        self._mode_switch_lockout_lock = True
        self._mode_switch_lockout_timer.set_time(0)
        try:
            self._mode_switch_lockout_timer.unpause()
        except TimerError.NotPausedTimerError:
            pass

        for user in self.get_users_in_areas():
            user.send_gamemode(name='nsd')
            self._send_current_timers(user)

    def _set_recording(self):
        """
        Set the NSD to be in recording mode.
        """

        if self._mode != NSDMode.PRERECORDING:
            raise RuntimeError(f'Should not have made it here for nsd {self}: {self._mode}')

        self._mode = NSDMode.RECORDING
        self._preintermission_mode = NSDMode.RECORDING
        if self._timer and not self._timer.terminated():
            self._timer.unpause()
        self._player_refresh_timer.unpause()

        for user in self.get_users_in_areas():
            user.send_gamemode(name='nsd')
            user.send_timer_resume(timer_id=self._client_timer_id)
            self._send_current_timers(user)

        for leader in self.get_leaders():
            leader.send_ooc('(X) Messages for your nonstop debate are now being recorded. Once you '
                            'are satisfied with the debate messages, you may pause the debate with '
                            '/nsd_pause and then loop the debate with /nsd_loop.')

    def set_intermission(self, blankpost: bool = True):
        """
        Set the NSD to be in intermission mode. This will pause the NSD timer, terminate the
        current message timer and order all players to pause their timers and switch to a
        trial gamemode.

        Parameters
        ----------
        blankpost : bool, optional
            If True, it will send a blank system IC message to every player so that they clear
            their screens.

        Raises
        ------
        NonStopDebateError.NSDAlreadyInModeError
            If the nonstop debate is already in intermission mode.
        NonStopDebateError.NSDNotInModeError
            If the nonstop debate is in prerecording mode.

        """

        if self._mode in [NSDMode.INTERMISSION, NSDMode.INTERMISSION_POSTBREAK,
                          NSDMode.INTERMISSION_TIMERANOUT]:
            raise NonStopDebateError.NSDAlreadyInModeError('Nonstop debate is already in this '
                                                           'mode.')
        if self._mode == NSDMode.PRERECORDING:
            raise NonStopDebateError.NSDNotInModeError

        self._mode = NSDMode.INTERMISSION

        if self._timer and not self._timer.paused() and not self._timer.terminated():
            self._timer.pause()
        if self._message_timer and not self._message_timer.paused():
            self._message_timer.pause()
        if self._player_refresh_timer and not self._player_refresh_timer.paused():
            self._player_refresh_timer.pause()

        self._mode_switch_lockout_lock = True
        self._mode_switch_lockout_timer.set_time(0)
        try:
            self._mode_switch_lockout_timer.unpause()
        except TimerError.NotPausedTimerError:
            pass

        for user in self.get_users_in_areas():
            user.send_timer_pause(timer_id=self._client_timer_id)
            self._send_current_timers(user)
            if blankpost:
                user.send_ic_blankpost()  # Blankpost

        def _variant():
            for user in self.get_users_in_areas():
                user.send_gamemode(name='trial')

        # Delay gamemode switch order by just a bit. This prevents a concurrency issue where
        # clients are unable to start playing the shout animation in time for them to be able
        # to properly delay it.
        variant_timer = self.new_timer(start_value=0, max_value=0.1)
        variant_timer._on_max_end = _variant
        variant_timer.start()

        self._intermission_messages = 0

    def _set_intermission_postbreak(self, breaker: ClientManager.Client, blankpost: bool = True):
        self.set_intermission(blankpost=blankpost)
        self._mode = NSDMode.INTERMISSION_POSTBREAK
        self._breaker = breaker

    def _set_intermission_timeranout(self, blankpost: bool = True):
        self.set_intermission(blankpost=blankpost)
        self._mode = NSDMode.INTERMISSION_TIMERANOUT

        for nonplayer in self.get_nonplayer_users_in_areas():
            nonplayer.send_ooc('Time ran out for the debate you are watching!')
        for player in self.get_players():
            player.send_ooc('Time ran out for your debate!')
        for leader in self.get_leaders():
            leader.send_ooc('(X) Type /nsd_resume to resume the debate where it was nonetheless, '
                            'or /nsd_end to end the debate.')

    def set_looping(self):
        """
        Set the NSD to be in looping mode. This will unpause the NSD timer, order all players
        to switch to an NSD gamemode and resume their timer, display the first message in the loop
        and set up a message timer so the messages transition automatically.

        Raises
        ------
        NonStopDebateError.NSDAlreadyInModeError
            If the nonstop debate is already in looping mode.
        NonStopDebateError.NSDNotInModeError
            If the nonstop debate is not in regular or post-break intermission mode.
        NonStopDebateError.NSDNoMessagesError
            If there are no recorded messages to loop.

        """

        if self._mode == NSDMode.LOOPING:
            raise NonStopDebateError.NSDAlreadyInModeError('Nonstop debate is already in this '
                                                           'mode.')
        if self._mode not in [NSDMode.INTERMISSION, NSDMode.INTERMISSION_POSTBREAK,
                              NSDMode.INTERMISSION_TIMERANOUT]:
            raise NonStopDebateError.NSDNotInModeError
        if not self._messages:
            raise NonStopDebateError.NSDNoMessagesError('There are no messages to loop.')

        self._mode = NSDMode.LOOPING
        self._preintermission_mode = NSDMode.LOOPING
        self._message_index = -1

        if self._timer and not self._timer.terminated():
            self._timer.unpause()

        for user in self.get_users_in_areas():
            user.send_gamemode(name='nsd')
            user.send_timer_resume(timer_id=self._client_timer_id)
        self._display_next_message()

        # Only unpause now. By the earlier check there is a guarantee that a message will be sent,
        # so display_next_message will not immediately set intermission.
        # The reason we unpause now is to reduce offsync with clients who do not get a chance to
        # run their timer code for a bit due to blocking.

        self._player_refresh_timer.unpause()
        self._message_timer.set_time(0)  # We also reset this just in case it was interrupted before
        self._message_timer.unpause()

    def resume(self) -> NSDMode:
        """
        Put the NSD in the mode it was before it entered intermission and return such mode.

        Raises
        ------
        NonStopDebateError.NSDNotInModeError
            If the NSD is not in intermission.

        Returns
        -------
        NSDMode
            Mode.

        """

        if self._mode not in [NSDMode.INTERMISSION, NSDMode.INTERMISSION_POSTBREAK,
                              NSDMode.INTERMISSION_TIMERANOUT]:
            raise NonStopDebateError.NSDNotInModeError
        if self._preintermission_mode in [NSDMode.PRERECORDING, NSDMode.RECORDING]:
            self.set_prerecording()
            return NSDMode.PRERECORDING
        if self._preintermission_mode == NSDMode.LOOPING:
            self.set_looping()
            return NSDMode.LOOPING
        raise RuntimeError(f'Should not have made it here for NSD {self}: '
                           f'{self._preintermission_mode}')

    def accept_break(self) -> bool:
        """
        Accepts a break and increases the breaker's influence by 0.5, provided they are still a
        player of the NSD and connected to the server. Regardless, this also destroys the nonstop
        debate.

        Raises
        ------
        NonStopDebateError.NSDNotInModeError
            If the nonstop debate is not in postbreak intermission mode.

        Returns
        -------
        bool
            True if the breaker was a player of the NSD and is connected to the server, False
            otherwise.

        """

        if self._mode != NSDMode.INTERMISSION_POSTBREAK:
            raise NonStopDebateError.NSDNotInModeError

        is_player = self.server.is_client(self._breaker) and self.is_player(self._breaker)
        if is_player:
            self._breaker.send_ooc('Your break was accepted and you recovered 0.5 influence.')
            self.get_trial().change_influence_by(self._breaker, 0.5)

        self.destroy()
        return is_player

    def reject_break(self) -> bool:
        """
        Rejects a break, and decreases the breaker's influence by 1, provided they are still a
        player of the NSD and connected to the server. This puts the debate in standard
        intermission mode.

        Raises
        ------
        NonStopDebateError.NSDNotInModeError
            If the nonstop debate is not in postbreak intermission mode.

        Returns
        -------
        bool
            True if the breaker was a player of the NSD and is connected to the server, False
            otherwise.

        """

        if self._mode != NSDMode.INTERMISSION_POSTBREAK:
            raise NonStopDebateError.NSDNotInModeError

        is_player = self.server.is_client(self._breaker) and self.is_player(self._breaker)
        if is_player:
            self._breaker.send_ooc('Your break was rejected and you lost 1 influence.')
            self.get_trial().change_influence_by(self._breaker, -1)

        self._mode = NSDMode.INTERMISSION
        self._breaker = None

        return is_player

    def unchecked_destroy(self):
        """
        Mark this nonstop debate as destroyed and notify its manager so that it is deleted.
        If the nonstop debate is already destroyed, this function does nothing.

        This method is reentrant (it will do nothing though).

        This method does not assert structural integrity.

        Returns
        -------
        None.

        """

        # Get backup of areas
        areas = self.get_areas()

        # Then carry on
        super().unchecked_destroy()

        # Force every user in the former areas of the trial to be dismissed
        for area in areas:
            for user in area.clients:
                self.dismiss_user(user)

    def setup_timers(self):
        """
        Setup the timers for the nonstop debate. This function can only be called once.

        Raises
        ------
        NonStopDebateError.TimersAlreadySetupError
            If the nonstop debate has already had its timers setup.

        Returns
        -------
        None.

        """

        if self._timers_are_setup:
            raise NonStopDebateError.TimersAlreadySetupError
        self._timers_are_setup = True

        PLAYER_REFRESH_RATE = 5
        self._player_refresh_timer = self.new_timer(start_value=0, max_value=PLAYER_REFRESH_RATE,
                                                    auto_restart=True)

        def _refresh():
            # print(f'NSD refreshed the timer for everyone at {time.time()}.')
            for user in self.get_users_in_areas():
                self._send_current_timers(user)

        self._player_refresh_timer._on_max_end = _refresh

        self._message_timer = self.new_timer(start_value=0, max_value=self._message_refresh_rate,
                                             auto_restart=True)
        self._message_timer._on_max_end = self._display_next_message

        def _mode_switch_lockout_unlock():
            self._mode_switch_lockout_lock = False
            self._mode_switch_lockout_timer.pause()

        self._mode_switch_lockout_timer = self.new_timer(start_value=0,
                                                         max_value=self._mode_switch_timeout_length,
                                                         auto_restart=True)
        self._mode_switch_lockout_timer._on_max_end = _mode_switch_lockout_unlock
        self._mode_switch_lockout_timer.unpause()

        if self._timer_start_value > 0:
            self._timer = self.new_timer(start_value=self._timer_start_value,
                                         tick_rate=-1, min_value=0)
            self._timer._on_min_end = functools.partial(
                self._set_intermission_timeranout, blankpost=True)

    def _send_current_timers(self, player: ClientManager.Client):
        if not self._timer:
            player.send_timer_set_time(timer_id=self._client_timer_id, new_time=0)
            player.send_timer_set_step_length(timer_id=self._client_timer_id,
                                              new_step_length=0)
            player.send_timer_set_firing_interval(timer_id=self._client_timer_id,
                                                  new_firing_interval=0)
        else:
            player.send_timer_set_time(timer_id=self._client_timer_id,
                                       new_time=round(self._timer.get()*1000))
            player.send_timer_set_step_length(timer_id=self._client_timer_id,
                                              new_step_length=round(-0.016*1000))
            player.send_timer_set_firing_interval(timer_id=self._client_timer_id,
                                                  new_firing_interval=round(0.016*1000))

    def _on_client_inbound_ms_check(
        self,
        player: ClientManager.Client,
        contents: Dict[str, Any] = None
    ):
        """
        Check if any of the following situations occur: They want to send a message...
        * Within 5 seconds of the mode being set to recording or intermission and not leader.
        * With some types of bullets ('MC', 'CUT') at any point.
        * With a bullet before any messages were recorded.
        * With a bullet during intermission mode.
        * Without a bullet during looping mode.

        If none of the above is true, allow the IC message as is.

        Parameters
        ----------
        player : ClientManager.Client
            Player that wants to send the IC message.
        contents : dict of str to Any
            Arguments of the IC message as indicated in AOProtocol.

        Raises
        ------
        ClientError
            If any of the above disqualifying situations is true.

        Returns
        -------
        None.

        """

        # Too soon
        if self._mode_switch_lockout_lock and not self.is_leader(player):
            raise ClientError('You may not send a message just after the current mode started.')
        # Trying to do an MC or CUT.
        if contents['button'] not in {0, 1, 2, 3, 5, 7, 8}:
            raise ClientError('You may not perform that action during a nonstop debate.')
        # Before a message was even sent
        if contents['button'] > 0 and self._message_index == -1:
            raise ClientError('You may not use a bullet now.')
        # Trying to talk during looping mode
        if contents['button'] == 0 and self._mode == NSDMode.LOOPING:
            raise ClientError('You may not speak now except if using a bullet.')
        # For perjury
        if contents['button'] == 8:
            def func(c): return 8 if c in {player}.union(self.get_leaders()) else 7
            contents['PER_CLIENT_button'] = func

    def _on_client_inbound_ms_final(
        self,
        player: ClientManager.Client,
        contents: Dict[str, Any] = None
    ):
        """
        Add message of player to record of messages.

        Parameters
        ----------
        player : ClientManager.Client
            Player that signaled it has sent an IC message.
        contents : dict of str to Any
            Arguments of the IC message as indicated in AOProtocol.

        Returns
        -------
        None.

        """

        if self._mode == NSDMode.PRERECORDING:
            self._set_recording()

        # Not an elif!
        if self._mode == NSDMode.RECORDING:
            # Check if player bulleted during recording mode, and whether it makes sense to do that
            if contents['button'] > 0:
                self._break_loop(player, contents)
            else:
                self._add_message(player, contents=contents)
        elif self._mode in [NSDMode.INTERMISSION, NSDMode.INTERMISSION_POSTBREAK,
                            NSDMode.INTERMISSION_TIMERANOUT]:
            # Keep track of how many messages were sent during intermission. Every 5 messages,
            # prompt leaders to end debate
            self._intermission_messages += 1
            if self._intermission_messages % 20 == 0 or contents['button'] > 0:
                if self._mode == NSDMode.INTERMISSION_POSTBREAK:
                    msg = ('(X) Your nonstop debate is still in intermission mode after a break. '
                           "Type /nsd_accept to accept the break and end the debate, "
                           "/nsd_reject to reject the break and penalize the breaker, "
                           "/nsd_resume to resume the debate where it was, or "
                           "/nsd_end to end the debate.")
                elif self._mode == NSDMode.INTERMISSION_TIMERANOUT:
                    msg = ('(X) Your nonstop debate is still in intermission mode after time ran '
                           'out. Type /nsd_resume to resume the debate where it was nonetheless, '
                           'or /nsd_end to end the debate.')
                else:
                    msg = ('(X) Your nonstop debate is still in intermission mode. '
                           'Type /nsd_resume to resume the debate where it was nonetheless, '
                           'or /nsd_end to end the debate.')
                for leader in self.get_leaders():
                    leader.send_ooc(msg)
                self._intermission_messages = 0
        elif self._mode == NSDMode.LOOPING:
            # NSD already verified the IC message should go through
            # This is a break!
            self._break_loop(player, contents)
        else:
            raise RuntimeError(f'Unrecognized mode {self._mode}')
        self.manager._check_structure()

    def _on_client_change_character(
        self,
        player: ClientManager.Client,
        old_char_id: int = -1,
        old_char_name: str = '',
        new_char_id: int = -1,
        new_char_name: str = '',
    ):
        """
        It checks if the player is now no longer having a participant character. If that is
        the case and the NSD requires all players have participant characters, the player is
        automatically removed.

        Note that it may not necessarily be the case that the following hold:
        1. `old_char_name == player.hub.character_manager.get_character_name(old_char_id)`.
        2. `new_char_name == player.hub.character_manager.get_character_name(new_char_id)`.
        This can occur for example if the character list changes, which prompts the player to
        change character.

        Parameters
        ----------
        player : ClientManager.Client
            Player that signaled it has changed character.
        old_char_id : int, optional
            Previous character ID. The default is -1.
        old_char_name : str, optional
            Previous character name. The default is the empty string.
        new_char_id : int, optional
            New character ID. The default is -1.
        new_char_name : int, optional
            New character name. The default is the empty string.

        Returns
        -------
        None.

        """

        if self.requires_participant_characters() and not player.has_participant_character():
            player.send_ooc('You were removed from your NSD as it required its players to have '
                            'participant characters.')
            player.send_ooc_others(f'(X) Player {player.id} changed character from {old_char_name} '
                                   f'to a non-participant character and was thus removed from your '
                                   f'NSD.',
                                   pred=lambda c: c in self.get_leaders())

            nonplayers = self.get_nonplayer_users_in_areas()
            nid = self.get_id()

            try:
                self.remove_player(player)
            except NonStopDebateError:
                # NonStopDebateError may be raised because the parent trial may have already
                # removed the player, and thus called remove_player.
                # We use a general NonStopDebateError as it could be
                # the case the NSD is scheduled for deletion or the user is already not a player.
                pass

            if self.is_unmanaged():
                player.send_ooc(f'Your nonstop debate `{nid}` was automatically '
                                f'ended as it lost all its players.')
                player.send_ooc_others(f'(X) Nonstop debate `{nid}` was automatically '
                                       f'ended as it lost all its players.',
                                       is_zstaff_flex=True, not_to=nonplayers)
                player.send_ooc_others('The nonstop debate you were watching was automatically '
                                       'ended as it lost all its players.',
                                       is_zstaff_flex=False, part_of=nonplayers)
        else:
            player.send_ooc_others(f'(X) Player {player.id} changed character from {old_char_name} '
                                   f'to {player.get_char_name()} in your NSD.',
                                   pred=lambda c: c in self.get_leaders())

        self.manager._check_structure()

    def _on_client_destroyed(self, player: ClientManager.Client):
        """
        Remove the player from the NSD. If the NSD is already unmanaged or
        the player is not in the nonstop debate, this callback does nothing.

        Parameters
        ----------
        player : ClientManager.Client
            Player that signaled it was destroyed.

        Returns
        -------
        None.

        """

        if self.is_unmanaged():
            return
        if player not in self.get_players():
            return

        player.send_ooc_others(f'(X) Player {player.displayname} of your nonstop debate '
                               f'disconnected ({player.area.id}).',
                               pred=lambda c: c in self.get_leaders())

        nonplayers = self.get_nonplayer_users_in_areas()
        nid = self.get_id()

        try:
            self.remove_player(player)
        except NonStopDebateError:
            # NonStopDebateError may be raised because the parent trial may have already
            # removed the player, and thus called remove_player.
            # We use a general NonStopDebateError as it could be
            # the case the NSD is scheduled for deletion or the user is already not a player.
            pass

        if self.is_unmanaged():
            # We check again, because now the NSD may be unmanaged
            player.send_ooc_others(f'(X) Nonstop debate `{nid}` was automatically '
                                   f'ended as it lost all its players.',
                                   is_zstaff_flex=True, not_to=nonplayers)
            player.send_ooc_others('The nonstop debate you were watching was automatically ended '
                                   'as it lost all its players.',
                                   is_zstaff_flex=False, part_of=nonplayers)

        self.manager._check_structure()

    def _on_area_client_left_final(
        self,
        area: AreaManager.Area,
        client: ClientManager.Client = None,
        old_displayname: str = None,
        ignore_bleeding: bool = False,
        ignore_autopass: bool = False
    ):
        """
        If a player left to an area not part of the NSD, remove the player and warn them and
        the leaders of the NSD.

        If a non-plyer left to an area not part of the NSD, warn them and the leaders of the
        NSD.

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

        if client.area in self.get_areas():
            return

        if client in self.get_players():
            client.send_ooc(f'You have left to an area not part of NSD '
                            f'`{self.get_id()}` and thus were automatically removed from the '
                            f'NSD.')
            client.send_ooc_others(f'(X) Player {old_displayname} [{client.id}] has left to '
                                   f'an area not part of your NSD and thus was '
                                   f'automatically removed from it ({area.id}->{client.area.id}).',
                                   pred=lambda c: c in self.get_leaders(), in_hub=area.hub)

            nonplayers = self.get_nonplayer_users_in_areas()
            nid = self.get_id()

            self.remove_player(client)

            if self.is_unmanaged():
                client.send_ooc(f'Your nonstop debate `{nid}` was automatically '
                                f'ended as it lost all its players.')
                client.send_ooc_others(f'(X) Nonstop debate `{nid}` was automatically '
                                       f'ended as it lost all its players.',
                                       is_zstaff_flex=True, not_to=nonplayers, in_hub=area.hub)
                client.send_ooc_others('The nonstop debate you were watching was automatically '
                                       'ended as it lost all its players.',
                                       is_zstaff_flex=False, part_of=nonplayers, in_hub=area.hub)

        else:
            client.send_ooc(f'You have left to an area not part of NSD '
                            f'`{self.get_id()}`.')
            client.send_ooc_others(f'(X) Player {old_displayname} [{client.id}] has left to an '
                                   f'area not part of your NSD '
                                   f'({area.id}->{client.area.id}).',
                                   pred=lambda c: c in self.get_leaders(), in_hub=area.hub)
            self.dismiss_user(client)

        self.manager._check_structure()

    def _on_area_client_entered_final(
        self,
        area: AreaManager.Area,
        client: ClientManager.Client = None,
        old_area: Union[AreaManager.Area, None] = None,
        old_displayname: str = None,
        ignore_bleeding: bool = False,
        ignore_autopass: bool = False
    ):
        """
        If a non-player entered, warn them and the leaders of the NSD.

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

        if old_area in self.get_areas():
            return

        if client not in self.get_players():
            old_area_id = str(old_area.id) if old_area else "SERVER_SELECT"
            client.send_ooc(f'You have entered an area part of NSD `{self.get_id()}`.')
            client.send_ooc_others(f'(X) Non-player {client.displayname} [{client.id}] has entered '
                                   f'an area part of your NSD '
                                   f'({old_area_id}->{area.id}).',
                                   pred=lambda c: c in self.get_leaders())
            if not self.get_trial().is_player(client):
                if client.is_staff():
                    client.send_ooc('You are not a player of the NSD of this trial. Join the trial '
                                    'first before trying to join the NSD.')
                client.send_ooc_others(f'(X) {client.displayname} is not a player of your trial. '
                                       f'Add them to your trial first before attempting to add '
                                       f'them to your NSD.',
                                       pred=lambda c: c in self.get_leaders())
            elif not self.requires_participant_characters() or client.has_participant_character():
                if client.is_staff():
                    client.send_ooc(f'Join this NSD with /nsd_join {self.get_id()}')
                client.send_ooc_others(f'(X) Add {client.displayname} to your NSD with '
                                       f'/nsd_add {client.id}',
                                       pred=lambda c: c in self.get_leaders())
            else:
                if client.is_staff():
                    client.send_ooc(f'This NSD requires you have a participant character to join. '
                                    f'Join this NSD with /nsd_join {self.get_id()} after choosing '
                                    f'a participant character.')
                client.send_ooc_others(f'(X) This NSD requires players have a participant '
                                       f'character to join. '
                                       f'Add {client.displayname} to your NSD with '
                                       f'/nsd_add {client.id} after they choose a participant '
                                       f'character.',
                                       pred=lambda c: c in self.get_leaders())
            self.introduce_user(client)

        self.manager._check_structure()

    def _on_area_client_inbound_ms_check(
        self,
        area: AreaManager.Area,
        client: ClientManager.Client = None,
        contents: Dict[str, Any] = None
    ):
        """
        Check if any of the following situations occur:
        * If the user is not part of the nonstop debate.

        If none of the above is true, allow the IC message as is.

        Parameters
        ----------
        area : AreaManager.Area
            Area of the user that wants to send the IC message.
        client : ClientManager.Client
            Client that wants to send the IC message (possibly not a player of the nonstop debate).
        contents : dict of str to Any
            Arguments of the IC message as indicated in AOProtocol.

        Raises
        ------
        ClientError
            If any of the above disquaLifying situations is true.

        Returns
        -------
        None.

        """

        if not self.is_player(client):
            raise ClientError('You are not a player of this nonstop debate.')

    def _on_areas_loaded(self, area_manager: AreaManager):
        """
        Destroy the trial and warn players and nonplayers in areas.

        Parameters
        ----------
        area_manager : AreaManager
            AreaManager that signaled the area list load.

        Returns
        -------
        None.

        """

        for nonplayer in self.get_nonleader_users_in_areas():
            nonplayer.send_ooc('The nonstop debate you were watching was deleted due to an area '
                               'list load.')
        for player in self.get_players():
            player.send_ooc('Your nonstop debate was deleted due to an area list load.')

        self.destroy()

    def _add_message(self, player: ClientManager.Client, contents: Dict[str, Any] = None):
        """
        Add a message to the log of messages of the NSD. If the NSD timer is paused, it will also
        resume the timer.

        Parameters
        ----------
        player : ClientManager.Client
            Player who spoke.
        contents : dict of str to Any
            Arguments of the IC message as indicated in AOProtocol.

        Returns
        -------
        None.

        """

        self._messages.append([player, contents])
        self._message_index += 1
        if self._timer and self._timer.paused():
            self._timer.unpause()
            for user in self.get_users_in_areas():
                user.send_timer_resume(timer_id=self._client_timer_id)

    def _display_next_message(self):
        """
        If there are still messages pending in the next NSD loop, send the next one to every player.
        Otherwise, enter intermission mode.

        Returns
        -------
        None.

        """

        # -1 avoids fencepost error
        if self._message_index < len(self._messages)-1:
            self._message_index += 1
            sender, contents = self._messages[self._message_index]
            for user in self.get_users_in_areas():
                user.send_ic(params=contents, sender=sender)
            logger.log_server('[IC][{}][{}][NSD]{}'
                              .format(sender.area.id, sender.get_char_name(), contents['msg']),
                              sender)
        else:
            for user in self.get_nonplayer_users_in_areas():
                user.send_ooc('A loop of the nonstop debate you are watching has finished.')
            for user in self.get_players():
                user.send_ooc('A loop of your nonstop debate has finished.')
            for leader in self.get_leaders():
                leader.send_ooc('(X) Type /nsd_loop to loop the debate again, or /nsd_end to end '
                                'the debate.')
            self.set_intermission()

    def _break_loop(self, player: ClientManager.Client, contents: Dict[str, Any]):
        """
        Handle 'break' logic. It will send OOC messages to the breaker and the leaders of the NSD
        indicating of this event, and set the NSD mode to intermission with a 3 second delay.

        Parameters
        ----------
        player : ClientManager.Client
            Player who 'broke'.
        contents : dict of str to Any
            Arguments of the IC message as indicated in AOProtocol.

        Returns
        -------
        None.

        """

        bullet_actions = {
            1: 'consented with',
            2: 'countered',
            3: 'indicated they want to argue against',
            # 4: 'mc'd',
            5: 'indicated they got it after hearing',
            # 6: 'cut',
            7: 'countered',
            8: 'committed perjury by countering',
        }
        regular_bullet_actions = bullet_actions.copy()
        regular_bullet_actions[8] = 'countered'

        broken_player, broken_ic = self._messages[self._message_index]
        action = bullet_actions[contents['button']]
        regular_action = regular_bullet_actions[contents['button']]

        you_action = action.replace(' they ', ' you ')

        if broken_player == player:
            player.send_ooc(f"You {you_action} your own statement "
                            f"`{broken_ic['text']}` and halted the debate.")
        else:
            player.send_ooc(f"You {you_action} {broken_player.displayname}'s statement "
                            f"`{broken_ic['text']}` and halted the debate.")

        for user in self.get_users_in_areas():
            if user in self.get_leaders():
                if user != player:
                    # Do not send duplicate messages
                    if broken_player == user:
                        user.send_ooc(f"{player.displayname} {action} "
                                      f"your statement "
                                      f"`{broken_ic['text']}` and halted the debate.")
                    elif broken_player == player:
                        user.send_ooc(f"{player.displayname} {action} "
                                      f"their own statement "
                                      f"`{broken_ic['text']}` and halted the debate.")
                    else:
                        user.send_ooc(f"{player.displayname} {action} "
                                      f"{broken_player.displayname}'s statement "
                                      f"`{broken_ic['text']}` and halted the debate.")
                # But still send leader important information.
                user.send_ooc("(X) Type /nsd_accept to accept the break and end the debate, "
                              "/nsd_reject to reject the break and penalize the breaker, "
                              "/nsd_resume to resume the debate where it was, or "
                              "/nsd_end to end the debate.")

        for regular in self.get_nonleader_users_in_areas():
            if regular != player:
                if broken_player == regular:
                    regular.send_ooc(f"{player.displayname} {regular_action} "
                                     f"your statement "
                                     f"`{broken_ic['text']}` and halted the debate.")
                elif broken_player == player:
                    regular.send_ooc(f"{player.displayname} {regular_action} "
                                     f"their own statement "
                                     f"`{broken_ic['text']}` and halted the debate.")
                else:
                    regular.send_ooc(f"{player.displayname} {regular_action} "
                                     f"{broken_player.displayname}'s statement "
                                     f"`{broken_ic['text']}` and halted the debate.")

        self._set_intermission_postbreak(player, blankpost=False)

    def _check_structure(self):
        """
        Assert that all invariants specified in the class description are maintained.

        Raises
        ------
        AssertionError
            If any of the invariants are not maintained.

        """

        # 1.
        super()._check_structure()

    def __str__(self):
        """
        Return a string representation of this nonstop debate.

        Returns
        -------
        str
            Representation.

        """

        return (f"NonStopDebate::{self.get_id()}:{self.get_trial()}"
                f"{self.get_players()}:{self.get_leaders()}:{self.get_invitations()}"
                f"{self.get_timers()}:"
                f"{self.get_teams()}:"
                f"{self.get_areas()}")

    def __repr__(self):
        """
        Return a representation of this nonstop debate.

        Returns
        -------
        str
            Printable representation.

        """

        return (f'NonStopDebate(server, {self.manager.get_id()}, "{self.get_id()}", '
                f'player_limit={self.get_player_limit()}, '
                f'player_concurrent_limit={self.get_player_concurrent_limit()}, '
                f'require_players={self.requires_players()}, '
                f'require_invitations={self.requires_invitations()}, '
                f'require_leaders={self.requires_leaders()}, '
                f'require_participant_character={self.requires_participant_characters()}, '
                f'team_limit={self._team_manager.get_managee_limit()}, '
                f'timer_limit={self._timer_manager.get_timer_limit()}, '
                f'areas={self.get_areas()}, '
                f'trial_id={self.get_trial().get_id()}), '
                f'mode={self._mode}'
                f'|| '
                f'players={self.get_players()}, '
                f'invitations={self.get_invitations()}, '
                f'leaders={self.get_leaders()}, '
                f'timers={self.get_timers()}, '
                f'teams={self.get_teams()}, '
                f'unmanaged={self.is_unmanaged()}), '
                f')')
