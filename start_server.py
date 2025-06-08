#!/usr/bin/env python3

# TsuserverDR, server software for Danganronpa Online based on tsuserver3,
# which is server software for Attorney Online.
#
# Copyright (C) 2016 argoneus <argoneuscze@gmail.com> (original tsuserver3)
#           (C) 2018-22 Chrezm/Iuvee <thechrezm@gmail.com> (further additions)
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

# WARNING!
# This class will suffer major reworkings for 4.3

import asyncio
import os
import pathlib
import sys
import traceback

from server import logger
from server.tsuserver import TsuserverDR


def _mandatory_python_version_check():
    current_python_tuple = sys.version_info
    current_python_simple = 'Python {}.{}.{}'.format(*current_python_tuple[:3])
    if current_python_tuple < (3, 9):
        # This deliberately uses .format() because f-strings were not available prior to
        # Python 3.7, and 3.7 < 3.9
        msg = ('This version of TsuserverDR requires at least Python 3.9. You currently have '
               '{}. Please refer to README.md for instructions on updating.'
               .format(current_python_simple))
        raise RuntimeError(msg)


def _upcoming_python_version_check():
    current_python_tuple = sys.version_info
    current_python_simple = 'Python {}.{}.{}'.format(*current_python_tuple[:3])
    if current_python_tuple < (3, 9):
        msg = (f'WARNING: The upcoming major release of TsuserverDR (4.4.0) will be requiring '
               f'at least Python 3.9. You currently have {current_python_simple}. '
               f'Please consider upgrading to at least Python 3.9 soon. You may find '
               f'additional instructions on updating in README.md')
        logger.log_print(msg)


async def _normal_shutdown(server=None):
    if not server:
        logger.log_pserver('Server has successfully shut down.')
        return

    await server.normal_shutdown()


async def _abnormal_shutdown(exception, server=None):
    # Print complete traceback to console
    etype, evalue, etraceback = (type(exception), exception, exception.__traceback__)
    info = 'TSUSERVERDR HAS ENCOUNTERED A FATAL PYTHON ERROR.'
    info += "\r\n" + "".join(traceback.format_exception(etype, evalue, etraceback))
    logger.log_print(info)
    logger.log_error(info, server=server, errortype='P')

    logger.log_server('Server is shutting down due to an unhandled exception.')
    logger.log_print('Attempting a graceful shutdown.')

    if not server:
        logger.log_pserver('Server has successfully shut down.')
        return

    try:
        await server.normal_shutdown()
    except Exception as exception2:
        server.shutting_down = True

        logger.log_print('Unable to gracefully shut down: Forcing a shutdown.')
        etype, evalue, etraceback = (type(exception2), exception2, exception2.__traceback__)
        info = "\r\n" + "".join(traceback.format_exception(etype, evalue, etraceback))

        logger.log_print(info)
        logger.log_error(info, server=server, errortype='P')


def _pre_launch_checks():
    # Check that config folder exists
    if not os.path.exists('config'):
        # If not, check if config_sample folder exists (common setup mistake)
        if os.path.exists('config_sample'):
            msg = ('Unable to locate the `config` folder. However, a `config_sample` folder '
                   'was found. Please rename `config_sample` to `config` as instructed in the '
                   'README and try again.')
            raise RuntimeError(msg)
        # Otherwise, something went wrong.
        msg = ('Unable to locate the `config` folder. Please make sure the folder exists and '
               'is named correctly and try again.')
        raise RuntimeError(msg)

    _mandatory_python_version_check()
    _upcoming_python_version_check()


def main():
    server = None

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        _pre_launch_checks()
        server = TsuserverDR()

        def _handle_exception(loop, context):
            # The function signature MUST be of the above form
            # https://docs.python.org/3/library/asyncio-eventloop.html
            exception = context.get('exception')
            server.error_queue.put_nowait(exception)
            server.error_queue.put_nowait(exception)
            # An exception is put twice, because it is pulled twice: once by the server object itself
            # (so that it leaves its main loop) and once by this main() function (so that it can
            # print traceback)
        loop.set_exception_handler(_handle_exception)
        loop.run_until_complete(server.start())
        # If we are done with this coroutine, that means an error was raised
        raise server.error_queue.get_nowait()
    except KeyboardInterrupt:
        print('')  # Lame
        logger.log_pdebug('You have initiated a server shut down.')
        loop.run_until_complete(_normal_shutdown(server=server))
        logger.log_pdebug('Server has successfully shut down.')
    except Exception as exception:
        loop.run_until_complete(_abnormal_shutdown(exception, server=server))
    finally:
        try:
            input("Press Enter to exit. ")
        except (Exception, KeyboardInterrupt):
            # Only errors that could realistically happen are just a bunch of Ctrl+C/Z leaking
            # in the input message and those being sent. We don't really care what happens now,
            # everything has shut down by this point.
            pass


if __name__ == '__main__':
    # Make launching via python.exe and python start_server.py possible
    path_to_this = pathlib.Path(__file__).absolute()
    os.chdir(os.path.dirname(path_to_this))
    main()
