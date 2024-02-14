from chiru.commands.dispatcher import CommandDispatchContext
from chiru.models.channel import AnyGuildChannel


class PreconditionFailed(ValueError):
    """
    Raised when a command precondition fails.
    """


# pre-built helpful preconditions
async def ran_by_owner(context: CommandDispatchContext):
    """
    A command precondition that requires a command to be ran by the bot owner.
    """

    client = context.event_context.client
    owner = client.app.owner
    if not owner:
        raise PreconditionFailed("Couldn't find owner")
    
    if owner.id != context.message_event.author.id:
        raise PreconditionFailed("Message author is not the owner")

    
async def ran_in_guild(context: CommandDispatchContext):
    """
    A command precondition that requires a command to be ran in a guild channel, not a DM.
    """

    if not isinstance(context.message_event.channel, AnyGuildChannel):
        raise PreconditionFailed("Channel is not a guild channel")
