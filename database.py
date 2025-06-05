from post import Post

import os

import dotenv
from peewee import SqliteDatabase, Model, BigIntegerField, TextField

dotenv.load_dotenv()

DATA_DIR = os.environ["RK81_DATA_DIR"]

db = SqliteDatabase(
    f"{DATA_DIR}/rk81.sqlite3", pragmas={"journal_mode": "wal", "synchronous": "normal"}
)


class BaseModel(Model):
    class Meta:
        database = db


class SiteState(BaseModel):
    site = TextField(primary_key=True)
    last_seen_post_id = BigIntegerField()


class Subscriptions(BaseModel):
    discord_id = BigIntegerField(index=True)
    site = TextField()

    class Meta:
        indexes = ((("discord_id", "site"), True),)


class Blacklists(BaseModel):
    discord_id = BigIntegerField(index=True)
    query = TextField()
    site = TextField(null=True)

    class Meta:
        # UNIQUE
        indexes = ((("discord_id", "query"), True),)

    def matches(self, post: Post) -> bool:
        must_have = set()
        must_not_have = set()

        post_tags = post.tags.copy()
        post_tags.add(f"rating:{post.rating}")

        for tag in self.query.split():
            if tag.startswith("-"):
                must_not_have.add(tag[1:])
            else:
                must_have.add(tag)

        return must_have.issubset(post_tags) and must_not_have.isdisjoint(post_tags)


db.connect()
db.create_tables([SiteState, Subscriptions, Blacklists])
