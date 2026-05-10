import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


class TicketButton(discord.ui.View):

    def __init__(self, ticket_type):
        super().__init__(timeout=None)
        self.ticket_type = ticket_type

    @discord.ui.button(
        label="Open Ticket",
        style=discord.ButtonStyle.blurple,
        emoji="📩"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild
        user = interaction.user

        category = discord.utils.get(guild.categories, name="TICKETS")

        if category is None:
            category = await guild.create_category("TICKETS")

        channel_name = f"{self.ticket_type}-{user.name}".lower()

        existing = discord.utils.get(guild.text_channels, name=channel_name)

        if existing:
            await interaction.response.send_message(
                f"You already have a ticket: {existing.mention}",
                ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),

            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),

            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True
            )
        }

        ticket_channel = await guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🎫 Ticket Created",
            description=(
                f"Welcome {user.mention}!\n\n"
                f"📂 Ticket Type: `{self.ticket_type}`\n"
                f"⚡ Support team will assist you shortly."
            ),
            color=0x00BFFF
        )

        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)

        embed.set_footer(
            text="Skyline Tickets • Premium Support",
            icon_url=guild.icon.url if guild.icon else None
        )

        await ticket_channel.send(embed=embed)
        await ticket_channel.send("🔒 Use `!close` to close this ticket.")

        await interaction.response.send_message(
            f"✅ Ticket created: {ticket_channel.mention}",
            ephemeral=True
        )


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.command()
async def joinus(ctx):

    embed = discord.Embed(
        title="🤝 JOIN US",
        description=(
            "━━━━━━━━━━━━━━━━━━\n"
            "Interested in joining our team?\n\n"
            "📩 Open a recruitment ticket\n"
            "⚡ Speak directly with management\n"
            "🚛 Become part of Skyline\n"
            "━━━━━━━━━━━━━━━━━━"
        ),
        color=0x00FF99
    )

    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)

    embed.set_footer(
        text="Skyline Tickets • Recruitment",
        icon_url=ctx.guild.icon.url if ctx.guild.icon else None
    )

    await ctx.send(embed=embed, view=TicketButton("join-us"))


@bot.command()
async def partnership(ctx):

    embed = discord.Embed(
        title="🧞 PARTNERSHIP REQUEST",
        description=(
            "━━━━━━━━━━━━━━━━━━\n"
            "Interested in partnering with us?\n\n"
            "🤝 Open a partnership ticket\n"
            "🌐 Collaborate with Skyline\n"
            "⚡ Quick management response\n"
            "━━━━━━━━━━━━━━━━━━"
        ),
        color=0xAA00FF
    )

    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)

    embed.set_footer(
        text="Skyline Tickets • Partnership",
        icon_url=ctx.guild.icon.url if ctx.guild.icon else None
    )

    await ctx.send(embed=embed, view=TicketButton("partnership"))


@bot.command()
async def bookus(ctx):

    embed = discord.Embed(
        title="🚛 BOOK US",
        description=(
            "━━━━━━━━━━━━━━━━━━\n"
            "Need Skyline for your convoy/event?\n\n"
            "📅 Open a booking ticket\n"
            "🚛 Professional convoy services\n"
            "⚡ Fast scheduling support\n"
            "━━━━━━━━━━━━━━━━━━"
        ),
        color=0xFF9900
    )

    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)

    embed.set_footer(
        text="Skyline Tickets • Booking",
        icon_url=ctx.guild.icon.url if ctx.guild.icon else None
    )

    await ctx.send(embed=embed, view=TicketButton("book-us"))


@bot.command()
async def support(ctx):

    embed = discord.Embed(
        title="🚀 SUPPORT CENTER",
        description=(
            "━━━━━━━━━━━━━━━━━━\n"
            "Need assistance from our team?\n\n"
            "🎫 Open a private support ticket\n"
            "🔒 Secure assistance\n"
            "⚡ Fast support response\n"
            "━━━━━━━━━━━━━━━━━━"
        ),
        color=0x00BFFF
    )

    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)

    embed.set_footer(
        text="Skyline Tickets • Premium Support",
        icon_url=ctx.guild.icon.url if ctx.guild.icon else None
    )

    await ctx.send(embed=embed, view=TicketButton("support"))


@bot.command()
async def close(ctx):

    if ctx.channel.name.startswith(("join-us", "partnership", "book-us", "support")):

        await ctx.send("🔒 Closing ticket...")
        await ctx.channel.delete()

    else:
        await ctx.send("❌ This is not a ticket channel.")


bot.run(TOKEN)