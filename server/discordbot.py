# TsuserverDR, server software for Danganronpa Online based on tsuserver3,
# which is server software for Attorney Online.
#
# Copyright (C) 2016 argoneus <argoneuscze@gmail.com> (original tsuserver3)
#           (C) 2018-22 Chrezm/Iuvee <thechrezm@gmail.com> (further additions)
#           (C) 2022 Tricky Leifa (further additions)
#           (C) 2025 Yuzuru (further additions)
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


import asyncio
import discord
from discord.ext import commands
from discord.utils import escape_markdown
from discord.errors import Forbidden, HTTPException
import time


def bot_intents() -> discord.Intents:
    """
    This function returns the intents for the bot. If you want to add more intents, add it here.
    """
    intents = discord.Intents.default()
    intents.message_content = True  # Needed for events like on_message
    intents.members = True  # Needed for member-related events
    return intents


def log_bot(statement: str) -> None:
    print(f"[Discord Bot] {statement}")


class DiscordBot(commands.Bot):
    def __init__(self, server) -> None:
        super().__init__(command_prefix=None, intents=bot_intents())  # Ensure no prefix is made.
        self.bot_start_time: int = 0
        self.server = server
        self.pending_messages = []
        self.setup_events()
        self.setup_commands()

    async def init(self, token: str) -> None:
        log_bot("Initialising discord bot...")
        try:
            await self.start(token=token)
        except Exception as e:
            print(e)

    def get_channel_data_from_channel_id(self, channel_id: int) -> dict:
        for k, v in self.server.discord_data.items():
            if str(channel_id) == k:
                return {"channel": channel_id, "hub_id": v[0], "area_id": v[1]}
        return {}

    def get_channel_data_from_hub_area_id(self, hub_id: int, area_id: int) -> dict:
        for k, v in self.server.discord_data.items():
            if str(v[0]) == str(hub_id):
                if str(v[1]) == str(area_id):
                    return {"channel": int(k), "hub_id": v[0], "area_id": v[1]}
        return {}

    def queue_message(self, name, message, hub_id, area_id) -> None:
        channel_content = self.get_channel_data_from_hub_area_id(hub_id=hub_id, area_id=area_id)
        if channel_content:
            self.pending_messages.append([name, message, channel_content['channel']])

    async def get_discord_channel(self, channel_id: int) -> discord.TextChannel:
        obj = self.get_channel(channel_id)
        return obj if obj is not None else await self.fetch_channel(channel_id)

    async def send_char_message(self, name, message, channel_id: int) -> None:
        webhook = None
        try:
            to_channel = await self.get_discord_channel(channel_id)
            webhooks = await to_channel.webhooks()
            for hook in webhooks:
                if hook.user == self.user or hook.name == "DRO Bridgebot":
                    webhook = hook
                    break

            if webhook is None:
                webhook = await to_channel.create_webhook(name="DRO Bridgebot")
            await webhook.send(message, username=name, avatar_url=self.server.config['discord_bot']['avatar_url'])
            print(f'[DiscordBridge] Sending message from "{name}" to "0"')

        except Forbidden:
            print(f'[DiscordBridge] Insufficient permissions - couldnt send char message "{name}: {message}"')
        except HTTPException:
            print(f'[DiscordBridge] HTTP Failure - couldnt send char message "{name}: {message}"')
        except Exception as ex:
            # This is a workaround to a problem - [Errno 104] Connection reset by peer occurs due to too many calls for this func.
            # Simple solution is to increase the tickspeed config so it waits longer between messages sent.
            print(f"[DiscordBridge] Exception - {ex}")

    async def discord_to_dro_message(self, message: discord.Message, channel_content) -> None:
        # FIXME: I have no clue what is AO/DRO's longest length so I'll just leave this one here.
        max_char = 256
        username = f"{message.author.display_name} ({message.author.name})" if not message.author.display_name == message.author.name else message.author.display_name
        if len(message.clean_content) > max_char:
            await message.channel.send(
                "Your message was too long - it was not received by the client. (The limit is 256 characters)")
            return

        self.server.send_discord_chat(
            username,
            escape_markdown(message.clean_content),
            channel_content['hub_id'],
            channel_content['area_id']
        )

    def setup_events(self) -> None:
        """Sets up event listeners."""

        @self.event
        async def on_ready() -> None:
            log_bot(f"logged on as {self.user}!")
            self.bot_start_time = round(time.time())
            await self.change_presence(
                activity=discord.Activity(
                    type=1, name="Danganronpa Online Integration Bot", url="https://twitch.tv/twitch"))
            await self.tree.sync()
            await self.wait_until_ready()

            while True:
                if len(self.pending_messages) > 0:
                    await self.send_char_message(*self.pending_messages.pop())

                await asyncio.sleep(max(0.1, self.server.config["discord_bot"]["tickspeed"]))

        @self.event
        async def on_message(message: discord.Message) -> None:
            if message.author.bot or message.webhook_id:  # if this doesnt work maybe add "is not None"
                return  # This is so it doesn't echo eternally

            channel_content = self.get_channel_data_from_channel_id(message.channel.id)
            if channel_content:
                await self.discord_to_dro_message(message=message, channel_content=channel_content)
            # log_bot(f"{message.author.display_name}: {message.clean_content}")

        @self.event
        async def on_interaction(interaction: discord.Interaction):
            if not interaction.guild:
                return
            if interaction.type == discord.InteractionType.application_command:
                log_bot(f"[SLASH COMMAND USED] ({interaction.user}): {interaction.data['name']}")

    def setup_commands(self) -> None:
        """Sets up event commands."""

        @self.tree.command(name="ping", description="Check bot's latency")
        async def ping(interaction: discord.Interaction) -> None:
            latency = round(self.latency * 1000)
            await interaction.response.send_message(f"**Pong! {latency}ms**")

        @self.tree.command(name="info", description="Show bot information")
        async def info(interaction: discord.Interaction) -> None:
            embed = discord.Embed(
                title=f"{self.user.display_name}'s Mirror World",
                description="A slash-command-only Discord bot for Danganronpa Online integration",
                color=discord.Color.red()
            )
            embed.add_field(name="Bot Creator", value="yuzurukyun", inline=True)
            embed.add_field(name="Bot Runtime", value=f"<t:{self.bot_start_time}:R>", inline=True)
            await interaction.response.send_message(embed=embed)

        @self.tree.command(name="bridgebot_channels")
        @commands.has_permissions(administrator=True)
        async def bridgebot_channels(interaction: discord.Interaction) -> None:
            # FIXME: This is barebones and complete ass so rewriting it later.
            await interaction.response.send_message(f"{self.server.discord_data}")
