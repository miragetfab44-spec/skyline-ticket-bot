import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import sqlite3
from datetime import datetime
import html

load_dotenv()
TOKEN = os.getenv("TOKEN")

BRAND_NAME = "Skyline Tickets"
LOG_CHANNEL_NAME = "ticket-logs"

TICKET_CONFIG = {
    "join-us": {"title": "🤝 JOIN US", "role": "Human Resource", "color": 0x00FF99},
    "partnership": {"title": "🧞 PARTNERSHIP REQUEST", "role": "Partnership Manager", "color": 0xAA00FF},
    "book-us": {"title": "🚛 BOOK US", "role": "SSV Staff", "color": 0xFF9900},
    "support": {"title": "🚀 SUPPORT CENTER", "role": "Support Staff", "color": 0x00BFFF},
}

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

db = sqlite3.connect("tickets.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    ticket_type TEXT,
    channel_name TEXT,
    created_at TEXT,
    closed_at TEXT,
    claimed_by TEXT,
    claimed_at TEXT,
    status TEXT
)
""")
db.commit()


async def send_log(guild, embed, file=None):
    log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
    if log_channel:
        await log_channel.send(embed=embed, file=file)


async def create_transcript(channel, ticket_id):
    messages = []

    async for msg in channel.history(limit=None, oldest_first=True):
        time = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        author = html.escape(str(msg.author))
        content = html.escape(msg.content)

        if msg.attachments:
            for attachment in msg.attachments:
                content += f'<br><a href="{attachment.url}">Attachment: {html.escape(attachment.filename)}</a>'

        messages.append(f"""
        <div class="message">
            <div class="meta">[{time}] <b>{author}</b></div>
            <div class="content">{content}</div>
        </div>
        """)

    transcript_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Ticket Transcript #{ticket_id}</title>
        <style>
            body {{
                background: #0f1117;
                color: #ffffff;
                font-family: Arial, sans-serif;
                padding: 30px;
            }}
            .header {{
                background: #111827;
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 20px;
                border-left: 5px solid #00BFFF;
            }}
            .message {{
                background: #1f2937;
                margin-bottom: 12px;
                padding: 14px;
                border-radius: 10px;
            }}
            .meta {{
                color: #7dd3fc;
                margin-bottom: 8px;
                font-size: 14px;
            }}
            .content {{
                color: #e5e7eb;
                white-space: pre-wrap;
            }}
            a {{
                color: #38bdf8;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{BRAND_NAME}</h1>
            <h2>Ticket Transcript #{ticket_id}</h2>
            <p>Channel: {html.escape(channel.name)}</p>
        </div>
        {''.join(messages)}
    </body>
    </html>
    """

    filename = f"transcript-ticket-{ticket_id}.html"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(transcript_html)

    return filename


class TicketControlView(discord.ui.View):
    def __init__(self, ticket_type):
        super().__init__(timeout=None)
        self.ticket_type = ticket_type

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.green, emoji="✅")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        config = TICKET_CONFIG[self.ticket_type]

        staff_role = discord.utils.get(guild.roles, name=config["role"])

        if staff_role not in user.roles:
            await interaction.response.send_message("❌ You are not allowed to claim this ticket.", ephemeral=True)
            return

        cursor.execute(
            "SELECT id, claimed_by FROM tickets WHERE channel_name = ? AND status = ?",
            (interaction.channel.name, "open")
        )
        result = cursor.fetchone()

        if result and result[1]:
            await interaction.response.send_message(f"❌ Already claimed by `{result[1]}`.", ephemeral=True)
            return

        ticket_id = result[0] if result else "Unknown"
        claimed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            "UPDATE tickets SET claimed_by = ?, claimed_at = ? WHERE channel_name = ? AND status = ?",
            (str(user), claimed_at, interaction.channel.name, "open")
        )
        db.commit()

        button.disabled = True
        button.label = f"Claimed by {user.display_name}"

        await interaction.response.edit_message(view=self)

        embed = discord.Embed(
            title=f"✅ Ticket #{ticket_id} Claimed",
            description=f"This ticket has been claimed by {user.mention}.",
            color=0x00FF99
        )
        embed.set_footer(text=BRAND_NAME)

        await interaction.channel.send(embed=embed)


