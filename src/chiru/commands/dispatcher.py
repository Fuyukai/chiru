from __future__ import annotations

import abc
import argparse
import shlex
import textwrap
from argparse import ArgumentParser, Namespace
from collections.abc import Awaitable, Callable, MutableMapping, Sequence
from functools import partial
from typing import NoReturn, final, override

import anyio
import attr
import structlog
from anyio import BrokenResourceError, ClosedResourceError
from anyio.abc import TaskGroup
from anyio.streams.memory import MemoryObjectSendStream
from cattrs import Converter
from chiru.commands.parsing import CommandRequestedHelp, InteractiveParser, ParsingError
from chiru.event.dispatcher import DispatchChannel, EventContext
from chiru.event.model import MessageCreate
from chiru.serialise import add_useful_conversions
from datargs import make_parser

type CommandCallable[T] = Callable[[CommandDispatchContext, T], Awaitable[None]]
type CommandPrecondition = Callable[[CommandDispatchContext], bool]
type ErrorChannel = MemoryObjectSendStream[tuple[BaseCommandDispatchContext, Exception]]
type SplittingStrategy = Callable[[str], Sequence[str]]

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


# TODO: This is kinda gross. Can we do better?
@attr.s(slots=True, kw_only=True, frozen=True)
class BaseCommandDispatchContext:
    """
    Context object used when dispatching a single command.
    """

    #: The event context for the event that caused command processing.
    event_context: EventContext = attr.ib()

    #: The message event that caused command processing.
    message_event: MessageCreate = attr.ib()

    #: The dispatcher for this command.
    dispatcher: CommandDispatcher = attr.ib()

    #: The name of the command that is to be ran.
    command_name: str = attr.ib()

    #: The command object that is being ran, if any.
    #:
    #: This may be none if there is no command to run.
    command: BaseCommand | None = attr.ib()


@attr.s(slots=True, kw_only=True, frozen=True)
@final
class CommandDispatchContext(BaseCommandDispatchContext):
    """
    A :class:`.BaseCommandDispatchContext` with a definitely not-null :class:`.BaseCommand`.
    """

    command: BaseCommand = attr.ib()


