# pyright: reportImplicitOverride=false
from __future__ import annotations

from typing import Self

import attr
from bitarray import bitarray
from bitarray.util import ba2int, zeros

# API kinda sucks.
# fwiw, this was automatically generated. I didn't type (most of this) out by hand like a madman.


@attr.s(slots=True, kw_only=True)
class ReadOnlyPermissions:
    """
    The bitfield of a set of permissions that a member or role can have in a guild. This is a
    read-only representation of the permissions; for a mutable implementation that can be used for
    HTTP requests and stateful objects, see :class:`.WriteablePermissions`.

    Each permission is a single bit in the backing bitfield, which may be any number of bits long.
    This class can be turned into an int with the ``int()`` method, which can then be used over the
    HTTP API.
    """

    @classmethod
    def all(cls) -> Self:
        """
        Returns a new instance of this type with all permissions set to True.
        """

        bf = bitarray(128)
        for i in range(128):
            bf[i] = 1

        return cls(bitfield=bf)

    # 128 bits should be enough for now.
    _bitfield: bitarray = attr.ib(factory=lambda: zeros(128), alias="bitfield")

    def __str__(self) -> str:
        return str(int(self))

    def __int__(self) -> int:
        return ba2int(self._bitfield)

    @property
    def create_instant_invites(self) -> bool:
        """
        Permission for allowing users to create invites
        """

        return self._bitfield[-1] == 1

    @property
    def kick_members(self) -> bool:
        """
        Permission for kicking guild members
        """

        return self._bitfield[-2] == 1

    @property
    def ban_members(self) -> bool:
        """
        Permission for banning guild member
        """

        return self._bitfield[-3] == 1

    @property
    def administrator(self) -> bool:
        """
        If set, *all* permissions are granted.
        """

        return self._bitfield[-4] == 1

    @property
    def manage_channels(self) -> bool:
        """
        Permission for creating, editing, and removing guild channels
        """

        return self._bitfield[-5] == 1

    @property
    def manage_guild(self) -> bool:
        """
        Permission for editing the guild directly
        """

        return self._bitfield[-6] == 1

    @property
    def add_reactions(self) -> bool:
        """
        Permission for adding reactions to messages
        """

        return self._bitfield[-7] == 1

    @property
    def view_audit_log(self) -> bool:
        """
        Permission for viewing the guild's audit log
        """

        return self._bitfield[-8] == 1

    @property
    def priority_speaker(self) -> bool:
        """
        Permission for being able to be the priority speaker in a voice channel
        """

        return self._bitfield[-9] == 1

    @property
    def stream(self) -> bool:
        """
        Permission for being able to stream in a channel
        """

        return self._bitfield[-10] == 1

    @property
    def view_channel(self) -> bool:
        """
        Permission for being able to see a channel
        """

        return self._bitfield[-11] == 1

    @property
    def send_messages(self) -> bool:
        """
        Permission for being able to send messages in a channel
        """

        return self._bitfield[-12] == 1

    @property
    def send_tts_messages(self) -> bool:
        """
        Permission for being able to send text-to-speech messages in a channel
        """

        return self._bitfield[-13] == 1

    @property
    def manage_messages(self) -> bool:
        """
        Permission for pining and deleting messages
        """

        return self._bitfield[-14] == 1

    @property
    def embed_links(self) -> bool:
        """
        Permission for creating embeds for links
        """

        return self._bitfield[-15] == 1

    @property
    def attach_files(self) -> bool:
        """
        Permission for uploading files
        """

        return self._bitfield[-16] == 1

    @property
    def read_message_history(self) -> bool:
        """
        Permission for reading the message history of a channel
        """

        return self._bitfield[-17] == 1

    @property
    def mention_everyone(self) -> bool:
        """
        Permission for sending at-everyone messages
        """

        return self._bitfield[-18] == 1

    @property
    def use_external_emojis(self) -> bool:
        """
        Permission for using emojis not from this guild
        """

        return self._bitfield[-19] == 1

    @property
    def view_guild_insights(self) -> bool:
        """
        No clue what this one is
        """

        return self._bitfield[-20] == 1

    @property
    def connect(self) -> bool:
        """
        Permission for connecting to a voice channel
        """

        return self._bitfield[-21] == 1

    @property
    def speak(self) -> bool:
        """
        Permission for speaking in a voice channel
        """

        return self._bitfield[-22] == 1

    @property
    def mute_members(self) -> bool:
        """
        Permission for muting other members in a voice channel
        """

        return self._bitfield[-23] == 1

    @property
    def deafen_members(self) -> bool:
        """
        Permission for deafening other members in a voice channel
        """

        return self._bitfield[-24] == 1

    @property
    def move_members(self) -> bool:
        """
        Permission for moving members between voice channels
        """

        return self._bitfield[-25] == 1

    @property
    def use_vad(self) -> bool:
        """
        Permission for cheating emissions tests
        """

        return self._bitfield[-26] == 1

    @property
    def change_nickname(self) -> bool:
        """
        Permission for changing own nickname
        """

        return self._bitfield[-27] == 1

    @property
    def manage_nicknames(self) -> bool:
        """
        Permission for changing other members' nicknames
        """

        return self._bitfield[-28] == 1

    @property
    def manage_roles(self) -> bool:
        """
        Permission for managing the roles for a guild
        """

        return self._bitfield[-29] == 1

    @property
    def manage_webhooks(self) -> bool:
        """
        Permission for managing the webhooks for a guild
        """

        return self._bitfield[-30] == 1

    @property
    def manage_emojis(self) -> bool:
        """
        Permission for updating the emojis
        """

        return self._bitfield[-31] == 1

    @property
    def use_application_commands(self) -> bool:
        """
        Permission for using cringe app commands in a channel
        """

        return self._bitfield[-32] == 1

    @property
    def request_to_speak(self) -> bool:
        """
        Permission for putting your hand up like a primary school student
        """

        return self._bitfield[-33] == 1

    @property
    def manage_events(self) -> bool:
        """
        Permission for creating, editing, and deleting events in a guild
        """

        return self._bitfield[-34] == 1

    @property
    def manage_threads(self) -> bool:
        """
        Permission for managing threads in a channel
        """

        return self._bitfield[-35] == 1

    @property
    def create_public_threads(self) -> bool:
        """
        Permission for creating new public threads in a channel
        """

        return self._bitfield[-36] == 1

    @property
    def create_private_threads(self) -> bool:
        """
        Permission for creating new private threads in a channel
        """

        return self._bitfield[-37] == 1

    @property
    def use_external_stickers(self) -> bool:
        """
        Permission for pretending to be telegram
        """

        return self._bitfield[-38] == 1

    @property
    def send_messages_in_threads(self) -> bool:
        """
        Permission for sending messages in threads...?
        """

        return self._bitfield[-39] == 1

    @property
    def use_embedded_activities(self) -> bool:
        """
        Permission for something something voice channels
        """

        return self._bitfield[-40] == 1

    @property
    def moderate_members(self) -> bool:
        """
        Permission for timing out members
        """

        return self._bitfield[-41] == 1

    @property
    def view_creator_monetization_analytics(self) -> bool:
        """
        Permission for doing patreon nonsense
        """

        return self._bitfield[-42] == 1

    @property
    def use_soundboard(self) -> bool:
        """
        Permission for using the soundboard
        """

        return self._bitfield[-43] == 1

    @property
    def create_guild_expressions(self) -> bool:
        """
        Permission for creating emojis...?
        """

        return self._bitfield[-44] == 1

    @property
    def create_events(self) -> bool:
        """
        Permission for creating events
        """

        return self._bitfield[-45] == 1

    @property
    def use_external_sounds(self) -> bool:
        """
        Permission for using other guilds' soundboards
        """

        return self._bitfield[-46] == 1

    @property
    def send_voice_messages(self) -> bool:
        """
        Permission for sending voice messages in a channel
        """

        return self._bitfield[-47] == 1


