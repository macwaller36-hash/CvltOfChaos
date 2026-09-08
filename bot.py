import os
import logging
import random

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
SUPPORT_CHANNEL_ID = int(os.getenv("DISCORD_SUPPORT_CHANNEL_ID", "0"))
STAFF_ROLE_IDS = [int(x) for x in os.getenv("DISCORD_STAFF_ROLE_IDS", "").split(",") if x.strip()]
STAFF_USER_IDS = [int(x) for x in os.getenv("DISCORD_STAFF_USER_IDS", "1322411501381877872").split(",") if x.strip()]
CLOSE_CHANNEL_ID = int(os.getenv("DISCORD_CLOSE_CHANNEL_ID", "0"))
CLOSED_NOTIFY_CHANNEL_ID = int(os.getenv("DISCORD_CLOSED_CHANNEL_ID", "0"))
MESSAGE_ONLY_MODE = os.getenv("MESSAGE_ONLY_MODE", "1") == "1"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

COMMAND_PREFIXES = ("!", "c!")

bot = commands.Bot(command_prefix=COMMAND_PREFIXES, intents=intents, help_command=None)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

application_questions = [
    "What is your Discord username and tag?",
    "How old are you?",
    "What previous moderation or staff experience do you have?",
    "Why do you want to join staff, and what will you bring to the team?",
    "Is there anything else you want the team to know?",
]

partnership_questions = [
    "What is your server name and invite link?",
    "What is the main topic or focus of your server?",
    "What type of partnership are you proposing (co-host, promotion, resource sharing, etc.)?",
    "What is your target audience and server size?",
    "Is there anything else you'd like to share about this partnership?",
]

pending_applications = {}
pending_partnerships = {}
pending_ticket_details = {}
ticket_threads_user = {}
ticket_threads_thread = {}

CATEGORY_KEYWORDS = {
    "support": "Support",
    "help": "Support",
    "issue": "Issue",
    "bug": "Issue",
    "suggestion": "Suggestion",
    "idea": "Suggestion",
    "application": "Application",
    "apply": "Application",
    "partnership": "Partnership",
    "partner": "Partnership",
    "collab": "Partnership",
}


def should_prompt_for_ticket_details(user_id: int, pending: set[int] | dict[int, str]) -> bool:
    return user_id not in pending


def mark_dm_prompt_seen(user_id: int, pending: set[int] | dict[int, str], category: str = "Support") -> None:
    if isinstance(pending, set):
        pending.add(user_id)
        return
    pending[user_id] = category


def should_use_followup_as_ticket_body(user_id: int, pending: set[int] | dict[int, str]) -> bool:
    return user_id in pending


def clear_dm_prompt(user_id: int, pending: set[int] | dict[int, str]) -> None:
    if isinstance(pending, set):
        pending.discard(user_id)
        return
    pending.pop(user_id, None)


def should_reply_with_hey(content: str) -> bool:
    return content.strip().lower() == "hi"


def should_play_cheeseburger_noise(content: str) -> bool:
    text = content.strip().lower()
    return "cheese burger" in text or "cheeseburger" in text


def get_staff_proxy_message(content: str) -> str | None:
    if not content.startswith("."):
        return None
    proxied = content[1:].strip()
    return proxied or None


def has_command_prefix(content: str) -> bool:
    return content.startswith(COMMAND_PREFIXES)


def draw_blackjack_card() -> str:
    return random.choice(["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"])


def get_blackjack_total(hand: list[str]) -> int:
    total = 0
    aces = 0
    for card in hand:
        if card == "A":
            total += 11
            aces += 1
        elif card in {"J", "Q", "K"}:
            total += 10
        else:
            total += int(card)

    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def format_blackjack_hand(hand: list[str]) -> str:
    return " ".join(hand)


def play_blackjack_hand() -> list[str]:
    hand = [draw_blackjack_card(), draw_blackjack_card()]
    while get_blackjack_total(hand) < 17:
        hand.append(draw_blackjack_card())
    return hand


def get_rps_round(user_pick: str) -> tuple[str, str]:
    # No-tie mode: bot pick is chosen so each side has a 50/50 chance to win.
    winning_pick = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
    losing_pick = {"rock": "paper", "paper": "scissors", "scissors": "rock"}
    if random.random() < 0.5:
        return winning_pick[user_pick], "You win."
    return losing_pick[user_pick], "You lose."


