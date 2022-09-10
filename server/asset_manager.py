from __future__ import annotations

import typing

from typing import Any, Callable

from server.exceptions import ServerError
from server.subscriber import Publisher

if typing.TYPE_CHECKING:
    from client_manager import ClientManager
    from server.tsuserver import TsuserverDR

class AssetManager:
    def __init__(self, server: TsuserverDR):
        self.server = server
        self.publisher = Publisher(self)

    def get_name(self) -> str:
        raise NotImplementedError

    def get_default_file(self) -> str:
        raise NotImplementedError

    def get_loader(self) -> Callable[[str, ], Any]:
        raise NotImplementedError

    def command_load_asset(self, client: ClientManager.Client, file: str):
        if not file:
            source_file = self.get_default_file()
            msg = f'the default {self.get_name()} file'
        else:
            source_file = f'config/{self.get_name().replace(" ", "_")}/{file}.yaml'
            msg = f'the custom {self.get_name()} file `{source_file}`'
        fail_msg = f'Unable to load {msg}'

        try:
            self.get_loader()(source_file)
        except ServerError.FileInvalidNameError:
            raise ServerError(f'{fail_msg}: '
                            f'File names may not contain relative directories.')
        except ServerError.FileNotFoundError:
            raise ServerError(f'{fail_msg}: '
                            f'File not found.')
        except ServerError.FileOSError as exc:
            raise ServerError(f'{fail_msg}: '
                            f'An OS error occurred: `{exc}`.')
        except ServerError.YAMLInvalidError as exc:
            raise ServerError(f'{fail_msg}: '
                            f'`{exc}`.')
        except ServerError.FileSyntaxError as exc:
            raise ServerError(f'{fail_msg}: '
                            f'An asset syntax error occurred: `{exc}`.')
        else:
            client.send_ooc(f'You have loaded {msg}.')
            client.send_ooc_others(f'The {msg} has been loaded.',
                                   is_officer=False)
            client.send_ooc_others(f'{client.name} [{client.id}] has loaded {msg}.',
                                   is_officer=True)
