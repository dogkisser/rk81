from dataclasses import dataclass
from datetime import datetime

import discord
from discord.utils import escape_markdown


@dataclass
class Post:
    id: int
    site: str
    post_link: str
    colour: int
    image_url: str
    timestamp: datetime
    description: str
    rating: str
    artist: str | None
    animated: bool
    tags: set[str]

    def __post_init__(self) -> None:
        description = self.description[:150] + (self.description[150:] and "..")
        embed = discord.Embed(
            title=f"#{self.id}",
            url=self.post_link,
            description=escape_markdown(description),
            colour=self.colour,
            timestamp=self.timestamp,
        )
        embed.set_image(url=self.image_url)
        embed.set_footer(text="/rk81/")

        if self.animated:
            embed.add_field(name=":play_pause: Animated", value="", inline=False)

        if self.artist:
            embed.set_author(name=self.artist)

        self.embed = embed
