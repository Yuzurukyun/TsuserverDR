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
Module that contains the hub manager and hub modules.

"""

from __future__ import annotations

import typing

from server.area_manager import AreaManager
from server.background_manager import BackgroundManager
from server.character_manager import CharacterManager
from server.constants import Constants
from server.exceptions import HubError, GameWithAreasError
from server.gamewithareas_manager import _GameWithAreas, GameWithAreasManager
from server.music_manager import MusicManager

from typing import Callable, Dict, List, Set, Any, Tuple, Type, Union

from server.trial_manager import TrialManager
from server.zone_manager import ZoneManager

if typing.TYPE_CHECKING:
    from server.client_manager import ClientManager
    from server.game_manager import _Team
    from server.timer_manager import Timer
    from server.tsuserver import TsuserverDR

class _HubTrivialInherited(_GameWithAreas):
    """
    This class should not be instantiated.
    """

    def get_id(self) -> str:
        """
        Return the ID of this hub.

        Returns
        -------
        str
            The ID.

        """

        return super().get_id()

    def get_player_limit(self) -> Union[int, None]:
        """
        Return the player membership limit of this hub.

        Returns
        -------
        Union[int, None]
            The player membership limit.

        """

        return super().get_player_limit()

    def get_player_concurrent_limit(self) -> Union[int, None]:
        """
        Return the concurrent player membership limit of this hub.

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
        Return (a shallow copy of) the set of players of this hub that satisfy a
        condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all players returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) players of this hub.

        """

        return super().get_players(cond=cond)

    def is_player(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is a player of the hub.

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
        Make a user a player of the hub. By default this player will not be a leader,
        unless the hub has no leaders and it requires a leader.
        It will also subscribe the hub to the player so it can listen to its updates.

        Newly added players will be ordered to switch to a 'hub' variant.

        Parameters
        ----------
        user : ClientManager.Client
            User to add to the hub. They must be in an area part of the hub.

        Raises
        ------
        HubError.GameIsUnmanagedError
            If the hub was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubError.UserNotInAreaError
            If the user is not in an area part of the hub.
        HubError.UserHasNoCharacterError
            If the user has no character but the hub requires that all players have
            characters.
        HubError.UserNotInvitedError
            If the hub requires players be invited to be added and the user is not
            invited.
        HubError.UserAlreadyPlayerError
            If the user to add is already a user of the hub.
        HubError.UserHitGameConcurrentLimitError
            If the player has reached the concurrent player membership of any of the hub
            managed by the manager of this hub, or by virtue of joining this
            hub they would violate this hub's concurrent player membership limit.
        HubError.GameIsFullError
            If the hub reached its player limit.

        """

        self.unchecked_add_player(user)
        self.manager._check_structure()

    def remove_player(self, user: ClientManager.Client):
        """
        Make a user be no longer a player of this hub. If they were part of a team
        managed by this hub, they will also be removed from said team. It will also
        unsubscribe the hub from the player so it will no longer listen to its updates.

        If the hub required that there it always had players and by calling this method
        the hub had no more players, the hub will automatically be scheduled
        for deletion.

        Parameters
        ----------
        user : ClientManager.Client
            User to remove.

        Raises
        ------
        HubError.GameIsUnmanagedError
            If the hub was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubError.UserNotPlayerError
            If the user to remove is already not a player of this hub.

        """

        self.unchecked_remove_player(user)
        self.manager._check_structure()

    def requires_players(self) -> bool:
        """
        Return whether the hub requires players at all times.

        Returns
        -------
        bool
            Whether the hub requires players at all times.
        """

        return super().requires_players()

    def get_invitations(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
        ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of invited users of this hub that satisfy a
        condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all invited users returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) invited users of this hub.

        """

        return super().get_invitations(cond=cond)

    def is_invited(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is invited to the hub.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Raises
        ------
        HubError.UserAlreadyPlayerError
            If the user is a player of this hub.

        Returns
        -------
        bool
            True if the user is invited, False otherwise.

        """

        try:
            return super().is_invited(user)
        except GameWithAreasError.UserAlreadyPlayerError:
            raise HubError.UserAlreadyPlayerError

    def add_invitation(self, user: ClientManager.Client):
        """
        Mark a user as invited to this hub.

        Parameters
        ----------
        user : ClientManager.Client
            User to invite to the hub.

        Raises
        ------
        HubError.GameIsUnmanagedError
            If the hub was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubError.GameDoesNotTakeInvitationsError
            If the hub does not require users be invited to the hub.
        HubError.UserAlreadyInvitedError
            If the player to invite is already invited to the hub.
        HubError.UserAlreadyPlayerError
            If the player to invite is already a player of the hub.

        """

        self.unchecked_add_invitation(user)
        self.manager._check_structure()

    def unchecked_add_invitation(self, user: ClientManager.Client):
        """
        Mark a user as invited to this hub.

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to invite to the hub.

        Raises
        ------
        HubError.GameIsUnmanagedError
            If the hub was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubError.GameDoesNotTakeInvitationsError
            If the hub does not require users be invited to the hub.
        HubError.UserAlreadyInvitedError
            If the player to invite is already invited to the hub.
        HubError.UserAlreadyPlayerError
            If the player to invite is already a player of the hub.

        """

        try:
            super().unchecked_add_invitation(user)
        except GameWithAreasError.GameIsUnmanagedError:
            raise HubError.GameIsUnmanagedError
        except GameWithAreasError.GameDoesNotTakeInvitationsError:
            raise HubError.GameDoesNotTakeInvitationsError
        except GameWithAreasError.UserAlreadyInvitedError:
            raise HubError.UserAlreadyInvitedError
        except GameWithAreasError.UserAlreadyPlayerError:
            raise HubError.UserAlreadyPlayerError

    def remove_invitation(self, user: ClientManager.Client):
        """
        Mark a user as no longer invited to this hub (uninvite).

        Parameters
        ----------
        user : ClientManager.Client
            User to uninvite.

        Raises
        ------
        HubError.GameIsUnmanagedError
            If the hub was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubError.GameDoesNotTakeInvitationsError
            If the hub does not require users be invited to the hub.
        HubError.UserNotInvitedError
            If the user to uninvite is already not invited to this hub.

        """

        self.unchecked_remove_invitation(user)
        self.manager._check_structure()

    def unchecked_remove_invitation(self, user: ClientManager.Client):
        """
        Mark a user as no longer invited to this hub (uninvite).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to uninvite.

        Raises
        ------
        HubError.GameIsUnmanagedError
            If the hub was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubError.GameDoesNotTakeInvitationsError
            If the hub does not require users be invited to the hub.
        HubError.UserNotInvitedError
            If the user to uninvite is already not invited to this hub.

        """

        try:
            super().unchecked_remove_invitation(user)
        except GameWithAreasError.GameIsUnmanagedError:
            raise HubError.GameIsUnmanagedError
        except GameWithAreasError.GameDoesNotTakeInvitationsError:
            raise HubError.GameDoesNotTakeInvitationsError
        except GameWithAreasError.UserNotInvitedError:
            raise HubError.UserNotInvitedError

    def requires_invitations(self):
        """
        Return True if the hub requires players be invited before being allowed to join
        the hub, False otherwise.

        Returns
        -------
        bool
            True if the hub requires players be invited before being allowed to join
            the hub, False otherwise.
        """

        return super().requires_invitations()

    def get_leaders(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
        ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of leaders of this hub that satisfy a condition
        if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all leaders returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) leaders of this hub.

        """

        return super().get_leaders(cond=cond)

    def get_regulars(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
        ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of players of this hub that are regulars and
        satisfy a condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all regulars returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) regulars of this hub.

        """

        return super().get_regulars(cond=cond)

    def is_leader(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is a leader of the hub.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Raises
        ------
        HubError.UserNotPlayerError
            If the player to test is not a player of this hub.

        Returns
        -------
        bool
            True if the player is a user, False otherwise.

        """

        try:
            return super().is_leader(user)
        except GameWithAreasError.UserNotPlayerError:
            raise HubError.UserNotPlayerError

    def add_leader(self, user: ClientManager.Client):
        """
        Set a user as leader of this hub (promote to leader).

        Parameters
        ----------
        user : ClientManager.Client
            Player to promote to leader.

        Raises
        ------
        HubError.GameIsUnmanagedError
            If the hub was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubError.UserNotPlayerError
            If the player to promote is not a player of this hub.
        HubError.UserAlreadyLeaderError
            If the player to promote is already a leader of this hub.

        """

        self.unchecked_add_leader(user)
        self.manager._check_structure()

    def unchecked_add_leader(self, user: ClientManager.Client):
        """
        Set a user as leader of this hub (promote to leader).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            Player to promote to leader.

        Raises
        ------
        HubError.GameIsUnmanagedError
            If the hub was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubError.UserNotPlayerError
            If the player to promote is not a player of this hub.
        HubError.UserAlreadyLeaderError
            If the player to promote is already a leader of this hub.

        """

        try:
            super().unchecked_add_leader(user)
        except GameWithAreasError.GameIsUnmanagedError:
            raise HubError.GameIsUnmanagedError
        except GameWithAreasError.UserNotPlayerError:
            raise HubError.UserNotPlayerError
        except GameWithAreasError.UserAlreadyLeaderError:
            raise HubError.UserAlreadyLeaderError

    def remove_leader(self, user: ClientManager.Client):
        """
        Make a user no longer leader of this hub (demote).

        Parameters
        ----------
        user : ClientManager.Client
            User to demote.

        Raises
        ------
        HubError.GameIsUnmanagedError
            If the hub was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubError.UserNotPlayerError
            If the player to demote is not a player of this hub.
        HubError.UserNotLeaderError
            If the player to demote is already not a leader of this hub.

        """

        self.unchecked_remove_leader(user)
        self.manager._check_structure()

    def unchecked_remove_leader(self, user: ClientManager.Client):
        """
        Make a user no longer leader of this hub (demote).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to demote.

        Raises
        ------
        HubError.GameIsUnmanagedError
            If the hub was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubError.UserNotPlayerError
            If the player to demote is not a player of this hub.
        HubError.UserNotLeaderError
            If the player to demote is already not a leader of this hub.

        """

        if self.is_unmanaged():
            raise HubError.GameIsUnmanagedError

        try:
            super().unchecked_remove_leader(user)
        except GameWithAreasError.GameIsUnmanagedError:
            raise HubError.GameIsUnmanagedError
        except GameWithAreasError.UserNotPlayerError:
            raise HubError.UserNotPlayerError
        except GameWithAreasError.UserNotLeaderError:
            raise HubError.UserNotLeaderError

    def has_ever_had_players(self) -> bool:
        """
        Return True if a player has ever been added to this hub, False otherwise.

        Returns
        -------
        bool
            True if the hub has ever had a player added, False otherwise.

        """

        return super().has_ever_had_players()

    def requires_leaders(self) -> bool:
        """
        Return whether the hub requires leaders at all times.

        Returns
        -------
        bool
            Whether the hub requires leaders at all times.
        """

        return super().requires_leaders()

    def has_ever_had_players(self):
        """
        Return True if a player has ever been added to this hub, False otherwise.

        Returns
        -------
        bool
            True if the hub has ever had a player added, False otherwise.

        """

        return super().has_ever_had_players()

    def requires_characters(self) -> bool:
        """
        Return whether the hub requires players have a character at all times.

        Returns
        -------
        bool
            Whether the hub requires players have a character at all times.
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
        Create a new timer managed by this hub with given parameters.

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
            If True, the hub will automatically delete the timer once it is terminated
            by it ticking out or manual termination. If False, no such automatic deletion will take
            place. Defaults to True.

        Returns
        -------
        Timer
            The created timer.

        Raises
        ------
        HubError.GameIsUnmanagedError
            If the hub was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubError.GameTooManyTimersError
            If the hub is already managing its maximum number of timers.

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
        Create a new timer managed by this hub with given parameters.

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
            If True, the hub will automatically delete the timer once it is terminated
            by it ticking out or manual termination. If False, no such automatic deletion will take
            place. Defaults to True.

        Returns
        -------
        Timer
            The created timer.

        Raises
        ------
        HubError.GameIsUnmanagedError
            If the hub was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubError.GameTooManyTimersError
            If the hub is already managing its maximum number of timers.

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
            raise HubError.GameIsUnmanagedError
        except GameWithAreasError.GameTooManyTimersError:
            raise HubError.GameTooManyTimersError

    def delete_timer(self, timer: Timer) -> str:
        """
        Delete a timer managed by this hub, terminating it first if needed.

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
        HubError.GameIsUnmanagedError
            If the hub was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubError.GameDoesNotManageTimerError
            If the hub does not manage the target timer.

        """

        timer_id = self.unchecked_delete_timer(timer)
        self.manager._check_structure()
        return timer_id

    def unchecked_delete_timer(self, timer: Timer) -> str:
        """
        Delete a timer managed by this hub, terminating it first if needed.

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
        HubError.GameIsUnmanagedError
            If the hub was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubError.GameDoesNotManageTimerError
            If the hub does not manage the target timer.

        """

        try:
            return super().unchecked_delete_timer(timer)
        except GameWithAreasError.GameIsUnmanagedError:
            raise HubError.GameIsUnmanagedError
        except GameWithAreasError.GameDoesNotManageTimerError:
            raise HubError.GameDoesNotManageTimerError

    def get_timers(self) -> Set[Timer]:
        """
        Return (a shallow copy of) the timers this hub manages.

        Returns
        -------
        Set[Timer]
            Timers this hub manages.

        """

        return super().get_timers()

    def get_timer_by_id(self, timer_id: str) -> Timer:
        """
        If `timer_tag` is the ID of a timer managed by this hub, return that timer.

        Parameters
        ----------
        timer_id: str
            ID of timer this hub manages.

        Returns
        -------
        Timer
            The timer whose ID matches the given ID.

        Raises
        ------
        HubError.GameInvalidTimerIDError:
            If `timer_tag` is a str and it is not the ID of a timer this hub manages.

        """

        try:
            return super().get_timer_by_id(timer_id)
        except GameWithAreasError.GameInvalidTimerIDError:
            raise HubError.GameInvalidTimerIDError

    def get_timer_limit(self) -> Union[int, None]:
        """
        Return the timer limit of this hub.

        Returns
        -------
        Union[int, None]
            Timer limit.

        """

        return super().get_timer_limit()

    def get_timer_ids(self) -> Set[str]:
        """
        Return (a shallow copy of) the IDs of all timers managed by this hub.

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
        Create a new team managed by this hub.

        Parameters
        ----------
        team_type : _Team
            Class of team that will be produced. Defaults to None (and converted to the
            default team created by games, namely, _Team).
        creator : ClientManager.Client, optional
            The player who created this team. If set, they will also be added to the team if
            possible. The creator must be a player of this hub. Defaults to None.
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
        HubError.GameIsUnmanagedError
            If the hub was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubError.GameTooManyTeamsError
            If the hub is already managing its maximum number of teams.
        HubError.UserInAnotherTeamError
            If `creator` is not None and already part of a team managed by this hub.

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
        Create a new team managed by this hub.

        This method does not assert structural integrity.

        Parameters
        ----------
        team_type : _Team
            Class of team that will be produced. Defaults to None (and converted to the
            default team created by games, namely, _Team).
        creator : ClientManager.Client, optional
            The player who created this team. If set, they will also be added to the team if
            possible. The creator must be a player of this hub. Defaults to None.
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
        HubError.GameIsUnmanagedError
            If the hub was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubError.GameTooManyTeamsError
            If the hub is already managing its maximum number of teams.
        HubError.UserInAnotherTeamError
            If `creator` is not None and already part of a team managed by this hub.

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
            raise HubError.GameIsUnmanagedError
        except GameWithAreasError.GameTooManyTeamsError:
            raise HubError.GameTooManyTeamsError
        except GameWithAreasError.UserInAnotherTeamError:
            raise HubError.UserInAnotherTeamError

    def delete_team(self, team: _Team) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a team managed by this hub.

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
        HubError.GameIsUnmanagedError
            If the hub was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubError.GameDoesNotManageTeamError
            If the hub does not manage the target team.

        """

        team_id, players = self.unchecked_delete_team(team)
        self.manager._check_structure()
        return team_id, players

    def unchecked_delete_team(self, team: _Team) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a team managed by this hub.

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
        HubError.GameIsUnmanagedError
            If the hub was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubError.GameDoesNotManageTeamError
            If the hub does not manage the target team.

        """

        try:
            return super().unchecked_delete_team(team)
        except GameWithAreasError.GameIsUnmanagedError:
            raise HubError.GameIsUnmanagedError
        except GameWithAreasError.GameDoesNotManageTeamError:
            raise HubError.GameDoesNotManageTeamError

    def manages_team(self, team: _Team) -> bool:
        """
        Return True if the team is managed by this hub, False otherwise.

        Parameters
        ----------
        team : _Team
            The team to check.

        Returns
        -------
        bool
            True if the hub manages this team, False otherwise.

        """

        return super().manages_team(team)

    def get_teams(self) -> Set[_Team]:
        """
        Return (a shallow copy of) the teams this hub manages.

        Returns
        -------
        Set[_Team]
            Teams this hub manages.

        """

        return super().get_teams()

    def get_team_by_id(self, team_id: str) -> _Team:
        """
        If `team_id` is the ID of a team managed by this hub, return the team.

        Parameters
        ----------
        team_id : str
            ID of the team this hub manages.

        Returns
        -------
        _Team
            The team that matches the given ID.

        Raises
        ------
        HubError.GameInvalidTeamIDError:
            If `team_id` is not the ID of a team this hub manages.

        """

        try:
            return super().get_team_by_id(team_id)
        except GameWithAreasError.GameInvalidTeamIDError:
            raise HubError.GameInvalidTeamIDError

    def get_team_limit(self) -> Union[int, None]:
        """
        Return the team limit of this hub.

        Returns
        -------
        Union[int, None]
            Team limit.

        """

        return super().get_team_limit()

    def get_team_ids(self) -> Set[str]:
        """
        Return (a shallow copy of) the IDs of all teams managed by this hub.

        Returns
        -------
        Set[str]
            The IDs of all managed teams.

        """

        return super().get_team_ids()

    def get_teams_of_user(self, user: ClientManager.Client) -> Set[_Team]:
        """
        Return (a shallow copy of) the teams managed by this hub user `user` is a player
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
        hub.

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
        HubError.GameTooManyTeamsError
            If the hub is already managing its maximum number of teams.

        """

        try:
            return super().get_available_team_id()
        except GameWithAreasError.GameTooManyTeamsError:
            raise HubError.GameTooManyTeamsError

    def get_autoadd_on_client_enter(self) -> bool:
        """
        Return True if the hub will always attempt to add nonplayer users who enter an
        area part of the hub, False otherwise.

        Returns
        -------
        bool
            True if the hub will always attempt to add nonplayer users who enter an area
            part of the hub, False otherwise.
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
        Add an area to this hub's set of areas.

        Parameters
        ----------
        area : AreaManager.Area
            Area to add.

        Raises
        ------
        HubError.GameIsUnmanagedError
            If the hub was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubError.AreaDisallowsBulletsError
            If the area to add disallows bullets.
        HubError.AreaAlreadyInGameError
            If the area is already part of the hub.
        HubError.AreaHitGameConcurrentLimitError.
            If `area` has reached the concurrent area membership limit of any of the games with
            areas it belongs to managed by this manager, or by virtue of adding this area it will
            violate this hub's concurrent area membership limit.

        """

        self.unchecked_add_area(area)
        self.manager._check_structure()

    def remove_area(self, area: AreaManager.Area):
        """
        Remove an area from this hub's set of areas.
        If the area is already a part of the hub, do nothing.
        If any player of the hub is in this area, they are removed from the
        hub.
        If the hub has no areas remaining, it will be automatically destroyed.

        Parameters
        ----------
        area : AreaManager.Area
            Area to remove.

        Raises
        ------
        HubError.GameIsUnmanagedError
            If the hub was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubError.AreaNotInGameError
            If the area is already not part of the hub.

        """

        self.unchecked_remove_area(area)
        self.manager._check_structure()

    def unchecked_remove_area(self, area: AreaManager.Area):
        """
        Remove an area from this hub's set of areas.
        If the area is already a part of the hub, do nothing.
        If any player of the hub is in this area, they are removed from the
        hub.
        If the hub has no areas remaining, it will be automatically destroyed.

        This method does not assert structural integrity.

        Parameters
        ----------
        area : AreaManager.Area
            Area to remove.

        Raises
        ------
        HubError.GameIsUnmanagedError
            If the hub was scheduled for deletion and thus does not accept any mutator
            public method calls.
        HubError.AreaNotInGameError
            If the area is already not part of the hub.

        """

        try:
            super().unchecked_remove_area(area)
        except GameWithAreasError.GameIsUnmanagedError:
            raise HubError.GameIsUnmanagedError
        except GameWithAreasError.AreaNotInGameError:
            raise HubError.AreaNotInGameError

    def has_area(self, area: AreaManager.Area) -> bool:
        """
        If the area is part of this hub's set of areas, return True; otherwise, return
        False.

        Parameters
        ----------
        area : AreaManager.Area
            Area to check.

        Returns
        -------
        bool
            True if the area is part of the hub's set of areas, False otherwise.

        """

        return super().has_area(area)

    def get_areas(self) -> Set[AreaManager.Area]:
        """
        Return (a shallow copy of) the set of areas of this hub.

        Returns
        -------
        Set[AreaManager.Area]
            Set of areas of the hub.

        """

        return super().get_areas()

    def get_area_concurrent_limit(self) -> Union[int, None]:
        """
        Return the concurrent area membership limit of this hub.

        Returns
        -------
        Union[int, None]
            The concurrent area membership limit.

        """

        return super().get_area_concurrent_limit()

    def get_users_in_areas(self) -> Set[ClientManager.Client]:
        """
        Return all users in areas part of the hub, even those that are not players of
        the hub.

        Returns
        -------
        Set[ClientManager.Client]
            All users in areas part of the hub.

        """

        return super().get_users_in_areas()

    def get_nonleader_users_in_areas(self) -> Set[ClientManager.Client]:
        """
        Return all users in areas part of the hub, even those that are not players of
        the hub, such that they are not leaders of the hub.

        Returns
        -------
        Set[ClientManager.Client]
            All users in areas part of the hub that are not leaders of the hub.

        """

        return super().get_nonleader_users_in_areas()

    def get_nonplayer_users_in_areas(self) -> Set[ClientManager.Client]:
        """
        Return all users in areas part of the hub that are not players of the
        hub.

        Returns
        -------
        Set[ClientManager.Client]
            All users in areas part of the hub that are not players of the hub.

        """

        return super().get_nonplayer_users_in_areas()

    def is_unmanaged(self):
        """
        Return True if this hub is unmanaged, False otherwise.

        Returns
        -------
        bool
            True if unmanaged, False otherwise.

        """

        return super().is_unmanaged()

    def destroy(self):
        """
        Mark this hub as destroyed and notify its manager so that it is deleted.
        If the hub is already destroyed, this function does nothing.
        A hub marked for destruction will delete all of its timers, teams, remove all
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
        Default callback for hub player signaling it wants to check if sending an IC
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
        Default callback for hub player signaling it has sent an IC message.
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
        Default callback for hub area signaling a client in the area sent an IC message.
        Unlike the ClientManager.Client callback for send_ic_check, this one is triggered
        regardless of whether the sender is part of the hub or not. This is useful for
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
        Default callback for hub area signaling it was destroyed.

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

class _Hub(_HubTrivialInherited):
    """
    A hub is a game with areas that hosts asset managers.

    Attributes
    ----------
    server : TsuserverDR
        Server the hub belongs to.
    manager : HubManager
        Manager for this hub.
    listener : Listener
        Standard listener of the hub.

    Callback Methods
    ----------------
    _on_area_client_left_final
        Method to perform once a client left an area of the hub.
    _on_area_client_entered_final
        Method to perform once a client entered an area of the hub.
    _on_area_destroyed
        Method to perform once an area of the hub is marked for destruction.
    _on_client_inbound_ms_check
        Method to perform once a player of the hub wants to send an IC message.
    _on_client_inbound_ms_final
        Method to perform once a player of the hub sends an IC message.
    _on_client_change_character
        Method to perform once a player of the hub has changed character.
    _on_client_destroyed
        Method to perform once a player of the hub is destroyed.

    """

    # Invariants
    # ----------
    # 1. The invariants from the parent class GameWithArea are satisfied.


    def __init__(
        self,
        server: TsuserverDR,
        manager: HubManager,
        hub_id: str,
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
        Create a new hub. A hub should not be fully initialized anywhere else other than
        some manager code, as otherwise the manager will not recognize the hub.

        Parameters
        ----------
        server : TsuserverDR
            Server the hub belongs to.
        manager : HubManager
            Manager for this hub.
        hub_id : str
            Identifier of the hub.
        player_limit : Union[int, None], optional
            If an int, it is the maximum number of players the hub supports. If None, it
            indicates the hub has no player limit. Defaults to None.
        player_concurrent_limit : Union[int, None], optional
            If an int, it is the maximum number of hubs managed by `manager` that any
            player of this hub may belong to, including this hub. If None, it indicates
            that this hub does not care about how many other hubs managed by `manager` each
            of its players belongs to. Defaults to None.
        require_invitation : bool, optional
            If True, players can only be added to the hub if they were previously invited. If
            False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the hub has no players left, the hub will
            automatically be deleted. If False, no such automatic deletion will happen.
            Defaults to True.
        require_leaders : bool, optional
            If True, if at any point the hub has no leaders left, the hub will choose a
            leader among any remaining players left; if no players are left, the next player
            added will be made leader. If False, no such automatic assignment will happen.
            Defaults to True.
        require_character : bool, optional
            If False, players without a character will not be allowed to join the hub, and
            players that switch to something other than a character will be automatically
            removed from the hub. If False, no such checks are made. A player without a
            character is considered one where player.has_character() returns False. Defaults
            to False.
        team_limit : Union[int, None], optional
            If an int, it is the maximum number of teams the hub supports. If None, it
            indicates the hub has no team limit. Defaults to None.
        timer_limit : Union[int, None], optional
            If an int, it is the maximum number of timers the hub supports. If None, it
            indicates the hub has no timer limit. Defaults to None.
        area_concurrent_limit : Union[int, None], optional
            If an int, it is the maximum number of hubs managed by `manager` that any
            area of this hub may belong to, including this hub. If None, it indicates
            that this hub does not care about how many other hubs managed by
            `manager` each of its areas belongs to. Defaults to 1 (an area may not be a part of
            another hub managed by `manager` while being an area of this hub).
        autoadd_on_client_enter : bool, optional
            If True, nonplayer users that enter an area part of the hub will be automatically
            added if permitted by the conditions of the hub. If False, no such adding will take
            place. Defaults to False.
        """

        super().__init__(
            server,
            manager,
            hub_id,
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
        )

        self.background_manager = BackgroundManager(server, hub=self)
        self.load_backgrounds()

        self.character_manager = CharacterManager(server, hub=self)
        self.load_characters()

        self.music_manager = MusicManager(server, hub=self)
        self.load_music()

        self.zone_manager = ZoneManager(server, self)

        # Has to be after character_manager to allow proper loading of areas,
        # as those need to compute restricted characters

        self.area_manager = AreaManager(server, hub=self)
        self.load_areas()

        self.trial_manager = TrialManager(self)
        self.manager: HubManager  # Setting for typing

    def unchecked_add_player(self, user: ClientManager.Client):
        return super().unchecked_add_player(user)

    def unchecked_remove_player(self, user: ClientManager.Client):
        return super().unchecked_remove_player(user)

    def load_areas(self, source_file: str = 'config/areas.yaml') -> List[AreaManager.Area]:
        """
        Load an area list file.

        Parameters
        ----------
        source_file : str
            Relative path from server root folder to the area list file, by default
            'config/areas.yaml'

        Returns
        -------
        List[AreaManager.Area]
            Areas.

        Raises
        ------
        ServerError.FileNotFoundError
            If the file was not found.
        ServerError.FileOSError
            If there was an operating system error when opening the file.
        ServerError.YAMLInvalidError
            If the file was empty, had a YAML syntax error, or could not be decoded using UTF-8.
        ServerError.FileSyntaxError
            If the file failed verification for its asset type.
        """

        areas = self.area_manager.load_file(source_file)
        return areas.copy()

    def load_backgrounds(self, source_file: str = 'config/backgrounds.yaml') -> List[str]:
        """
        Load a background list file.

        Parameters
        ----------
        source_file : str
            Relative path from server root folder to background list file, by default
            'config/backgrounds.yaml'

        Returns
        -------
        List[str]
            Backgrounds.

        Raises
        ------
        ServerError.FileNotFoundError
            If the file was not found.
        ServerError.FileOSError
            If there was an operating system error when opening the file.
        ServerError.YAMLInvalidError
            If the file was empty, had a YAML syntax error, or could not be decoded using UTF-8.
        ServerError.FileSyntaxError
            If the file failed verification for its asset type.
        """

        old_backgrounds = self.background_manager.get_backgrounds()
        backgrounds = self.background_manager.load_file(source_file)

        if old_backgrounds == backgrounds:
            # No change implies backgrounds still valid, do nothing more
            return backgrounds.copy()

        # Make sure each area still has a valid background
        default_background = self.background_manager.get_default_background()
        for area in self.get_areas():
            if not self.background_manager.is_background(area.background) and not area.cbg_allowed:
                # The area no longer has a valid background, so change it to some valid background
                # like the first one
                area.change_background(default_background)
                area.broadcast_ooc(f'After a change in the background list, your area no longer '
                                   f'had a valid background. Switching to {default_background}.')

        return backgrounds.copy()

    def load_characters(self, source_file: str = 'config/characters.yaml') -> List[str]:
        """
        Load a character list file.

        Parameters
        ----------
        source_file : str, optional
            Relative path from server root folder to character list file, by default
            'config/characters.yaml'

        Returns
        -------
        List[str]
            Characters.

        Raises
        ------
        ServerError.FileNotFoundError
            If the file was not found.
        ServerError.FileOSError
            If there was an operating system error when opening the file.
        ServerError.YAMLInvalidError
            If the file was empty, had a YAML syntax error, or could not be decoded using UTF-8.
        ServerError.FileSyntaxError
            If the file failed verification for its asset type.
        """

        old_characters = self.character_manager.get_characters()
        characters = self.character_manager.validate_file(source_file)
        if old_characters == characters:
            return characters.copy()

        # Inconsistent character list, so change to spectator those who lost their character.
        new_chars = {char: num for (num, char) in enumerate(characters)}

        for client in self.server.get_clients():
            target_char_id = -1
            old_char_name = client.get_char_name()

            if not client.has_character():
                # Do nothing for spectators
                pass
            elif old_char_name not in new_chars:
                # Character no longer exists, so switch to spectator
                client.send_ooc(f'After a change in the character list, your character is no '
                                f'longer available. Switching to '
                                f'{self.server.config["spectator_name"]}.')
            else:
                target_char_id = new_chars[old_char_name]

            if client.packet_handler.ALLOWS_CHAR_LIST_RELOAD:
                client.send_command_dict('SC', {
                    'chars_ao2_list': characters,
                    })
                client.change_character(target_char_id, force=True)
            else:
                client.send_ooc('After a change in the character list, your client character list '
                                'is no longer synchronized. Please rejoin the server.')

        # Only now update internally. This is to allow `change_character` to work properly.
        self.character_manager.load_file(source_file)
        return characters.copy()

    def load_music(self, music_list_file: str = 'config/music.yaml') -> List[Dict[str, Any]]:
        music = self.music_manager.load_file(music_list_file)
        return music.copy()

    def _on_area_client_left_final(self, area: AreaManager.Area, client: ClientManager.Client = None, old_displayname: str = None, ignore_bleeding: bool = False, ignore_autopass: bool = False):
        return super()._on_area_client_left_final(area, client, old_displayname, ignore_bleeding, ignore_autopass)

    def _on_area_client_entered_final(self, area: AreaManager.Area, client: ClientManager.Client = None, old_area: Union[AreaManager.Area, None] = None, old_displayname: str = None, ignore_bleeding: bool = False, ignore_autopass: bool = False):
        return super()._on_area_client_entered_final(area, client, old_area, old_displayname, ignore_bleeding, ignore_autopass)

    def _on_client_change_character(self, player: ClientManager.Client, old_char_id: Union[int, None] = None, new_char_id: Union[int, None] = None):
        return super()._on_client_change_character(player, old_char_id, new_char_id)

    def __str__(self) -> str:
        return (f"Hub::{self.get_id()}:"
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

        return (f'Hub(server, {self.manager.get_id()}, "{self.get_id()}", '
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


class _HubManagerTrivialInherited(GameWithAreasManager):
    """
    This class should not be instantiated.
    """

    def new_managee(
        self,
        managee_type: Type[_Hub] = None,
        creator: Union[ClientManager.Client, None] = None,
        player_limit: Union[int, None] = None,
        player_concurrent_limit: Union[int, None] = 1,
        require_invitations: bool = False,
        require_players: bool = False,  # Overriden from parent
        require_leaders: bool = False,  # Overriden from parent
        require_character: bool = False,
        team_limit: Union[int, None] = None,
        timer_limit: Union[int, None] = None,
        areas: Set[AreaManager.Area] = None,
        area_concurrent_limit: Union[int, None] = 1,  # Overriden from parent
        autoadd_on_client_enter: bool = False,
        autoadd_on_creation_existing_users: bool = False,
        **kwargs: Any,
        ) -> _Hub:
        """
        Create a new hub managed by this manager. Overriden default parameters include:
        * A hub does not require leaders.
        * A hub does not require players.
        * An area cannot belong to two or more hubs at the same time.

        Parameters
        ----------
        creator : ClientManager.Client, optional
            The player who created this hub. If set, they will also be added to the hub.
            Defaults to None.
        player_limit : Union[int, None], optional
            If an int, it is the maximum number of players the hub supports. If None, it
            indicates the hub has no player limit. Defaults to None.
        require_invitations : bool, optional
            If True, users can only be added to the hub if they were previously invited. If
            False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the hub loses all its players, the hub will automatically
            be deleted. If False, no such automatic deletion will happen. Defaults to True.
        require_character : bool, optional
            If False, players without a character will not be allowed to join the hub, and
            players that switch to something other than a character will be automatically
            removed from the hub. If False, no such checks are made. A player without a
            character is considered one where player.has_character() returns False. Defaults
            to False.
        team_limit : Union[int, None], optional
            If an int, it is the maximum number of teams the hub will support. If None, it
            indicates the hub will have no team limit. Defaults to None.
        timer_limit : Union[int, None], optional
            If an int, it is the maximum number of timers the hub will support. If None, it
            indicates the hub will have no timer limit. Defaults to None.
        area_concurrent_limit : Union[int, None], optional
            If an int, it is the maximum number of hubs managed by `manager` that any
            area of the created hub may belong to, including the created hub. If None, it
            indicates that this hub does not care about how many other hubs managed by
            `manager` each of its areas belongs to. Defaults to 1 (an area may not be a part of
            another hub managed by `manager` while being an area of this hubs).
        autoadd_on_client_enter : bool, optional
            If True, nonplayer users that enter an area part of the game will be automatically
            added if permitted by the conditions of the game. If False, no such adding will take
            place. Defaults to False.
        autoadd_on_creation_existing_users : bool
            If the hub will attempt to add nonplayer users who were in an area added
            to the hub on creation. Defaults to False.

        Returns
        -------
        _Hub
            The created hub.

        Raises
        ------
        HubError.ManagerTooManyGamesError
            If the manager is already managing its maximum number of minigames.
        Any error from the created hub's add_player(creator)
            If the hub cannot add `creator` to the hub if given one.

        """

        if managee_type is None:
            managee_type = self.get_managee_type()

        hub = self.unchecked_new_managee(
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
            **kwargs,
            )
        self._check_structure()

        return hub

    def get_managee_type(self) -> Type[_Hub]:
        """
        Return the type of the hub that will be constructed by default with a call of
        `new_managee`.

        Returns
        -------
        Type[_Hub]
            Type of the hub.

        """

        return super().get_managee_type()

    def delete_managee(self, managee: _Hub) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a hub managed by this manager, so all its players no longer belong to
        this hub.

        Parameters
        ----------
        managee : _Hub
            The hub to delete.

        Returns
        -------
        Tuple[str, Set[ClientManager.Client]]
            The ID and players of the hub that was deleted.

        Raises
        ------
        HubError.ManagerDoesNotManageGameError
            If the manager does not manage the target hub.

        """

        game_id, game_players = self.unchecked_delete_managee(managee)
        self._check_structure()
        return game_id, game_players

    def unchecked_delete_managee(
        self,
        managee: _Hub
        ) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a hub managed by this manager, so all its players no longer belong to
        this hub.

        Parameters
        ----------
        managee : _Hub
            The hub to delete.

        Returns
        -------
        Tuple[str, Set[ClientManager.Client]]
            The ID and players of the hub that was deleted.

        Raises
        ------
        HubError.ManagerDoesNotManageGameError
            If the manager does not manage the target hub.

        """

        try:
            return super().unchecked_delete_managee(managee)
        except GameWithAreasError.ManagerDoesNotManageGameError:
            raise HubError.ManagerDoesNotManageGameError

    def manages_managee(self, game: _Hub):
        """
        Return True if the hub is managed by this manager, False otherwise.

        Parameters
        ----------
        game : _Hub
            The game to check.

        Returns
        -------
        bool
            True if the manager manages this hub, False otherwise.

        """

        return super().manages_managee(game)

    def get_managees(self) -> Set[_Hub]:
        """
        Return (a shallow copy of) the hubs this manager manages.

        Returns
        -------
        Set[_Hub]
            Hubs this manager manages.

        """

        return super().get_managees()

    def get_managee_by_id(self, managee_id: str) -> _Hub:
        """
        If `managee_id` is the ID of a hub managed by this manager, return that.

        Parameters
        ----------
        managee_id : str
            ID of the hub this manager manages.

        Returns
        -------
        _Hub
            The hub with that ID.

        Raises
        ------
        HubError.ManagerInvalidGameIDError
            If `game_id` is not the ID of a hub this manager manages.

        """

        try:
            return super().get_managee_by_id(managee_id)
        except GameWithAreasError.ManagerInvalidGameIDError:
            raise HubError.ManagerInvalidGameIDError

    def get_managee_limit(self) -> Union[int, None]:
        """
        Return the hub limit of this manager.

        Returns
        -------
        Union[int, None]
            Game with areas limit.

        """

        return super().get_managee_limit()

    def get_managee_ids(self) -> Set[str]:
        """
        Return (a shallow copy of) the IDs of all hubs managed by this manager.

        Returns
        -------
        Set[str]
            The IDs of all managed hubs.

        """

        return super().get_managee_ids()

    def get_managee_ids_to_managees(self) -> Dict[str, _Hub]:
        """
        Return a mapping of the IDs of all hubs managed by this manager to their
        associated hub.

        Returns
        -------
        Dict[str, _Hub]
            Mapping.
        """

        return super().get_managee_ids_to_managees()

    def get_managees_of_user(self, user: ClientManager.Client):
        """
        Return (a shallow copy of) the hubs managed by this manager user `user` is a
        player of. If the user is part of no such hub, an empty set is returned.

        Parameters
        ----------
        user : ClientManager.Client
            User whose hubs will be returned.

        Returns
        -------
        Set[_Hub]
            Hubs the player belongs to.

        """

        return super().get_managees_of_user(user)

    def get_player_to_managees_map(self) -> Dict[ClientManager.Client, Set[_Hub]]:
        """
        Return a mapping of the players part of any hub managed by this manager to the
        hub managed by this manager such players belong to.

        Returns
        -------
        Dict[ClientManager.Client, Set[_Hub]]
            Mapping.
        """

        return super().get_player_to_managees_map()

    def get_users_in_some_managee(self) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) all the users that are part of some hub managed by
        this manager.

        Returns
        -------
        Set[ClientManager.Client]
            Users in some managed hub.

        """

        return super().get_users_in_some_managee()

    def is_managee_creatable(self) -> bool:
        """
        Return whether a new hub can currently be created without creating one.

        Returns
        -------
        bool
            True if a hub can be currently created, False otherwise.
        """

        return super().is_managee_creatable()

    def get_managees_in_area(self, area: AreaManager.Area) -> Set[_Hub]:
        """
        Return (a shallow copy of) all hubs managed by this manager that contain
        the given area.

        Parameters
        ----------
        area : AreaManager.Area
            Area that all returned hubs must contain.

        Returns
        -------
        Set[_Hub]
            Hubs that contain the given area.

        """

        return super().get_managees_in_area(area)

    def find_area_concurrent_limiting_managee(
        self,
        area: AreaManager.Area
        ) -> Union[_Hub, None]:
        """
        For area `area`, find a hub `most_restrictive_game` managed by this manager
        such that, if `area` were to be added to another hub managed by this manager,
        they would violate `most_restrictive_game`'s concurrent area membership limit.
        If no such hub exists (or the area is not an area of any hub
        managed by this  manager), return None.
        If multiple such hubs exist, any one of them may be returned.

        Parameters
        ----------
        area : AreaManager.Area
            Area to test.

        Returns
        -------
        Union[_Hub, None]
            Limiting hub as previously described if it exists, None otherwise.

        """

        return super().find_area_concurrent_limiting_managee(area)

    def get_areas_to_managees_map(self) -> Dict[ClientManager.Client, Set[_Hub]]:
        """
        Return a mapping of the areas part of any hub managed by this manager to the
        hub managed by this manager such players belong to.

        Returns
        -------
        Dict[ClientManager.Client, Set[_Hub]]
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
        ) -> Union[_Hub, None]:
        """
        For user `user`, find a hub `most_restrictive_game` managed by this manager such
        that, if `user` were to join another hub managed by this manager, they would
        violate `most_restrictive_game`'s concurrent player membership limit.
        If no such hub exists (or the player is not member of any hub
        managed by this manager), return None.
        If multiple such hubs exist, any one of them may be returned.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Returns
        -------
        Union[_Hub, None]
            Limiting hub as previously described if it exists, None otherwise.

        """

        return super().find_player_concurrent_limiting_managee(user)


class HubManager(_HubManagerTrivialInherited):
    """
    A hub manager is a game with areas manager with dedicated hub management functions.

    Attributes
    ----------
    server : TsuserverDR
        Server the hub manager belongs to.

    """

    # Invariants
    # ----------
    # 1. If `self.get_managees()` is empty, then `self._ever_had_hubs` is True.
    # 2. The invariants of the parent class are maintained.

    def __init__(
        self,
        server: TsuserverDR,
        managee_limit: Union[int, None] = None,
        default_managee_type: Type[_Hub] = None,
        ):
        """
        Create a hub manager object.

        Parameters
        ----------
        server : TsuserverDR
            The server this hub manager belongs to.
        managee_limit : int, optional
            The maximum number of hub this manager can handle. Defaults to None
            (no limit).
        default_managee_type : Type[_Hub], optional
            The default type of hub this manager will create. Defaults to None (and then
            converted to _Hub).

        """

        if default_managee_type is None:
            default_managee_type = _Hub

        self._ever_had_hubs = False

        super().__init__(
            server,
            managee_limit=managee_limit,
            default_managee_type=default_managee_type
        )

    def unchecked_new_managee(
        self,
        managee_type: Type[_Hub] = None,
        creator: Union[ClientManager.Client, None] = None,
        player_limit: Union[int, None] = None,
        player_concurrent_limit: Union[int, None] = 1,
        require_invitations: bool = False,
        require_players: bool = False,  # Overriden from parent
        require_leaders: bool = False,  # Overriden from parent
        require_character: bool = False,
        team_limit: Union[int, None] = None,
        timer_limit: Union[int, None] = None,
        areas: Set[AreaManager.Area] = None,
        area_concurrent_limit: Union[int, None] = 1,  # Overriden from parent
        autoadd_on_client_enter: bool = False,
        autoadd_on_creation_existing_users: bool = False,
        **kwargs: Any,
        ) -> _Hub:
        """
        Create a new hub managed by this manager. Overriden default parameters include:
        * A hub does not require leaders.
        * A hub does not require players.
        * An area cannot belong to two or more hubs at the same time.

        This method does not assert structural integrity.

        Parameters
        ----------
        creator : ClientManager.Client, optional
            The player who created this hub. If set, they will also be added to the hub.
            Defaults to None.
        player_limit : Union[int, None], optional
            If an int, it is the maximum number of players the hub supports. If None, it
            indicates the hub has no player limit. Defaults to None.
        require_invitations : bool, optional
            If True, users can only be added to the hub if they were previously invited. If
            False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the hub loses all its players, the hub will automatically
            be deleted. If False, no such automatic deletion will happen. Defaults to False.
        require_character : bool, optional
            If False, players without a character will not be allowed to join the hub, and
            players that switch to something other than a character will be automatically
            removed from the hub. If False, no such checks are made. A player without a
            character is considered one where player.has_character() returns False. Defaults
            to False.
        team_limit : Union[int, None], optional
            If an int, it is the maximum number of teams the hub will support. If None, it
            indicates the hub will have no team limit. Defaults to None.
        timer_limit : Union[int, None], optional
            If an int, it is the maximum number of timers the hub will support. If None, it
            indicates the hub will have no timer limit. Defaults to None.
        area_concurrent_limit : Union[int, None], optional
            If an int, it is the maximum number of hubs managed by `manager` that any
            area of the created hub may belong to, including the created hub. If None, it
            indicates that this hub does not care about how many other hubs managed by
            `manager` each of its areas belongs to. Defaults to 1 (an area may not be a part of
            another hub managed by `manager` while being an area of this hubs).
        autoadd_on_client_enter : bool, optional
            If True, nonplayer users that enter an area part of the game will be automatically
            added if permitted by the conditions of the game. If False, no such adding will take
            place. Defaults to False.
        autoadd_on_creation_existing_users : bool
            If the hub will attempt to add nonplayer users who were in an area added
            to the hub on creation. Defaults to False.

        Returns
        -------
        _Hub
            The created hub.

        Raises
        ------
        HubError.ManagerTooManyGamesError
            If the manager is already managing its maximum number of minigames.
        Any error from the created hub's add_player(creator)
            If the hub cannot add `creator` to the hub if given one.

        """

        if managee_type is None:
            managee_type = self.get_managee_type()

        try:
            hub: _Hub = super().unchecked_new_managee(
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
                # kwargs
                **kwargs,
                )
        except GameWithAreasError.ManagerTooManyGamesError:
            raise HubError.ManagerTooManyGamesError

        self._ever_had_hubs = True
        return hub

    def get_managee_of_user(self, user: ClientManager.Client) -> _Hub:
        """
        Get the hub the user is in.

        Parameters
        ----------
        user : ClientManager.Client
            User to check.

        Raises
        ------
        HubError.UserNotPlayerError
            If the user is not in a hub managed by this manager.

        Returns
        -------
        HubManager.Hub
            Hub of the user.

        """

        games = self.get_managees_of_user(user)
        hubs = {game for game in games if isinstance(game, _Hub)}
        if not hubs:
            raise HubError.UserNotPlayerError
        if len(hubs) > 1:
            raise RuntimeError(hubs)
        return next(iter(hubs))

    def get_available_managee_id(self):
        """
        Get a hub ID that no other hub managed by this manager has.

        Returns
        -------
        str
            A unique hub ID.

        Raises
        ------
        HubError.ManagerTooManyGamesError
            If the manager is already managing its maximum number of games.

        """

        game_number = 0
        game_limit = self.get_managee_limit()
        while game_limit is None or game_number < game_limit:
            new_game_id = "H{}".format(game_number)
            if new_game_id not in self.get_managee_ids():
                return new_game_id
            game_number += 1
        raise HubError.ManagerTooManyGamesError

    def get_default_managee(self) -> _Hub:
        id_to_managees = self.get_managee_ids_to_managees()
        earliest_id = sorted(id_to_managees.keys())[0]
        return id_to_managees[earliest_id]

    def get_client_view(self, client: ClientManager.Client) -> List[str]:
        # Now add areas
        prepared_list = list()
        prepared_list.append(Constants.get_first_area_list_item('AREA', client.hub, client.area))

        for hub in self.get_managees():
            prepared_list.append(f'{hub.get_id()[1:]}-{hub.get_name()}')

        return prepared_list

    def _check_structure(self):
        """
        Assert that all invariants specified in the class description are maintained.

        Raises
        ------
        AssertionError
            If any of the invariants are not maintained.

        """

        hubs = self.get_managees()

        # 1.
        if not hubs and self._ever_had_hubs:
            err = (f'For hub manager {self}, expected that it had no hubs managed only if it had '
                   f'never had any hubs, found it managed no hubs after it had hubs {hubs} '
                   f'beforehand.')
            raise AssertionError(err)

        # 2.
        super()._check_structure()
