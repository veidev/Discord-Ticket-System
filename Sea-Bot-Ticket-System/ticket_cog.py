"""
Discord.py ticket sistemi — Sea Bot'tan ayrılmış modül.

Entegrasyon: bot oluşturduktan sonra:
    from ticket_cog import TicketCog
    bot.add_cog(
        TicketCog(
            bot,
            get_guild_config=get_guild_config,
            save_config=save_config,
            prefix=PREFIX,
            allowed_guild_ids=ALLOWED_GUILD_IDS,
            is_moderator=is_member_moderator,
        )
    )

config.json guild kaydı şu anahtarları içermeli:
    ticket_category_id, ticket_log_channel_id, ticket_support_role_id
"""

from __future__ import annotations

import io
from typing import Callable, FrozenSet, Optional

import discord
from discord.ext import commands


def _format_reason(reason: Optional[str]) -> str:
    return reason if reason else "Sebep belirtilmedi."


class TicketOpenView(discord.ui.View):
    def __init__(self, cog: "TicketCog"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Open Ticket",
        style=discord.ButtonStyle.green,
        emoji="🎫",
        custom_id="ticket_open_button",
    )
    async def ticket_open(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Tickets can only be used inside a server.",
                ephemeral=True,
            )
            return

        if interaction.guild.id not in self.cog.allowed_guild_ids:
            await interaction.response.send_message(
                "Bu bot bu sunucuda bilet açmayı desteklemiyor.",
                ephemeral=True,
            )
            return

        ticket_channel, error = await self.cog.create_ticket_channel_for_user(
            interaction.guild,
            interaction.user,
            reason=None,
        )
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        await interaction.response.send_message(
            f"Your ticket has been created: {ticket_channel.mention}",
            ephemeral=True,
        )


class TicketManageView(discord.ui.View):
    def __init__(self, cog: "TicketCog", opener_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.opener_id = opener_id

    async def _is_support(self, member: discord.Member) -> bool:
        if self.cog.is_moderator(member):
            return True
        gconf = self.cog.get_guild_config(member.guild.id)
        support_role_id = gconf.get("ticket_support_role_id")
        if support_role_id:
            role = member.guild.get_role(support_role_id)
            if role and role in member.roles:
                return True
        return False

    @discord.ui.button(
        label="Claim",
        style=discord.ButtonStyle.primary,
        emoji="✅",
        custom_id="ticket_claim_button",
    )
    async def claim_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "This button can only be used inside a server ticket.",
                ephemeral=True,
            )
            return

        if not await self._is_support(interaction.user):
            await interaction.response.send_message(
                "Only support staff or moderators can claim tickets.",
                ephemeral=True,
            )
            return

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "This is not a valid ticket channel.",
                ephemeral=True,
            )
            return

        topic = channel.topic or ""
        if "CLAIMED_BY:" in topic:
            await interaction.response.send_message(
                "This ticket is already claimed.",
                ephemeral=True,
            )
            return

        new_topic = (topic + f" | CLAIMED_BY:{interaction.user.id}").strip()
        try:
            await channel.edit(
                topic=new_topic,
                reason=f"Ticket claimed by {interaction.user}",
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

        await channel.send(f"✅ Ticket claimed by {interaction.user.mention}.")
        await interaction.response.send_message(
            "You have claimed this ticket.", ephemeral=True
        )

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="ticket_close_button",
    )
    async def close_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "This button can only be used inside a server ticket.",
                ephemeral=True,
            )
            return

        channel = interaction.channel
        if (
            not isinstance(channel, discord.TextChannel)
            or not channel.topic
            or "TICKET_USER:" not in channel.topic
        ):
            await interaction.response.send_message(
                "This button can only be used inside a ticket channel.",
                ephemeral=True,
            )
            return

        member = interaction.user
        is_support = await self._is_support(member)
        allowed = is_support or (member.id == self.opener_id)
        if not allowed:
            await interaction.response.send_message(
                "Only the ticket opener or support staff can close this ticket.",
                ephemeral=True,
            )
            return

        await self.cog.close_ticket_core(
            channel=channel,
            guild=interaction.guild,
            closed_by=member,
            reason="Closed via button",
        )

        try:
            await interaction.response.defer()
        except discord.HTTPException:
            pass


