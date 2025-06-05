from database import Subscriptions, Blacklists
from sites import Post, E621, Gelbooru, Rule34Xxx

import os
import logging

import dotenv
import discord
from discord import app_commands
import discord.ext.commands as commands
import discord.ext.tasks as tasks

dotenv.load_dotenv()
discord.utils.setup_logging(level=logging.DEBUG)

OWNER_GUILD = discord.Object(id=os.environ["RK81_OWNER_GUILD"])


class Rk81(commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(command_prefix="/", intents=intents)
        self.supported_sites = [E621(), Gelbooru(), Rule34Xxx()]
        self.supported_site_choices = [
            app_commands.Choice(name=x.name, value=x.name) for x in self.supported_sites
        ]

    async def setup_hook(self):
        await self.add_cog(Blacklist(self))

        self.tree.copy_global_to(guild=OWNER_GUILD)
        await self.tree.sync(guild=OWNER_GUILD)

        for site in self.supported_sites:
            await site.init_state()

        self.send_new_posts.start()

    @tasks.loop(minutes=5.0)
    async def send_new_posts(self):
        await self.wait_until_ready()

        for site in self.supported_sites:
            subscribers = Subscriptions.select().where(Subscriptions.site == site.name)
            if not subscribers:
                continue

            new_posts = await site.new_posts()

            for subscriber in subscribers:
                subscriber = self.get_user(subscriber.discord_id)
                await self.send_posts(subscriber, new_posts)

    async def send_posts(
        self,
        subscriber: discord.User,
        posts: list[Post],
    ) -> None:
        if not posts:
            return

        blacklists = Blacklists.select().where(
            Blacklists.discord_id == subscriber.id,
            ((Blacklists.site == posts[0].site) | (Blacklists.site == None)),
        )

        if not (channel := subscriber.dm_channel):
            channel = await subscriber.create_dm()

        for post in posts:
            if all(not b.matches(post) for b in blacklists):
                await channel.send(embed=post.embed)


intents = discord.Intents.default()
intents.members = True
client = Rk81(intents=intents)


class Blacklist(commands.GroupCog, name="blacklist"):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    @app_commands.command(name="list")
    async def blacklist_list(self, interaction: discord.Interaction):
        blacklisted = (
            Blacklists.select()
            .where(Blacklists.discord_id == interaction.user.id)
            .order_by(Blacklists.site.desc())
        )

        paginator = commands.Paginator(prefix="", suffix="")

        current_site = 0
        for blacklist in blacklisted:
            if current_site != blacklist.site:
                paginator.add_line(f"{blacklist.site if blacklist.site else 'Global'}:")
                current_site = blacklist.site

            paginator.add_line(f"* `{blacklist.query}`")

        await interaction.response.send_message(paginator.pages[0], ephemeral=True)
        for page in paginator.pages[1:]:
            await interaction.followup.send(page, ephemeral=True)

    @app_commands.command()
    @app_commands.choices(site=client.supported_site_choices)
    async def add(
        self,
        interaction: discord.Interaction,
        query: str,
        site: app_commands.Choice[str] | None,
    ) -> None:
        """Add a query to your blacklist"""
        query = query.strip()
        if (not query) or (query[0] == "-" and " " not in query):
            await interaction.response.send_message("Invalid syntax", ephemeral=True)
            return

        Blacklists.insert(
            discord_id=interaction.user.id,
            query=query,
            site=site.value if site else None,
        ).on_conflict_ignore().execute()

        await interaction.response.send_message("OK", ephemeral=True)

    @app_commands.command()
    @app_commands.choices(site=client.supported_site_choices)
    async def remove(
        self,
        interaction: discord.Interaction,
        query: str,
        site: app_commands.Choice[str] | None,
    ) -> None:
        query = query.strip()
        Blacklists.delete().where(
            Blacklists.discord_id == interaction.user.id,
            Blacklists.query == query,
            Blacklists.site == site.value if site else None,
        ).execute()

        await interaction.response.send_message("OK", ephemeral=True)


@client.event
async def on_ready() -> None:
    logging.info(f"I'm {client.user}")


@client.tree.command()
@app_commands.choices(to=client.supported_site_choices)
async def subscribe(
    interaction: discord.Interaction, to: app_commands.Choice[str]
) -> None:
    """Subscribe to the e621 post feed"""
    already_was = not Subscriptions.get_or_create(
        discord_id=interaction.user.id, site=to.value
    )[1]
    response = "You're already subscribed" if already_was else "Subscribed"

    await interaction.response.send_message(response, ephemeral=True)


@client.tree.command()
@app_commands.choices(to=client.supported_site_choices)
async def unsubscribe(
    interaction: discord.Interaction, to: app_commands.Choice[str]
) -> None:
    """Unsubscribe from the e621 post feed"""
    was = (
        Subscriptions.delete()
        .where(
            Subscriptions.discord_id == interaction.user.id,
            Subscriptions.site == to.value,
        )
        .execute()
    )
    response = "Unsubscribed" if was else "You weren't subscribed"

    await interaction.response.send_message(response, ephemeral=True)


@client.tree.command()
async def subscriptions(interaction: discord.Interaction) -> None:
    subscriptions = Subscriptions.select().where(
        Subscriptions.discord_id == interaction.user.id
    )
    result = [f"* `{s.site}`\n" for s in subscriptions] if subscriptions else "None"

    await interaction.response.send_message(result, ephemeral=True)


@client.tree.command()
async def sync(interaction: discord.Interaction):
    """Sync commands globally"""
    await client.tree.sync()
    await interaction.response.send_message("Syncing", ephemeral=True)


@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    channel = client.get_user(payload.user_id)
    if not channel:
        return

    message = await channel.fetch_message(payload.message_id)

    if "/rk81/" in message.embeds[0].footer.text:
        if payload.emoji.name == "👎":
            await message.delete()
        elif payload.emoji.name == "🚫" and message.embeds[0].author:
            author = message.embeds[0].author.name
            if " " not in author:
                Blacklists.insert(
                    discord_id=payload.user_id, query=author
                ).on_conflict_ignore().execute()

            await message.delete()


client.run(os.environ["RK81_DISCORD_TOKEN"])
