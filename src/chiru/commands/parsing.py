# ruff: noqa: F841

import argparse
from typing import IO, Any, NoReturn, override

# Some notes:
#
# This requires a kludgy exception flow to properly handle help. Argparse does this in a hacky
# way anyway (always exiting on --help)... so it's not that bad.


class ParsingError(ValueError):
    """
    Root error for command parsing errors.
    """


class CommandRequestedHelp(ParsingError):
    """
    Control flow exception used when a command requests help.
    """


class InteractiveParser(argparse.ArgumentParser):
    """
    A :class:`argparse.ArgumentParser` that is kludged into working interactively.
    """

    def __init__(
        self,
        command_name: str,
        command_usage: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        kwargs.pop("exit_on_error", None)
        kwargs.pop("add_help", None)

        super().__init__(
            *args,
            prog=command_name,
            usage=command_usage,
            **kwargs,
            exit_on_error=False,
            add_help=True,
        )

    @override
    def print_help(self, file: IO[str] | None = None) -> None:
        raise CommandRequestedHelp()
        
    @override
    def error(self, message: str) -> NoReturn:
        raise ParsingError(message)

    @override
    def exit(self, status: int = 0, message: str | None = None) -> NoReturn:
        print(self._registries["action"])
        raise RuntimeError("Somehow, exit() got called") from ParsingError(message)
