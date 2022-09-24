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
Module that contains the GameManager class, which itself contains the Game and Team subclasses.

Games maintain a PlayerGroup-like structure and methods, but also allow the creation of teams with
thier players. Teams are proper PlayerGroups, and no player of a game can be part of two teams
managed by the same game. Players of a game need not be part of a team managed by the game, but a
team can only have players of the game as players of the team. Removing a player from a game
also removes them from their team if they were in any.

Games also maintain a TimerManager-like structure, allowing the creation of timers
managed by the game.

Each game is managed by a game manager, which itself maintains a PlayerGroupManager-like structure.
Unless specified otherwise in the games, a player may be part of two or more games managed by the
same game manager.

"""

from __future__ import annotations

import typing
from typing import Any, Callable, Dict, Set, Tuple, Type, Union

from server.exceptions import GameError, PlayerGroupError, TimerError
from server.playergroup_manager import _PlayerGroup, PlayerGroupManager
from server.timer_manager import Timer, TimerManager
from server.subscriber import Listener, Publisher

if typing.TYPE_CHECKING:
    from server.client_manager import ClientManager
    from server.tsuserver import TsuserverDR

class _Team(_PlayerGroup):
    """
    Teams are player groups that have a game associated with them. Users may only be added as
    players of the team if they are a player of the game.
    """

    # (Private) Attributes
    # --------------------
    # _game : _Game
    #     Game this team is a part of.

    def __init__(self, server, manager, playergroup_id, player_limit=None,
                 player_concurrent_limit=None, require_invitations=False, require_players=True,
                 require_leaders=True, game: _Game = None):
        """
        Create a new team.

        Parameters
        ----------
        server : TsuserverDR
            Server the team belongs to.
        manager : PlayerGroupManager
            Manager for this team.
        playergroup_id : str
            Identifier of the team.
        game : _Game
            Game of this team.
        player_limit : Union[int, None], optional
            If an int, it is the maximum number of players the team supports. If None,
            it indicates the team has no player limit. Defaults to None.
        player_concurrent_limit : Union[int, None], optional
            If an int, it is the maximum number of teams managed by `manager` that any
            player of this team may belong to, including this team. If None, it indicates
            that this team does not care about how many other teams managed by
            `manager` each of its players belongs to. It is always overwritten by 1 (a player
            may not be in another team managed by `manager` while in this team).
        require_invitations : bool, optional
            If True, players can only be added to the team if they were previously invited. If
            False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the team has no players left, the team will
            automatically be deleted. If False, no such automatic deletion will happen.
            Defaults to True.
        require_leaders : bool, optional
            If True, if at any point the team has no leaders left, the team will choose a
            leader among any remaining players left; if no players are left, the next player
            added will be made leader. If False, no such automatic assignment will happen.
            Defaults to True.

        """

        super().__init__(server, manager, playergroup_id, player_limit=player_limit,
                         player_concurrent_limit=player_concurrent_limit,
                         require_invitations=require_invitations,
                         require_players=require_players, require_leaders=require_leaders)
        self._game = game
        self.manager: GameManager  # Setting for typing

    def add_player(self, user):
        """
        Make a user a player of the team. By default this player will not be a
        leader.

        Parameters
        ----------
        user : ClientManager.Client
            User to add to the team.
        cond : types.LambdaType: ClientManager.Client -> bool, optional
            Condition that the player to add must satisfy. If the user fails this condition,
            they will not be added. Defaults to None (no checked conditions).

        Raises
        ------
        PlayerGroupError.UserNotInvitedError
            If the team requires players be invited to be added and the user is not invited.
        PlayerGroupError.UserAlreadyPlayerError
            If the user to add is already a user of the team.
        PlayerGroupError.GroupIsFullError
            If the team reached its player limit.
        PlayerGroupError.UserHitGroupConcurrentLimitError.
            If the player has reached any of the groups it belongs to managed by this player
            team's manager concurrent player membership limit, or by virtue of joining this team
            will violate this team's concurrent player membership limit.
        PlayerGroupError.UserNotPlayerError
            If the user to add is not a player of the game.

        """

        if not self._game.is_player(user):
            raise PlayerGroupError.UserNotPlayerError

        super().add_player(user)

class _GameTrivialInherited(_PlayerGroup):
    """
    This class should not be instantiated.
    """

    def get_id(self) -> str:
        """
        Return the ID of this game.

        Returns
        -------
        str
            The ID.

        """

        return super().get_id()

    def get_numerical_id(self) -> int:
        """
        Return the numerical portion of the ID of this game.

        Returns
        -------
        int
            Numerical portion of the ID.
        """

        return super().get_numerical_id()

    def get_name(self) -> str:
        """
        Get the name of the game.

        Returns
        -------
        str
            Name.
        """

        return super().get_name()

    def set_name(self, name: str):
        """
        Set the name of the game.

        Parameters
        ----------
        name : str
            Name.
        """

        self.unchecked_set_name(name)
        self.manager._check_structure()

    def unchecked_set_name(self, name: str):
        """
        Set the name of the game.

        This method does not assert structural integrity.

        Parameters
        ----------
        name : str
            Name.
        """

        super().unchecked_set_name(name)

    def get_player_limit(self) -> Union[int, None]:
        """
        Return the player membership limit of this game.

        Returns
        -------
        Union[int, None]
            The player membership limit.

        """

        return super().get_player_limit()

    def get_player_concurrent_limit(self) -> Union[int, None]:
        """
        Return the concurrent player membership limit of this game.

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
        Return (a shallow copy of) the set of players of this game that satisfy a condition
        if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all players returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) players of this game.

        """

        return super().get_players(cond=cond)

    def is_player(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is a player of the game.

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
        Make a user a player of the game. By default this player will not be a leader, unless the
        game has no leaders and it requires a leader.
        It will also subscribe the game to the player so it can listen to its updates.

        Parameters
        ----------
        user : ClientManager.Client
            User to add to the game.

        Raises
        ------
        GameError.GameIsUnmanagedError
            If the game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameError.UserHasNoCharacterError
            If the user has no character but the game requires that all players have characters.
        GameError.UserNotInvitedError
            If the game requires players be invited to be added and the user is not invited.
        GameError.UserAlreadyPlayerError
            If the user to add is already a user of the game.
        GameError.UserHitGameConcurrentLimitError
            If the player has reached the concurrent player membership of any of the games managed
            by the manager of this game, or by virtue of joining this game they
            would violate this game's concurrent player membership limit.
        GameError.GameIsFullError
            If the game reached its player limit.

        """

        self.unchecked_add_player(user)
        self.manager._check_structure()

    def remove_player(self, user: ClientManager.Client):
        """
        Make a user be no longer a player of this game. If they were part of a team managed by
        this game, they will also be removed from said team. It will also unsubscribe the game
        from the player so it will no longer listen to its updates.

        If the game required that there it always had players and by calling this method the
        game had no more players, the game will automatically be scheduled for deletion.

        Parameters
        ----------
        user : ClientManager.Client
            User to remove.

        Raises
        ------
        GameError.GameIsUnmanagedError
            If the game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameError.UserNotPlayerError
            If the user to remove is already not a player of this game.

        """

        self.unchecked_remove_player(user)
        self.manager._check_structure()

    def requires_players(self) -> bool:
        """
        Return whether the game requires players at all times.

        Returns
        -------
        bool
            Whether the game requires players at all times.
        """

        return super().requires_players()

    def get_invitations(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
        ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of invited users of this game that satisfy a
        condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all invited users returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) invited users of this game.

        """

        return super().get_invitations(cond=cond)

    def is_invited(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is invited to the game.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Raises
        ------
        GameError.UserAlreadyPlayerError
            If the user is a player of this game.

        Returns
        -------
        bool
            True if the user is invited, False otherwise.

        """

        try:
            return super().is_invited(user)
        except PlayerGroupError.UserAlreadyPlayerError:
            raise GameError.UserAlreadyPlayerError

    def add_invitation(self, user: ClientManager.Client):
        """
        Mark a user as invited to this game.

        Parameters
        ----------
        user : ClientManager.Client
            User to invite to the game.

        Raises
        ------
        GameError.GameIsUnmanagedError
            If the game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameError.GameDoesNotTakeInvitationsError
            If the game does not require users be invited to the game.
        GameError.UserAlreadyInvitedError
            If the player to invite is already invited to the game.
        GameError.UserAlreadyPlayerError
            If the player to invite is already a player of the game.

        """

        self.unchecked_add_invitation(user)
        self.manager._check_structure()

    def unchecked_add_invitation(self, user: ClientManager.Client):
        """
        Mark a user as invited to this game.

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to invite to the game.

        Raises
        ------
        GameError.GameIsUnmanagedError
            If the game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameError.GameDoesNotTakeInvitationsError
            If the game does not require users be invited to the game.
        GameError.UserAlreadyInvitedError
            If the player to invite is already invited to the game.
        GameError.UserAlreadyPlayerError
            If the player to invite is already a player of the game.

        """

        try:
            super().unchecked_add_invitation(user)
        except PlayerGroupError.GroupIsUnmanagedError:
            raise GameError.GameIsUnmanagedError
        except PlayerGroupError.GroupDoesNotTakeInvitationsError:
            raise GameError.GameDoesNotTakeInvitationsError
        except PlayerGroupError.UserAlreadyInvitedError:
            raise GameError.UserAlreadyInvitedError
        except PlayerGroupError.UserAlreadyPlayerError:
            raise GameError.UserAlreadyPlayerError

    def remove_invitation(self, user: ClientManager.Client):
        """
        Mark a user as no longer invited to this game (uninvite).

        Parameters
        ----------
        user : ClientManager.Client
            User to uninvite.

        Raises
        ------
        GameError.GameIsUnmanagedError
            If the game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameError.GameDoesNotTakeInvitationsError
            If the game does not require users be invited to the game.
        GameError.UserNotInvitedError
            If the user to uninvite is already not invited to this game.

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
        GameError.GameIsUnmanagedError
            If the game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameError.GameDoesNotTakeInvitationsError
            If the game does not require users be invited to the game.
        GameError.UserNotInvitedError
            If the user to uninvite is already not invited to this game.

        """

        try:
            super().unchecked_remove_invitation(user)
        except PlayerGroupError.GroupIsUnmanagedError:
            raise GameError.GameIsUnmanagedError
        except PlayerGroupError.GroupDoesNotTakeInvitationsError:
            raise GameError.GameDoesNotTakeInvitationsError
        except PlayerGroupError.UserNotInvitedError:
            raise GameError.UserNotInvitedError

    def requires_invitations(self):
        """
        Return True if the game requires players be invited before being allowed to join
        the game, False otherwise.

        Returns
        -------
        bool
            True if the game requires players be invited before being allowed to join
            the game, False otherwise.
        """

        return super().requires_invitations()

    def get_leaders(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
        ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of leaders of this game that satisfy a condition
        if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all leaders returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) leaders of this game.

        """

        return super().get_leaders(cond=cond)

    def get_regulars(
        self,
        cond: Callable[[ClientManager.Client, ], bool] = None
        ) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) the set of players of this game that are regulars and satisfy
        a condition if given.

        Parameters
        ----------
        cond : Callable[[ClientManager.Client, ], bool], optional
            Condition that all regulars returned satisfy. Defaults to None (no checked
            conditions).

        Returns
        -------
        Set[ClientManager.Client]
            The (filtered) regulars of this game.

        """

        return super().get_regulars(cond=cond)

    def is_leader(self, user: ClientManager.Client) -> bool:
        """
        Decide if a user is a leader of the game.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Raises
        ------
        GameError.UserNotPlayerError
            If the player to test is not a player of this game.

        Returns
        -------
        bool
            True if the player is a user, False otherwise.

        """

        try:
            return super().is_leader(user)
        except PlayerGroupError.UserNotPlayerError:
            raise GameError.UserNotPlayerError

    def add_leader(self, user: ClientManager.Client):
        """
        Set a user as leader of this game (promote to leader).

        Parameters
        ----------
        user : ClientManager.Client
            Player to promote to leader.

        Raises
        ------
        GameError.GameIsUnmanagedError
            If the game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameError.UserNotPlayerError
            If the player to promote is not a player of this game.
        GameError.UserAlreadyLeaderError
            If the player to promote is already a leader of this game.

        """

        self.unchecked_add_leader(user)
        self.manager._check_structure()

    def unchecked_add_leader(self, user: ClientManager.Client):
        """
        Set a user as leader of this game (promote to leader).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            Player to promote to leader.

        Raises
        ------
        GameError.GameIsUnmanagedError
            If the game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameError.UserNotPlayerError
            If the player to promote is not a player of this game.
        GameError.UserAlreadyLeaderError
            If the player to promote is already a leader of this game.

        """

        try:
            super().unchecked_add_leader(user)
        except PlayerGroupError.GroupIsUnmanagedError:
            raise GameError.GameIsUnmanagedError
        except PlayerGroupError.UserNotPlayerError:
            raise GameError.UserNotPlayerError
        except PlayerGroupError.UserAlreadyLeaderError:
            raise GameError.UserAlreadyLeaderError

    def remove_leader(self, user: ClientManager.Client):
        """
        Make a user no longer leader of this game (demote).

        Parameters
        ----------
        user : ClientManager.Client
            User to demote.

        Raises
        ------
        GameError.GameIsUnmanagedError
            If the game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameError.UserNotPlayerError
            If the player to demote is not a player of this game.
        GameError.UserNotLeaderError
            If the player to demote is already not a leader of this game.

        """

        self.unchecked_remove_leader(user)
        self.manager._check_structure()

    def unchecked_remove_leader(self, user: ClientManager.Client):
        """
        Make a user no longer leader of this game (demote).

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to demote.

        Raises
        ------
        GameError.GameIsUnmanagedError
            If the game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameError.UserNotPlayerError
            If the player to demote is not a player of this game.
        GameError.UserNotLeaderError
            If the player to demote is already not a leader of this game.

        """

        try:
            super().unchecked_remove_leader(user)
        except PlayerGroupError.GroupIsUnmanagedError:
            raise GameError.GameIsUnmanagedError
        except PlayerGroupError.UserNotPlayerError:
            raise GameError.UserNotPlayerError
        except PlayerGroupError.UserNotLeaderError:
            raise GameError.UserNotLeaderError

    def has_ever_had_players(self) -> bool:
        """
        Return True if a player has ever been added to this game, False otherwise.

        Returns
        -------
        bool
            True if the game has ever had a player added, False otherwise.

        """

        return super().has_ever_had_players()

    def requires_leaders(self) -> bool:
        """
        Return whether the game requires leaders at all times.

        Returns
        -------
        bool
            Whether the game requires leaders at all times.
        """

        return super().requires_leaders()

    def has_ever_had_players(self):
        """
        Return True if a player has ever been added to this game, False otherwise.

        Returns
        -------
        bool
            True if the game has ever had a player added, False otherwise.

        """

        return super().has_ever_had_players()

    def is_unmanaged(self):
        """
        Return True if this game is unmanaged, False otherwise.

        Returns
        -------
        bool
            True if unmanaged, False otherwise.

        """

        return super().is_unmanaged()

    def destroy(self):
        """
        Mark this game as destroyed and notify its manager so that it is deleted.
        If the game is already destroyed, this function does nothing.
        A game marked for destruction will delete all of its timers, teams, remove all its
        players and unsubscribe it from updates of its former players.

        This method is reentrant (it will do nothing though).

        Returns
        -------
        None.

        """

        self.unchecked_destroy()
        self.manager._check_structure()
        self._check_structure()  # Manager will not check this otherwise.


