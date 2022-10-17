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
Module that contains the trial manager and trial modules.

"""

from __future__ import annotations

import typing

from server.exceptions import NonStopDebateError, TrialError, HubbedGameError
from server.hubbedgame_manager import _HubbedGame, HubbedGameManager
from server.trialminigame import _TrialMinigame, TRIALMINIGAMES
from server.nonstopdebate import _NonStopDebate

from typing import Callable, Dict, Set, Any, Tuple, Type, Union

if typing.TYPE_CHECKING:
    from server.area_manager import AreaManager
    from server.client_manager import ClientManager
    from server.game_manager import _Team
    from server.hub_manager import _Hub
    from server.timer_manager import Timer
    from server.tsuserver import TsuserverDR

class _TrialTrivialInherited(_HubbedGame):
    """
    This class should not be instantiated.
    """

    def get_id(self) -> str:
        """
        Return the ID of this trial.

        Returns
        -------
        str
            The ID.

        """

        return super().get_id()

    def get_numerical_id(self) -> int:
        """
        Return the numerical portion of the ID of this trial.

        Returns
        -------
        int
            Numerical portion of the ID.
        """

        return super().get_numerical_id()

    def get_name(self) -> str:
        """
        Get the name of the trial.

        Returns
        -------
        str
            Name.
        """

        return super().get_name()

    def set_name(self, name: str):
        """
        Set the name of the trial.

        Parameters
        ----------
        name : str
            Name.
        """

        self.unchecked_set_name(name)
        self.manager._check_structure()

    def unchecked_set_name(self, name: str):
        """
        Set the name of the trial.

        This method does not assert structural integrity.

        Parameters
        ----------
        name : str
            Name.
        """

        super().unchecked_set_name(name)

    def get_player_limit(self) -> Union[int, None]:
        """
        Return the player membership limit of this trial.

        Returns
        -------
        Union[int, None]
            The player membership limit.

        """

        return super().get_player_limit()

    def get_player_concurrent_limit(self) -> Union[int, None]:
        """
        Return the concurrent player membership limit of this trial.

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
        Return (a shallow copy of) the set of players of this trial that satisfy a
        condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all players returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) players of this trial.

        """

        return super().get_players(cond=cond)

    def is_player(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is a player of the trial.

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
        Make a user a player of the trial. By default this player will not be a leader,
        unless the trial has no leaders and it requires a leader.
        It will also subscribe the trial to the player so it can listen to its updates.

        Newly added players will be ordered to switch to a 'trial' variant.

        Parameters
        ----------
        user : ClientManager.Client
            User to add to the trial. They must be in an area part of the trial.

        Raises
        ------
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.UserNotInAreaError
            If the user is not in an area part of the trial.
        TrialError.UserHasNoCharacterError
            If the user has no character but the trial requires that all players have
            characters.
        TrialError.UserNotInvitedError
            If the trial requires players be invited to be added and the user is not
            invited.
        TrialError.UserAlreadyPlayerError
            If the user to add is already a user of the trial.
        TrialError.UserHitGameConcurrentLimitError
            If the player has reached the concurrent player membership of any of the trial
            managed by the manager of this trial, or by virtue of joining this
            trial they would violate this trial's concurrent player membership limit.
        TrialError.GameIsFullError
            If the trial reached its player limit.

        """

        self.unchecked_add_player(user)
        self.manager._check_structure()

    def remove_player(self, user: ClientManager.Client):
        """
        Make a user be no longer a player of this trial. If they were part of a team
        managed by this trial, they will also be removed from said team. It will also
        unsubscribe the trial from the player so it will no longer listen to its updates.

        If the trial required that there it always had players and by calling this method
        the trial had no more players, the trial will automatically be scheduled
        for deletion.

        Parameters
        ----------
        user : ClientManager.Client
            User to remove.

        Raises
        ------
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.UserNotPlayerError
            If the user to remove is already not a player of this trial.

        """

        self.unchecked_remove_player(user)
        self.manager._check_structure()

    def requires_players(self) -> bool:
        """
        Return whether the trial requires players at all times.

        Returns
        -------
        bool
            Whether the trial requires players at all times.
        """

        return super().requires_players()

    def get_invitations(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
        ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of invited users of this trial that satisfy a
        condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all invited users returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) invited users of this trial.

        """

        return super().get_invitations(cond=cond)

    def is_invited(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is invited to the trial.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Raises
        ------
        TrialError.UserAlreadyPlayerError
            If the user is a player of this trial.

        Returns
        -------
        bool
            True if the user is invited, False otherwise.

        """

        try:
            return super().is_invited(user)
        except HubbedGameError.UserAlreadyPlayerError:
            raise TrialError.UserAlreadyPlayerError

    def add_invitation(self, user: ClientManager.Client):
        """
        Mark a user as invited to this trial.

        Parameters
        ----------
        user : ClientManager.Client
            User to invite to the trial.

        Raises
        ------
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.GameDoesNotTakeInvitationsError
            If the trial does not require users be invited to the trial.
        TrialError.UserAlreadyInvitedError
            If the player to invite is already invited to the trial.
        TrialError.UserAlreadyPlayerError
            If the player to invite is already a player of the trial.

        """

        self.unchecked_add_invitation(user)
        self.manager._check_structure()

    def unchecked_add_invitation(self, user: ClientManager.Client):
        """
        Mark a user as invited to this trial.

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to invite to the trial.

        Raises
        ------
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.GameDoesNotTakeInvitationsError
            If the trial does not require users be invited to the trial.
        TrialError.UserAlreadyInvitedError
            If the player to invite is already invited to the trial.
        TrialError.UserAlreadyPlayerError
            If the player to invite is already a player of the trial.

        """

        try:
            super().unchecked_add_invitation(user)
        except HubbedGameError.GameIsUnmanagedError:
            raise TrialError.GameIsUnmanagedError
        except HubbedGameError.GameDoesNotTakeInvitationsError:
            raise TrialError.GameDoesNotTakeInvitationsError
        except HubbedGameError.UserAlreadyInvitedError:
            raise TrialError.UserAlreadyInvitedError
        except HubbedGameError.UserAlreadyPlayerError:
            raise TrialError.UserAlreadyPlayerError

    def remove_invitation(self, user: ClientManager.Client):
        """
        Mark a user as no longer invited to this trial (uninvite).

        Parameters
        ----------
        user : ClientManager.Client
            User to uninvite.

        Raises
        ------
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.GameDoesNotTakeInvitationsError
            If the trial does not require users be invited to the trial.
        TrialError.UserNotInvitedError
            If the user to uninvite is already not invited to this trial.

        """

        self.unchecked_remove_invitation(user)
        self.manager._check_structure()

    def unchecked_remove_invitation(self, user: ClientManager.Client):
        """
        Mark a user as no longer invited to this trial (uninvite).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to uninvite.

        Raises
        ------
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.GameDoesNotTakeInvitationsError
            If the trial does not require users be invited to the trial.
        TrialError.UserNotInvitedError
            If the user to uninvite is already not invited to this trial.

        """

        try:
            super().unchecked_remove_invitation(user)
        except HubbedGameError.GameIsUnmanagedError:
            raise TrialError.GameIsUnmanagedError
        except HubbedGameError.GameDoesNotTakeInvitationsError:
            raise TrialError.GameDoesNotTakeInvitationsError
        except HubbedGameError.UserNotInvitedError:
            raise TrialError.UserNotInvitedError

    def requires_invitations(self):
        """
        Return True if the trial requires players be invited before being allowed to join
        the trial, False otherwise.

        Returns
        -------
        bool
            True if the trial requires players be invited before being allowed to join
            the trial, False otherwise.
        """

        return super().requires_invitations()

    def get_leaders(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
        ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of leaders of this trial that satisfy a condition
        if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all leaders returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) leaders of this trial.

        """

        return super().get_leaders(cond=cond)

    def get_regulars(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
        ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of players of this trial that are regulars and
        satisfy a condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all regulars returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) regulars of this trial.

        """

        return super().get_regulars(cond=cond)

    def is_leader(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is a leader of the trial.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Raises
        ------
        TrialError.UserNotPlayerError
            If the player to test is not a player of this trial.

        Returns
        -------
        bool
            True if the player is a user, False otherwise.

        """

        try:
            return super().is_leader(user)
        except HubbedGameError.UserNotPlayerError:
            raise TrialError.UserNotPlayerError

    def add_leader(self, user: ClientManager.Client):
        """
        Set a user as leader of this trial (promote to leader).

        Parameters
        ----------
        user : ClientManager.Client
            Player to promote to leader.

        Raises
        ------
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.UserNotPlayerError
            If the player to promote is not a player of this trial.
        TrialError.UserAlreadyLeaderError
            If the player to promote is already a leader of this trial.

        """

        self.unchecked_add_leader(user)
        self.manager._check_structure()

    def unchecked_add_leader(self, user: ClientManager.Client):
        """
        Set a user as leader of this trial (promote to leader).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            Player to promote to leader.

        Raises
        ------
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.UserNotPlayerError
            If the player to promote is not a player of this trial.
        TrialError.UserAlreadyLeaderError
            If the player to promote is already a leader of this trial.

        """

        try:
            super().unchecked_add_leader(user)
        except HubbedGameError.GameIsUnmanagedError:
            raise TrialError.GameIsUnmanagedError
        except HubbedGameError.UserNotPlayerError:
            raise TrialError.UserNotPlayerError
        except HubbedGameError.UserAlreadyLeaderError:
            raise TrialError.UserAlreadyLeaderError

    def remove_leader(self, user: ClientManager.Client):
        """
        Make a user no longer leader of this trial (demote).

        Parameters
        ----------
        user : ClientManager.Client
            User to demote.

        Raises
        ------
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.UserNotPlayerError
            If the player to demote is not a player of this trial.
        TrialError.UserNotLeaderError
            If the player to demote is already not a leader of this trial.

        """

        self.unchecked_remove_leader(user)
        self.manager._check_structure()

    def unchecked_remove_leader(self, user: ClientManager.Client):
        """
        Make a user no longer leader of this trial (demote).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to demote.

        Raises
        ------
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.UserNotPlayerError
            If the player to demote is not a player of this trial.
        TrialError.UserNotLeaderError
            If the player to demote is already not a leader of this trial.

        """

        if self.is_unmanaged():
            raise TrialError.GameIsUnmanagedError

        try:
            super().unchecked_remove_leader(user)
        except HubbedGameError.GameIsUnmanagedError:
            raise TrialError.GameIsUnmanagedError
        except HubbedGameError.UserNotPlayerError:
            raise TrialError.UserNotPlayerError
        except HubbedGameError.UserNotLeaderError:
            raise TrialError.UserNotLeaderError

    def has_ever_had_players(self) -> bool:
        """
        Return True if a player has ever been added to this trial, False otherwise.

        Returns
        -------
        bool
            True if the trial has ever had a player added, False otherwise.

        """

        return super().has_ever_had_players()

    def requires_leaders(self) -> bool:
        """
        Return whether the trial requires leaders at all times.

        Returns
        -------
        bool
            Whether the trial requires leaders at all times.
        """

        return super().requires_leaders()

    def has_ever_had_players(self):
        """
        Return True if a player has ever been added to this trial, False otherwise.

        Returns
        -------
        bool
            True if the trial has ever had a player added, False otherwise.

        """

        return super().has_ever_had_players()

    def requires_characters(self) -> bool:
        """
        Return whether the trial requires players have a character at all times.

        Returns
        -------
        bool
            Whether the trial requires players have a character at all times.
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
        Create a new timer managed by this trial with given parameters.

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
            If True, the trial will automatically delete the timer once it is terminated
            by it ticking out or manual termination. If False, no such automatic deletion will take
            place. Defaults to True.

        Returns
        -------
        Timer
            The created timer.

        Raises
        ------
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.GameTooManyTimersError
            If the trial is already managing its maximum number of timers.

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
        Create a new timer managed by this trial with given parameters.

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
            If True, the trial will automatically delete the timer once it is terminated
            by it ticking out or manual termination. If False, no such automatic deletion will take
            place. Defaults to True.

        Returns
        -------
        Timer
            The created timer.

        Raises
        ------
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.GameTooManyTimersError
            If the trial is already managing its maximum number of timers.

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
            raise TrialError.GameIsUnmanagedError
        except HubbedGameError.GameTooManyTimersError:
            raise TrialError.GameTooManyTimersError

    def delete_timer(self, timer: Timer) -> str:
        """
        Delete a timer managed by this trial, terminating it first if needed.

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
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.GameDoesNotManageTimerError
            If the trial does not manage the target timer.

        """

        timer_id = self.unchecked_delete_timer(timer)
        self.manager._check_structure()
        return timer_id

    def unchecked_delete_timer(self, timer: Timer) -> str:
        """
        Delete a timer managed by this trial, terminating it first if needed.

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
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.GameDoesNotManageTimerError
            If the trial does not manage the target timer.

        """

        try:
            return super().unchecked_delete_timer(timer)
        except HubbedGameError.GameIsUnmanagedError:
            raise TrialError.GameIsUnmanagedError
        except HubbedGameError.GameDoesNotManageTimerError:
            raise TrialError.GameDoesNotManageTimerError

    def get_timers(self) -> Set[Timer]:
        """
        Return (a shallow copy of) the timers this trial manages.

        Returns
        -------
        Set[Timer]
            Timers this trial manages.

        """

        return super().get_timers()

    def get_timer_by_id(self, timer_id: str) -> Timer:
        """
        If `timer_tag` is the ID of a timer managed by this trial, return that timer.

        Parameters
        ----------
        timer_id: str
            ID of timer this trial manages.

        Returns
        -------
        Timer
            The timer whose ID matches the given ID.

        Raises
        ------
        TrialError.GameInvalidTimerIDError:
            If `timer_tag` is a str and it is not the ID of a timer this trial manages.

        """

        try:
            return super().get_timer_by_id(timer_id)
        except HubbedGameError.GameInvalidTimerIDError:
            raise TrialError.GameInvalidTimerIDError

    def get_timer_limit(self) -> Union[int, None]:
        """
        Return the timer limit of this trial.

        Returns
        -------
        Union[int, None]
            Timer limit.

        """

        return super().get_timer_limit()

    def get_timer_ids(self) -> Set[str]:
        """
        Return (a shallow copy of) the IDs of all timers managed by this trial.

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
        Create a new team managed by this trial.

        Parameters
        ----------
        team_type : _Team
            Class of team that will be produced. Defaults to None (and converted to the
            default team created by games, namely, _Team).
        creator : ClientManager.Client, optional
            The player who created this team. If set, they will also be added to the team if
            possible. The creator must be a player of this trial. Defaults to None.
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
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.GameTooManyTeamsError
            If the trial is already managing its maximum number of teams.
        TrialError.UserInAnotherTeamError
            If `creator` is not None and already part of a team managed by this trial.

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
        Create a new team managed by this trial.

        This method does not assert structural integrity.

        Parameters
        ----------
        team_type : _Team
            Class of team that will be produced. Defaults to None (and converted to the
            default team created by games, namely, _Team).
        creator : ClientManager.Client, optional
            The player who created this team. If set, they will also be added to the team if
            possible. The creator must be a player of this trial. Defaults to None.
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
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.GameTooManyTeamsError
            If the trial is already managing its maximum number of teams.
        TrialError.UserInAnotherTeamError
            If `creator` is not None and already part of a team managed by this trial.

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
            raise TrialError.GameIsUnmanagedError
        except HubbedGameError.GameTooManyTeamsError:
            raise TrialError.GameTooManyTeamsError
        except HubbedGameError.UserInAnotherTeamError:
            raise TrialError.UserInAnotherTeamError

    def delete_team(self, team: _Team) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a team managed by this trial.

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
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.GameDoesNotManageTeamError
            If the trial does not manage the target team.

        """

        team_id, players = self.unchecked_delete_team(team)
        self.manager._check_structure()
        return team_id, players

    def unchecked_delete_team(self, team: _Team) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a team managed by this trial.

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
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.GameDoesNotManageTeamError
            If the trial does not manage the target team.

        """

        try:
            return super().unchecked_delete_team(team)
        except HubbedGameError.GameIsUnmanagedError:
            raise TrialError.GameIsUnmanagedError
        except HubbedGameError.GameDoesNotManageTeamError:
            raise TrialError.GameDoesNotManageTeamError

    def manages_team(self, team: _Team) -> bool:
        """
        Return True if the team is managed by this trial, False otherwise.

        Parameters
        ----------
        team : _Team
            The team to check.

        Returns
        -------
        bool
            True if the trial manages this team, False otherwise.

        """

        return super().manages_team(team)

    def get_teams(self) -> Set[_Team]:
        """
        Return (a shallow copy of) the teams this trial manages.

        Returns
        -------
        Set[_Team]
            Teams this trial manages.

        """

        return super().get_teams()

    def get_team_by_id(self, team_id: str) -> _Team:
        """
        If `team_id` is the ID of a team managed by this trial, return the team.

        Parameters
        ----------
        team_id : str
            ID of the team this trial manages.

        Returns
        -------
        _Team
            The team that matches the given ID.

        Raises
        ------
        TrialError.GameInvalidTeamIDError:
            If `team_id` is not the ID of a team this trial manages.

        """

        try:
            return super().get_team_by_id(team_id)
        except HubbedGameError.GameInvalidTeamIDError:
            raise TrialError.GameInvalidTeamIDError

    def get_team_limit(self) -> Union[int, None]:
        """
        Return the team limit of this trial.

        Returns
        -------
        Union[int, None]
            Team limit.

        """

        return super().get_team_limit()

    def get_team_ids(self) -> Set[str]:
        """
        Return (a shallow copy of) the IDs of all teams managed by this trial.

        Returns
        -------
        Set[str]
            The IDs of all managed teams.

        """

        return super().get_team_ids()

    def get_teams_of_user(self, user: ClientManager.Client) -> Set[_Team]:
        """
        Return (a shallow copy of) the teams managed by this trial user `user` is a player
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
        trial.

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
        TrialError.GameTooManyTeamsError
            If the trial is already managing its maximum number of teams.

        """

        try:
            return super().get_available_team_id()
        except HubbedGameError.GameTooManyTeamsError:
            raise TrialError.GameTooManyTeamsError

    def get_autoadd_on_client_enter(self) -> bool:
        """
        Return True if the trial will always attempt to add nonplayer users who enter an
        area part of the trial, False otherwise.

        Returns
        -------
        bool
            True if the trial will always attempt to add nonplayer users who enter an area
            part of the trial, False otherwise.
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
        Add an area to this trial's set of areas.

        Parameters
        ----------
        area : AreaManager.Area
            Area to add.

        Raises
        ------
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.AreaDisallowsBulletsError
            If the area to add disallows bullets.
        TrialError.AreaAlreadyInGameError
            If the area is already part of the trial.
        TrialError.AreaHitGameConcurrentLimitError.
            If `area` has reached the concurrent area membership limit of any of the games with
            areas it belongs to managed by this manager, or by virtue of adding this area it will
            violate this trial's concurrent area membership limit.

        """

        self.unchecked_add_area(area)
        self.manager._check_structure()

    def remove_area(self, area: AreaManager.Area):
        """
        Remove an area from this trial's set of areas.
        If the area is already a part of the trial, do nothing.
        If any player of the trial is in this area, they are removed from the
        trial.
        If the trial has no areas remaining, it will be automatically destroyed.

        Parameters
        ----------
        area : AreaManager.Area
            Area to remove.

        Raises
        ------
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.AreaNotInGameError
            If the area is already not part of the trial.

        """

        self.unchecked_remove_area(area)
        self.manager._check_structure()

    def unchecked_remove_area(self, area: AreaManager.Area):
        """
        Remove an area from this trial's set of areas.
        If the area is already a part of the trial, do nothing.
        If any player of the trial is in this area, they are removed from the
        trial.
        If the trial has no areas remaining, it will be automatically destroyed.

        This method does not assert structural integrity.

        Parameters
        ----------
        area : AreaManager.Area
            Area to remove.

        Raises
        ------
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.AreaNotInGameError
            If the area is already not part of the trial.

        """

        try:
            super().unchecked_remove_area(area)
        except HubbedGameError.GameIsUnmanagedError:
            raise TrialError.GameIsUnmanagedError
        except HubbedGameError.AreaNotInGameError:
            raise TrialError.AreaNotInGameError

    def requires_areas(self) -> bool:
        """
        Return whether the trial requires areas at all times.

        Returns
        -------
        bool
            Whether the trial requires areas at all times.
        """

        return super().requires_areas()

    def has_area(self, area: AreaManager.Area) -> bool:
        """
        If the area is part of this trial's set of areas, return True; otherwise, return
        False.

        Parameters
        ----------
        area : AreaManager.Area
            Area to check.

        Returns
        -------
        bool
            True if the area is part of the trial's set of areas, False otherwise.

        """

        return super().has_area(area)

    def get_areas(self) -> Set[AreaManager.Area]:
        """
        Return (a shallow copy of) the set of areas of this trial.

        Returns
        -------
        Set[AreaManager.Area]
            Set of areas of the trial.

        """

        return super().get_areas()

    def get_area_concurrent_limit(self) -> Union[int, None]:
        """
        Return the concurrent area membership limit of this trial.

        Returns
        -------
        Union[int, None]
            The concurrent area membership limit.

        """

        return super().get_area_concurrent_limit()

    def get_users_in_areas(self) -> Set[ClientManager.Client]:
        """
        Return all users in areas part of the trial, even those that are not players of
        the trial.

        Returns
        -------
        Set[ClientManager.Client]
            All users in areas part of the trial.

        """

        return super().get_users_in_areas()

    def get_nonleader_users_in_areas(self) -> Set[ClientManager.Client]:
        """
        Return all users in areas part of the trial, even those that are not players of
        the trial, such that they are not leaders of the trial.

        Returns
        -------
        Set[ClientManager.Client]
            All users in areas part of the trial that are not leaders of the trial.

        """

        return super().get_nonleader_users_in_areas()

    def get_nonplayer_users_in_areas(self) -> Set[ClientManager.Client]:
        """
        Return all users in areas part of the trial that are not players of the
        trial.

        Returns
        -------
        Set[ClientManager.Client]
            All users in areas part of the trial that are not players of the trial.

        """

        return super().get_nonplayer_users_in_areas()

    def is_unmanaged(self):
        """
        Return True if this trial is unmanaged, False otherwise.

        Returns
        -------
        bool
            True if unmanaged, False otherwise.

        """

        return super().is_unmanaged()

    def destroy(self):
        """
        Mark this trial as destroyed and notify its manager so that it is deleted.
        If the trial is already destroyed, this function does nothing.
        A trial marked for destruction will delete all of its timers, teams, remove all
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
        Default callback for trial player signaling it wants to check if sending an IC
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
        Default callback for trial player signaling it has sent an IC message.
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

    def _on_area_client_inbound_ms_check(
        self,
        area: AreaManager.Area,
        client: ClientManager.Client = None,
        contents: Dict[str, Any] = None
        ):
        """
        Default callback for trial area signaling a client in the area sent an IC message.
        Unlike the ClientManager.Client callback for send_ic_check, this one is triggered
        regardless of whether the sender is part of the trial or not. This is useful for
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
        Default callback for trial area signaling it was destroyed.

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

class _Trial(_TrialTrivialInherited):
    """
    A trial is a hubbed game that can manage 'trial minigames', which are the following
    trial games (server.trialminigame):
    * Nonstop Debates (server.nonstopdebate).

    While multiple minigames may be going on at the same time, no player may be part of two
    minigames simultaneously.

    Attributes
    ----------
    server : TsuserverDR
        Server the trial belongs to.
    manager : TrialManager
        Manager for this trial.
    hub: _Hub
        Hub for this hubbed game.
    listener : Listener
        Standard listener of the trial.

    Callback Methods
    ----------------
    _on_area_client_left_final
        Method to perform once a client left an area of the trial.
    _on_area_client_entered_final
        Method to perform once a client entered an area of the trial.
    _on_area_destroyed
        Method to perform once an area of the trial is marked for destruction.
    _on_client_inbound_ms_check
        Method to perform once a player of the trial wants to send an IC message.
    _on_client_inbound_ms_final
        Method to perform once a player of the trial sends an IC message.
    _on_client_change_character
        Method to perform once a player of the trial has changed character.
    _on_client_destroyed
        Method to perform once a player of the trial is destroyed.

    """

    # (Private) Attributes
    # --------------------
    # _player_to_influence : Dict[ClientManager.Client, float]
    #   Mapping of trial players to their current influence.
    # _player_to_focus : Dict[ClientManager.Client, float]
    #   Mapping of trial players to their current focus.
    # _min_influence : int
    #   Minimum influence any player of the trial may have.
    # _max_influence : int
    #   Maximum influence any player of the trial may have.
    # _min_focus : int
    #   Minimum influence any player of the trial may have.
    # _max_focus : int
    #   Maximum influence any player of the trial may have.
    # _autoadd_minigame_on_player_added : bool
    #   Whether to automatically add new players of the trial to any active minigames of the trial.
    # _client_timer_id : int
    #   ID of the client timer to use for trial purposes.
    # _minigame_manager : GameManager
    #   Manager for all games of the trial.

    # Invariants
    # ----------
    # 1. For each player of a minigame of this trial, they are also a player of the trial.
    # 2. For each area of a minigame of this trial, they are also an area of the trial.
    # 3. The player to influence and player to focus maps contain exactly the IDs of all players
    # of the trial.
    # 4. For each influence and focus value in the player to influence and player to focus maps,
    # they are a value between 0 and 10 inclusive.
    # 5. The invariants from the parent class GameWithArea are satisfied.


    def __init__(
        self,
        server: TsuserverDR,
        manager: TrialManager,
        trial_id: str,
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
        autoadd_minigame_on_player_added: bool = False,
        minigame_limit: int = 1,
    ):
        """
        Create a new trial. A trial should not be fully initialized anywhere else other than
        some manager code, as otherwise the manager will not recognize the trial.

        Parameters
        ----------
        server : TsuserverDR
            Server the trial belongs to.
        hub : _Hub
            Hub the trial belongs to.
        manager : TrialManager
            Manager for this trial.
        trial_id : str
            Identifier of the trial.
        player_limit : Union[int, None], optional
            If an int, it is the maximum number of players the trial supports. If None, it
            indicates the trial has no player limit. Defaults to None.
        player_concurrent_limit : Union[int, None], optional
            If an int, it is the maximum number of trials managed by `manager` that any
            player of this trial may belong to, including this trial. If None, it indicates
            that this trial does not care about how many other trials managed by `manager` each
            of its players belongs to. Defaults to None.
        require_invitation : bool, optional
            If True, players can only be added to the trial if they were previously invited. If
            False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the trial has no players left, the trial will
            automatically be deleted. If False, no such automatic deletion will happen.
            Defaults to True.
        require_leaders : bool, optional
            If True, if at any point the trial has no leaders left, the trial will choose a
            leader among any remaining players left; if no players are left, the next player
            added will be made leader. If False, no such automatic assignment will happen.
            Defaults to True.
        require_character : bool, optional
            If False, players without a character will not be allowed to join the trial, and
            players that switch to something other than a character will be automatically
            removed from the trial. If False, no such checks are made. A player without a
            character is considered one where player.has_participant_character() returns False. Defaults
            to False.
        team_limit : Union[int, None], optional
            If an int, it is the maximum number of teams the trial supports. If None, it
            indicates the trial has no team limit. Defaults to None.
        timer_limit : Union[int, None], optional
            If an int, it is the maximum number of timers the trial supports. If None, it
            indicates the trial has no timer limit. Defaults to None.
        area_concurrent_limit : Union[int, None], optional
            If an int, it is the maximum number of trials managed by `manager` that any
            area of this trial may belong to, including this trial. If None, it indicates
            that this trial does not care about how many other trials managed by
            `manager` each of its areas belongs to. Defaults to 1 (an area may not be a part of
            another trial managed by `manager` while being an area of this trial).
        autoadd_on_client_enter : bool, optional
            If True, nonplayer users that enter an area part of the trial will be automatically
            added if permitted by the conditions of the trial. If False, no such adding will take
            place. Defaults to False.
        require_areas : bool, optional
            If True, if at any point the trial has no areas left, the game with areas
            will automatically be deleted. If False, no such automatic deletion will happen.
            Defaults to True.
        hub : _Hub, optional
            Hub the hubbed game belongs to. Defaults to None.
        autoadd_minigame_on_player_added: bool, optional
            If True, any player added to the trial will be automatically added as a player of the
            latest minigame currently open in the trial. If no such minigame is open or the
            player addition fails, no action is taken. If False, no such adding will take place.
            Defaults to False.
        minigame_limit : Union[int, None], optional
            If an int, it is the maximum number of minigames the trial may have simultaneously.
            If None, it indicates the trial has no minigame limit. Defaults to 1.

        """

        self._player_to_influence: Dict[ClientManager.Client, float] = dict()
        self._player_to_focus: Dict[ClientManager.Client, float] = dict()
        self._min_influence = 0
        self._max_influence = 10
        self._min_focus = 0
        self._max_focus = 10

        self._client_timer_id = 0
        self._autoadd_minigame_on_player_added = autoadd_minigame_on_player_added

        self._minigame_manager = HubbedGameManager(
            server,
            managee_limit=minigame_limit,
            default_managee_type=_TrialMinigame,
        )
        super().__init__(
            server,
            manager,
            trial_id,
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

        self.listener.update_events({
            'client_inbound_rt': self._on_client_inbound_rt,
            })
        self.manager: TrialManager  # Setting for typing

    def get_type_name(self) -> str:
        """
        Return the type name of the trial. Names are fully lowercase.
        Implementations of the class should replace this with a human readable name of the trial.

        Returns
        -------
        str
            Type name of the trial.

        """

        return "trial"

    def get_autoadd_minigame_on_player_added(self) -> bool:
        """
        Get the default behavior to do when a player is added to a trial:
        * If True, the trial will automatically try to add any players that are added to the
        trial to all minigames it hosts in some arbitrary order.
        * If False, no such automatic attempts are done.

        Returns
        -------
        bool
            True if an attempt will be made, False otherwise.

        """

        return self._autoadd_minigame_on_player_added

    def set_autoadd_minigame_on_player_added(self, new_value: bool):
        """
        Set the default behavior to do when a player is added to a trial:
        * If True, the trial will automatically try to add any players that are added to the
        trial to all minigames it hosts in some arbitrary order.
        * If False, no such automatic attempts are done.

        Parameters
        ----------
        new_value : bool
            New value.

        """

        self.unchecked_set_autoadd_minigame_on_player_added(new_value)
        self.manager._check_structure()

    def unchecked_set_autoadd_minigame_on_player_added(self, new_value: bool):
        """
        Set the default behavior to do when a player is added to a trial:
        * If True, the trial will automatically try to add any players that are added to the
        trial to all minigames it hosts in some arbitrary order.
        * If False, no such automatic attempts are done.

        This method does not assert structural integrity.

        Parameters
        ----------
        new_value : bool
            New value.

        """

        self._autoadd_minigame_on_player_added = new_value

    def unchecked_add_player(self, user: ClientManager.Client):
        """
        Make a user a player of the trial. By default this player will not be a leader,
        unless the trial has no leaders and it requires a leader.
        It will also subscribe the trial to the player so it can listen to its updates.

        Newly added players will be ordered to switch to a 'trial' variant.

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to add to the trial. They must be in an area part of the trial.

        Raises
        ------
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.UserNotInAreaError
            If the user is not in an area part of the trial.
        TrialError.UserHasNoCharacterError
            If the user has no character but the trial requires that all players have
            characters.
        TrialError.UserNotInvitedError
            If the trial requires players be invited to be added and the user is not
            invited.
        TrialError.UserAlreadyPlayerError
            If the user to add is already a user of the trial.
        TrialError.UserHitGameConcurrentLimitError
            If the player has reached the concurrent player membership of any of the trials
            managed by the manager of this trial, or by virtue of joining this
            trial they would violate this trial's concurrent player membership
            limit.
        TrialError.GameIsFullError
            If the trial reached its player limit.

        """

        try:
            super().unchecked_add_player(user)
        except HubbedGameError.GameIsUnmanagedError:
            raise TrialError.GameIsUnmanagedError
        except HubbedGameError.UserNotInAreaError:
            raise TrialError.UserNotInAreaError
        except HubbedGameError.UserHasNoCharacterError:
            raise TrialError.UserHasNoCharacterError
        except HubbedGameError.UserNotInvitedError:
            raise TrialError.UserNotInvitedError
        except HubbedGameError.UserAlreadyPlayerError:
            raise TrialError.UserAlreadyPlayerError
        except HubbedGameError.UserHitGameConcurrentLimitError:
            raise TrialError.UserHitGameConcurrentLimitError
        except HubbedGameError.GameIsFullError:
            raise TrialError.GameIsFullError

        self._player_to_influence[user.id] = (self._max_influence, self._min_influence,
                                              self._max_influence)
        self._player_to_focus[user.id] = (self._max_focus, self._min_focus, self._max_focus)

        self.introduce_user(user)
        self.publisher.publish('trial_player_added', {
            'player': user,
            })

    def unchecked_remove_player(self, user: ClientManager.Client):
        """
        Make a user be no longer a player of this trial. If they were part of a team
        managed by this trial, they will also be removed from said team. It will also
        unsubscribe the trial from the player so it will no longer listen to its updates.

        If the trial required that there it always had players and by calling this method
        the trial had no more players, the trial will automatically be scheduled for
        deletion.

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to remove.

        Raises
        ------
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.UserNotPlayerError
            If the user to remove is already not a player of this trial.

        """

        if self.is_unmanaged():
            raise TrialError.GameIsUnmanagedError
        if not self.is_player(user):
            raise TrialError.UserNotPlayerError

        self._player_to_influence.pop(user.id)
        self._player_to_focus.pop(user.id)
        for game in self._minigame_manager.get_managees():
            if user in game.get_players():
                game.remove_player(user)

        try:
            super().unchecked_remove_player(user)
        except HubbedGameError.GameIsUnmanagedError:
            # Should not have made it here as we already asserted the trial is not unmanaged
            raise RuntimeError(self, user)
        except HubbedGameError.UserNotPlayerError:
            # Should not have made it here as we already asserted the user is a player of the trial
            raise RuntimeError(self, user)

    def introduce_user(self, user: ClientManager.Client):
        """
        Broadcast information relevant for a user entering an area of the trial, namely current
        gamemode if needed.
        Note the user needs not be in the same area as the trial, nor be a player of the trial.

        Parameters
        ----------
        user : ClientManager.Client
            User to introduce.

        """

        if self.is_player(user):
            user.send_health(side=1, health=int(self._player_to_focus[user.id][0]))
            user.send_health(side=2, health=int(self._player_to_influence[user.id][0]))

        # If there are any minigames, let them set the splashes, gamemode and timers
        if self.get_minigames():
            return

        user.send_gamemode(name='trial')
        user.send_splash(name='testimony1')

        user.send_timer_pause(timer_id=self._client_timer_id)
        user.send_timer_set_time(timer_id=self._client_timer_id, new_time=0)
        user.send_timer_set_step_length(timer_id=self._client_timer_id,
                                        new_step_length=0)
        user.send_timer_set_firing_interval(timer_id=self._client_timer_id,
                                            new_firing_interval=0)

    def dismiss_user(self, user: ClientManager.Client):
        """
        Broadcast information relevant for a user that has left the trial, namely clear out
        gamemode and health bars. Gamemode is only cleared if the user's new area is not part
        of the trial's areas.
        Note the user needs not be in the same area as the NSD, nor be a player of the NSD.
        If the trial has never had any players, this method does nothing.

        Parameters
        ----------
        user : ClientManager.Client
            User to dismiss.

        """

        if not self.has_ever_had_players():
            return

        # We use .new_area rather than .area as this function may have been called as a result
        # of the user moving, in which case .area still points to the user's old area.

        user.send_health(side=1, health=user.area.hp_pro)
        user.send_health(side=2, health=user.area.hp_def)

        # If the user is no longer in an area part of an area of the trial, clear out gamemode
        if user.new_area not in self.get_areas():
            user.send_gamemode(name='')

    def unchecked_add_area(self, area: AreaManager.Area):
        """
        Add an area to this trial's set of areas.

        This method does not assert structural integrity.

        Parameters
        ----------
        area : AreaManager.Area
            Area to add.

        Raises
        ------
        TrialError.GameIsUnmanagedError
            If the trial was scheduled for deletion and thus does not accept any mutator
            public method calls.
        TrialError.AreaDisallowsBulletsError
            If the area to add disallows bullets.
        TrialError.AreaAlreadyInGameError
            If the area is already part of the trial.
        TrialError.AreaHitGameConcurrentLimitError.
            If `area` has reached the concurrent area membership limit of any of the games with
            areas it belongs to managed by this manager, or by virtue of adding this area it will
            violate this trial's concurrent area membership limit.

        """

        if self.is_unmanaged():
            raise TrialError.GameIsUnmanagedError
        if not area.bullet:
            raise TrialError.AreaDisallowsBulletsError

        try:
            super().unchecked_add_area(area)
        except HubbedGameError.GameIsUnmanagedError:
            raise RuntimeError(self)
        except HubbedGameError.AreaAlreadyInGameError:
            raise TrialError.AreaAlreadyInGameError
        except HubbedGameError.AreaHitGameConcurrentLimitError:
            raise TrialError.AreaHitGameConcurrentLimitError

    def get_influence(self, user: ClientManager.Client) -> float:
        """
        Get the current influence of a player of the trial.

        Parameters
        ----------
        user : ClientManager.Client
            Player to check.

        Raises
        ------
        TrialError.UserNotPlayerError
            If the user is not a player of the trial.

        Returns
        -------
        float
            Current influence of the player.

        """

        try:
            return self._player_to_influence[user.id][0]
        except KeyError:
            raise TrialError.UserNotPlayerError

    def set_influence(self, user: ClientManager.Client, new_influence: float):
        """
        Set the influence of a player of the trial.

        Parameters
        ----------
        user : ClientManager.Client
            Client to change.
        new_influence : float
            New influence.

        Raises
        ------
        TrialError.UserNotPlayerError
            If the user is not a player of the trial.
        TrialError.InfluenceIsInvalidError
            If the new influence is below the trial minimum or above the trial maximum.

        """

        self.unchecked_set_influence(user, new_influence)
        self.manager._check_structure()

    def unchecked_set_influence(self, user: ClientManager.Client, new_influence: float):
        """
        Set the influence of a player of the trial.

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            Client to change.
        new_influence : float
            New influence.

        Raises
        ------
        TrialError.UserNotPlayerError
            If the user is not a player of the trial.
        TrialError.InfluenceIsInvalidError
            If the new influence is below the trial minimum or above the trial maximum.

        """


        if user not in self.get_players():
            raise TrialError.UserNotPlayerError
        _, min_influence, max_influence = self._player_to_influence[user.id]

        if not min_influence <= new_influence <= max_influence:
            raise TrialError.InfluenceIsInvalidError

        self._player_to_influence[user.id] = (new_influence, min_influence, max_influence)
        user.send_health(side=2, health=int(new_influence))

        # If the new influence is 0, warn all trial leaders
        if new_influence == 0:
            user.send_ooc('You ran out of influence!')
            user.send_ooc_others(f'(X) {user.displayname} ran out of influence!',
                                 pred=lambda c: c in self.get_leaders())

    def change_influence_by(self, user: ClientManager.Client, change_by: float):
        """
        Change the influence of a player by a certain value. If the new influence value goes
        below the trial minimum, it is set to the trial minimum. If instead it goes above the
        trial maximum, it is set to the trial maximum.

        Parameters
        ----------
        user : ClientManager.Client
            Client to change.
        change_by : float
            Amount to change influence by.

        Raises
        ------
        TrialError.UserNotPlayerError
            If the user is not a player of the trial.

        """

        self.unchecked_change_influence_by(user, change_by)
        self.manager._check_structure()

    def unchecked_change_influence_by(self, user: ClientManager.Client, change_by: float):
        """
        Change the influence of a player by a certain value. If the new influence value goes
        below the trial minimum, it is set to the trial minimum. If instead it goes above the
        trial maximum, it is set to the trial maximum.

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            Client to change.
        change_by : float
            Amount to change influence by.

        Raises
        ------
        TrialError.UserNotPlayerError
            If the user is not a player of the trial.

        """

        if user not in self.get_players():
            raise TrialError.UserNotPlayerError

        new_influence = self._player_to_influence[user.id][0] + change_by
        new_influence = max(self._min_influence, min(self._max_influence, new_influence))
        self.unchecked_set_influence(user, new_influence)

    def get_min_influence(self, user: ClientManager.Client) -> float:
        """
        Get the current minimum influence of a player of the trial.

        Parameters
        ----------
        user : ClientManager.Client
            Player to check.

        Raises
        ------
        TrialError.UserNotPlayerError
            If the user is not a player of the trial.

        Returns
        -------
        float
            Current minimum influence of the player.

        """

        try:
            return self._player_to_influence[user.id][1]
        except KeyError:
            raise TrialError.UserNotPlayerError

    def get_max_influence(self, user: ClientManager.Client) -> float:
        """
        Get the current maximum influence of a player of the trial.

        Parameters
        ----------
        user : ClientManager.Client
            Player to check.

        Raises
        ------
        TrialError.UserNotPlayerError
            If the user is not a player of the trial.

        Returns
        -------
        float
            Current maximum influence of the player.

        """

        try:
            return self._player_to_influence[user.id][2]
        except KeyError:
            raise TrialError.UserNotPlayerError

    def get_focus(self, user: ClientManager.Client) -> float:
        """
        Get the current focus of a player of the trial.

        Parameters
        ----------
        user : ClientManager.Client
            Player to check.

        Raises
        ------
        TrialError.UserNotPlayerError
            If the user is not a player of the trial.

        Returns
        -------
        float
            Current focus of the player.

        """

        try:
            return self._player_to_focus[user.id][0]
        except KeyError:
            raise TrialError.UserNotPlayerError

    def set_focus(self, user: ClientManager.Client, new_focus: float):
        """
        Set the focus of a player of the trial.

        Parameters
        ----------
        user : ClientManager.Client
            Client to change.
        new_focus : float
            New focus.

        Raises
        ------
        TrialError.UserNotPlayerError
            If the user is not a player of the trial.
        TrialError.FocusIsInvalidError
            If the new focus is below the trial minimum or above the trial maximum.

        """

        self.unchecked_set_focus(user, new_focus)
        self.manager._check_structure()

    def unchecked_set_focus(self, user: ClientManager.Client, new_focus: float):
        """
        Set the focus of a player of the trial.

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            Client to change.
        new_focus : float
            New focus.

        Raises
        ------
        TrialError.UserNotPlayerError
            If the user is not a player of the trial.
        TrialError.FocusIsInvalidError
            If the new focus is below the trial minimum or above the trial maximum.

        """

        if user not in self.get_players():
            raise TrialError.UserNotPlayerError
        _, min_focus, max_focus = self._player_to_focus[user.id]

        if not min_focus <= new_focus <= max_focus:
            raise TrialError.FocusIsInvalidError

        self._player_to_focus[user.id] = (new_focus, min_focus, max_focus)
        user.send_health(side=1, health=int(new_focus))

    def change_focus_by(self, user: ClientManager.Client, change_by: float):
        """
        Change the focus of a player by a certain value. If the new focus value goes
        below the trial minimum, it is set to the trial minimum. If instead it goes above the
        trial maximum, it is set to the trial maximum.

        Parameters
        ----------
        user : ClientManager.Client
            Client to change.
        change_by : float
            Amount to change focus by.

        Raises
        ------
        TrialError.UserNotPlayerError
            If the user is not a player of the trial.

        """

        self.unchecked_change_focus_by(user, change_by)
        self.manager._check_structure()

    def unchecked_change_focus_by(self, user: ClientManager.Client, change_by: float):
        """
        Change the focus of a player by a certain value. If the new focus value goes
        below the trial minimum, it is set to the trial minimum. If instead it goes above the
        trial maximum, it is set to the trial maximum.

        Parameters
        ----------
        user : ClientManager.Client
            Client to change.
        change_by : float
            Amount to change focus by.

        Raises
        ------
        TrialError.UserNotPlayerError
            If the user is not a player of the trial.

        """

        if user not in self.get_players():
            raise TrialError.UserNotPlayerError

        new_focus = self._player_to_focus[user.id][0] + change_by
        new_focus = max(self._min_focus, min(self._max_focus, new_focus))
        self.unchecked_set_focus(user, new_focus)

    def get_min_focus(self, user: ClientManager.Client) -> float:
        """
        Get the current minimum focus of a player of the trial.

        Parameters
        ----------
        user : ClientManager.Client
            Player to check.

        Raises
        ------
        TrialError.UserNotPlayerError
            If the user is not a player of the trial.

        Returns
        -------
        float
            Current minimum focus of the player.

        """

        try:
            return self._player_to_focus[user.id][1]
        except KeyError:
            raise TrialError.UserNotPlayerError

    def get_max_focus(self, user: ClientManager.Client) -> float:
        """
        Get the current maximum focus of a player of the trial.

        Parameters
        ----------
        user : ClientManager.Client
            Player to check.

        Raises
        ------
        TrialError.UserNotPlayerError
            If the user is not a player of the trial.

        Returns
        -------
        float
            Current maximum focus of the player.

        """

        try:
            return self._player_to_focus[user.id][2]
        except KeyError:
            raise TrialError.UserNotPlayerError

    def new_nsd(
        self,
        creator: ClientManager.Client = None,
        player_limit: Union[int, None] = None,
        require_invitations: bool = False,
        require_players: bool = True,
        require_character: bool = False,
        team_limit: Union[int, None] = None,
        timer_limit: Union[int, None] = None,
        #
        autoadd_on_creation_existing_users: bool = False,
        autoadd_on_trial_player_add: Union[bool, None] = None,
        timer_start_value: float = 300,
        ) -> _NonStopDebate:
        """
        Create a new NSD managed by this trial. Overriden default parameters include:
        * An NSD does not require leaders.

        Parameters
        ----------
        creator : ClientManager.Client, optional
            The player who created this NSD. If set, they will also be added to the NSD.
            Defaults to None.
        player_limit : Union[int, None], optional
            If an int, it is the maximum number of players the NSD supports. If None, it
            indicates the NSD has no player limit. Defaults to None.
        require_invitations : bool, optional
            If True, users can only be added to the NSD if they were previously invited. If
            False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the NSD loses all its players, the NSD will automatically
            be deleted. If False, no such automatic deletion will happen. Defaults to True.
        require_character : bool, optional
            If False, players without a character will not be allowed to join the NSD, and
            players that switch to something other than a character will be automatically
            removed from the NSD. If False, no such checks are made. A player without a
            character is considered one where player.has_participant_character() returns False. Defaults
            to False.
        team_limit : Union[int, None], optional
            If an int, it is the maximum number of teams the NSD will support. If None, it
            indicates the NSD will have no team limit. Defaults to None.
        timer_limit : Union[int, None], optional
            If an int, it is the maximum number of timers the NSD will support. If None, it
            indicates the NSD will have no timer limit. Defaults to None.
        autoadd_on_creation_existing_users : bool, optional
            If True, all players of the trial that are in the same area of the creator (if given a
            creator) will be automatically added to the NSD. If False, no such check is performed.
            Defaults to None.
        autoadd_on_trial_player_add : bool, optional
            If True, players that are added to the trial will be automatically added if permitted
            by the conditions of the game. If False, no such adding will take place. Defaults to
            None (use self.autoadd_minigame_on_player_added).
        timer_start_value : float, optional
            In seconds, the length of time the main timer of this nonstop debate will have at the
            start. It must be a positive number. Defaults to 300 (5 minutes).

        Returns
        -------
        NonStopDebate
            The created NSD.

        Raises
        ------
        TrialError.ManagerTooManyGamesError
            If the manager is already managing its maximum number of minigames.
        Any error from the created NSD's add_player(creator)
            If the NSD cannot add `creator` to the NSD if given one.

        """

        if autoadd_on_trial_player_add is None:
            autoadd_on_trial_player_add = self.get_autoadd_minigame_on_player_added()

        areas = {creator.area} if creator else set()
        hub = creator.hub

        try:
            nsd: _NonStopDebate = self._minigame_manager.new_managee(
                managee_type=_NonStopDebate,
                creator=None,
                player_limit=player_limit,
                player_concurrent_limit=1,
                require_invitations=require_invitations,
                require_players=require_players,
                require_leaders=False,
                require_character=require_character,
                team_limit=team_limit,
                timer_limit=timer_limit,
                areas=areas,
                area_concurrent_limit=1,
                autoadd_on_client_enter=False,
                hub=hub,
                # kwargs
                trial=self,
                autoadd_on_trial_player_add=autoadd_on_trial_player_add,
                timer_start_value=timer_start_value,
            )
        except HubbedGameError.ManagerTooManyGamesError:
            raise TrialError.ManagerTooManyGamesError

        nsd.setup_timers()
        # Add creator manually. This is because otherwise the creator does not get access to
        # the timer info.
        try:
            if creator:
                nsd.add_player(creator)
        except NonStopDebateError as ex:
            # Discard game
            self._minigame_manager.delete_managee(nsd)
            raise ex

        if autoadd_on_creation_existing_users:
            clients_to_add = {client for area in areas for client in area.clients}
            if creator:
                clients_to_add.discard(creator)
            for client in clients_to_add:
                try:
                    nsd.add_player(client)
                except NonStopDebateError.UserNotPlayerError:
                    continue

        # Manually give packets to nonplayers
        for nonplayer in nsd.get_nonplayer_users_in_areas():
            nsd.introduce_user(nonplayer)

        return nsd

    def get_nsd_of_user(self, user: ClientManager.Client) -> _NonStopDebate:
        """
        Get the NSD the user is in.

        Parameters
        ----------
        user : ClientManager.Client
            User to check.

        Raises
        ------
        TrialError.UserNotInMinigameError
            If the user is not in an NSD managed by this trial.

        Returns
        -------
        NonStopDebate
            NSD of the user.

        """

        games = self._minigame_manager.get_managees_of_user(user)
        nsds = {game for game in games if isinstance(game, _NonStopDebate)}
        if not nsds:
            raise TrialError.UserNotInMinigameError
        if len(nsds) > 1:
            raise RuntimeError(nsds)
        return next(iter(nsds))

    def get_minigames(self) -> Set[_TrialMinigame]:
        """
        Return the minigames of this trial.

        Returns
        -------
        Set[TrialMinigame]
            Trial minigames of this trial.

        """

        return self._minigame_manager.get_managees()

    def get_minigame_by_id(self, minigame_id: str) -> _TrialMinigame:
        """
        If `minigame_id` is the ID of a minigame managed by this trial, return that.

        Parameters
        ----------
        minigame_id : str
            ID of the minigame this trial manages.

        Returns
        -------
        TrialMinigame
            The minigame with that ID.

        Raises
        ------
        TrialError.ManagerInvalidGameIDError
            If `minigame_id` is not the ID of a minigame this game manages.

        """

        try:
            return self._minigame_manager.get_managee_by_id(minigame_id)
        except HubbedGameError.ManagerInvalidGameIDError:
            raise TrialError.ManagerInvalidGameIDError

    def get_nsd_by_id(self, nsd_id: str) -> _NonStopDebate:
        """
        If `nsd_id` is the ID of a nonstop debate managed by this trial, return that.

        Parameters
        ----------
        nsd_id : str
            ID of the nonstop debate this trial manages.

        Returns
        -------
        NonStopDebate
            The nonstop debate with that ID.

        Raises
        ------
        TrialError.ManagerInvalidGameIDError
            If `nsd_id` is not the ID of a nonstop debate this game manages.

        """

        try:
            minigame = self.get_minigame_by_id(nsd_id)
        except HubbedGameError.ManagerInvalidGameIDError:
            raise TrialError.ManagerInvalidGameIDError

        minigame_type = minigame.get_type()
        if minigame_type != TRIALMINIGAMES.NONSTOP_DEBATE:
            raise TrialError.ManagerInvalidGameIDError(f'`{nsd_id}` is a minigame of type '
                                                       f'{minigame_type}, not nonstop debate.')
        return minigame

    def get_available_minigame_id(self) -> str:
        """
        Get a minigame ID that no other minigame managed by this manager has.

        Returns
        -------
        str
            A unique minigame ID.

        Raises
        ------
        TrialError.ManagerTooManyGamesError
            If the manager is already managing its maximum number of games.

        """

        game_number = 0
        game_limit = self._minigame_manager.get_managee_limit()
        while game_limit is None or game_number < game_limit:
            new_game_id = "{}g{}".format(self.get_id(), game_number)
            if new_game_id not in self._minigame_manager.get_managee_ids():
                return new_game_id
            game_number += 1
        raise TrialError.ManagerTooManyGamesError

    def get_info(self, include_health: bool = True) -> str:
        """
        Obtain a long description of the trial and its players.

        Parameters
        ----------
        include_health : bool
            If True, the description will include the influence and focus values of the trial
            players; if False, these values will be omitted. Defaults to True.

        Returns
        -------
        str
            Description.

        """

        tid = self.get_id()
        leaders = self.get_leaders()
        regulars = self.get_regulars()

        num_members = len(leaders.union(regulars))
        group_texts = list()
        for group in (leaders, regulars):
            if not group:
                group_texts.append('\n*None')
                continue
            group_text = ''
            for player in sorted(group, key=lambda c: c.displayname):
                player_text = f'[{player.id}] {player.displayname}'
                if include_health:
                    player_text += ': '
                    influence = self.get_influence(player)
                    focus = self.get_focus(player)
                    player_text += f'Influence: {influence}; '
                    player_text += f'Focus: {focus}'
                group_text += f'\n*{player_text}'
            group_texts.append(group_text)

        leader_text, regular_text = group_texts
        area_ids = ', '.join(sorted({str(area.id) for area in self.get_areas()}))
        info = (f'Trial {tid} [{num_members}/-] ({area_ids}).'
                f'\nLeaders: {leader_text}'
                f'\nRegular members: {regular_text}')
        return info

    def unchecked_destroy(self):
        """
        Mark this game as destroyed and notify its manager so that it is deleted.
        If the game is already destroyed, this function does nothing.

        This method is reentrant (it will do nothing though).

        This method does not assert structural integrity.

        """

        # Store for later
        users = self.get_users_in_areas()

        # Remove minigames first. This is done first so as to enforce explicit destruction
        # (rather than rely on other methods).
        for game in self._minigame_manager.get_managees():
            game.destroy()

        super().unchecked_destroy()

        self._player_to_focus = dict()
        self._player_to_influence = dict()

        # Force every user in the former areas of the trial to be dismissed
        for user in users:
            self.dismiss_user(user)

    def end(self):
        """
        Destroy the trial and play the trial end splash animation to all users in the trial areas.

        This method does not assert structural integrity.
        """

        self.unchecked_end()
        self.manager._check_structure()
        self._check_structure()

    def unchecked_end(self):
        """
        Destroy the trial and play the trial end splash animation to all users in the trial areas.
        """

        users = self.get_users_in_areas()  # Store for later

        self.unchecked_destroy()

        for user in users:
            user.send_splash(name='testimony2')

    def _on_area_client_left_final(
        self,
        area: AreaManager.Area,
        client: ClientManager.Client = None,
        old_displayname: str = None,
        ignore_bleeding: bool = False,
        ignore_autopass: bool = False,
        ):
        """
        If a player left to an area not part of the trial, remove the player and warn them and
        the leaders of the trial.

        If a non-plyer left to an area not part of the trial, warn them and the leaders of the
        trial.

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
            client.send_ooc(f'You have left to an area not part of trial `{self.get_id()}` and '
                            f'thus were automatically removed from the trial.')
            client.send_ooc_others(f'(X) Player {old_displayname} [{client.id}] has left to '
                                   f'an area not part of your trial and thus was automatically '
                                   f'removed it ({area.id}->{client.area.id}).',
                                   pred=lambda c: c in self.get_leaders(), in_hub=area.hub)

            nonplayers = self.get_nonplayer_users_in_areas()
            tid = self.get_id()

            self.remove_player(client)

            if self.is_unmanaged():
                client.send_ooc(f'Your trial `{tid}` was automatically '
                                f'ended as it lost all its players.')
                client.send_ooc_others(f'(X) Trial `{tid}` was automatically '
                                       f'ended as it lost all its players.',
                                       is_zstaff_flex=True, not_to=nonplayers, in_hub=area.hub)
                client.send_ooc_others('The trial you were watching was automatically ended '
                                       'as it lost all its players.',
                                       is_zstaff_flex=False, part_of=nonplayers, in_hub=area.hub)
        else:
            client.send_ooc(f'You have left to an area not part of trial `{self.get_id()}`.')
            client.send_ooc_others(f'(X) Player {old_displayname} [{client.id}] has left to '
                                   f'an area not part of your trial ({area.id}->{client.area.id}).',
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
        ignore_autopass: bool = False,
        ):
        """
        If a non-player entered, warn them and the leaders of the trial.

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
            client.send_ooc(f'You have entered an area part of trial `{self.get_id()}`.')
            client.send_ooc_others(f'(X) Non-player {client.displayname} [{client.id}] has entered '
                                   f'an area part of your trial ({old_area_id}->{area.id}).',
                                   pred=lambda c: c in self.get_leaders())
            if self._require_character and not client.has_participant_character():
                if client.is_staff():
                    client.send_ooc(f'This trial requires you have a character to join. Join this '
                                    f'trial with /trial_join {self.get_id()} after choosing a '
                                    f'character.')
                client.send_ooc_others(f'(X) This trial requires players have a character to join. '
                                       f'Add {client.displayname} to your trial with '
                                       f'/trial_add {client.id} after they choose a character.',
                                       pred=lambda c: c in self.get_leaders())
                self.introduce_user(client)
            elif self.get_autoadd_on_client_enter():
                try:
                    msg = ''
                    self.add_player(client)
                except TrialError.UserHitGameConcurrentLimitError:
                    msg = 'Player is concurrently in too many trials.'
                except TrialError.GameIsFullError:
                    msg = 'The trial is full.'
                if msg:
                    client.send_ooc(f'Unable to automatically add you to the trial: {msg}')
                    client.send_ooc_others(f'(X) Unable to automatically add non-player '
                                           f'{client.displayname} [{client.id}] to your trial: '
                                           f'{msg}', pred=lambda c: c in self.get_leaders())
                else:
                    client.send_ooc(f'You were automatically added to trial `{self.get_id()}`.')
                    client.send_ooc_others(f'(X) Non-player {client.displayname} [{client.id}] '
                                           'was automatically added to your trial.',
                                           pred=lambda c: c in self.get_leaders())

                # Check if client was added to any minigames automatically or not.
                # If so, notifidy leaders
                for minigame in self.get_minigames():
                    name = minigame.get_type_name()
                    if minigame.is_player(client):
                        client.send_ooc(f'You were automatically added to {name} '
                                        f'`{minigame.get_id()}`.')
                        client.send_ooc_others(f'(X) {client.displayname} [{client.id}] was '
                                               f'automatically added to your {name}.',
                                               pred=lambda c: c in minigame.get_leaders())
                    else:
                        client.send_ooc(f'Unable to be automatically added to {name} '
                                        f'`{minigame.get_id()}`.')
                        client.send_ooc_others(f'(X) {client.displayname} [{client.id}] could not '
                                               f'be automatically added to your {name}.',
                                               pred=lambda c: c in minigame.get_leaders())

            else:
                if client.is_staff():
                    client.send_ooc(f'Join this trial with /trial_join {self.get_id()}')
                client.send_ooc_others(f'(X) Add {client.displayname} to your trial with '
                                       f'/trial_add {client.id}',
                                       pred=lambda c: c in self.get_leaders())
                self.introduce_user(client)
        self.manager._check_structure()

    def _on_client_change_character(
        self,
        player: ClientManager.Client,
        old_char_id: Union[int, None] = None,
        new_char_id: Union[int, None] = None
        ):
        """
        It checks if the player is now no longer having a character. If that is
        the case and the trial requires all players have characters, the player is automatically
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

        old_char = player.hub.character_manager.get_character_name(old_char_id)
        if self._require_character and not player.has_participant_character():
            player.send_ooc('You were removed from your trial as it required its players to have '
                            'characters.')
            player.send_ooc_others(f'(X) Player {player.id} changed character from {old_char} to '
                                   f'a non-character and was removed from your trial.',
                                   pred=lambda c: c in self.get_leaders())

            nonplayers = self.get_nonplayer_users_in_areas()
            tid = self.get_id()

            self.remove_player(player)

            if self.is_unmanaged():
                player.send_ooc(f'Your trial `{tid}` was automatically '
                                f'ended as it lost all its players.')
                player.send_ooc_others(f'(X) Trial `{tid}` was automatically '
                                       f'ended as it lost all its players.',
                                       is_zstaff_flex=True, not_to=nonplayers)
                player.send_ooc_others('The trial you were watching was automatically ended '
                                       'as it lost all its players.',
                                       is_zstaff_flex=False, part_of=nonplayers)
        else:
            player.send_ooc_others(f'(X) Player {player.id} changed character from {old_char} '
                                   f'to {player.get_char_name()} in your trial.',
                                   pred=lambda c: c in self.get_leaders())
        self.manager._check_structure()

    def _on_client_destroyed(self, player: ClientManager.Client):
        """
        Remove the player from the trial. If the trial is already unmanaged or
        the player is not in the game, this callback does nothing.

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

        player.send_ooc_others(f'(X) Player {player.displayname} of your trial disconnected. '
                               f'({player.area.id})', pred=lambda c: c in self.get_leaders())
        nonplayers = self.get_nonplayer_users_in_areas()
        tid = self.get_id()

        self.remove_player(player)

        if self.is_unmanaged():
            # player.send_ooc(f'Your trial `{tid}` was automatically '
            #                 f'ended as it lost all its players.')
            player.send_ooc_others(f'(X) Trial `{tid}` was automatically '
                                   f'ended as it lost all its players.',
                                   is_zstaff_flex=True, not_to=nonplayers)
            player.send_ooc_others('The trial you were watching was automatically ended '
                                   'as it lost all its players.',
                                   is_zstaff_flex=False, part_of=nonplayers)

        self.manager._check_structure()

    def _on_client_inbound_rt(self, player: ClientManager.Client, contents: Dict[str, Any]):
        """
        Callback for trial player signaling they have used a splash button.

        If the splash button is "testimony2" and the player is a leader of the trial, the trial
        is automatically ended.

        Parameters
        ----------
        player : ClientManager.Client
            Player that signaled it has used a splash button.
        contents : Dict[str, Any]
            Arguments of the splash packet as indicated in AOProtocol.

        Returns
        -------
        None.

        """

        if contents['name'] == 'testimony2':
            # Trial end button
            if self.is_leader(player):
                # Save leaders and regulars before destruction
                leaders = self.get_leaders()
                regulars = self.get_regulars()
                nonplayers = self.get_nonplayer_users_in_areas()
                self.destroy()

                player.send_ooc('You ended your trial.')
                player.send_ooc_others('The trial you were watching was ended.',
                                       pred=lambda c: c in nonplayers)
                player.send_ooc_others('Your trial was ended.',
                                       pred=lambda c: c in regulars)
                player.send_ooc_others(f'(X) {player.displayname} [{player.id}] ended your trial.',
                                       pred=lambda c: c in leaders)

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
            nonplayer.send_ooc('The trial you were watching was deleted due to an area list load.')
        for player in self.get_players():
            player.send_ooc('Your trial was deleted due to an area list load.')

        self.destroy()

    def _check_structure(self):
        """
        Assert that all invariants specified in the class description are maintained.

        Raises
        ------
        AssertionError
            If any of the invariants are not maintained.

        """

        _id = self.get_id()

        # 1.
        for game in self.get_minigames():
            for player in game.get_players():
                assert player in self.get_players(), (
                    f'For trial {_id}, expected that player {player} of its minigame '
                    f'{game} was a player of the trial, found that was not the case. || {self}'
                    )

        # 2.
        for game in self.get_minigames():
            for area in game.get_areas():
                assert area in self.get_areas(), (
                    f'For trial {_id}, expected that area {area} of its minigame '
                    f'{game} was an area of the trial, found that was not the case. || {self}'
                    )

        # 3.
        for player in self.get_players():
            assert player.id in self._player_to_influence, (
                f'For trial {_id}, expected that player {player} of the trial appeared in the '
                f'player to influence map of the trial {self._player_to_influence}, found that was '
                f'not the case. || {self}'
                )

            assert player.id in self._player_to_focus, (
                f'For trial {_id}, expected that player {player} of the trial appeared in the '
                f'player to focus map of the trial {self._player_to_focus}, found that was '
                f'not the case. || {self}'
                )

        player_ids = {player.id for player in self.get_players()}
        for player_id in self._player_to_influence:
            assert player_id in player_ids, (
                f'For trial {_id}, expected that player with ID {player_id} that appeared '
                f'in the player to influence map of the trial {self._player_to_influence} was '
                f'a player of the trial, found that was not the case. || {self}'
                )

        for player_id in self._player_to_focus:
            assert player_id in player_ids, (
                f'For trial {_id}, expected that player with ID {player_id} that appeared '
                f'in the player to focus map of the trial {self._player_to_focus} was '
                f'a player of the trial, found that was not the case. || {self}'
                )

        # 4.
        for (player_id, influences) in self._player_to_influence.items():
            assert isinstance(influences, tuple) and len(influences) == 3, (
                f'For trial {_id}, expected that the player with ID {player_id} had a '
                f'3-tuple of current influence, min influence and max influence associated '
                f'to it in the player to influence map, found it was {influences} instead. '
                f'|| {self}'
                )

            influence, min_influence, max_influence = self._player_to_influence[player_id]
            all_numbers = [isinstance(value, (int, float)) for value in influences]
            assert all(all_numbers), (
                f'For trial {_id}, expected that the player with ID {player_id} had a '
                f'3-tuple of floats associated to it in the player to influence map, found it '
                f'was {influences} instead. || {self}'
                )

            assert min_influence <= influence <= max_influence, (
                f'For trial {_id}, expected that player with ID {player_id} had an influence '
                f'value between {min_influence} and {max_influence} inclusive, '
                f'found it was {influence} instead. || {self}'
                )

        for (player_id, focuses) in self._player_to_focus.items():
            assert isinstance(focuses, tuple) and len(focuses) == 3, (
                f'For trial {_id}, expected that the player with ID {player_id} had a '
                f'3-tuple of current focus, min focus and max focus associated '
                f'to it in the player to focus map, found it was {focuses} instead. || {self}'
                )

            focus, min_focus, max_focus = self._player_to_focus[player_id]
            all_numbers = [isinstance(value, (int, float)) for value in focuses]
            assert all(all_numbers), (
                f'For trial {_id}, expected that the player with ID {player_id} had a '
                f'3-tuple of floats associated to it in the player to focus map, found it '
                f'was {focuses} instead. || {self}'
                )

            assert min_focus <= focus <= max_focus, (
                f'For trial {self}, expected that player with ID {player_id} had an focus '
                f'value between {min_focus} and {max_focus} inclusive, '
                f'found it was {focus} instead. || {self}'
                )

        # 5.
        super()._check_structure()

    def __str__(self):
        """
        Return a string representation of this trial.

        Returns
        -------
        str
            Representation.

        """

        return (f"Trial::{self.get_id()}:"
                f"{self.get_players()}:{self.get_leaders()}:{self.get_invitations()}"
                f"{self.get_timers()}:"
                f"{self.get_teams()}:"
                f"{self.get_areas()}:"
                f"{self.get_minigames()}")

    def __repr__(self):
        """
        Return a representation of this trial.

        Returns
        -------
        str
            Printable representation.

        """

        return (f'Trial(server, {self.manager.get_id()}, "{self.get_id()}", '
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
                f'areas={self.get_areas()}), '
                f'minigames={self.get_minigames()}, '
                f'unmanaged={self.is_unmanaged()}), '
                f')')

class _TrialManagerTrivialInherited(HubbedGameManager):
    """
    This class should not be instantiated.
    """

    def new_managee(
        self,
        managee_type: Type[_Trial] = None,
        creator: Union[ClientManager.Client, None] = None,
        player_limit: Union[int, None] = None,
        player_concurrent_limit: Union[int, None] = 1,
        require_invitations: bool = False,
        require_players: bool = True,
        require_leaders: bool = False,  # Overriden from parent
        require_character: bool = False,
        team_limit: Union[int, None] = None,
        timer_limit: Union[int, None] = None,
        areas: Set[AreaManager.Area] = None,
        area_concurrent_limit: Union[int, None] = 1,  # Overriden from parent
        autoadd_on_client_enter: bool = False,
        autoadd_on_creation_existing_users: bool = False,
        require_areas: bool = True,
        hub: Union[_Hub, None] = None,
        # new
        autoadd_minigame_on_player_added: bool = False,
        **kwargs: Any,
        ) -> _Trial:
        """
        Create a new trial managed by this manager. Overriden default parameters include:
        * A trial does not require leaders.
        * An area cannot belong to two or more trials at the same time.

        Parameters
        ----------
        creator : ClientManager.Client, optional
            The player who created this trial. If set, they will also be added to the trial.
            Defaults to None.
        player_limit : Union[int, None], optional
            If an int, it is the maximum number of players the trial supports. If None, it
            indicates the trial has no player limit. Defaults to None.
        require_invitations : bool, optional
            If True, users can only be added to the trial if they were previously invited. If
            False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the trial loses all its players, the trial will automatically
            be deleted. If False, no such automatic deletion will happen. Defaults to True.
        require_character : bool, optional
            If False, players without a character will not be allowed to join the trial, and
            players that switch to something other than a character will be automatically
            removed from the trial. If False, no such checks are made. A player without a
            character is considered one where player.has_participant_character() returns False. Defaults
            to False.
        team_limit : Union[int, None], optional
            If an int, it is the maximum number of teams the trial will support. If None, it
            indicates the trial will have no team limit. Defaults to None.
        timer_limit : Union[int, None], optional
            If an int, it is the maximum number of timers the trial will support. If None, it
            indicates the trial will have no timer limit. Defaults to None.
        area_concurrent_limit : Union[int, None], optional
            If an int, it is the maximum number of trials managed by `manager` that any
            area of the created trial may belong to, including the created trial. If None, it
            indicates that this trial does not care about how many other trials managed by
            `manager` each of its areas belongs to. Defaults to 1 (an area may not be a part of
            another trial managed by `manager` while being an area of this trials).
        autoadd_on_client_enter : bool, optional
            If True, nonplayer users that enter an area part of the game will be automatically
            added if permitted by the conditions of the game. If False, no such adding will take
            place. Defaults to False.
        autoadd_on_creation_existing_users : bool
            If the trial will attempt to add nonplayer users who were in an area added
            to the trial on creation. Defaults to False.
        require_areas : bool, optional
            If True, if at any point the trial has no areas left, the game with areas
            will automatically be deleted. If False, no such automatic deletion will happen.
            Defaults to True.
        hub : _Hub, optional
            Hub of the hubbed game. Defaults to None (and converted to the creator's hub if given a
            creator, and None otherwise).
        autoadd_minigame_on_player_added : bool, optional
            If True, nonplayer users that are added to the trial will also be automatically added
            to the minigame if permitted by its conditions. If False, no such adding will take
            place. Defaults to False.

        Returns
        -------
        _Trial
            The created trial.

        Raises
        ------
        TrialError.AreaDisallowsBulletsError
            If `creator` is given and the area of the creator disallows bullets.
        TrialError.ManagerTooManyGamesError
            If the manager is already managing its maximum number of minigames.
        Any error from the created trial's add_player(creator)
            If the trial cannot add `creator` to the trial if given one.

        """

        if managee_type is None:
            managee_type = self.get_managee_type()

        trial = self.unchecked_new_managee(
            managee_type=managee_type,
            creator=creator,
            player_limit=player_limit,
            player_concurrent_limit=player_concurrent_limit,
            require_invitations=require_invitations,
            require_players=require_players,
            require_leaders=require_leaders,
            require_character=require_character,
            team_limit=team_limit,
            timer_limit=timer_limit,
            areas=areas,
            area_concurrent_limit=area_concurrent_limit,
            autoadd_on_client_enter=autoadd_on_client_enter,
            autoadd_on_creation_existing_users=autoadd_on_creation_existing_users,
            require_areas=require_areas,
            hub=hub,
            autoadd_minigame_on_player_added=autoadd_minigame_on_player_added,
            **kwargs,
            )
        self._check_structure()

        return trial

    def get_managee_type(self) -> Type[_Trial]:
        """
        Return the type of the trial that will be constructed by default with a call of
        `new_managee`.

        Returns
        -------
        Type[_Trial]
            Type of the trial.

        """

        return super().get_managee_type()

    def delete_managee(self, managee: _Trial) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a trial managed by this manager, so all its players no longer belong to
        this trial.

        Parameters
        ----------
        managee : _Trial
            The trial to delete.

        Returns
        -------
        Tuple[str, Set[ClientManager.Client]]
            The ID and players of the trial that was deleted.

        Raises
        ------
        TrialError.ManagerDoesNotManageGameError
            If the manager does not manage the target trial.

        """

        game_id, game_players = self.unchecked_delete_managee(managee)
        self._check_structure()
        return game_id, game_players

    def unchecked_delete_managee(
        self,
        managee: _Trial
        ) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a trial managed by this manager, so all its players no longer belong to
        this trial.

        Parameters
        ----------
        managee : _Trial
            The trial to delete.

        Returns
        -------
        Tuple[str, Set[ClientManager.Client]]
            The ID and players of the trial that was deleted.

        Raises
        ------
        TrialError.ManagerDoesNotManageGameError
            If the manager does not manage the target trial.

        """

        try:
            return super().unchecked_delete_managee(managee)
        except HubbedGameError.ManagerDoesNotManageGameError:
            raise TrialError.ManagerDoesNotManageGameError

    def manages_managee(self, game: _Trial):
        """
        Return True if the trial is managed by this manager, False otherwise.

        Parameters
        ----------
        game : _Trial
            The game to check.

        Returns
        -------
        bool
            True if the manager manages this trial, False otherwise.

        """

        return super().manages_managee(game)

    def get_managees(self) -> Set[_Trial]:
        """
        Return (a shallow copy of) the trials this manager manages.

        Returns
        -------
        Set[_Trial]
            Trials this manager manages.

        """

        return super().get_managees()

    def get_managee_by_id(self, managee_id: str) -> _Trial:
        """
        If `managee_id` is the ID of a trial managed by this manager, return that.

        Parameters
        ----------
        managee_id : str
            ID of the trial this manager manages.

        Returns
        -------
        _Trial
            The trial with that ID.

        Raises
        ------
        TrialError.ManagerInvalidGameIDError
            If `game_id` is not the ID of a trial this manager manages.

        """

        try:
            return super().get_managee_by_id(managee_id)
        except HubbedGameError.ManagerInvalidGameIDError:
            raise TrialError.ManagerInvalidGameIDError

    def get_managee_by_numerical_id(self, managee_numerical_id: Union[str, int]) -> _Trial:
        """
        If `managee_numerical_id` is the numerical ID of a trial managed by this manager,
        return the trial.

        Parameters
        ----------
        managee_numerical_id : Union[str, int]
            Numerical ID of the trial this manager manages.

        Returns
        -------
        _Trial
            The trial with that ID.

        Raises
        ------
        TrialError.ManagerInvalidGameIDError:
            If `managee_numerical_id` is not the numerical ID of a trial
            this manager manages.

        """

        try:
            return super().get_managee_by_numerical_id(managee_numerical_id)
        except HubbedGameError.ManagerInvalidGameIDError:
            raise TrialError.ManagerInvalidGameIDError

    def get_managee_limit(self) -> Union[int, None]:
        """
        Return the trial limit of this manager.

        Returns
        -------
        Union[int, None]
            Trial limit.

        """

        return super().get_managee_limit()

    def get_managee_ids(self) -> Set[str]:
        """
        Return (a shallow copy of) the IDs of all trials managed by this manager.

        Returns
        -------
        Set[str]
            The IDs of all managed trials.

        """

        return super().get_managee_ids()

    def get_managee_ids_to_managees(self) -> Dict[str, _Trial]:
        """
        Return a mapping of the IDs of all trials managed by this manager to their
        associated trial.

        Returns
        -------
        Dict[str, _Trial]
            Mapping.
        """

        return super().get_managee_ids_to_managees()

    def get_managee_numerical_ids_to_managees(self) -> Dict[int, _Trial]:
        """
        Return a mapping of the numerical IDs of all trials managed by this manager to
        their associated trial.

        Returns
        -------
        Dict[int, _Trial]
            Mapping.
        """

        return super().get_managee_numerical_ids_to_managees()

    def get_managees_of_user(self, user: ClientManager.Client):
        """
        Return (a shallow copy of) the trials managed by this manager user `user` is a
        player of. If the user is part of no such trial, an empty set is returned.

        Parameters
        ----------
        user : ClientManager.Client
            User whose trials will be returned.

        Returns
        -------
        Set[_Trial]
            Trials the player belongs to.

        """

        return super().get_managees_of_user(user)

    def get_player_to_managees_map(self) -> Dict[ClientManager.Client, Set[_Trial]]:
        """
        Return a mapping of the players part of any trial managed by this manager to the
        trial managed by this manager such players belong to.

        Returns
        -------
        Dict[ClientManager.Client, Set[_Trial]]
            Mapping.
        """

        return super().get_player_to_managees_map()

    def get_users_in_some_managee(self) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) all the users that are part of some trial managed by
        this manager.

        Returns
        -------
        Set[ClientManager.Client]
            Users in some managed trial.

        """

        return super().get_users_in_some_managee()

    def is_managee_creatable(self) -> bool:
        """
        Return whether a new trial can currently be created without creating one.

        Returns
        -------
        bool
            True if a trial can be currently created, False otherwise.
        """

        return super().is_managee_creatable()

    def get_managees_in_area(self, area: AreaManager.Area) -> Set[_Trial]:
        """
        Return (a shallow copy of) all trials managed by this manager that contain
        the given area.

        Parameters
        ----------
        area : AreaManager.Area
            Area that all returned trials must contain.

        Returns
        -------
        Set[_Trial]
            Trials that contain the given area.

        """

        return super().get_managees_in_area(area)

    def find_area_concurrent_limiting_managee(
        self,
        area: AreaManager.Area
        ) -> Union[_Trial, None]:
        """
        For area `area`, find a trial `most_restrictive_game` managed by this manager
        such that, if `area` were to be added to another trial managed by this manager,
        they would violate `most_restrictive_game`'s concurrent area membership limit.
        If no such trial exists (or the area is not an area of any trial
        managed by this  manager), return None.
        If multiple such trials exist, any one of them may be returned.

        Parameters
        ----------
        area : AreaManager.Area
            Area to test.

        Returns
        -------
        Union[_Trial, None]
            Limiting trial as previously described if it exists, None otherwise.

        """

        return super().find_area_concurrent_limiting_managee(area)

    def get_areas_to_managees_map(self) -> Dict[ClientManager.Client, Set[_Trial]]:
        """
        Return a mapping of the areas part of any trial managed by this manager to the
        trial managed by this manager such players belong to.

        Returns
        -------
        Dict[ClientManager.Client, Set[_Trial]]
            Mapping.
        """

        return super().get_areas_to_managees_map()

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
        ) -> Union[_Trial, None]:
        """
        For user `user`, find a trial `most_restrictive_game` managed by this manager such
        that, if `user` were to join another trial managed by this manager, they would
        violate `most_restrictive_game`'s concurrent player membership limit.
        If no such trial exists (or the player is not member of any trial
        managed by this manager), return None.
        If multiple such trials exist, any one of them may be returned.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Returns
        -------
        Union[_Trial, None]
            Limiting trial as previously described if it exists, None otherwise.

        """

        return super().find_player_concurrent_limiting_managee(user)


