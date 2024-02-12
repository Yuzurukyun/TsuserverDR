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
Module that contains the Task class and the TaskManager class.
"""

from __future__ import annotations

import asyncio
import time
import typing

from typing import Any, Callable, Coroutine, Dict, Hashable, Tuple

from server.constants import Constants, Effects
from server.exceptions import TaskError, ServerError

if typing.TYPE_CHECKING:
    from server.client_manager import ClientManager
    from server.tsuserver import TsuserverDR


class Task:
    """
    A task is a wrapper around a coroutine that also stores an owner, name, creation time and
    user modifiable parameters.
    """

    def __init__(
        self,
        async_function: Callable[[Task], Coroutine],
        owner: Hashable,
        name: str,
        creation_time: float,
        parameters: Dict[str, Any]
    ):
        """
        Create a task

        Parameters
        ----------
        async_function : Callable[[Task], Coroutine]
            Async function that describes what the task will do. This async function will be
            scheduled for execution with `self` as its argument.
        owner : Hashable
            Entity that created the task.
        name : str
            Name of the task.
        creation_time : float
            Creation time of the task. Recommended to use time.time().
        parameters : Dict[str, Any]
            User parameters to hold for the task.
        """

        async_future = Constants.create_fragile_task(async_function(self))
        self.asyncio_task = async_future
        self.owner = owner
        self.name = name
        self.creation_time = creation_time
        self.parameters = parameters.copy()


class TaskManager:
    """
    A task manager is a manager for tasks.

    Tasks should only be created with a task manager.
    """

    def __init__(self, server: TsuserverDR):
        """
        Parameters
        ----------
        server: TsuserverDR
            Server of the task manager.
        """

        self.server = server
        self.tasks: Dict[Hashable, Dict[str, Task]] = dict()
        self.active_timers: Dict[str, ClientManager.Client] = dict()

    def new_task(
        self,
        owner: Hashable,
        name: str,
        parameters: Dict[str, Any] = None
    ) -> Task:
        """
        Create a new task with a particular name and owner. If a task linked to that owner and name
        already exists, it will be scheduled for cancellation and replaced with this new task.

        Parameters
        ----------
        owner : Hashable
            Entity that created the task.
        name : str
            Name of the task. This should be the name of an async function defined within the class.
        parameters : Dict[str, Any], optional
            Initial user parameters of the task, by default None (and converted to an empty
            dictionary).

        Returns
        -------
        Task
            Created task.
        """

        if parameters is None:
            parameters = dict()

        try:
            old_task = self.get_task(owner, name)
        except TaskError.TaskNotFoundError:
            pass
        else:
            if not old_task.asyncio_task.done() and not old_task.asyncio_task.cancelled():
                self.force_asyncio_cancelled_error(old_task)

        async_function = getattr(self, name)
        creation_time = time.time()

        if owner not in self.tasks:
            self.tasks[owner] = dict()

        self.tasks[owner][name] = Task(async_function, owner, name, creation_time, parameters)
        return self.tasks[owner][name]

    def force_asyncio_cancelled_error(
        self,
        task: Task
    ):
        """
        Force the task to raise an asyncio.CancelledError. This is useful to change execution flow
        when a task is internally sleeping.

        Parameters
        ----------
        task : Task
            Task that will be forced to raise an asyncio.CancelledError.
        """

        task.asyncio_task.cancel()
        # TODO: For some odd reason, it complains if I set it to create_task. Figure that out.
        asyncio.ensure_future(Constants.await_cancellation(task.asyncio_task))

    def delete_task(
        self,
        owner: Hashable,
        name: str,
    ):
        """
        Attempt to delete a task linked to an owner and name.

        Parameters
        ----------
        owner : Hashable
            Owner of the task.
        name : str
            Name of the task.

        Raises
        ------
        TaskError.TaskNotFoundError
            If no such task exists.
        """

        task = self.get_task(owner, name)
        owner_tasks = self.tasks[owner]
        owner_tasks.pop(name)
        self.force_asyncio_cancelled_error(task)

    def get_task(
        self,
        owner: Hashable,
        name: str,
    ) -> Task:
        """
        Attempt to get a task linked to an owner and name.

        Parameters
        ----------
        owner : Hashable
            Owner of the task.
        name : str
            Name of the task.

        Returns
        -------
        Task
            Task that matches the description.

        Raises
        ------
        TaskError.TaskNotFoundError
            If no such task exists.
        """

        try:
            owner_tasks = self.tasks[owner]
        except KeyError:
            raise TaskError.TaskNotFoundError

        try:
            task = owner_tasks[name]
        except KeyError:
            raise TaskError.TaskNotFoundError

        return task

    def is_task(
        self,
        owner: Hashable,
        name: str,
    ) -> bool:
        """
        Return whether there exists a task managed by this manager with given owner and name.

        Parameters
        ----------
        owner : Hashable
            Owner of the task.
        name : str
            Name of the task.

        Returns
        -------
        bool
            Whether such a task exists.
        """

        try:
            self.get_task(owner, name)
            return True
        except TaskError.TaskNotFoundError:
            return False

    ######
    # Currently supported tasks
    ######

    async def as_afk_kick(self, task: Task):
        client: ClientManager.Client = task.owner
        afk_delay: int = task.parameters['afk_delay']
        afk_sendto: int = task.parameters['afk_sendto']

        try:
            delay = int(afk_delay)*60  # afk_delay is in minutes, so convert to seconds
        except (TypeError, ValueError):
            # This shouldn't happen with a well-verified area list
            info = ('The area file contains an invalid AFK kick delay for area {}: {}'.
                    format(client.area.id, afk_delay))
            raise RuntimeError(info)

        if delay <= 0:  # Assumes 0-minute delay means that AFK kicking is disabled
            return

        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            raise
        else:
            try:
                area = client.hub.area_manager.get_area_by_id(int(afk_sendto))
            except Exception:
                # This shouldn't happen with a well-verified area list
                info = ('The area file contains an invalid AFK kick destination area for area {}: '
                        '{}'.format(client.area.id, afk_sendto))
                raise RuntimeError(info)
            if client.area.id == afk_sendto:  # Don't try and kick back to same area
                return
            if not client.has_participant_character():  # Assumes spectators are exempted from AFK kicks
                return
            if client.is_staff():  # Assumes staff are exempted from AFK kicks
                return

            try:
                original_area = client.area
                original_name = client.displayname
                client.change_area(area, override_passages=True, override_effects=True,
                                   ignore_bleeding=True)
            except Exception:
                pass  # Server raised an error trying to perform the AFK kick, ignore AFK kick
            else:
                client.send_ooc('You were kicked from area {} to area {} for being inactive for '
                                '{} minutes.'.format(original_area.id, afk_sendto, afk_delay))

                if client.area.is_locked or client.area.is_modlocked:
                    try:  # Try and remove the IPID from the area's invite list
                        client.area.invite_list.pop(client.ipid)
                    except KeyError:
                        # only happens if target had joined the locked area through mod powers
                        pass

                if client.party:
                    p = client.party
                    client.party.remove_member(client)
                    client.send_ooc('You were also kicked off from your party.')
                    for c in p.get_members():
                        c.send_ooc('{} was AFK kicked from your party.'.format(original_name))

    async def as_day_cycle(self, task: Task):
        client: ClientManager.Client = task.owner
        area_1: int = task.parameters['area_1']
        area_2: int = task.parameters['area_2']
        hour_length: int = task.parameters['hour_length']
        hour_start: int = task.parameters['hour_start']
        hours_in_day: int = task.parameters['hours_in_day']
        send_first_hour: bool = task.parameters['send_first_hour']

        hour = hour_start
        hub = client.hub  # For later, in case client changes hub
        minute_at_interruption = 0
        main_hour_length = hour_length
        time_started_at = time.time()
        time_refreshed_at = time.time()  # Doesnt need init, but PyLint complains otherwise
        periods = list()
        force_period_refresh = False
        current_period = (-1, '', main_hour_length)
        notify_others = False

        # Initialize task attributes
        task.parameters['is_paused'] = False
        task.parameters['is_unknown'] = False
        task.parameters['refresh_reason'] = ''
        task.parameters['period'] = ''
        task.parameters['hours_in_day'] = hours_in_day
        task.parameters['main_hour_length'] = main_hour_length

        # Manually notify for the very first hour (if needed)
        targets = [c for c in client.hub.get_players() if c == client or
                   ((c.is_staff() or send_first_hour)
                    and area_1 <= c.area.id <= area_2)]
        for c in targets:
            c.send_ooc('It is now {}:00.'.format('{0:02d}'.format(hour)))
            c.send_clock(client_id=client.id, hour=hour)

        def find_period_of_hour(hour) -> Tuple[int, str, int]:
            if not periods:
                return (-1, '', main_hour_length)
            if hour < periods[0][0]:
                return periods[-1]
            output = None
            for period_tuple in periods:
                period_start, _, _ = period_tuple
                if hour >= period_start:
                    output = period_tuple
            return output

        while True:
            try:
                refresh_reason = task.parameters['refresh_reason']
                task.parameters['refresh_reason'] = ''

                # If timer is in unknown phase, there is no time progression
                # Check again in one second.
                if task.parameters['is_unknown']:
                    # Manually restart other flags because they are no longer relevant
                    notify_others = True
                    await asyncio.sleep(1)
                    continue

                # If timer is paused, check again in one second.
                if task.parameters['is_paused']:
                    # Manually restart other flags because they are no longer relevant
                    notify_others = True
                    await asyncio.sleep(1)
                    continue

                # Otherwise, timer is not paused, so either an hour just finished or the timer
                # was refreshed for some reason (unpausing, new period, etc.)
                # If the clock was just set again, do not wait, execute actions immediately
                if refresh_reason in ['set', 'set_hours_reset']:
                    pass

                # If the clock just had a new period added, its number of hours changed, or was just
                # unpaused, restart the current hour
                elif refresh_reason in ['period', 'unpause', 'set_hours_proceed']:
                    notify_others = True
                    await asyncio.sleep((60-minute_at_interruption)/60 * hour_length)
                # Otherwise, just wait full hour
                else:
                    notify_others = True
                    await asyncio.sleep(hour_length)

                # After handling any interrupts, an hour just finished without any
                # interruptions
                # In all cases now, update hour
                # We can do that as code only runs here if the timer is not paused
                hour = (hour + 1) % hours_in_day
                targets = [c for c in client.hub.get_players()
                           if c == client
                           or (notify_others and area_1 <= c.area.id <= area_2)]

                # Check if new period has started
                if not periods:
                    if current_period[1] != '':
                        for c in targets:
                            task.parameters['period'] = ''
                            c.send_time_of_day(name='')
                            c.send_ooc('It is no longer some particular period of day.')
                    current_period = find_period_of_hour(hour)
                    hour_length = main_hour_length
                else:
                    current_period = find_period_of_hour(hour)
                    new_period_start, new_period_name, new_period_length = current_period
                    hour_length = new_period_length
                    if new_period_start == hour or force_period_refresh:
                        for c in targets:
                            task.parameters['period'] = new_period_name
                            c.send_time_of_day(name=new_period_name)
                            c.send_ooc(f'It is now {new_period_name}.')
                force_period_refresh = False

                # Regardless of new period, send other packets
                for c in targets:
                    c.send_ooc('It is now {}:00.'.format('{0:02d}'.format(hour)))
                    c.send_clock(client_id=client.id, hour=hour)

                time_started_at = time.time()
                minute_at_interruption = 0
                notify_others = True

            except (asyncio.CancelledError, KeyError):
                # Code can run here for a few reasons
                # 1. The timer was ended
                # 2. The clock current hour and hourt length was manually set
                # 3. The clock's number of hours was manually set
                # 4. The clock was set to be at an unknown time
                # 5. A new period was added
                # 6. The clock was just unpaused
                # 7. The clock was just paused
                time_refreshed_at = time.time()

                if 'refresh_reason' not in task.parameters:
                    task.parameters['refresh_reason'] = ''

                refresh_reason = task.parameters['refresh_reason']

                if not refresh_reason:
                    # refresh_reason may be undefined or the empty string.
                    # Both cases imply cancelation
                    for c in targets:
                        c.send_clock(client_id=client.id, hour=-1)
                        c.send_time_of_day(name='')  # Reset time of day
                    client.send_ooc('Your day cycle in areas {} through {} has been ended.'
                                    .format(area_1, area_2))
                    client.send_ooc_others('(X) The day cycle initiated by {} in areas {} through '
                                           '{} has been ended.'
                                           .format(client.name, area_1, area_2),
                                           is_zstaff_flex=True, in_hub=hub)
                    targets = [c for c in client.hub.get_players()
                               if c == client or area_1 <= c.area.id <= area_2]
                    break

                if refresh_reason == 'set':
                    old_hour = hour
                    hour_length, hour = task.parameters['new_day_cycle_args']
                    main_hour_length = hour_length
                    task.parameters['main_hour_length'] = main_hour_length

                    # Do not notify of clock set to normies if only hour length changed
                    notify_others = (old_hour != hour)
                    minute_at_interruption = 0
                    force_period_refresh = True
                    str_hour = '{0:02d}'.format(hour)
                    task.parameters['is_unknown'] = False
                    client.send_ooc('Your day cycle in areas {} through {} was updated. New hour '
                                    'length: {} seconds. New hour: {}:00.'
                                    .format(area_1, area_2, hour_length, str_hour))
                    client.send_ooc_others('(X) The day cycle initiated by {} in areas {} through '
                                           '{} has been updated. New hour length: {} seconds. '
                                           'New hour: {}:00.'
                                           .format(client.name, area_1, area_2, hour_length,
                                                   str_hour),
                                           is_zstaff_flex=True, in_hub=hub)
                    # Setting time does not unpause the timer, warn clock master
                    if task.parameters['is_paused']:
                        client.send_ooc('(X) Warning: Your day cycle is still paused.')

                    # Moreover, hour is +1'd automatically if the clock is unpaused
                    # So preemptively -1
                    if not task.parameters['is_paused']:
                        hour -= 1  # Take one hour away, because an hour would be added anyway

                    # This does not modify the hour length of active periods, so if there are any
                    # periods, warn clock master
                    if periods:
                        client.send_ooc('(X) Warning: A period is currently active, so the day '
                                        'cycle is using its hour length. Modify its hour length '
                                        'using /clock_period.')

                elif refresh_reason == 'set_hours':
                    old_hour = hour
                    task.parameters['refresh_reason'] = 'set_hours_proceed'
                    # Only update minute and time started at if timer is not paused
                    if not task.parameters['is_paused']:
                        minute_at_interruption += (time_refreshed_at-time_started_at)/hour_length*60
                        time_started_at = time.time()

                    hours_in_day = task.parameters['hours_in_day']
                    client.send_ooc(f'Your day cycle in areas {area_1} through {area_2} was '
                                    f'updated. New number of hours in the day: {hours_in_day} '
                                    f'hours.')
                    client.send_ooc_others(f'(X) The day cycle initiated by {client.displayname} '
                                           f'[{client.id}] in areas {area_1} through {area_2} has '
                                           f'been updated. New number of hours in the day: '
                                           f'{hours_in_day} hours.',
                                           is_zstaff_flex=True, in_hub=hub)
                    # Check if current hours exceed new number of hours in the day
                    if hour >= hours_in_day:
                        hour = 0
                        minute_at_interruption = 0
                        task.parameters['refresh_reason'] = 'set_hours_reset'
                        client.send_ooc(f'(X) The current hour {old_hour} was beyond the new '
                                        f'number of hours in the day you set, so your current hour '
                                        f'was set to 0.')
                        client.send_ooc_others(f'(X) The day cycle initiated by '
                                               f'{client.displayname} [{client.id}] in areas '
                                               f'{area_1} through {area_2} has had its current '
                                               f'hour be set to 0 because it was beyond the number '
                                               f'of hours it was set to now have.',
                                               is_zstaff_flex=True, in_hub=hub,
                                               pred=lambda c: area_1 <= c.area.id <= area_2)

                        # Moreover, hour is +1'd automatically if the clock is unpaused
                        # So preemptively -1
                        if not task.parameters['is_paused']:
                            hour -= 1  # Take one hour away, because an hour would be added anyway

                    # Pop any periods that are beyond the new number of hours in the day
                    popped_periods = list()
                    for (period_start, period_name) in periods.copy():
                        if period_start >= hours_in_day:
                            periods.remove((period_start, period_name))
                            popped_periods.append((period_start, period_name))
                    if popped_periods:
                        client.send_ooc(f'(X) The following periods were removed from the list of '
                                        f'periods as they were beyond the new number of hours in '
                                        f'the day: {popped_periods}.')
                        client.send_ooc_others(f'(X) The day cycle initiated by '
                                               f'{client.displayname} [{client.id}] in areas '
                                               f'{area_1} through {area_2} has had the following '
                                               f'periods be removed from the list of periods as '
                                               f'they were beyond the number of hours it was set '
                                               f'to now have: {popped_periods}.',
                                               is_zstaff_flex=True, in_hub=hub,
                                               pred=lambda c: area_1 <= c.area.id <= area_2)

                    force_period_refresh = True  # Super conservative but always correct.
                    # Setting time does not unpause the timer, warn clock master
                    if task.parameters['is_paused']:
                        client.send_ooc('(X) Warning: Your day cycle is still paused.')

                elif refresh_reason == 'unknown':
                    hour = -1
                    task.parameters['is_unknown'] = True

                    client.send_ooc('You have set the time to be unknown.')
                    client.send_ooc_others(f'(X) The day cycle initiated by {client.displayname} '
                                           f'[{client.id}] in areas {area_1} through {area_2} has '
                                           f'been set to be at an unknown time.',
                                           is_zstaff_flex=True, in_hub=hub,
                                           pred=lambda c: area_1 <= c.area.id <= area_2)
                    client.send_ooc_others('You seem to have lost track of time.',
                                           is_zstaff_flex=False, in_hub=hub,
                                           pred=lambda c: area_1 <= c.area.id <= area_2)

                    task.parameters['period'] = 'unknown'
                    targets = [c for c in client.hub.get_players()
                               if c == client or (area_1 <= c.area.id <= area_2)]
                    for c in targets:
                        c.send_clock(client_id=client.id, hour=-1)
                        c.send_time_of_day(name='unknown')

                elif refresh_reason == 'period':
                    # Only update minute and time started at if timer is not paused
                    if not task.parameters['is_paused']:
                        minute_at_interruption += (time_refreshed_at-time_started_at)/hour_length*60
                        time_started_at = time.time()
                    start, name, length = task.parameters['new_period_start']

                    # Pop entries with same start or name if needed (duplicated entries)
                    found = False
                    for (entry_start, entry_name, entry_length) in periods.copy():
                        if entry_start == start or entry_name == name:
                            periods.remove((entry_start, entry_name, entry_length))
                            found = True

                    if not found and start < 0:
                        # Check if attempted to remove a non-existing period
                        client.send_ooc(f'Period `{name}` not found.')
                    else:
                        if start >= 0:
                            periods.append((start, name, length))

                        # start=-1 is used to indicate *please erase this period name*. By the previous
                        # for loop, any matching period names are removed, and by the if statement
                        # -1 is not added.

                        periods.sort()
                        # Decide which period the current hour belongs to
                        # Note it could be possible the current hour is smaller than than the first
                        # period start. By wrapping around 24 hours logic, that means the current
                        # period is the one given by the latest period.

                        # Also note this is only relevant if the time is not unknown. If it is,
                        # then no updates should be sent
                        changed_current_period = False
                        if not task.parameters['is_unknown']:
                            new_period_start, new_period_name, new_period_length = find_period_of_hour(hour)
                            changed_current_period = (current_period[1] != new_period_name)
                            current_period = new_period_start, new_period_name, new_period_length
                            if periods and new_period_start == hour:
                                changed_current_period = True

                        if changed_current_period:
                            targets = [c for c in client.hub.get_players()
                                       if c == client or area_1 <= c.area.id <= area_2]
                            task.parameters['period'] = new_period_name
                            if new_period_name:
                                for c in targets:
                                    c.send_time_of_day(name=new_period_name)
                                    c.send_ooc(f'It is now {new_period_name}.')
                            else:
                                for c in targets:
                                    c.send_time_of_day(name='')
                                    c.send_ooc('It is no longer some particular period of day.')

                        # Send notifications appropriately
                        if start >= 0:
                            # Case added a period
                            formatted_time = '{}:00'.format('{0:02d}'.format(start))
                            client.send_ooc(f'(X) You have added period `{name}`. '
                                            f'Period hour length: {current_period[2]} seconds. '
                                            f'Period hour start: {formatted_time}.')
                            client.send_ooc_others(
                                f'(X) {client.displayname} [{client.id}] has added period `{name}` '
                                f'to their day cycle. '
                                f'Period hour length: {current_period[2]} seconds. '
                                f'Period hour start: {formatted_time} '
                                f'({client.area.id}).',
                                is_zstaff_flex=True, in_hub=hub,
                            )
                        else:
                            # Case removed a period
                            client.send_ooc(f'(X) You have removed period `{name}`.')
                            client.send_ooc_others(f'(X) {client.displayname} [{client.id}] has '
                                                   f'removed period `{name}` off their day cycle '
                                                   f'({client.area.id}).',
                                                   is_zstaff_flex=True, in_hub=hub)
                elif refresh_reason == 'unpause':
                    task.parameters['is_paused'] = False

                    client.send_ooc('Your day cycle in areas {} through {} has been unpaused.'
                                    .format(area_1, area_2))
                    client.send_ooc_others('(X) The day cycle initiated by {} in areas {} through '
                                           '{} has been unpaused.'
                                           .format(client.name, area_1, area_2),
                                           is_zstaff_flex=True, in_hub=hub)

                    time_started_at = time.time()
                    igt_now = '{}:{}'.format('{0:02d}'.format(hour),
                                             '{0:02d}'.format(int(minute_at_interruption)))
                    igt_rounded = '{}:00.'.format('{0:02d}'.format(hour))
                    client.send_ooc('It is now {}.'.format(igt_now))
                    client.send_ooc_others('It is now {}.'.format(igt_now),
                                           is_zstaff_flex=True, in_hub=hub,
                                           pred=lambda c: area_1 <= c.area.id <= area_2)
                    client.send_ooc_others('It is now some time past {}.'.format(igt_rounded),
                                           is_zstaff_flex=False, in_hub=hub,
                                           pred=lambda c: area_1 <= c.area.id <= area_2)
                    targets = [c for c in client.hub.get_players()
                               if c == client or area_1 <= c.area.id <= area_2]
                    for c in targets:
                        c.send_clock(client_id=client.id, hour=hour)

                elif refresh_reason == 'pause':
                    task.parameters['is_paused'] = True

                    minute_at_interruption += (time_refreshed_at - time_started_at)/hour_length*60
                    igt_now = '{}:{}'.format('{0:02d}'.format(hour),
                                             '{0:02d}'.format(int(minute_at_interruption)))
                    client.send_ooc('Your day cycle in areas {} through {} has been paused at {}.'
                                    .format(area_1, area_2, igt_now))
                    client.send_ooc_others('(X) The day cycle initiated by {} in areas {} through '
                                           '{} has been paused at {}.'
                                           .format(client.name, area_1, area_2, igt_now),
                                           is_zstaff_flex=True, in_hub=hub)
                else:
                    raise ValueError(f'Unknown refresh reason {refresh_reason} for day cycle.')

    async def _as_effect(self, task: Task):
        client: ClientManager.Client = task.owner
        length: int = task.parameters['length']    # Length in seconds, already converted
        effect: Effects = task.parameters['effect']
        new_value: bool = task.parameters['new_value']

        try:
            await asyncio.sleep(length)
        except asyncio.CancelledError:
            pass  # Cancellation messages via send_oocs must be sent manually
        else:
            if new_value:
                client.send_ooc('The effect `{}` kicked in.'.format(effect.name))
                client.send_ooc_others('(X) {} [{}] is now subject to the effect `{}`.'
                                       .format(client.displayname, client.id, effect.name),
                                       is_zstaff_flex=True)
                effect.function(client, True)
            else:
                client.send_ooc('The effect `{}` stopped.')
                client.send_ooc_others('(X) {} [{}] is no longer subject to the effect `{}`.'
                                       .format(client.displayname, client.id, effect.name),
                                       is_zstaff_flex=True)
                effect.function(client, False)

    async def as_effect_blindness(self, task: Task):
        await self._as_effect(task)

    async def as_effect_deafness(self, task: Task):
        await self._as_effect(task)

    async def as_effect_gagged(self, task: Task):
        await self._as_effect(task)

    async def as_handicap(self, task: Task):
        client: ClientManager.Client = task.owner
        length: int = task.parameters['length']
        handicap_name: str = task.parameters['handicap_name']
        announce_if_over: bool = task.parameters['announce_if_over']

        client.is_movement_handicapped = True

        try:
            await asyncio.sleep(length)
        except asyncio.CancelledError:
            pass  # Cancellation messages via send_oocs must be sent manually
        else:
            if announce_if_over and not client.is_staff():
                client.send_ooc('Your movement handicap has expired. You may move to a new area.')
        finally:
            client.is_movement_handicapped = False

    async def as_timer(self, task: Task):
        client: ClientManager.Client = task.owner
        length: int = task.parameters['length']  # Length in seconds, already converted
        timer_name: str = task.parameters['timer_name']
        is_public: bool = task.parameters['is_public']

        client_name = client.name  # Failsafe in case disconnection before task is cancelled/expires

        try:
            await asyncio.sleep(length)
        except asyncio.CancelledError:
            client.send_ooc(f'Your timer {timer_name} has been ended.')
            client.send_ooc_others(
                f'Timer "{timer_name}" initiated by {client_name} has been ended.',
                pred=lambda c: (c.is_staff() or (is_public and c.area == client.area)))
        else:
            client.send_ooc(f'Your timer {timer_name} has expired.')
            client.send_ooc_others(
                f'Timer "{timer_name}" initiated by {timer_name} has expired.',
                pred=lambda c: (c.is_staff() or (is_public and c.area == client.area)))
        finally:
            del self.active_timers[timer_name]

    async def as_lurk(self, task: Task):
        client: ClientManager.Client = task.owner
        length: int = task.parameters['length']

        # The lurk callout timer once it finishes will restart itself except if cancelled
        while True:
            try:
                await asyncio.sleep(length)
            except asyncio.CancelledError:
                break  # Cancellation messages via send_oocs must be sent manually
            else:
                if client.is_gagged:
                    client.send_ooc_others('(X) Gagged player {} has not attempted to speak in the '
                                           'past {} seconds'.format(client.displayname, length),
                                           is_zstaff_flex=True, in_area=True)
                    client.send_ooc_others('You see {} not speaking, but they seem to not be able '
                                           'speak.'.format(client.displayname),
                                           is_zstaff_flex=False, in_area=True, is_blind=False)
                else:
                    client.send_ooc_others('(X) {} has not spoken in the past {} seconds.'
                                           .format(client.displayname, length),
                                           is_zstaff_flex=True, in_area=True)
                    # Only deaf and blind players would not be able to automatically tell someone
                    # had not been talking for a while.
                    client.send_ooc_others('{} is being tightlipped.'.format(client.displayname),
                                           is_zstaff_flex=False, in_area=True,
                                           pred=lambda c: not (c.is_blind and c.is_deaf))

    async def as_phantom_peek(self, task: Task):
        client: ClientManager.Client = task.owner
        length: int = task.parameters['length']

        try:
            await asyncio.sleep(length)
        except asyncio.CancelledError:
            return
        else:
            if client.is_blind:
                return
            if not client.area.lights:
                return
            if client.area.lobby_area:
                return
            if client.area.private_area:
                return
            if client.is_staff():
                return
            if not client.has_participant_character():
                return
            client.send_ooc('You feel as though you are being peeked on.')
