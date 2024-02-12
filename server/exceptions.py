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

# This whole class will be rewritten for 4.3

class TsuserverException(Exception):
    def __init__(self, message='', code=None):
        self.message = message
        if code:
            self.code = code

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        if self.message != other.message:
            return False
        return True

    @classmethod
    def subexceptions(cls):
        return [item for item in cls.__dict__.keys() if not item.startswith('__')]

    @classmethod
    def reset_subexceptions(cls):
        for subexception_name in cls.subexceptions():
            setattr(cls, subexception_name, type(subexception_name, (cls, ), dict()))


def recreate_subexceptions(cls):
    """
    Recreate all subexceptions so that their parent is the exception class itself, rather
    than TsuserverException.

    """
    #subexceptions = [item for item in cls.__dict__.keys() if not item.startswith('__')]

    current_class = cls
    subexceptions = set()
    while current_class != TsuserverException:
        subexceptions |= {item for item in current_class.__dict__.keys()
                          if not item.startswith('__')}
        current_class = current_class.__bases__[0]

    for subexception_name in subexceptions:
        fullname = '{}.{}'.format(cls.__name__, subexception_name)
        setattr(cls, subexception_name, type(fullname, (cls, ), dict()))
    return cls


@recreate_subexceptions
class ClientError(TsuserverException):
    class UnauthorizedError(TsuserverException):
        pass


@recreate_subexceptions
class AOProtocolError(TsuserverException):
    class InvalidInboundPacketArguments(TsuserverException):
        pass


@recreate_subexceptions
class AreaError(TsuserverException):
    class ClientNotFound(TsuserverException):
        pass


@recreate_subexceptions
class BackgroundError(TsuserverException):
    class BackgroundNotFoundError(TsuserverException):
        pass


@recreate_subexceptions
class CharacterError(TsuserverException):
    class CharacterNotFoundError(TsuserverException):
        pass

    class CharacterIDNotFoundError(TsuserverException):
        pass


@recreate_subexceptions
class MusicError(TsuserverException):
    class MusicNotFoundError(TsuserverException):
        pass


class ArgumentError(TsuserverException):
    pass


@recreate_subexceptions
class ServerError(TsuserverException):
    class FileSyntaxError(TsuserverException):
        pass

    class FileInvalidNameError(TsuserverException):
        pass

    class FileNotCreatedError(TsuserverException):
        pass

    class FileNotFoundError(TsuserverException):
        pass

    class FileOSError(TsuserverException):
        pass

    class MusicNotFoundError(TsuserverException):
        pass

    class YAMLNotFoundError(TsuserverException):
        pass

    class YAMLInvalidError(TsuserverException):
        pass


class PartyError(TsuserverException):
    pass


@recreate_subexceptions
class PlayerGroupError(TsuserverException):
    class UserAlreadyPlayerError(TsuserverException):
        pass

    class UserAlreadyInvitedError(TsuserverException):
        pass

    class UserAlreadyLeaderError(TsuserverException):
        pass

    class UserHitGroupConcurrentLimitError(TsuserverException):
        pass

    class UserInNoGroupError(TsuserverException):
        pass

    class UserNotInvitedError(TsuserverException):
        pass

    class UserNotPlayerError(TsuserverException):
        pass

    class UserNotLeaderError(TsuserverException):
        pass

    class GroupIsEmptyError(TsuserverException):
        pass

    class GroupIsFullError(TsuserverException):
        pass

    class GroupDoesNotTakeInvitationsError(TsuserverException):
        pass

    class GroupIsUnmanagedError(TsuserverException):
        pass

    class ManagerTooManyGroupsError(TsuserverException):
        pass

    class ManagerDoesNotManageGroupError(TsuserverException):
        pass

    class ManagerInvalidGroupIDError(TsuserverException):
        pass