class BlackjackView(discord.ui.View):
    def __init__(self, player_id: int):
        super().__init__(timeout=90)
        self.player_id = player_id
        self.player_hand = [draw_blackjack_card(), draw_blackjack_card()]
        self.dealer_hand = [draw_blackjack_card(), draw_blackjack_card()]
        self.finished = False
        self.message: discord.Message | None = None

    def render(self, reveal_dealer: bool = False, result: str | None = None) -> str:
        player_total = get_blackjack_total(self.player_hand)

        if reveal_dealer:
            dealer_cards = format_blackjack_hand(self.dealer_hand)
            dealer_total = get_blackjack_total(self.dealer_hand)
            lines = [
                "Blackjack round:",
                f"You: **{format_blackjack_hand(self.player_hand)}** (total: **{player_total}**)",
                f"Dealer: **{dealer_cards}** (total: **{dealer_total}**)",
            ]
            if result:
                lines.append(result)
            return "\n".join(lines)

        dealer_show = self.dealer_hand[0]
        return (
            "Blackjack round:\n"
            f"You: **{format_blackjack_hand(self.player_hand)}** (total: **{player_total}**)\n"
            f"Dealer: **{dealer_show} ?**\n"
            "Press **Hit** or **Stand**."
        )

    def finish_and_lock(self) -> None:
        self.finished = True
        for child in self.children:
            child.disabled = True

    def dealer_play(self) -> None:
        while get_blackjack_total(self.dealer_hand) < 17:
            self.dealer_hand.append(draw_blackjack_card())

    def resolve_winner_text(self) -> str:
        player_total = get_blackjack_total(self.player_hand)
        dealer_total = get_blackjack_total(self.dealer_hand)

        if player_total > 21:
            return "You bust. Dealer wins."
        if dealer_total > 21:
            return "Dealer busts. You win!"
        if player_total > dealer_total:
            return "You win!"
        if dealer_total > player_total:
            return "Dealer wins."
        return random.choice(["Push broken by luck: You win!", "Push broken by luck: Dealer wins."])

    async def guard_player(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.player_id:
            return True
        await interaction.response.send_message("Only the player who started this blackjack round can press these buttons.", ephemeral=True)
        return False

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.guard_player(interaction):
            return
        if self.finished:
            await interaction.response.defer()
            return

        self.player_hand.append(draw_blackjack_card())
        player_total = get_blackjack_total(self.player_hand)

        if player_total >= 21:
            if player_total == 21:
                self.dealer_play()
            result = self.resolve_winner_text()
            self.finish_and_lock()
            await interaction.response.edit_message(content=self.render(reveal_dealer=True, result=result), view=self)
            return

        await interaction.response.edit_message(content=self.render(), view=self)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.guard_player(interaction):
            return
        if self.finished:
            await interaction.response.defer()
            return

        self.dealer_play()
        result = self.resolve_winner_text()
        self.finish_and_lock()
        await interaction.response.edit_message(content=self.render(reveal_dealer=True, result=result), view=self)

    async def on_timeout(self) -> None:
        if self.finished:
            return
        self.finish_and_lock()
        if self.message is not None:
            try:
                await self.message.edit(content=self.render(reveal_dealer=True, result="Round timed out."), view=self)
            except Exception:
                pass


def is_staff(member: discord.Member) -> bool:
    if member.id in STAFF_USER_IDS:
        return True
    if member.guild_permissions.manage_messages:
        return True
    if not STAFF_ROLE_IDS:
        return False
    return any(role.id in STAFF_ROLE_IDS for role in member.roles)


async def is_staff_user(user: discord.User) -> bool:
    if user.id in STAFF_USER_IDS:
        return True
    for guild in bot.guilds:
        member = guild.get_member(user.id)
        if not member:
            continue
        if member.guild_permissions.manage_messages:
            return True
        if STAFF_ROLE_IDS and any(role.id in STAFF_ROLE_IDS for role in member.roles):
            return True
    return False


def staff_check():
    async def predicate(ctx: commands.Context):
        if ctx.guild is None:
            return False
        if is_staff(ctx.author):
            return True
        raise commands.CheckFailure("You do not have permission to use this command.")

    return commands.check(predicate)


class TicketActionView(discord.ui.View):
    def __init__(self, user_id: int, category: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.category = category

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_staff_user(interaction.user):
            await interaction.response.send_message("You do not have permission to perform this action.", ephemeral=True)
            return

        target = await bot.fetch_user(self.user_id)
        template = os.getenv(
            "APPLICATION_ACCEPT_TEMPLATE",
            "Hello! Your application has been accepted. We will follow up soon.",
        )
        if self.category == "Partnership":
            template = os.getenv(
                "PARTNER_ACCEPT_TEMPLATE",
                "Hello! Your partnership request has been accepted. We'll follow up with next steps soon.",
            )
        try:
            await target.send(template)
            await interaction.response.send_message("Requester notified (accepted).", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Unable to DM the requester; their DMs may be closed.", ephemeral=True)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_staff_user(interaction.user):
            await interaction.response.send_message("You do not have permission to perform this action.", ephemeral=True)
            return

        target = await bot.fetch_user(self.user_id)
        template = os.getenv(
            "APPLICATION_REJECT_TEMPLATE",
            "Thank you for applying. At this time we are not proceeding with your application.",
        )
        if self.category == "Partnership":
            template = os.getenv(
                "PARTNER_REJECT_TEMPLATE",
                "Thank you for your interest. At this time we are not proceeding with a partnership.",
            )
        try:
            await target.send(template)
            await interaction.response.send_message("Requester notified (rejected).", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Unable to DM the requester; their DMs may be closed.", ephemeral=True)


def get_category(name: str) -> str | None:
    text = name.lower().lstrip("!")
    if category := CATEGORY_KEYWORDS.get(text):
        return category
    import re

    words = re.sub(r"[^a-z0-9 ]+", " ", text).split()
    for word in words:
        if word in CATEGORY_KEYWORDS:
            return CATEGORY_KEYWORDS[word]
    return None


def format_embed(author: discord.User, category: str, content: str) -> discord.Embed:
    colors = {
        "Issue": discord.Color.red(),
        "Support": discord.Color.blue(),
        "Suggestion": discord.Color.green(),
        "Application": discord.Color.gold(),
        "Partnership": discord.Color.purple(),
        "Closed Ticket": discord.Color.dark_red(),
    }
    embed = discord.Embed(
        title=f"New {category} Message",
        description=content or "(No message content)",
        color=colors.get(category, discord.Color.blurple()),
    )
    embed.set_author(name=str(author), icon_url=author.display_avatar.url)
    embed.add_field(name="User ID", value=str(author.id), inline=False)
    return embed


def get_dm_intro_text() -> str:
    return (
        "Hello! What would you like to open a ticket for?\n\n"
        "**Available ticket types:**\n"
        "• `support` - General support requests\n"
        "• `issue` - Report a bug or problem\n"
        "• `suggestion` - Share an idea or suggestion\n"
        "• `application` - Apply to join staff\n"
        "• `partnership` - Partnership proposals\n\n"
        "**Examples:**\n"
        "`support I need help with my account`\n"
        "`issue I found a bug in the bot`\n"
        "`suggestion Add a cool new feature`"
    )


async def send_dm_intro(user: discord.User) -> None:
    await user.send(get_dm_intro_text())


def get_ticket_details_prompt(category: str) -> str:
    if category == "Issue":
        return "Please tell me what issue you want to report."
    if category == "Suggestion":
        return "Please tell me your suggestion so I can log it properly."
    return "Please tell me what you want to open this ticket for."


async def ask_for_ticket_details(user: discord.User, category: str) -> None:
    if pending_ticket_details.get(user.id) == category:
        return
    mark_dm_prompt_seen(user.id, pending_ticket_details, category)
    await user.send(get_ticket_details_prompt(category))


async def get_support_channel() -> discord.TextChannel | None:
    if SUPPORT_CHANNEL_ID == 0:
        return None
    channel = bot.get_channel(SUPPORT_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(SUPPORT_CHANNEL_ID)
        except discord.NotFound:
            return None
    return channel if isinstance(channel, discord.TextChannel) else None


async def find_or_sync_thread_for_user(user: discord.User) -> discord.Thread | None:
    channel = await get_support_channel()
    if channel is None:
        return None

    if user.id in ticket_threads_user:
        thread_id = ticket_threads_user[user.id]
        try:
            thread = bot.get_channel(thread_id) or await bot.fetch_channel(thread_id)
            if isinstance(thread, discord.Thread):
                return thread
        except Exception:
            logger.exception("Failed to fetch mapped thread %s for user %s", thread_id, user.id)
        ticket_threads_user.pop(user.id, None)
        ticket_threads_thread.pop(thread_id, None)

    try:
        async for thread in channel.archived_threads(limit=100):
            if thread.name == f"ticket-{user.id}":
                ticket_threads_user[user.id] = thread.id
                ticket_threads_thread[thread.id] = user.id
                return thread
    except Exception:
        logger.exception("Failed to search archived threads for user %s", user.id)

    try:
        for thread in channel.threads:
            if thread.name == f"ticket-{user.id}":
                ticket_threads_user[user.id] = thread.id
                ticket_threads_thread[thread.id] = user.id
                return thread
    except Exception:
        logger.exception("Failed to search active threads for user %s", user.id)

    return None


async def send_support_log(author: discord.User, category: str, content: str, footer: str | None = None):
    channel = await get_support_channel()
    if channel is None:
        logger.warning("Support channel not configured")
        return None

    embed = format_embed(author, category, content)
    if footer:
        embed.set_footer(text=footer)

    view = None
    if category in {"Application", "Partnership"}:
        view = TicketActionView(author.id, category)

    msg = await channel.send(embed=embed, view=view)
    try:
        if author.id not in ticket_threads_user:
            thread = await msg.create_thread(name=f"ticket-{author.id}", auto_archive_duration=1440)
            ticket_threads_user[author.id] = thread.id
            ticket_threads_thread[thread.id] = author.id
    except Exception:
        logger.exception("Failed to create ticket thread for %s", author.id)
    return msg


async def ask_application_question(user: discord.User, step: int):
    question = application_questions[step]
    await user.send(
        f"Thank you for applying! Please answer question {step + 1} of {len(application_questions)}:\n\n{question}"
    )


async def finish_application(user: discord.User):
    state = pending_applications.pop(user.id, None)
    if state is None:
        return
    answers = state["answers"]
    content = "\n\n".join(
        f"**Q{idx + 1}.** {question}\n**A:** {answer}"
        for idx, (question, answer) in enumerate(zip(application_questions, answers))
    )
    await send_support_log(user, "Application", content, footer="Staff application submitted")
    await user.send("The staff team has been notified. Please wait for their response — thank you for applying!")


async def finish_partnership(user: discord.User):
    state = pending_partnerships.pop(user.id, None)
    if state is None:
        return
    answers = state["answers"]
    content = "\n\n".join(
        f"**Q{idx + 1}.** {question}\n**A:** {answer}"
        for idx, (question, answer) in enumerate(zip(partnership_questions, answers))
    )
    await send_support_log(user, "Partnership", content, footer="Partnership request submitted")
    await user.send("Thank you — your partnership request has been sent to the staff team. They will review and respond if interested.")


@bot.event
async def on_ready() -> None:
    activity_name = "for staff messages" if MESSAGE_ONLY_MODE else "for support tickets"
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=activity_name))
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")


@bot.command()
async def ping(ctx: commands.Context) -> None:
    await ctx.send("pong")


@bot.command(name="8ball")
async def eight_ball_command(ctx: commands.Context) -> None:
    responses = [
        "Yes.",
        "No.",
        "Definitely.",
        "Not a chance.",
        "Ask again later.",
        "Signs point to yes.",
        "Very doubtful.",
        "Absolutely.",
    ]
    await ctx.send(random.choice(responses))


@bot.command(name="coinflip")
async def coinflip_command(ctx: commands.Context) -> None:
    await ctx.send(random.choice(["Heads.", "Tails."]))


@bot.command(name="roll")
async def roll_command(ctx: commands.Context, sides: str = "6") -> None:
    if not sides.isdigit():
        await ctx.send("Usage: `!roll [number_of_sides]` (example: `!roll 20`)")
        return
    total_sides = int(sides)
    if total_sides < 2 or total_sides > 1000:
        await ctx.send("Please pick a dice size between 2 and 1000.")
        return
    await ctx.send(f"You rolled **{random.randint(1, total_sides)}** (1-{total_sides}).")


@bot.command(name="choose")
async def choose_command(ctx: commands.Context, *, options: str) -> None:
    choices = [item.strip() for item in options.split("|") if item.strip()]
    if len(choices) < 2:
        await ctx.send("Usage: `!choose option 1 | option 2 | option 3`")
        return
    await ctx.send(f"I choose: **{random.choice(choices)}**")


@bot.command(name="rps")
async def rps_command(ctx: commands.Context, choice: str = "") -> None:
    user_pick = choice.strip().lower()
    valid = {"rock", "paper", "scissors"}
    if user_pick not in valid:
        await ctx.send("Usage: `!rps rock`, `!rps paper`, or `!rps scissors`")
        return

    bot_pick, result = get_rps_round(user_pick)

    await ctx.send(f"You picked **{user_pick}**. I picked **{bot_pick}**. {result}")


@bot.command(name="blackjack")
async def blackjack_command(ctx: commands.Context) -> None:
    view = BlackjackView(ctx.author.id)
    message = await ctx.send(view.render(), view=view)
    view.message = message


@bot.command(name="start")
async def start_command(ctx: commands.Context):
    await ctx.send(
        "This bot is set up for server messages only. Try `!ping`, `!8ball`, `!coinflip`, `!roll`, `!choose`, `!rps`, `!blackjack`, `hi`, `.message`, `c!send <message>`, or `c!whoami` in the server."
    )


@bot.command(name="help")
async def help_command(ctx: commands.Context):
    embed = discord.Embed(title="Support Bot Commands", color=discord.Color.green())
    embed.add_field(name="Server", value="Say `hi` and the bot replies with `hey`.", inline=False)
    embed.add_field(
        name="Fun",
        value=(
            "Use `!8ball`, `!coinflip`, `!roll [sides]`, `!choose option 1 | option 2`, `!rps rock|paper|scissors`, or `!blackjack`. "
            "All also work with `c!` prefix."
        ),
        inline=False,
    )
    embed.add_field(name="Staff", value="Use `c!send <message>`, `.message`, or `c!whoami` in the server.", inline=False)
    await ctx.send(embed=embed)


@bot.command(name="whoami")
async def whoami_command(ctx: commands.Context):
    await ctx.reply(f"Your user ID is {ctx.author.id}. Staff access: {is_staff(ctx.author)}")


@bot.command(name="send")
@staff_check()
async def send_command(ctx: commands.Context, *, response: str):
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        logger.warning("Missing permission to delete c!send command message in guild %s", ctx.guild.id if ctx.guild else "dm")
    await ctx.channel.send(response)


@bot.command(name="reply")
@staff_check()
async def reply_command(ctx: commands.Context, user_id: int, *, response: str):
    try:
        user = await bot.fetch_user(user_id)
    except discord.NotFound:
        await ctx.reply("Could not find a user with that ID.")
        return
    try:
        await user.send(f"A staff member sent the following response to your ticket:\n\n{response}")
        await ctx.reply("Reply sent successfully.")
    except discord.Forbidden:
        await ctx.reply("Unable to DM that user.")


@bot.command(name="close")
@staff_check()
async def close_command(ctx: commands.Context, user_id: int, *, reason: str = "Your ticket has been closed."):
    try:
        user = await bot.fetch_user(user_id)
    except discord.NotFound:
        await ctx.reply("Could not find a user with that ID.")
        return

    try:
        await user.send(f"Your ticket has been closed by staff. {reason}")
    except discord.Forbidden:
        await ctx.reply("Unable to DM that user.")
        return

    await ctx.reply(f"Ticket closed for {user}.")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if MESSAGE_ONLY_MODE and message.guild is None:
        return

    if message.guild is not None:
        if should_reply_with_hey(message.content):
            await message.channel.send("hey")

        if should_play_cheeseburger_noise(message.content):
            await message.channel.send("*SIZZLE SIZZLE* burger noise")

        proxied_message = get_staff_proxy_message(message.content)
        if proxied_message is not None and is_staff(message.author):
            try:
                await message.delete()
            except discord.Forbidden:
                logger.warning("Missing permission to delete staff proxy message in guild %s", message.guild.id)
            await message.channel.send(proxied_message)
            return

    if message.guild is not None and isinstance(message.channel, discord.Thread):
        user_id = ticket_threads_thread.get(message.channel.id)
        if user_id and not message.author.bot:
            if message.content and has_command_prefix(message.content):
                await bot.process_commands(message)
                return
            target_user = await bot.fetch_user(user_id)
            content = message.content or "(no text)"
            files = []
            for attachment in message.attachments:
                files.append(await attachment.to_file())
            try:
                await target_user.send(content, files=files or None)
                await message.channel.send("Message forwarded to the user.")
            except discord.Forbidden:
                await message.channel.send("Unable to DM the user; their DMs may be closed.")
            return

    if message.guild is None:
        user = message.author
        content = message.content.strip()

        if has_command_prefix(content):
            await bot.process_commands(message)
            return

        if await is_staff_user(user):
            parts = content.split(maxsplit=2)
            cmd = parts[0].lower() if parts else ""
            if cmd in {"reply", "!reply"} and len(parts) >= 3:
                try:
                    target_id = int(parts[1])
                    response = parts[2]
                    target_user = await bot.fetch_user(target_id)
                except Exception:
                    await user.send("Usage: reply <user_id> <message>")
                    return
                try:
                    await target_user.send(f"A staff member sent the following response to your ticket:\n\n{response}")
                    await user.send("Reply sent successfully.")
                except discord.Forbidden:
                    await user.send("Unable to send that DM.")
                return

            if cmd in {"close", "!close"} and len(parts) >= 2:
                try:
                    target_id = int(parts[1])
                    target_user = await bot.fetch_user(target_id)
                except Exception:
                    await user.send("Usage: close <user_id> [reason]")
                    return
                try:
                    await target_user.send("Your ticket has been closed by staff.")
                    await user.send("Ticket closed.")
                except discord.Forbidden:
                    await user.send("Unable to send that DM.")
                return

        if user.id in pending_applications:
            state = pending_applications[user.id]
            state["answers"].append(content or "(No response)")
            state["step"] += 1
            if state["step"] < len(application_questions):
                await ask_application_question(user, state["step"])
            else:
                await finish_application(user)
            return

        if user.id in pending_partnerships:
            state = pending_partnerships[user.id]
            state["answers"].append(content or "(No response)")
            state["step"] += 1
            if state["step"] < len(partnership_questions):
                await user.send(
                    f"Please answer question {state['step'] + 1} of {len(partnership_questions)}:\n\n{partnership_questions[state['step']]}"
                )
            else:
                await finish_partnership(user)
            return

        if user.id in pending_ticket_details:
            category = pending_ticket_details[user.id]
            clear_dm_prompt(user.id, pending_ticket_details)
            if not content:
                await ask_for_ticket_details(user, category)
                return
            thread = await find_or_sync_thread_for_user(user)
            if thread:
                await thread.send(embed=format_embed(user, category, content))
            else:
                await send_support_log(user, category, content)
            await user.send("The staff team has been notified. Please wait for their response — thank you!")
            return

        if not content:
            await send_dm_intro(user)
            return

        parts = content.split(maxsplit=1)
        category = get_category(parts[0])
        body = parts[1].strip() if len(parts) > 1 else ""

        if category == "Application":
            pending_applications[user.id] = {"step": 0, "answers": []}
            await user.send("I will collect your application questions one by one. Reply to this DM to continue.")
            await ask_application_question(user, 0)
            return

        if category == "Partnership":
            pending_partnerships[user.id] = {"step": 0, "answers": []}
            await user.send("I will collect your partnership request details one by one. Reply to this DM to continue.")
            await user.send(
                f"Please answer question 1 of {len(partnership_questions)}:\n\n{partnership_questions[0]}"
            )
            return

        if category in {"Support", "Issue", "Suggestion"} and not body:
            await ask_for_ticket_details(user, category)
            return

        if category is None:
            await send_dm_intro(user)
            return

        sent = await send_support_log(user, category, body or "(No additional details provided)")
        if sent is not None:
            await user.send("The staff team has been notified. Please wait for their response — thank you!")
        else:
            await user.send("I could not deliver your message because the support channel is not configured correctly.")
        return

    await bot.process_commands(message)


@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    if isinstance(error, commands.CheckFailure):
        await ctx.reply("You do not have permission to use that command.")
        return
    if isinstance(error, commands.CommandNotFound):
        await ctx.reply("Unknown command. Try `!help`, `!ping`, `!8ball`, `!coinflip`, `!roll`, `!choose`, `!rps`, or `!blackjack`.")
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply("That command is missing required information. Try `!help` for examples.")
        return
    logger.exception("Unhandled command error: %s", error)
    try:
        await ctx.reply("An unexpected error occurred.")
    except Exception:
        pass


def main() -> None:
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is not set")
    try:
        bot.run(TOKEN)
    except discord.LoginFailure as exc:
        raise RuntimeError(
            "Discord login failed: DISCORD_TOKEN is invalid. Regenerate the bot token in the Discord Developer Portal and update your host environment variable."
        ) from exc


if __name__ == "__main__":
    main()