class _Game(_GameTrivialInherited):
    """
    A mutable data type for games.

    Games are groups of users (called players) with an ID, that may also manage some timers
    and teams.

    Some players of the game (possibly none) may become leaders. A player that is not a leader
    is called regular. Each game may have a player limit (beyond which no new players may be added),
    may require that it never loses all its players as soon as it gets its first one (or else it
    is automatically deleted) and may require that if it has at least one player, then that there
    is at least one leader (or else one is automatically chosen between all players). Each of these
    games may also impose a concurrent player membership limit, so that every user that is a player
    of it is at most of that many games managed by this game's manager. Each game may also
    require all its players have characters when trying to join the game, as well as remove any
    player that switches to a non-character.

    Each of the timers a game manages are timer_manager.Timers.

    For each managed team, its players must also be players of this game.

    Once a game is scheduled for deletion, its manager will no longer recognize it as a game
    it is managing (it will unmanage it), so no further mutator public method calls would be
    allowed on the game.

    Each game also has a standard listener. By default the game subscribes to all its players'
    updates.

    Attributes
    ----------
    server : TsuserverDR
        Server the game belongs to.
    manager : GameManager
        Manager for this game.
    listener : Listener
        Standard listener of the game.

    Callback Methods
    ----------------
    _on_client_inbound_ms_check
        Method to perform once a player of the game wants to send an IC message.
    _on_client_inbound_ms_final
        Method to perform once a player of the game sends an IC message.
    _on_client_change_character
        Method to perform once a player of the game has changed character.
    _on_client_destroyed
        Method to perform once a player of the game is destroyed.

    """

    # (Private) Attributes
    # --------------------
    # _require_character : bool
    #   If False, players without a character will not be allowed to join the game, and players
    #   that switch to something other than a character will be automatically removed from the
    #   game. If False, no such checks are made.
    # _team_manager : PlayerGroupManager
    #   Internal manager that handles the teams of the game.
    # _timer_manager: TimerManager
    #   Internal manager that handles the timers of the game.

    # Invariants
    # ----------
    # 1. All players part of a team managed by this game are players of the game.
    # 2. For each player of the game, the game is subscribed to it.
    # 3. If the game requires its players have characters, all its players do have characters.
    # 4. Each internal structure satisfies its invariants.
    # 5. The invariants from the parent class _PlayerGroup are satisfied.

    def __init__(
        self,
        server: TsuserverDR,
        manager: GameManager,
        game_id: str,
        player_limit: Union[int, None] = None,
        player_concurrent_limit: Union[int, None] = None,
        require_invitations: bool = False,
        require_players: bool = True,
        require_leaders: bool = True,
        require_character: bool = False,
        team_limit: Union[int, None] = None,
        timer_limit: Union[int, None] = None,
    ):
        """
        Create a new game. A game should not be fully initialized anywhere else other than
        some manager code, as otherwise the manager will not recognize the game.

        Parameters
        ----------
        server : TsuserverDR
            Server the game belongs to.
        manager : GameManager
            Manager for this game.
        game_id : str
            Identifier of the game.
        player_limit : Union[int, None], optional
            If an int, it is the maximum number of players the game supports. If None, it
            indicates the game has no player limit. Defaults to None.
        player_concurrent_limit : Union[int, None], optional
            If an int, it is the maximum number of games managed by `manager` that any
            player of this game may belong to, including this game. If None, it indicates
            that this game does not care about how many other games managed by `manager` each
            of its players belongs to. Defaults to None.
        require_invitation : bool, optional
            If True, players can only be added to the game if they were previously invited. If
            False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the game has no players left, the game will
            automatically be deleted. If False, no such automatic deletion will happen.
            Defaults to True.
        require_leaders : bool, optional
            If True, if at any point the game has no leaders left, the game will choose a
            leader among any remaining players left; if no players are left, the next player
            added will be made leader. If False, no such automatic assignment will happen.
            Defaults to True.
        require_character : bool, optional
            If False, players without a character will not be allowed to join the game, and
            players that switch to something other than a character will be automatically
            removed from the game. If False, no such checks are made. A player without a
            character is considered one where player.has_character() returns False. Defaults to
            False.
        team_limit : Union[int, None], optional
            If an int, it is the maximum number of teams the game supports. If None, it
            indicates the game has no team limit. Defaults to None.
        timer_limit : Union[int, None], optional
            If an int, it is the maximum number of timers the game supports. If None, it
            indicates the game has no timer limit. Defaults to None.

        """

        super().__init__(
            server,
            manager,
            game_id,
            player_limit=player_limit,
            player_concurrent_limit=player_concurrent_limit,
            require_invitations=require_invitations,
            require_players=require_players,
            require_leaders=require_leaders,
        )

        self._team_manager = PlayerGroupManager(
            server,
            managee_limit=team_limit,
            default_managee_type=_Team
        )
        self._timer_manager = TimerManager(
            server,
            timer_limit=timer_limit
        )
        self._require_character = require_character

        self.publisher = Publisher(self)
        # Implementation detail: the callbacks of the internal objects of the game are (to be)
        # ignored.
        self.listener = Listener(self, {
            'client_inbound_ms_final': self._on_client_inbound_ms_final,
            'client_inbound_ms_check': self._on_client_inbound_ms_check,
            'client_change_character': self._on_client_change_character,
            'client_destroyed': self._on_client_destroyed,
            })

    def get_type_name(self) -> str:
        """
        Return the type name of the game. Names are fully lowercase.
        Implementations of the class should replace this with a human readable name of the game.

        Returns
        -------
        str
            Type name of the game.

        """

        return "game"

    def unchecked_add_player(self, user: ClientManager.Client):
        """
        Make a user a player of the game. By default this player will not be a leader, unless the
        game has no leaders and the game requires a leader.
        It will also subscribe the game to the player so it can listen to its updates.

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to add to the game.

        Raises
        ------
        GameError.GameIsUnmanagedError
            If the game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameError.UserHasNoCharacterError
            If the user has no character but the game requires that all players have characters.
        GameError.UserNotInvitedError
            If the game requires players be invited to be added and the user is not invited.
        GameError.UserAlreadyPlayerError
            If the user to add is already a user of the game.
        GameError.UserHitGameConcurrentLimitError
            If the player has reached the concurrent player membership of any of the games managed
            by the manager of this game, or by virtue of joining this game they
            would violate this game's concurrent player membership limit.
        GameError.GameIsFullError
            If the game reached its player limit.

        """

        if self.is_unmanaged():
            raise GameError.GameIsUnmanagedError
        if self._require_character and not user.has_character():
            raise GameError.UserHasNoCharacterError

        try:
            super().unchecked_add_player(user)
        except PlayerGroupError.GroupIsUnmanagedError:
            raise RuntimeError(self, user)
        except PlayerGroupError.UserNotInvitedError:
            raise GameError.UserNotInvitedError
        except PlayerGroupError.UserAlreadyPlayerError:
            raise GameError.UserAlreadyPlayerError
        except PlayerGroupError.UserHitGroupConcurrentLimitError:
            raise GameError.UserHitGameConcurrentLimitError
        except PlayerGroupError.GroupIsFullError:
            raise GameError.GameIsFullError

        self.listener.subscribe(user)

    def unchecked_remove_player(self, user: ClientManager.Client):
        """
        Make a user be no longer a player of this game. If they were part of a team managed by
        this game, they will also be removed from said team. It will also unsubscribe the game
        from the player so it will no longer listen to its updates.

        If the game required that there it always had players and by calling this method the
        game had no more players, the game will automatically be scheduled for deletion.

        This method does not assert structural integrity.

        Parameters
        ----------
        user : ClientManager.Client
            User to remove.

        Raises
        ------
        GameError.GameIsUnmanagedError
            If the game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameError.UserNotPlayerError
            If the user to remove is already not a player of this game.

        """

        if self.is_unmanaged():
           raise GameError.GameIsUnmanagedError
        if not self.is_player(user):
            raise GameError.UserNotPlayerError

        user_teams = self.get_teams_of_user(user)
        for team in user_teams:
            team.remove_player(user)

        try:
            super().unchecked_remove_player(user)
        except PlayerGroupError.GroupIsUnmanagedError:
            # Should not have made it here as we already asserted the game is not unmmanaged
            raise RuntimeError(self, user)
        except PlayerGroupError.UserNotPlayerError:
            # Should not have made it here as we already asserted the user is a player
            raise RuntimeError(self, user)

        self.listener.unsubscribe(user)

    def requires_characters(self) -> bool:
        """
        Return whether the game requires players have a character at all times.

        Returns
        -------
        bool
            Whether the game requires players have a character at all times.
        """

        return self._require_character

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
        Create a new timer managed by this game with given parameters.

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
            If True, the game will automatically delete the timer once it is terminated by it
            ticking out or manual termination. If False, no such automatic deletion will take place.
            Defaults to True.

        Returns
        -------
        Timer
            The created timer.

        Raises
        ------
        GameError.GameIsUnmanagedError
            If the game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameError.GameTooManyTimersError
            If the game is already managing its maximum number of timers.

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
        Create a new timer managed by this game with given parameters.

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
            If True, the game will automatically delete the timer once it is terminated by it
            ticking out or manual termination. If False, no such automatic deletion will take place.
            Defaults to True.

        Returns
        -------
        Timer
            The created timer.

        Raises
        ------
        GameError.GameIsUnmanagedError
            If the game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameError.GameTooManyTimersError
            If the game is already managing its maximum number of timers.

        """

        if self.is_unmanaged():
            raise GameError.GameIsUnmanagedError

        try:
            timer = self._timer_manager.new_timer(
                timer_type=timer_type,
                start_value=start_value,
                tick_rate=tick_rate,
                min_value=min_value,
                max_value=max_value,
                auto_restart=auto_restart,
                auto_destroy=auto_destroy
                )
        except TimerError.ManagerTooManyTimersError:
            raise GameError.GameTooManyTimersError

        return timer

    def delete_timer(self, timer: Timer) -> str:
        """
        Delete a timer managed by this game, terminating it first if needed.

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
        GameError.GameIsUnmanagedError
            If the game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameError.GameDoesNotManageTimerError
            If the game does not manage the target timer.

        """

        timer_id = self.unchecked_delete_timer(timer)
        self.manager._check_structure()
        return timer_id

    def unchecked_delete_timer(self, timer: Timer) -> str:
        """
        Delete a timer managed by this game, terminating it first if needed.

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
        GameError.GameIsUnmanagedError
            If the game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameError.GameDoesNotManageTimerError
            If the game does not manage the target timer.

        """

        if self.is_unmanaged():
            raise GameError.GameIsUnmanagedError

        try:
            timer_id = self._timer_manager.delete_timer(timer)
        except TimerError.ManagerDoesNotManageTimerError:
            raise GameError.GameDoesNotManageTimerError

        return timer_id

    def get_timers(self) -> Set[Timer]:
        """
        Return (a shallow copy of) the timers this game manages.

        Returns
        -------
        Set[Timer]
            Timers this game manages.

        """

        return self._timer_manager.get_timers()

    def get_timer_by_id(self, timer_id: str) -> Timer:
        """
        If `timer_tag` is the ID of a timer managed by this game, return that timer.

        Parameters
        ----------
        timer_id: str
            ID of timer this game manages.

        Returns
        -------
        Timer
            The timer whose ID matches the given ID.

        Raises
        ------
        GameError.GameInvalidTimerIDError:
            If `timer_tag` is a str and it is not the ID of a timer this game manages.

        """

        try:
            return self._timer_manager.get_timer_by_id(timer_id)
        except TimerError.ManagerInvalidTimerIDError:
            raise GameError.GameInvalidTimerIDError

    def get_timer_limit(self) -> Union[int, None]:
        """
        Return the timer limit of this game.

        Returns
        -------
        Union[int, None]
            Timer limit.

        """

        return self._timer_manager.get_timer_limit()

    def get_timer_ids(self) -> Set[str]:
        """
        Return (a shallow copy of) the IDs of all timers managed by this game.

        Returns
        -------
        Set[str]
            The IDs of all managed timers.

        """

        return self._timer_manager.get_timer_ids()

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
        Create a new team managed by this game.

        Parameters
        ----------
        team_type : _Team
            Class of team that will be produced. Defaults to None (and converted to the
            default team created by games, namely, _Team).
        creator : ClientManager.Client, optional
            The player who created this team. If set, they will also be added to the team if
            possible. The creator must be a player of this game. Defaults to None.
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
        GameError.GameIsUnmanagedError
            If the game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameError.GameTooManyTeamsError
            If the game is already managing its maximum number of teams.
        GameError.UserInAnotherTeamError
            If `creator` is not None and already part of a team managed by this game.

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
        Create a new team managed by this game.

        This method does not assert structural integrity.

        Parameters
        ----------
        team_type : _Team
            Class of team that will be produced. Defaults to None (and converted to the
            default team created by games, namely, _Team).
        creator : ClientManager.Client, optional
            The player who created this team. If set, they will also be added to the team if
            possible. The creator must be a player of this game. Defaults to None.
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
        GameError.GameIsUnmanagedError
            If the game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameError.GameTooManyTeamsError
            If the game is already managing its maximum number of teams.
        GameError.UserInAnotherTeamError
            If `creator` is not None and already part of a team managed by this game.

        """

        if self.is_unmanaged():
            raise GameError.GameIsUnmanagedError

        if team_type is None:
            team_type = _Team

        try:
            team = self._team_manager.new_managee(
                managee_type=team_type,
                creator=creator,
                player_limit=player_limit,
                player_concurrent_limit=1,
                require_invitations=require_invitations,
                require_players=require_players,
                require_leaders=require_leaders,
                game=self,
            )
        except PlayerGroupError.ManagerTooManyGroupsError:
            raise GameError.GameTooManyTeamsError
        except PlayerGroupError.UserHitGroupConcurrentLimitError:
            raise GameError.UserInAnotherTeamError
        return team

    def delete_team(self, team: _Team) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a team managed by this game.

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
        GameError.GameIsUnmanagedError
            If the game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameError.GameDoesNotManageTeamError
            If the game does not manage the target team.

        """

        team_id, players = self.unchecked_delete_team(team)
        self.manager._check_structure()
        return team_id, players

    def unchecked_delete_team(self, team: _Team) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a team managed by this game.

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
        GameError.GameIsUnmanagedError
            If the game was scheduled for deletion and thus does not accept any mutator
            public method calls.
        GameError.GameDoesNotManageTeamError
            If the game does not manage the target team.

        """

        if self.is_unmanaged():
            raise GameError.GameIsUnmanagedError

        try:
            return self._team_manager.delete_managee(team)
        except PlayerGroupError.ManagerDoesNotManageGroupError:
            raise GameError.GameDoesNotManageTeamError

    def manages_team(self, team: _Team) -> bool:
        """
        Return True if the team is managed by this game, False otherwise.

        Parameters
        ----------
        team : _Team
            The team to check.

        Returns
        -------
        bool
            True if the game manages this team, False otherwise.

        """

        return self._team_manager.manages_managee(team)

    def get_teams(self) -> Set[_Team]:
        """
        Return (a shallow copy of) the teams this game manages.

        Returns
        -------
        Set[_Team]
            Teams this game manages.

        """

        return self._team_manager.get_managees()

    def get_team_by_id(self, team_id: str) -> _Team:
        """
        If `team_id` is the ID of a team managed by this game, return the team.

        Parameters
        ----------
        team_id : str
            ID of the team this game manages.

        Returns
        -------
        _Team
            The team that matches the given ID.

        Raises
        ------
        GameError.GameInvalidTeamIDError:
            If `team_id` is not the ID of a team this game manages.

        """

        try:
            return self._team_manager.get_managee_by_id(team_id)
        except PlayerGroupError.ManagerInvalidGroupIDError:
            raise GameError.GameInvalidTeamIDError

    def get_team_limit(self) -> Union[int, None]:
        """
        Return the team limit of this game.

        Returns
        -------
        Union[int, None]
            Team limit.

        """

        return self._team_manager.get_managee_limit()

    def get_team_ids(self) -> Set[str]:
        """
        Return (a shallow copy of) the IDs of all teams managed by this game.

        Returns
        -------
        Set[str]
            The IDs of all managed teams.

        """

        return self._team_manager.get_managee_ids()

    def get_teams_of_user(self, user: ClientManager.Client) -> Set[_Team]:
        """
        Return (a shallow copy of) the teams managed by this game user `user` is a player of.
        If the user is part of no such team, an empty set is returned.

        Parameters
        ----------
        user : ClientManager.Client
            User whose teams will be returned.

        Returns
        -------
        Set[_Team]
            Teams the player belongs to.

        """

        return self._team_manager.get_managees_of_user(user)

    def get_users_in_some_team(self):
        """
        Return (a shallow copy of) all the users that are part of some team managed by this game.

        Returns
        -------
        Set[ClientManager.Client]
            Users in some managed team.

        """

        return self._team_manager.get_users_in_some_managee()

    def get_available_team_id(self) -> str:
        """
        Get a team ID that no other team managed by this team has.

        Returns
        -------
        str
            A unique team ID.

        Raises
        ------
        GameError.GameTooManyTeamsError
            If the game is already managing its maximum number of teams.

        """

        try:
            return self._team_manager.get_available_managee_id()
        except PlayerGroupError.ManagerTooManyGroupsError:
            raise GameError.GameTooManyTeamsError

    def unchecked_destroy(self):
        """
        Mark this game as destroyed and notify its manager so that it is deleted.
        If the game is already destroyed, this function does nothing.
        A game marked for destruction will delete all of its timers, teams, remove all its
        players and unsubscribe it from updates of its former players.

        This method is reentrant (it will do nothing though).

        Returns
        -------
        None.

        """

        for timer in self._timer_manager.get_timers():
            self._timer_manager.delete_timer(timer)
        for team in self._team_manager.get_managees():
            team.unchecked_destroy()

        players = self.get_players()
        super().unchecked_destroy()

        for player in players:
            self.listener.unsubscribe(player)

    def _on_client_inbound_ms_check(
        self,
        player: ClientManager.Client,
        contents: Dict[str, Any] = None
        ):
        """
        Default callback for game player signaling it wants to check if sending an IC message
        is appropriate. The IC arguments can be passed by reference, so this also serves as an
        opportunity to modify the IC message if neeeded.

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

        # print('Player', player, 'wants to check sent', contents)

    def _on_client_inbound_ms_final(
        self,
        player: ClientManager.Client,
        contents: Dict[str, Any] = None
        ):
        """
        Default callback for game player signaling it has sent an IC message.
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

        # print('Player', player, 'sent', contents)

    def _on_client_change_character(
        self,
        player: ClientManager.Client,
        old_char_id: Union[int, None] = None,
        new_char_id: Union[int, None] = None
        ):
        """
        Default callback for game player signaling it has changed character.

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

        # print('Player', player, 'changed character from', old_char_id, 'to', new_char_id)
        if self._require_character and not player.has_character():
            self.remove_player(player)

    def _on_client_destroyed(self, player: ClientManager.Client):
        """
        Default callback for game player signaling it was destroyed, for example, as a result
        of a disconnection.

        By default it only removes the player from the game. If the game is already unmanaged or
        the player is not in the game, this callback does nothing.

        Parameters
        ----------
        player : ClientManager.Client
            Player that signaled it was destroyed.

        Returns
        -------
        None.

        """

        # print('Player', player, 'was destroyed', self)
        if self.is_unmanaged():
            return
        if player not in self.get_players():
            return
        self.remove_player(player)

    def _check_structure(self):
        """
        Assert that all invariants specified in the class description are maintained.

        Raises
        ------
        AssertionError
            If any of the invariants are not maintained.

        """

        # 1.
        team_players = self._team_manager.get_users_in_some_managee()
        game_players = self.get_players()
        team_not_in_game = {player for player in team_players if player not in game_players}
        err = (f'For game {self}, expected that every player in the set {team_players} of all '
               f'players in a team managed by the game is in the set {game_players} of players '
               f'of the game, found the following players that did not satisfy this: '
               f'{team_not_in_game}')
        assert team_players.issubset(game_players), err

        # 2.
        listener_parents = {obj.get_parent() for obj in self.listener.get_subscriptions()}
        for player in self.get_players():
            err = (f'For game {self}, expected that its player {player} was among its '
                   f'subscriptions {listener_parents} found it was not.')
            assert player in listener_parents, err

        # 3.
        if self._require_character:
            for player in self.get_players():
                err = (f'For game with areas {self} that expected all its players had '
                       f'characters, found player {player} did not have a character.')
                assert player.has_character(), err

        # 4.
        self._timer_manager._check_structure()
        self._team_manager._check_structure()

    def __str__(self):
        """
        Return a string representation of this game.

        Returns
        -------
        str
            Representation.

        """

        return (f"Game::{self.get_id()}:"
                f"{self.get_players()}:{self.get_leaders()}:{self.get_invitations()}"
                f"{self.get_timers()}:"
                f"{self.get_teams()}")

    def __repr__(self):
        """
        Return a representation of this game.

        Returns
        -------
        str
            Printable representation.

        """

        return (f'_Game(server, {self.get_id()}, "{self.get_id()}", '
                f'player_limit={self.get_player_limit()}, '
                f'player_concurrent_limit={self.get_player_concurrent_limit()}, '
                f'require_players={self.requires_players()}, '
                f'require_invitations={self.requires_invitations()}, '
                f'require_leaders={self.requires_leaders()}, '
                f'require_character={self.requires_characters()}, '
                f'team_limit={self.get_team_limit()}, '
                f'timer_limit={self.get_timer_limit()}, '
                f'|| '
                f'players={self.get_players()}, '
                f'invitations={self.get_invitations()}, '
                f'leaders={self.get_leaders()}, '
                f'timers={self.get_timers()}, '
                f'teams={self.get_teams()}), '
                f'unmanaged={self.is_unmanaged()}), '
                f')')


class _GameManagerTrivialInherited(PlayerGroupManager):
    """
    This class should not be instantiated.
    """



    def __init__(
        self,
        server: TsuserverDR,
        managee_limit: Union[int, None] = None,
        default_managee_type: Type[_Game] = None,
        ):
        """
        Create a game manager object.

        Parameters
        ----------
        server : TsuserverDR
            The server this game manager belongs to.
        managee_limit : int, optional
            The maximum number of games this manager can handle. Defaults to None (no limit).
        default_managee_type : Type[_Game], optional
            The default type of game this manager will create. Defaults to None (and then
            converted to _Game).

        """

        if default_managee_type is None:
            default_managee_type = _Game

        super().__init__(
            server,
            managee_limit=managee_limit,
            default_managee_type=default_managee_type
        )

    def get_managee_type(self) -> Type[_Game]:
        """
        Return the type of the game that will be constructed by default with a call of
        `new_managee`.

        Returns
        -------
        Type[_Game]
            Type of the game.

        """

        return super().get_managee_type()

    def new_managee(
        self,
        managee_type: Type[_Game] = None,
        creator: Union[ClientManager.Client, None] = None,
        player_limit: Union[int, None] = None,
        player_concurrent_limit: Union[int, None] = 1,
        require_invitations: bool = False,
        require_players: bool = True,
        require_leaders: bool = True,
        require_character: bool = False,
        team_limit: Union[int, None] = None,
        timer_limit: Union[int, None] = None,
        **kwargs,
        ) -> _Game:
        """
        Create a new game managed by this manager.

        Parameters
        ----------
        managee_type : Type[_Game], optional
            Class of game that will be produced. Defaults to None (and converted to the default
            game created by this game manager).
        creator : Union[ClientManager.Client, None], optional
            The player who created this game. If set, they will also be added to the game.
            Defaults to None.
        player_limit : Union[int, None], optional
            If an int, it is the maximum number of players the game supports. If None, it
            indicates the game has no player limit. Defaults to None.
        player_concurrent_limit : Union[int, None], optional
            If an int, it is the maximum number of games managed by `self` that any player
            of this game to create may belong to, including this game to create. If None, it
            indicates that this game does not care about how many other games managed by `self`
            each of its players belongs to. Defaults to 1 (a player may not be in another game
            managed by `self` while in this game).
        require_invitations : bool, optional
            If True, users can only be added to the game if they were previously invited. If
            False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the game loses all its players, the game will automatically
            be deleted. If False, no such automatic deletion will happen. Defaults to True.
        require_leaders : bool, optional
            If True, if at any point the game has no leaders left, the game will choose a leader
            among any remaining players left; if no players are left, the next player added will
            be made leader. If False, no such automatic assignment will happen. Defaults to True.
        require_character : bool, optional
            If False, players without a character will not be allowed to join the game, and players
            that switch to something other than a character will be automatically removed from the
            game. If False, no such checks are made. A player without a character is considered
            one where player.has_character() returns False. Defaults to False.
        team_limit : Union[int, None], optional
            If an int, it is the maximum number of teams the game will support. If None, it
            indicates the game will have no team limit. Defaults to None.
        timer_limit : Union[int, None], optional
            If an int, it is the maximum number of timers the game will support. If None, it
            indicates the game will have no timer limit. Defaults to None.
        **kwargs : Any
            Additional arguments to consider when producing the game.

        Returns
        -------
        _Game
            The created game.

        Raises
        ------
        GameError.ManagerTooManyGamesError
            If the manager is already managing its maximum number of games.
        Any error from the created game's add_player(creator)
            If the game cannot add `creator` as a player if given one.

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
            **kwargs,
            )
        self._check_structure()
        return game

    def unchecked_new_managee(
        self,
        managee_type: Type[_Game] = None,
        creator: Union[ClientManager.Client, None] = None,
        player_limit: Union[int, None] = None,
        player_concurrent_limit: Union[int, None] = 1,
        require_invitations: bool = False,
        require_players: bool = True,
        require_leaders: bool = True,
        require_character: bool = False,
        team_limit: Union[int, None] = None,
        timer_limit: Union[int, None] = None,
        **kwargs,
        ) -> _Game:
        """
        Create a new game managed by this manager.

        This method does not assert structural integrity.

        Parameters
        ----------
        managee_type : Type[_Game], optional
            Class of game that will be produced. Defaults to None (and converted to the default
            game created by this game manager).
        creator : Union[ClientManager.Client, None], optional
            The player who created this game. If set, they will also be added to the game.
            Defaults to None.
        player_limit : Union[int, None], optional
            If an int, it is the maximum number of players the game supports. If None, it
            indicates the game has no player limit. Defaults to None.
        player_concurrent_limit : Union[int, None], optional
            If an int, it is the maximum number of games managed by `self` that any player
            of this game to create may belong to, including this game to create. If None, it
            indicates that this game does not care about how many other games managed by `self`
            each of its players belongs to. Defaults to 1 (a player may not be in another game
            managed by `self` while in this game).
        require_invitations : bool, optional
            If True, users can only be added to the game if they were previously invited. If
            False, no checking for invitations is performed. Defaults to False.
        require_players : bool, optional
            If True, if at any point the game loses all its players, the game will automatically
            be deleted. If False, no such automatic deletion will happen. Defaults to True.
        require_leaders : bool, optional
            If True, if at any point the game has no leaders left, the game will choose a leader
            among any remaining players left; if no players are left, the next player added will
            be made leader. If False, no such automatic assignment will happen. Defaults to True.
        require_character : bool, optional
            If False, players without a character will not be allowed to join the game, and players
            that switch to something other than a character will be automatically removed from the
            game. If False, no such checks are made. A player without a character is considered
            one where player.has_character() returns False. Defaults to False.
        team_limit : Union[int, None], optional
            If an int, it is the maximum number of teams the game will support. If None, it
            indicates the game will have no team limit. Defaults to None.
        timer_limit : Union[int, None], optional
            If an int, it is the maximum number of timers the game will support. If None, it
            indicates the game will have no timer limit. Defaults to None.
        **kwargs : Any
            Additional arguments to consider when producing the game.

        Returns
        -------
        _Game
            The created game.

        Raises
        ------
        GameError.ManagerTooManyGamesError
            If the manager is already managing its maximum number of games.
        Any error from the created game's add_player(creator)
            If the game cannot add `creator` as a player if given one.

        """

        try:
            return super().unchecked_new_managee(
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
                **kwargs,
                )
        except PlayerGroupError.ManagerTooManyGroupsError:
            raise GameError.ManagerTooManyGamesError

    def delete_managee(self, managee: _Game) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a game managed by this manager, so all its players no longer belong to this game.

        Parameters
        ----------
        managee : _Game
            The game to delete.

        Returns
        -------
        Tuple[str, Set[ClientManager.Client]]
            The ID and players of the game that was deleted.

        Raises
        ------
        GameError.ManagerDoesNotManageGameError
            If the manager does not manage the target game.

        """

        game_id, game_players = self.unchecked_delete_managee(managee)
        self._check_structure()
        return game_id, game_players

    def unchecked_delete_managee(
        self,
        managee: _Game
        ) -> Tuple[str, Set[ClientManager.Client]]:
        """
        Delete a game managed by this manager, so all its players no longer belong to this game.

        Parameters
        ----------
        managee : _Game
            The game to delete.

        Returns
        -------
        Tuple[str, Set[ClientManager.Client]]
            The ID and players of the game that was deleted.

        Raises
        ------
        GameError.ManagerDoesNotManageGameError
            If the manager does not manage the target game.

        """

        try:
            return super().unchecked_delete_managee(managee)
        except PlayerGroupError.ManagerDoesNotManageGroupError:
            raise GameError.ManagerDoesNotManageGameError

    def manages_managee(self, game: _Game):
        """
        Return True if the game is managed by this manager, False otherwise.

        Parameters
        ----------
        game : _Game
            The game to check.

        Returns
        -------
        bool
            True if the manager manages this game, False otherwise.

        """

        return super().manages_managee(game)

    def get_managees(self) -> Set[_Game]:
        """
        Return (a shallow copy of) the games this manager manages.

        Returns
        -------
        Set[_Game]
            Games this manager manages.

        """

        return super().get_managees()

    def get_managee_by_id(self, managee_id: str) -> _Game:
        """
        If `managee_id` is the ID of a game managed by this manager, return that.

        Parameters
        ----------
        managee_id : str
            ID of the game this manager manages.

        Returns
        -------
        _Game
            The game with that ID.

        Raises
        ------
        GameError.ManagerInvalidGameIDError
            If `game_id` is not the ID of a game this manager manages.

        """

        try:
            return super().get_managee_by_id(managee_id)
        except PlayerGroupError.ManagerInvalidGroupIDError:
            raise GameError.ManagerInvalidGameIDError

    def get_managee_by_numerical_id(self, managee_numerical_id: Union[str, int]) -> _Game:
        """
        If `managee_numerical_id` is the numerical ID of a game managed by this manager,
        return the game.

        Parameters
        ----------
        managee_numerical_id : Union[str, int]
            Numerical ID of the game this manager manages.

        Returns
        -------
        _Game
            The game with that ID.

        Raises
        ------
        GameError.ManagerInvalidGroupIDError:
            If `managee_numerical_id` is not the numerical ID of a game
            this manager manages.

        """

        try:
            return super().get_managee_by_numerical_id(managee_numerical_id)
        except PlayerGroupError.ManagerInvalidGroupIDError:
            raise GameError.ManagerInvalidGameIDError

    def get_managee_limit(self) -> Union[int, None]:
        """
        Return the game limit of this manager.

        Returns
        -------
        Union[int, None]
            Game limit.

        """

        return super().get_managee_limit()

    def get_managee_ids(self) -> Set[str]:
        """
        Return (a shallow copy of) the IDs of all games managed by this manager.

        Returns
        -------
        Set[str]
            The IDs of all managed games.

        """

        return super().get_managee_ids()

    def get_managee_ids_to_managees(self) -> Dict[str, _Game]:
        """
        Return a mapping of the IDs of all games managed by this manager to their associated
        game.

        Returns
        -------
        Dict[str, _Game]
            Mapping.
        """

        return super().get_managee_ids_to_managees()

    def get_managee_numerical_ids_to_managees(self) -> Dict[int, _Game]:
        """
        Return a mapping of the numerical IDs of all games managed by this manager to their
        associated game.

        Returns
        -------
        Dict[int, _Game]
            Mapping.
        """

        return super().get_managee_numerical_ids_to_managees()

    def get_managees_of_user(self, user: ClientManager.Client):
        """
        Return (a shallow copy of) the games managed by this manager user `user` is a
        player of. If the user is part of no such game, an empty set is returned.

        Parameters
        ----------
        user : ClientManager.Client
            User whose games will be returned.

        Returns
        -------
        Set[_Game]
            Games the player belongs to.

        """

        return super().get_managees_of_user(user)

    def get_player_to_managees_map(self) -> Dict[ClientManager.Client, Set[_Game]]:
        """
        Return a mapping of the players part of any game managed by this manager to the
        game managed by this manager such players belong to.

        Returns
        -------
        Dict[ClientManager.Client, Set[_Game]]
            Mapping.
        """

        return super().get_player_to_managees_map()

    def get_users_in_some_managee(self) -> Set[ClientManager.Client]:
        """
        Return (a shallow copy of) all the users that are part of some game managed by this
        manager.

        Returns
        -------
        Set[ClientManager.Client]
            Users in some managed game.

        """

        return super().get_users_in_some_managee()

    def is_managee_creatable(self) -> bool:
        """
        Return whether a new game can currently be created without creating one.

        Returns
        -------
        bool
            True if a game can be currently created, False otherwise.
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
        ) -> Union[_Game, None]:
        """
        For user `user`, find a game `most_restrictive_game` managed by this manager such
        that, if `user` were to join another game managed by this manager, they would
        violate `most_restrictive_game`'s concurrent player membership limit.
        If no such game exists (or the player is not member of any game managed by this
        manager), return None.
        If multiple such games exist, any one of them may be returned.

        Parameters
        ----------
        user : ClientManager.Client
            User to test.

        Returns
        -------
        Union[_Game, None]
            Limiting game as previously described if it exists, None otherwise.

        """

        return super().find_player_concurrent_limiting_managee(user)