class TicketCog(commands.Cog):
    """Support ticket panel, private channels, claim/close, HTML transcript."""

    def __init__(
        self,
        bot: commands.Bot,
        *,
        get_guild_config: Callable[[int], dict],
        save_config: Callable[[], None],
        prefix: str,
        allowed_guild_ids: FrozenSet[int],
        is_moderator: Callable[[discord.Member], bool],
    ):
        self.bot = bot
        self.get_guild_config = get_guild_config
        self.save_config = save_config
        self.prefix = prefix
        self.allowed_guild_ids = allowed_guild_ids
        self.is_moderator = is_moderator
        self._persistent_views_registered = False

    @commands.Cog.listener()
    async def on_ready(self):
        if not self._persistent_views_registered:
            self.bot.add_view(TicketOpenView(self))
            self._persistent_views_registered = True

    def find_existing_ticket_channel(
        self, guild: discord.Guild, user: discord.Member
    ) -> Optional[discord.TextChannel]:
        for channel in guild.text_channels:
            if channel.topic and f"TICKET_USER:{user.id}" in channel.topic:
                return channel
        return None

    def build_ticket_transcript_html(
        self, channel: discord.TextChannel, messages: list[discord.Message]
    ) -> str:
        html_lines = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<meta charset='utf-8'><title>Ticket Transcript - {channel.name}</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; background: #2c2f33; color: #ddd; }",
            ".msg { margin: 4px 0; padding: 4px 6px; border-bottom: 1px solid #444; }",
            ".author { font-weight: bold; color: #fff; }",
            ".timestamp { color: #aaa; font-size: 0.8em; margin-left: 6px; }",
            ".content { margin-top: 2px; white-space: pre-wrap; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h2>Ticket Transcript - {channel.name}</h2>",
            f"<p>Guild: {channel.guild.name}</p>",
            "<hr>",
        ]

        for msg in messages:
            created = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            author = f"{msg.author} ({msg.author.id})"
            content = (
                msg.content.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            html_lines.append("<div class='msg'>")
            html_lines.append(
                f"<div><span class='author'>{author}</span><span class='timestamp'>{created}</span></div>"
            )
            if content:
                html_lines.append(f"<div class='content'>{content}</div>")
            if msg.attachments:
                html_lines.append("<div class='content'>Attachments:<br>")
                for att in msg.attachments:
                    safe_name = (
                        att.filename.replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                    )
                    html_lines.append(
                        f"- <a href='{att.url}' target='_blank'>{safe_name}</a><br>"
                    )
                html_lines.append("</div>")
            html_lines.append("</div>")

        html_lines.append("</body></html>")
        return "\n".join(html_lines)

    async def create_ticket_channel_for_user(
        self,
        guild: discord.Guild,
        user: discord.Member,
        reason: Optional[str] = None,
    ) -> tuple[Optional[discord.TextChannel], Optional[str]]:
        if guild.id not in self.allowed_guild_ids:
            return None, "Bu sunucuda bilet oluşturulamaz."

        gconf = self.get_guild_config(guild.id)
        category_id = gconf.get("ticket_category_id")
        support_role_id = gconf.get("ticket_support_role_id")

        if not category_id:
            return (
                None,
                "Ticket category is not configured. Ask an admin to run "
                f"`{self.prefix}config ticket-category <category>`.",
            )

        existing = self.find_existing_ticket_channel(guild, user)
        if existing:
            return None, f"You already have an open ticket: {existing.mention}"

        category = guild.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            return None, "Ticket category in config is invalid. Please reconfigure it."

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                read_messages=False, send_messages=False
            ),
            user: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                attach_files=True,
                embed_links=True,
            ),
            guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True,
            ),
        }

        support_role = None
        if support_role_id:
            support_role = guild.get_role(support_role_id)
            if support_role:
                overwrites[support_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    embed_links=True,
                )

        channel_name = f"ticket-{user.name}".replace(" ", "-")[:90]
        topic = f"TICKET_USER:{user.id} | Created by {user} | Reason: {_format_reason(reason)}"

        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=topic,
            reason=f"Ticket created by {user} - {_format_reason(reason)}",
        )

        mention_support = support_role.mention if support_role else ""
        embed = discord.Embed(
            title="New Ticket",
            description=(
                f"Hello {user.mention}, a staff member will be with you shortly.\n"
                f"Use `{self.prefix}close [reason]` to close this ticket when you're done."
            ),
            color=discord.Color.blurple(),
        )
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)

        await ticket_channel.send(
            content=mention_support,
            embed=embed,
            view=TicketManageView(self, user.id),
        )
        return ticket_channel, None

    async def close_ticket_core(
        self,
        channel: discord.TextChannel,
        guild: discord.Guild,
        closed_by: discord.abc.User,
        reason: Optional[str],
    ) -> None:
        gconf = self.get_guild_config(guild.id)
        log_channel_id = gconf.get("ticket_log_channel_id")
        log_channel = guild.get_channel(log_channel_id) if log_channel_id else None

        messages: list[discord.Message] = []
        async for msg in channel.history(limit=None, oldest_first=True):
            messages.append(msg)

        html_content = self.build_ticket_transcript_html(channel, messages)
        fp = io.BytesIO(html_content.encode("utf-8"))
        filename = f"{channel.name}-transcript.html"

        target = (
            log_channel if isinstance(log_channel, discord.TextChannel) else channel
        )
        file = discord.File(fp, filename=filename)

        embed = discord.Embed(
            title="Ticket Closed",
            description=(
                f"Ticket channel: {channel.mention}\n"
                f"Closed by: {closed_by.mention if isinstance(closed_by, discord.Member) else closed_by}"
            ),
            color=discord.Color.dark_gray(),
        )
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)

        await target.send(embed=embed, file=file)

        try:
            await channel.send(
                f"Ticket closed by {closed_by}. Transcript has been saved."
            )
        except discord.HTTPException:
            pass

        await channel.delete(
            reason=f"Ticket closed by {closed_by} - {_format_reason(reason)}"
        )

    @commands.command(name="ticket")
    @commands.guild_only()
    async def create_ticket(
        self, ctx: commands.Context, *, reason: Optional[str] = None
    ):
        """Create a private support ticket channel for the user."""
        ticket_channel, error = await self.create_ticket_channel_for_user(
            ctx.guild, ctx.author, reason
        )
        if error:
            await ctx.send(error)
            return

        await ctx.send(f"Ticket created: {ticket_channel.mention}")

    @commands.command(name="ticket-panel")
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def ticket_panel(
        self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None
    ):
        """Post a message with a button to open tickets."""
        target = channel or ctx.channel

        embed = discord.Embed(
            title="Support Tickets",
            description=(
                "If you need help, click the button below to create a private ticket.\n"
                "A staff member will respond as soon as possible."
            ),
            color=discord.Color.blurple(),
        )
        embed.set_footer(
            text="A new private channel will be created for your ticket."
        )

        await target.send(embed=embed, view=TicketOpenView(self))
        if target.id != ctx.channel.id:
            await ctx.send(f"Ticket panel sent to {target.mention}.")

    @commands.command(name="close")
    @commands.guild_only()
    async def close_ticket_cmd(
        self, ctx: commands.Context, *, reason: Optional[str] = None
    ):
        """Close the current ticket, generate HTML transcript, send to log channel."""
        channel = ctx.channel
        if (
            not isinstance(channel, discord.TextChannel)
            or not channel.topic
            or "TICKET_USER:" not in channel.topic
        ):
            await ctx.send("This command can only be used inside a ticket channel.")
            return

        await self.close_ticket_core(
            channel=channel,
            guild=ctx.guild,
            closed_by=ctx.author,
            reason=reason,
        )

    @commands.group(name="ticket-config", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def ticket_config_group(self, ctx: commands.Context):
        p = self.prefix
        await ctx.send(
            "Ticket yapılandırması:\n"
            f"`{p}ticket-config category <category>`\n"
            f"`{p}ticket-config log-channel #channel`\n"
            f"`{p}ticket-config support-role @role`"
        )

    @ticket_config_group.command(name="category")
    async def set_ticket_category(
        self, ctx: commands.Context, category: discord.CategoryChannel
    ):
        gconf = self.get_guild_config(ctx.guild.id)
        gconf["ticket_category_id"] = category.id
        self.save_config()
        await ctx.send(f"Ticket category set to `{category.name}`.")

    @ticket_config_group.command(name="log-channel")
    async def set_ticket_log_channel(
        self, ctx: commands.Context, channel: discord.TextChannel
    ):
        gconf = self.get_guild_config(ctx.guild.id)
        gconf["ticket_log_channel_id"] = channel.id
        self.save_config()
        await ctx.send(f"Ticket log channel set to {channel.mention}.")

    @ticket_config_group.command(name="support-role")
    async def set_ticket_support_role(
        self, ctx: commands.Context, role: discord.Role
    ):
        gconf = self.get_guild_config(ctx.guild.id)
        gconf["ticket_support_role_id"] = role.id
        self.save_config()
        await ctx.send(f"Ticket support role set to `{role.name}`.")