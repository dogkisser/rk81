from database import SiteState
from post import Post

from datetime import datetime

import aiohttp
from aiolimiter import AsyncLimiter


class Site:
    name = None

    async def new_posts(self) -> list[Post]:
        raise NotImplementedError

    async def newest_post_id(self) -> int:
        raise NotImplementedError

    async def init_state(self) -> None:
        newest_id = await self.newest_post_id()
        SiteState.insert(
            site=self.name, last_seen_post_id=newest_id
        ).on_conflict_ignore().execute()


def flatten(xss):
    return [x for xs in xss for x in xs]


class E621(Site):
    name = "e621.net"

    def __init__(self) -> None:
        super().__init__()
        self.e6_rate_limit = AsyncLimiter(1, 1)
        self.headers = {"user-agent": "github.com/dogkisser/rk981"}

    async def newest_post_id(self) -> int:
        async with (
            self.e6_rate_limit,
            aiohttp.ClientSession(headers=self.headers) as session,
            session.get("https://e621.net/posts.json?limit=1") as response,
        ):
            response = await response.json()
            return response["posts"][0]["id"]

    async def new_posts(self) -> list[Post]:
        last_seen_id = SiteState.get(site=self.name).last_seen_post_id

        url = f"https://e621.net/posts.json?tags=id:>{last_seen_id} limit:200"

        async with (
            self.e6_rate_limit,
            aiohttp.ClientSession(headers=self.headers) as session,
            session.get(url) as response,
        ):
            response = await response.json()
            posts = response["posts"]
            result = []
            for post in posts:
                img_hash = post["file"]["md5"]
                path = "/data/sample/" if post["sample"]["has"] else "/data/"
                ext = "jpg" if post["sample"]["has"] else post["file"]["ext"]
                url = f"https://static1.e621.net{path}{img_hash[0:2]}/{img_hash[2:4]}/{img_hash}.{ext}"

                rating = {"s": "safe", "q": "questionable", "e": "explicit"}[
                    post["rating"]
                ]

                result.append(
                    Post(
                        id=post["id"],
                        site=self.name,
                        image_url=url,
                        post_link=f"https://e621.net/posts/{post['id']}",
                        timestamp=datetime.fromisoformat(post["created_at"]),
                        description=post["description"],
                        artist=", ".join(post["tags"]["artist"]),
                        colour=0x1F2F56,
                        animated=post["file"]["ext"] in ["webm", "mp4"],
                        tags=set(flatten(post["tags"].values())),
                        rating=rating,
                    )
                )

            if len(posts) > 0:
                SiteState.update(last_seen_post_id=posts[0]["id"]).where(
                    SiteState.site == self.name
                ).execute()

            return result


class Gelbooru(Site):
    name = "gelbooru.com"
    colour = 0x006FFA

    def __init__(self) -> None:
        super().__init__()
        self.rate_limit = AsyncLimiter(1, 1)

    def _extract_posts(self, data: dict) -> list:
        return data["post"]

    async def newest_post_id(self) -> int:
        async with (
            self.rate_limit,
            aiohttp.ClientSession() as session,
            session.get(
                f"https://{self.name}/index.php?page=dapi&s=post&q=index&limit=1&json=1"
            ) as response,
        ):
            posts = await response.json()
            return self._extract_posts(posts)[0]["id"]

    async def new_posts(self) -> list[Post]:
        last_seen_id = SiteState.get(site=self.name).last_seen_post_id
        url = f"https://{self.name}/index.php?page=dapi&s=post&q=index&limit=1000&json=1&tags=id:>{last_seen_id}"

        async with (
            self.rate_limit,
            aiohttp.ClientSession() as session,
            session.get(url) as response,
        ):
            posts = await response.json()
            posts = self._extract_posts(posts)
            if not posts:
                return []

            result = []
            for post in posts:
                result.append(
                    Post(
                        id=post["id"],
                        site=self.name,
                        image_url=post["sample_url"]
                        if post["sample_url"]
                        else post["preview_url"],
                        post_link=f"https://{self.name}/index.php?page=post&s=view&id={post['id']}",
                        timestamp=datetime.utcfromtimestamp(post["change"]),
                        colour=self.colour,
                        animated="video" in post["tags"],
                        artist=None,
                        description="",
                        tags=set(post["tags"].split()),
                        rating=post["rating"],
                    )
                )

            if len(posts) > 0:
                SiteState.update(last_seen_post_id=posts[0]["id"]).where(
                    SiteState.site == self.name
                ).execute()

            return result


class Rule34Xxx(Gelbooru):
    name = "rule34.xxx"
    colour = 0xAAE5A4

    def _extract_posts(self, data: list) -> list:
        return data