class GameManager(_GameManagerTrivialInherited):
    """
    A game manager is a player group manager.

    Attributes
    ----------
    server : TsuserverDR
        Server the game manager belongs to.
    """

    # Invariants
    # ----------
    # 1. The invariants of the parent class are maintained.

    def get_available_managee_id(self):
        """
        Get a game ID that no other game managed by this manager has.

        Returns
        -------
        str
            A unique game ID.

        Raises
        ------
        GameError.ManagerTooManyGamesError
            If the manager is already managing its maximum number of games.

        """

        game_number = 0
        game_limit = self.get_managee_limit()
        while game_limit is None or game_number < game_limit:
            new_game_id = "g{}".format(game_number)
            if new_game_id not in self.get_managee_ids():
                return new_game_id
            game_number += 1
        raise GameError.ManagerTooManyGamesError

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
        Return a representation of this game manager.

        Returns
        -------
        str
            Printable representation.

        """

        return (f"GameManager(server, managee_limit={self.get_managee_limit()}, "
                f"default_managee_type={self.get_managee_type()}, "
                f"|| "
                f"_user_to_managees={self.get_player_to_managees_map()}, "
                f"_id_to_managee={self.get_managee_ids_to_managees()}, "
                f"id={self.get_id()}), ",
                f')')