@recreate_subexceptions
class TimerError(TsuserverException):
    class TimerTooLowError(TsuserverException):
        pass

    class TimerTooHighError(TsuserverException):
        pass

    class InvalidMinTimerValueError(TsuserverException):
        pass

    class InvalidMaxTimerValueError(TsuserverException):
        pass

    class InvalidTickRateError(TsuserverException):
        pass

    class AlreadyStartedTimerError(TsuserverException):
        pass

    class NotStartedTimerError(TsuserverException):
        pass

    class AlreadyPausedTimerError(TsuserverException):
        pass

    class NotPausedTimerError(TsuserverException):
        pass

    class AlreadyTerminatedTimerError(TsuserverException):
        pass

    class ManagerTooManyTimersError(TsuserverException):
        pass

    class ManagerDoesNotManageTimerError(TsuserverException):
        pass

    class ManagerInvalidTimerIDError(TsuserverException):
        pass


@recreate_subexceptions
class ZoneError(TsuserverException):
    class AreaConflictError(TsuserverException):
        pass

    class AreaNotInZoneError(TsuserverException):
        pass

    class PlayerConflictError(TsuserverException):
        pass

    class PlayerNotInZoneError(TsuserverException):
        pass

    class WatcherConflictError(TsuserverException):
        pass

    class WatcherNotInZoneError(TsuserverException):
        pass

    class PropertyNotFoundError(TsuserverException):
        pass


@recreate_subexceptions
class GameError(TsuserverException):
    class UserAlreadyPlayerError(TsuserverException):
        pass

    class UserAlreadyInvitedError(TsuserverException):
        pass

    class UserAlreadyLeaderError(TsuserverException):
        pass

    class UserHitGameConcurrentLimitError(TsuserverException):
        pass

    class UserInNoGameError(TsuserverException):
        pass

    class UserInAnotherTeamError(TsuserverException):
        pass

    class UserInNoTeamError(TsuserverException):
        pass

    class UserNotInvitedError(TsuserverException):
        pass

    class UserNotPlayerError(TsuserverException):
        pass

    class UserNotLeaderError(TsuserverException):
        pass

    class UserDoesNotSatisfyConditionsError(TsuserverException):
        pass

    class UserHasNoCharacterError(TsuserverException):
        pass

    class GameIsEmptyError(TsuserverException):
        pass

    class GameIsFullError(TsuserverException):
        pass

    class GameDoesNotTakeInvitationsError(TsuserverException):
        pass

    class GameIsUnmanagedError(TsuserverException):
        pass

    class GameTooManyTimersError(TsuserverException):
        pass

    class GameDoesNotManageTimerError(TsuserverException):
        pass

    class GameInvalidTimerIDError(TsuserverException):
        pass

    class GameTooManyTeamsError(TsuserverException):
        pass

    class GameDoesNotManageTeamError(TsuserverException):
        pass

    class GameInvalidTeamIDError(TsuserverException):
        pass

    class ManagerTooManyGamesError(TsuserverException):
        pass

    class ManagerDoesNotManageGameError(TsuserverException):
        pass

    class ManagerInvalidGameIDError(TsuserverException):
        pass


@recreate_subexceptions
class GameWithAreasError(GameError):
    class UserNotInAreaError(GameError):
        pass

    class AreaAlreadyInGameError(GameError):
        pass

    class AreaNotInGameError(GameError):
        pass

    class AreaHitGameConcurrentLimitError(TsuserverException):
        pass


@recreate_subexceptions
class HubbedGameError(GameWithAreasError):
    class AreaNotInHubError(GameWithAreasError):
        pass


@recreate_subexceptions
class TrialError(HubbedGameError):
    class AreaDisallowsBulletsError(GameWithAreasError):
        pass

    class UserNotInMinigameError(GameWithAreasError):
        pass

    class InfluenceIsInvalidError(GameWithAreasError):
        pass

    class FocusIsInvalidError(GameWithAreasError):
        pass


@recreate_subexceptions
class TrialMinigameError(HubbedGameError):
    pass


@recreate_subexceptions
class NonStopDebateError(TrialMinigameError):
    class NSDAlreadyInModeError(TrialMinigameError):
        pass

    class NSDNotInModeError(TrialMinigameError):
        pass

    class NSDNoMessagesError(TrialMinigameError):
        pass

    class TimersAlreadySetupError(TrialMinigameError):
        pass


@recreate_subexceptions
class HubError(GameWithAreasError):
    class ManagerCannotManageeNoManagees(GameWithAreasError):
        pass


@recreate_subexceptions
class TaskError(TsuserverException):
    class TaskNotFoundError(TsuserverException):
        pass