class WriteablePermissions(ReadOnlyPermissions):
    """
    Like :class:`.ReadOnlyPermissions`, but with setters.
    """

    @property
    def create_instant_invites(self) -> bool:
        """
        Permission for allowing users to create invites
        """

        return self._bitfield[-1] == 1

    @create_instant_invites.setter
    def create_instant_invites(self, value: bool) -> None:
        self._bitfield[-1] = int(value)

    @property
    def kick_members(self) -> bool:
        """
        Permission for kicking guild members
        """

        return self._bitfield[-2] == 1

    @kick_members.setter
    def kick_members(self, value: bool) -> None:
        self._bitfield[-2] = int(value)

    @property
    def ban_members(self) -> bool:
        """
        Permission for banning guild member
        """

        return self._bitfield[-3] == 1

    @ban_members.setter
    def ban_members(self, value: bool) -> None:
        self._bitfield[-3] = int(value)

    @property
    def administrator(self) -> bool:
        """
        If set, *all* permissions are granted.
        """

        return self._bitfield[-4] == 1

    @administrator.setter
    def administrator(self, value: bool) -> None:
        self._bitfield[-4] = int(value)

    @property
    def manage_channels(self) -> bool:
        """
        Permission for creating, editing, and removing guild channels
        """

        return self._bitfield[-5] == 1

    @manage_channels.setter
    def manage_channels(self, value: bool) -> None:
        self._bitfield[-5] = int(value)

    @property
    def manage_guild(self) -> bool:
        """
        Permission for editing the guild directly
        """

        return self._bitfield[-6] == 1

    @manage_guild.setter
    def manage_guild(self, value: bool) -> None:
        self._bitfield[-6] = int(value)

    @property
    def add_reactions(self) -> bool:
        """
        Permission for adding reactions to messages
        """

        return self._bitfield[-7] == 1

    @add_reactions.setter
    def add_reactions(self, value: bool) -> None:
        self._bitfield[-7] = int(value)

    @property
    def view_audit_log(self) -> bool:
        """
        Permission for viewing the guild's audit log
        """

        return self._bitfield[-8] == 1

    @view_audit_log.setter
    def view_audit_log(self, value: bool) -> None:
        self._bitfield[-8] = int(value)

    @property
    def priority_speaker(self) -> bool:
        """
        Permission for being able to be the priority speaker in a voice channel
        """

        return self._bitfield[-9] == 1

    @priority_speaker.setter
    def priority_speaker(self, value: bool) -> None:
        self._bitfield[-9] = int(value)

    @property
    def stream(self) -> bool:
        """
        Permission for being able to stream in a channel
        """

        return self._bitfield[-10] == 1

    @stream.setter
    def stream(self, value: bool) -> None:
        self._bitfield[-10] = int(value)

    @property
    def view_channel(self) -> bool:
        """
        Permission for being able to see a channel
        """

        return self._bitfield[-11] == 1

    @view_channel.setter
    def view_channel(self, value: bool) -> None:
        self._bitfield[-11] = int(value)

    @property
    def send_messages(self) -> bool:
        """
        Permission for being able to send messages in a channel
        """

        return self._bitfield[-12] == 1

    @send_messages.setter
    def send_messages(self, value: bool) -> None:
        self._bitfield[-12] = int(value)

    @property
    def send_tts_messages(self) -> bool:
        """
        Permission for being able to send text-to-speech messages in a channel
        """

        return self._bitfield[-13] == 1

    @send_tts_messages.setter
    def send_tts_messages(self, value: bool) -> None:
        self._bitfield[-13] = int(value)

    @property
    def manage_messages(self) -> bool:
        """
        Permission for pining and deleting messages
        """

        return self._bitfield[-14] == 1

    @manage_messages.setter
    def manage_messages(self, value: bool) -> None:
        self._bitfield[-14] = int(value)

    @property
    def embed_links(self) -> bool:
        """
        Permission for creating embeds for links
        """

        return self._bitfield[-15] == 1

    @embed_links.setter
    def embed_links(self, value: bool) -> None:
        self._bitfield[-15] = int(value)

    @property
    def attach_files(self) -> bool:
        """
        Permission for uploading files
        """

        return self._bitfield[-16] == 1

    @attach_files.setter
    def attach_files(self, value: bool) -> None:
        self._bitfield[-16] = int(value)

    @property
    def read_message_history(self) -> bool:
        """
        Permission for reading the message history of a channel
        """

        return self._bitfield[-17] == 1

    @read_message_history.setter
    def read_message_history(self, value: bool) -> None:
        self._bitfield[-17] = int(value)

    @property
    def mention_everyone(self) -> bool:
        """
        Permission for sending at-everyone messages
        """

        return self._bitfield[-18] == 1

    @mention_everyone.setter
    def mention_everyone(self, value: bool) -> None:
        self._bitfield[-18] = int(value)

    @property
    def use_external_emojis(self) -> bool:
        """
        Permission for using emojis not from this guild
        """

        return self._bitfield[-19] == 1

    @use_external_emojis.setter
    def use_external_emojis(self, value: bool) -> None:
        self._bitfield[-19] = int(value)

    @property
    def view_guild_insights(self) -> bool:
        """
        No clue what this one is
        """

        return self._bitfield[-20] == 1

    @view_guild_insights.setter
    def view_guild_insights(self, value: bool) -> None:
        self._bitfield[-20] = int(value)

    @property
    def connect(self) -> bool:
        """
        Permission for connecting to a voice channel
        """

        return self._bitfield[-21] == 1

    @connect.setter
    def connect(self, value: bool) -> None:
        self._bitfield[-21] = int(value)

    @property
    def speak(self) -> bool:
        """
        Permission for speaking in a voice channel
        """

        return self._bitfield[-22] == 1

    @speak.setter
    def speak(self, value: bool) -> None:
        self._bitfield[-22] = int(value)

    @property
    def mute_members(self) -> bool:
        """
        Permission for muting other members in a voice channel
        """

        return self._bitfield[-23] == 1

    @mute_members.setter
    def mute_members(self, value: bool) -> None:
        self._bitfield[-23] = int(value)

    @property
    def deafen_members(self) -> bool:
        """
        Permission for deafening other members in a voice channel
        """

        return self._bitfield[-24] == 1

    @deafen_members.setter
    def deafen_members(self, value: bool) -> None:
        self._bitfield[-24] = int(value)

    @property
    def move_members(self) -> bool:
        """
        Permission for moving members between voice channels
        """

        return self._bitfield[-25] == 1

    @move_members.setter
    def move_members(self, value: bool) -> None:
        self._bitfield[-25] = int(value)

    @property
    def use_vad(self) -> bool:
        """
        Permission for cheating emissions tests
        """

        return self._bitfield[-26] == 1

    @use_vad.setter
    def use_vad(self, value: bool) -> None:
        self._bitfield[-26] = int(value)

    @property
    def change_nickname(self) -> bool:
        """
        Permission for changing own nickname
        """

        return self._bitfield[-27] == 1

    @change_nickname.setter
    def change_nickname(self, value: bool) -> None:
        self._bitfield[-27] = int(value)

    @property
    def manage_nicknames(self) -> bool:
        """
        Permission for changing other members' nicknames
        """

        return self._bitfield[-28] == 1

    @manage_nicknames.setter
    def manage_nicknames(self, value: bool) -> None:
        self._bitfield[-28] = int(value)

    @property
    def manage_roles(self) -> bool:
        """
        Permission for managing the roles for a guild
        """

        return self._bitfield[-29] == 1

    @manage_roles.setter
    def manage_roles(self, value: bool) -> None:
        self._bitfield[-29] = int(value)

    @property
    def manage_webhooks(self) -> bool:
        """
        Permission for managing the webhooks for a guild
        """

        return self._bitfield[-30] == 1

    @manage_webhooks.setter
    def manage_webhooks(self, value: bool) -> None:
        self._bitfield[-30] = int(value)

    @property
    def manage_emojis(self) -> bool:
        """
        Permission for updating the emojis
        """

        return self._bitfield[-31] == 1

    @manage_emojis.setter
    def manage_emojis(self, value: bool) -> None:
        self._bitfield[-31] = int(value)

    @property
    def use_application_commands(self) -> bool:
        """
        Permission for using cringe app commands in a channel
        """

        return self._bitfield[-32] == 1

    @use_application_commands.setter
    def use_application_commands(self, value: bool) -> None:
        self._bitfield[-32] = int(value)

    @property
    def request_to_speak(self) -> bool:
        """
        Permission for putting your hand up like a primary school student
        """

        return self._bitfield[-33] == 1

    @request_to_speak.setter
    def request_to_speak(self, value: bool) -> None:
        self._bitfield[-33] = int(value)

    @property
    def manage_events(self) -> bool:
        """
        Permission for creating, editing, and deleting events in a guild
        """

        return self._bitfield[-34] == 1

    @manage_events.setter
    def manage_events(self, value: bool) -> None:
        self._bitfield[-34] = int(value)

    @property
    def manage_threads(self) -> bool:
        """
        Permission for managing threads in a channel
        """

        return self._bitfield[-35] == 1

    @manage_threads.setter
    def manage_threads(self, value: bool) -> None:
        self._bitfield[-35] = int(value)

    @property
    def create_public_threads(self) -> bool:
        """
        Permission for creating new public threads in a channel
        """

        return self._bitfield[-36] == 1

    @create_public_threads.setter
    def create_public_threads(self, value: bool) -> None:
        self._bitfield[-36] = int(value)

    @property
    def create_private_threads(self) -> bool:
        """
        Permission for creating new private threads in a channel
        """

        return self._bitfield[-37] == 1

    @create_private_threads.setter
    def create_private_threads(self, value: bool) -> None:
        self._bitfield[-37] = int(value)

    @property
    def use_external_stickers(self) -> bool:
        """
        Permission for pretending to be telegram
        """

        return self._bitfield[-38] == 1

    @use_external_stickers.setter
    def use_external_stickers(self, value: bool) -> None:
        self._bitfield[-38] = int(value)

    @property
    def send_messages_in_threads(self) -> bool:
        """
        Permission for sending messages in threads...?
        """

        return self._bitfield[-39] == 1

    @send_messages_in_threads.setter
    def send_messages_in_threads(self, value: bool) -> None:
        self._bitfield[-39] = int(value)

    @property
    def use_embedded_activities(self) -> bool:
        """
        Permission for something something voice channels
        """

        return self._bitfield[-40] == 1

    @use_embedded_activities.setter
    def use_embedded_activities(self, value: bool) -> None:
        self._bitfield[-40] = int(value)

    @property
    def moderate_members(self) -> bool:
        """
        Permission for timing out members
        """

        return self._bitfield[-41] == 1

    @moderate_members.setter
    def moderate_members(self, value: bool) -> None:
        self._bitfield[-41] = int(value)

    @property
    def view_creator_monetization_analytics(self) -> bool:
        """
        Permission for doing patreon nonsense
        """

        return self._bitfield[-42] == 1

    @view_creator_monetization_analytics.setter
    def view_creator_monetization_analytics(self, value: bool) -> None:
        self._bitfield[-42] = int(value)

    @property
    def use_soundboard(self) -> bool:
        """
        Permission for using the soundboard
        """

        return self._bitfield[-43] == 1

    @use_soundboard.setter
    def use_soundboard(self, value: bool) -> None:
        self._bitfield[-43] = int(value)

    @property
    def create_guild_expressions(self) -> bool:
        """
        Permission for creating emojis...?
        """

        return self._bitfield[-44] == 1

    @create_guild_expressions.setter
    def create_guild_expressions(self, value: bool) -> None:
        self._bitfield[-44] = int(value)

    @property
    def create_events(self) -> bool:
        """
        Permission for creating events
        """

        return self._bitfield[-45] == 1

    @create_events.setter
    def create_events(self, value: bool) -> None:
        self._bitfield[-45] = int(value)

    @property
    def use_external_sounds(self) -> bool:
        """
        Permission for using other guilds' soundboards
        """

        return self._bitfield[-46] == 1

    @use_external_sounds.setter
    def use_external_sounds(self, value: bool) -> None:
        self._bitfield[-46] = int(value)

    @property
    def send_voice_messages(self) -> bool:
        """
        Permission for sending voice messages in a channel
        """

        return self._bitfield[-47] == 1

    @send_voice_messages.setter
    def send_voice_messages(self, value: bool) -> None:
        self._bitfield[-47] = int(value)