class BaseCommand(abc.ABC):
    """
    Base class for a command object.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """
        The name of this command.
        """

    @abc.abstractmethod
    def make_help_message(self) -> str:
        """
        Makes the help message content for this command.
        """

    @abc.abstractmethod
    async def execute(
        self,
        context: CommandDispatchContext,
        command_content: str,
    ) -> None:
        """
        Executes the underlying command.

        :param dispatcher: The :class:`.CommandDispatcher` this command call came from.
        :param context: The :class:`.EventContext` for the provided event.
        :param event: The :class:`.MessageCreate` that created this command invocation.
        :param command_content: The command content with the command prefix removed.
        """

@attr.s(slots=True, kw_only=True, frozen=True)
class RawArgumentParserCommand(BaseCommand):
    """
    A command that uses a raw :class:`argparse.ArgumentParser` for arguments.
    """

    parser: ArgumentParser = attr.ib()
    fn: CommandCallable[Namespace]

    @property
    @override
    def name(self) -> str:
        return self.parser.prog

    @override    
    def make_help_message(self) -> str:
        return self.parser.format_help()

    @override
    async def execute(
        self,
        context: CommandDispatchContext,
        command_content: str,
    ) -> None:
        try:
            parsed = self.parser.parse_args(command_content)
        except argparse.ArgumentError as e:
            raise ParsingError(e.message) from e

        await self.fn(context, parsed)


@attr.s(slots=True, kw_only=True)
class SpecCommand[Spec](BaseCommand):
    """
    A command that uses a command specification for arguments.
    """

    parser: ArgumentParser = attr.ib()
    typ: type[Spec] = attr.ib()
    fn: CommandCallable[Spec] = attr.ib()

    @property
    @override
    def name(self) -> str:
        return self.parser.prog
    
    @override    
    def make_help_message(self) -> str:
        return self.parser.format_help()

    @override
    async def execute(
        self,
        context: CommandDispatchContext,
        command_content: str,
    ) -> None:
        try:
            parsed = self.parser.parse_args(shlex.split(command_content))
        except argparse.ArgumentError as e:
            raise ParsingError(e.message) from e

        created = context.dispatcher.converter.structure(vars(parsed), self.typ)
        await self.fn(context, created)


@attr.s(slots=True, kw_only=True)
@final
class CommandDispatcher:
    """
    A dispatcher for traditional, IRC-style commands that uses ``argparse``.

    A single bot can (and should) have multiple command dispatchers registered, each with its own
    set of commands.
    """

    @staticmethod
    def _make_default_converter() -> Converter:
        return add_useful_conversions(Converter())

    #: The command prefix to use for commands.
    command_prefix: str = attr.ib()

    #: A mapping of ``command name`` -> :class:`.BaseCommand` instances used as the backing
    #: store for this command dispatcher. This can be inserted into for raw commands that don't
    #: need or want ``argparse`` behaviour.
    #:
    #: If this is not provided, then a default empty dictionary will be provided.
    command_mapping: MutableMapping[str, BaseCommand] = attr.ib(factory=dict)

    #: The :class:`cattrs.Converter` used for turning the parsed arguments into command
    #: specifications.
    converter: Converter = attr.ib(factory=_make_default_converter)

    #: A list of command preconditions that must be checked before a command is ran.
    #:
    #: A precondition is a (CommandDispatchContext)
    command_preconditions: list[CommandPrecondition] = attr.ib(factory=list)

    #: A channel where command errors are published on. This includes parsing errors, precondition
    #: errors, and command errors.
    #:
    #: This must be passed into the dispatcher. If no channel is provided, the default behaviour
    #: is to log errors.
    error_channel: ErrorChannel | None = attr.ib(default=None)

    #: A channel where unknown command messages are published on.
    #:
    #: This must be passed into the dispatcher. If no channel is provided, the default behaviour is
    #: to silently discard the event.
    unknown_commands_channel: MemoryObjectSendStream[BaseCommandDispatchContext] | None = attr.ib(
        default=None
    )

    #: A channel where help request messages are published on.
    #:
    #: This can be used to customise the action for help on a per-command or per-dispatcher basis.
    #:
    #: This must be passed into the dispattcher. If no channel is provided, the default behaviour
    #: is to reply to the user with a help message, which is exposed as :meth`.reply_with_help`.
    help_requests_channel: MemoryObjectSendStream[BaseCommandDispatchContext] | None = attr.ib(
        default=None
    )

    #: The :class:`anyio.abc.TaskGroup` to spawn command invocations inside of.
    #:
    #: This must be passed into the dispatcher. If no task group is provided, the default behaviour
    #: is to run commands linearly.
    task_group: TaskGroup | None = attr.ib(default=None)

    async def _process_exception(self, context: CommandDispatchContext, exception: Exception):
        """
        Processes a single command exception.
        """

        if self.error_channel is not None:
            try:
                await self.error_channel.send((context, exception))
                return
            except (BrokenResourceError, ClosedResourceError):
                # wtf?
                self.error_channel = None

        logger.error(
            "Command error",
            command=context.command_name,
            message=context.message_event.message.id,
            exc_info=exception,
        )

    async def _process_command_not_found(self, context: BaseCommandDispatchContext) -> None:
        """
        Processes a single command not found error.
        """

        if self.unknown_commands_channel is not None:
            try:
                await self.unknown_commands_channel.send(context)
            except (BrokenResourceError, ClosedResourceError):
                self.unknown_commands_channel = None
        else:
            # always checkpoint
            await anyio.sleep(0)

    async def send_help_for_command(self, context: CommandDispatchContext):
        """
        Sends the help message for the command contained within the provided context.
        """

        help_message = context.command.make_help_message()
        await context.message_event.channel.send_message(help_message)

    async def _process_command_help(self, cmd_context: CommandDispatchContext) -> None:
        """
        Default action for processing command help.
        """

        if self.help_requests_channel is not None:
            try:
                await self.help_requests_channel.send(cmd_context)
                return
            except (BrokenResourceError, ClosedResourceError):
                self.help_requests_channel = None

        await self.send_help_for_command(cmd_context)

    async def _execute_command(
        self,
        command: BaseCommand,
        cmd_context: CommandDispatchContext,
        content: str,
    ) -> None:
        """
        Wrapper that executes a command.
        """

        # double try, just in case the send-help message fails too somehow
        try:
            try:
                await command.execute(cmd_context, content)
            except CommandRequestedHelp:
                await self._process_command_help(cmd_context)
        except Exception as e:
            await self._process_exception(cmd_context, e)

    def add_command_with_parser(
        self,
        parser: ArgumentParser,
        fn: CommandCallable[Namespace],
    ) -> None:
        """
        Adds a new command to this dispatcher that uses a raw argument parser.

        The arguments to this function are the same as :metth:`.add_command`, with the exception of
        the keyword arguments which must be set on the :class:`.ArgumentParser` directly.

        .. note::

            Your argument parser should convert any internal errors into a :class:`.ParsingError`
            instead of exiting.
        """

        raise NotImplementedError()

    def add_command[T](
        self,
        spec: type[T],
        fn: CommandCallable[T],
        *,
        name: str | None = None,
        help: str | None = None,
        splitting_strategy: SplittingStrategy = shlex.split,
    ) -> None:
        """
        Adds a new command to this dispatcher.

        :param spec: A *command specification* for this command.

            A command specification is an ``attrs`` (or ``@dataclass``) class that provides a
            statically typed list of arguments to a class. A new instance of this object will be
            provided to the command callable on every invocation of the command.

        :param fn: The command callable to run.

            This is a callable that accepts a :class:`.EventContext`, the :class:`.MessageCreate`
            that invoked the command, and the command specification object provided,
            and returns an ``Awaitable[None]`` that is used to run the command.

            The same command function can be provided for multiple commands, provided it accepts
            multiple types of command specifications.

        :param name: The name of the command.

            If this parameter is not provided, it will be automatically set to the ``__name__`` of
            the provided callable converted to kebab case.

        :param help: The one-line help for this command.

            If this parameter is not provided, it will be automatically set to the first line of
            the ``__doc__`` of the provided callable. If the provided callable has no ``__doc__``,
            then the command will have no help.

        :param splitting_strategy: A callable that is responsible for splitting command arguments.

            This defaults to :func:`shlex.split`,
        """

        name = name or fn.__name__.replace("_", "-")
        if help is None:
            doc: str | None = getattr(fn, "__doc__", None)

            if doc is not None:
                doc = textwrap.dedent(doc).strip()
                help = doc.split("\n", 1)[0]

        parser = InteractiveParser(
            command_name=name,
            command_usage=help or "No help specified.",
        )
        parser = make_parser(spec, parser)
        command = SpecCommand(parser=parser, typ=spec, fn=fn)
        self.command_mapping[command.name] = command

    async def process_command_event(self, context: EventContext, event: MessageCreate) -> None:
        """
        Processes a single command event.

        If you use an alternative event handling scheme to the default :class:`.ChannelDispatcher`,
        then you should use this method to process commands. Otherwise, you should use
        :meth:`.listen_to_commands`.
        """

        content = event.message.content
        prefix, rest = content[: len(self.command_prefix)], content[len(self.command_prefix) :]

        if prefix != self.command_prefix:
            await anyio.sleep(0)
            return

        try:
            command_name, rest = rest.split(" ", 1)
        except ValueError:
            command_name = rest
            rest = ""

        command = self.command_mapping.get(command_name)
        if command is None:
            cmd_context = BaseCommandDispatchContext(
                event_context=context,
                message_event=event,
                dispatcher=self,
                command_name=command_name,
                command=command,
            )
            await self._process_command_not_found(cmd_context)
            return

        cmd_context = CommandDispatchContext(
            event_context=context,
            message_event=event,
            dispatcher=self,
            command_name=command_name,
            command=command,
        )

        fn = partial(self._execute_command, command=command, cmd_context=cmd_context, content=rest)

        if self.task_group is not None:
            # XXX: works fine on the playground.
            # https://pyright-play.net/?code=GYJw9gtgBMCuB2BjALmMAbAzlAlhADmCMlPgIbE5noBQokUyAnvjvAOa4FEkDC16MgCN0AUwA0UAKrxyiANY0aAE1HAY8ABRkAXLnjJJQvW0NREJgwEooAWgB8UAHJh4onTShfSZTJiWq6ogCoiAA2gBUACoAuprA8Hr86IIiomGRsZIubjGSERTsmHoycvJhsTYOzq7unt7kfkrqALw%2BlNTx8JJkLQCMRi0ATJKILQDMVjTCiFBtwSmh8VZAA
            self.task_group.start_soon(fn)  # type: ignore
        else:
            await fn()

    async def listen_to_commands(self, channel: DispatchChannel[MessageCreate]) -> NoReturn:
        """
        Event for listening to incoming commands.

        This should be spawned inside your nursery or used with
        :meth:`.ChannelDispatcher.register_event_handling_task`.
        """

        async for context, message in channel:
            await self.process_command_event(context, message)