class TrialManager(_TrialManagerTrivialInherited):
    """
    A trial manager is a hubbed game manager with dedicated trial management functions.

    Attributes
    ----------
    server : TsuserverDR
        Server the trial manager belongs to.

    """

    # Invariants
    # ----------
    # 1. The invariants of the parent class are maintained.

    def __init__(
        self,
        server: TsuserverDR,
        managee_limit: Union[int, None] = None,
        default_managee_type: Type[_Trial] = None,
        ):
        """
        Create a trial manager object.

        Parameters
        ----------
        server : TsuserverDR
            The server this trial manager belongs to.
        managee_limit : int, optional
            The maximum number of trial this manager can handle. Defaults to None
            (no limit).
        default_managee_type : Type[_Trial], optional
            The default type of trial this manager will create. Defaults to None (and then
            converted to _Trial).

        """

        if default_managee_type is None:
            default_managee_type = _Trial

        super().__init__(
            server,
            managee_limit=managee_limit,
            default_managee_type=default_managee_type
        )

    def unchecked_new_managee(
        self,
        managee_type: Type[_Trial] = None,
        creator: Union[ClientManager.Client, None] = None,
        player_limit: Union[int, None] = None,
        player_concurrent_limit: Union[int, None] = 1,
        require_invitations: bool = False,
        require_players: bool = True,
        require_leaders: bool = False,  # Overriden from parent
        require_character: bool = False,
        team_limit: Union[int, None] = None,
        timer_limit: Union[int, None] = None,
        areas: Set[AreaManager.Area] = None,
        area_concurrent_limit: Union[int, None] = 1,  # Overriden from parent
        autoadd_on_client_enter: bool = False,
        autoadd_on_creation_existing_users: bool = False,
        require_areas: bool = True,
        hub: Union[_Hub, None] = None,
        # new
        autoadd_minigame_on_player_added: bool = False,
        **kwargs: Any,
        ) -> _Trial:
        """
        Create a new trial managed by this manager. Overriden default parameters include:
        * A trial does not require leaders.
        * An area cannot belong to two or more trials at the same time.

        This method does not assert structural integrity.

        Parameters
        ----------
        creator : ClientManager.Client, optional
            The player who created this trial. If set, they will also be added to the trial.
            Defaults to None.
        player_limit : Union[int, None], optional
            If an int, it is the maximum number of players the trial supports. If None, it
            indicates the trial has no player limit. Defaults to None.
        require_invitations : bool, optional
            If True, users can only be added to the trial if they were previously invited. If
            False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the trial loses all its players, the trial will automatically
            be deleted. If False, no such automatic deletion will happen. Defaults to True.
        require_character : bool, optional
            If False, players without a character will not be allowed to join the trial, and
            players that switch to something other than a character will be automatically
            removed from the trial. If False, no such checks are made. A player without a
            character is considered one where player.has_participant_character() returns False. Defaults
            to False.
        team_limit : Union[int, None], optional
            If an int, it is the maximum number of teams the trial will support. If None, it
            indicates the trial will have no team limit. Defaults to None.
        timer_limit : Union[int, None], optional
            If an int, it is the maximum number of timers the trial will support. If None, it
            indicates the trial will have no timer limit. Defaults to None.
        area_concurrent_limit : Union[int, None], optional
            If an int, it is the maximum number of trials managed by `manager` that any
            area of the created trial may belong to, including the created trial. If None, it
            indicates that this trial does not care about how many other trials managed by
            `manager` each of its areas belongs to. Defaults to 1 (an area may not be a part of
            another trial managed by `manager` while being an area of this trials).
        autoadd_on_client_enter : bool, optional
            If True, nonplayer users that enter an area part of the game will be automatically
            added if permitted by the conditions of the game. If False, no such adding will take
            place. Defaults to False.
        autoadd_on_creation_existing_users : bool
            If the trial will attempt to add nonplayer users who were in an area added
            to the trial on creation. Defaults to False.
        require_areas : bool, optional
            If True, if at any point the trial has no areas left, the game with areas
            will automatically be deleted. If False, no such automatic deletion will happen.
            Defaults to True.
        hub : _Hub, optional
            Hub of the hubbed game. Defaults to None (and converted to the creator's hub if given a
            creator, and None otherwise).
        autoadd_minigame_on_player_added : bool, optional
            If True, nonplayer users that are added to the trial will also be automatically added
            to the minigame if permitted by its conditions. If False, no such adding will take
            place. Defaults to False.

        Returns
        -------
        _Trial
            The created trial.

        Raises
        ------
        TrialError.AreaDisallowsBulletsError
            If `creator` is given and the area of the creator disallows bullets.
        TrialError.ManagerTooManyGamesError
            If the manager is already managing its maximum number of minigames.
        Any error from the created trial's add_player(creator)
            If the trial cannot add `creator` to the trial if given one.

        """

        if managee_type is None:
            managee_type = self.get_managee_type()

        try:
            trial: _Trial = super().unchecked_new_managee(
                managee_type=managee_type,
                creator=creator,
                player_limit=player_limit,
                player_concurrent_limit=player_concurrent_limit,
                require_invitations=require_invitations,
                require_players=require_players,
                require_leaders=require_leaders,
                require_character=require_character,
                team_limit=team_limit,
                timer_limit=timer_limit,
                areas=areas,
                area_concurrent_limit=area_concurrent_limit,
                autoadd_on_client_enter=autoadd_on_client_enter,
                autoadd_on_creation_existing_users=autoadd_on_creation_existing_users,
                require_areas=require_areas,
                hub=hub,
                # kwargs
                autoadd_minigame_on_player_added=autoadd_minigame_on_player_added,
                **kwargs,
                )
        except HubbedGameError.ManagerTooManyGamesError:
            raise TrialError.ManagerTooManyGamesError

        # Manually give packets to nonplayers
        for nonplayer in trial.get_nonplayer_users_in_areas():
            trial.introduce_user(nonplayer)

        return trial

    def get_managee_of_user(self, user: ClientManager.Client) -> _Trial:
        """
        Get the trial the user is in.

        Parameters
        ----------
        user : ClientManager.Client
            User to check.

        Raises
        ------
        TrialError.UserNotPlayerError
            If the user is not in a trial managed by this manager.

        Returns
        -------
        TrialManager.Trial
            Trial of the user.

        """

        games = self.get_managees_of_user(user)
        trials = {game for game in games if isinstance(game, _Trial)}
        if not trials:
            raise TrialError.UserNotPlayerError
        if len(trials) > 1:
            raise RuntimeError(trials)
        return next(iter(trials))

    def get_available_managee_id(self):
        """
        Get a trial ID that no other trial managed by this manager has.

        Returns
        -------
        str
            A unique trial ID.

        Raises
        ------
        TrialError.ManagerTooManyGamesError
            If the manager is already managing its maximum number of games.

        """

        game_number = 0
        game_limit = self.get_managee_limit()
        while game_limit is None or game_number < game_limit:
            new_game_id = "trial{}".format(game_number)
            if new_game_id not in self.get_managee_ids():
                return new_game_id
            game_number += 1
        raise TrialError.ManagerTooManyGamesError

    def _check_structure(self):
        """
        Assert that all invariants specified in the class description are maintained.

        Raises
        ------
        AssertionError
            If any of the invariants are not maintained.

        """

        super()._check_structure()

    def __repr__(self):
        """
        Return a representation of this trial manager.

        Returns
        -------
        str
            Printable representation.

        """

        return (f"TrialManager(server, managee_limit={self.get_managee_limit()}, "
                f"default_managee_type={self.get_managee_type()}, "
                f"|| "
                f"_id_to_managee={self.get_managee_ids_to_managees()}, "
                f"_user_to_managees={self.get_player_to_managees_map()}, "
                f"_area_to_managees={self.get_areas_to_managees_map()}, "
                f"id={self.get_id()}), "
                f')')