class TicketButton(discord.ui.View):
    def __init__(self, ticket_type):
        super().__init__(timeout=None)
        self.ticket_type = ticket_type

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.blurple, emoji="📩")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        config = TICKET_CONFIG[self.ticket_type]

        staff_role = discord.utils.get(guild.roles, name=config["role"])

        if staff_role is None:
            await interaction.response.send_message(f"❌ Role `{config['role']}` not found.", ephemeral=True)
            return

        category = discord.utils.get(guild.categories, name="TICKETS")
        if category is None:
            category = await guild.create_category("TICKETS")

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            "INSERT INTO tickets (user_id, username, ticket_type, created_at, status) VALUES (?, ?, ?, ?, ?)",
            (user.id, str(user), self.ticket_type, created_at, "open")
        )
        db.commit()

        ticket_id = cursor.lastrowid
        safe_name = user.name.lower().replace(" ", "-")
        channel_name = f"{self.ticket_type}-{ticket_id}-{safe_name}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            staff_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True)
        }

        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        cursor.execute(
            "UPDATE tickets SET channel_name = ? WHERE id = ?",
            (ticket_channel.name, ticket_id)
        )
        db.commit()

        embed = discord.Embed(
            title=f"🎫 Ticket Created #{ticket_id}",
            description=(
                f"Welcome {user.mention}!\n\n"
                f"🆔 **Ticket ID:** `#{ticket_id}`\n"
                f"📂 **Type:** `{config['title']}`\n"
                f"👮 **Staff Team:** {staff_role.mention}\n\n"
                f"Please explain your request clearly."
            ),
            color=config["color"]
        )

        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.set_footer(text=f"{BRAND_NAME} • Premium Ticket System")

        await ticket_channel.send(
            content=f"{staff_role.mention} New ticket opened by {user.mention}",
            embed=embed
        )

        await ticket_channel.send(
            "✅ Staff can claim this ticket below.\n🔒 Use `!close` to close this ticket.",
            view=TicketControlView(self.ticket_type)
        )

        log_embed = discord.Embed(title=f"📥 Ticket Opened #{ticket_id}", color=0x00FF99)
        log_embed.add_field(name="User", value=user.mention, inline=True)
        log_embed.add_field(name="Type", value=config["title"], inline=True)
        log_embed.add_field(name="Channel", value=ticket_channel.mention, inline=False)
        log_embed.add_field(name="Staff Role", value=staff_role.mention, inline=True)
        log_embed.add_field(name="Created At", value=created_at, inline=True)
        log_embed.set_footer(text=BRAND_NAME)

        await send_log(guild, log_embed)

        await interaction.response.send_message(
            f"✅ Ticket created: {ticket_channel.mention} `#{ticket_id}`",
            ephemeral=True
        )


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


async def send_ticket_panel(ctx, ticket_type):
    config = TICKET_CONFIG[ticket_type]

    embed = discord.Embed(
        title=config["title"],
        description=(
            "━━━━━━━━━━━━━━━━━━\n"
            "🔒 Private ticket\n"
            "⚡ Fast staff response\n"
            "🆔 Auto ticket ID\n"
            "📄 HTML transcript on close\n"
            "📩 Click below to open\n"
            "━━━━━━━━━━━━━━━━━━"
        ),
        color=config["color"]
    )

    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
    embed.set_footer(text=f"{BRAND_NAME} • {config['role']}")

    await ctx.send(embed=embed, view=TicketButton(ticket_type))


@bot.command()
async def joinus(ctx):
    await send_ticket_panel(ctx, "join-us")


@bot.command()
async def partnership(ctx):
    await send_ticket_panel(ctx, "partnership")


@bot.command()
async def bookus(ctx):
    await send_ticket_panel(ctx, "book-us")


@bot.command()
async def support(ctx):
    await send_ticket_panel(ctx, "support")


@bot.command()
async def close(ctx):
    if not ctx.channel.name.startswith(tuple(TICKET_CONFIG.keys())):
        await ctx.send("❌ This is not a ticket channel.")
        return

    cursor.execute(
        "SELECT id, ticket_type, username FROM tickets WHERE channel_name = ? AND status = ?",
        (ctx.channel.name, "open")
    )
    result = cursor.fetchone()

    ticket_id = result[0] if result else "Unknown"
    ticket_type = result[1] if result else "Unknown"
    username = result[2] if result else "Unknown"

    await ctx.send("📄 Saving transcript...")

    transcript_file = await create_transcript(ctx.channel, ticket_id)

    closed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        "UPDATE tickets SET closed_at = ?, status = ? WHERE channel_name = ? AND status = ?",
        (closed_at, "closed", ctx.channel.name, "open")
    )
    db.commit()

    log_embed = discord.Embed(title=f"📤 Ticket Closed #{ticket_id}", color=0xFF0000)
    log_embed.add_field(name="Closed By", value=ctx.author.mention, inline=True)
    log_embed.add_field(name="Opened By", value=username, inline=True)
    log_embed.add_field(name="Type", value=ticket_type, inline=True)
    log_embed.add_field(name="Channel", value=ctx.channel.name, inline=False)
    log_embed.add_field(name="Closed At", value=closed_at, inline=False)
    log_embed.set_footer(text=f"{BRAND_NAME} • Transcript Attached")

    file = discord.File(transcript_file)
    await send_log(ctx.guild, log_embed, file=file)

    await ctx.send("🔒 Closing ticket...")
    await ctx.channel.delete()

    if os.path.exists(transcript_file):
        os.remove(transcript_file)


bot.run(TOKEN)