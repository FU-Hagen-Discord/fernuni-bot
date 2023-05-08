import discord
from peewee import *
from peewee import ModelSelect

db = SqliteDatabase("db.sqlite3")


class BaseModel(Model):
    class Meta:
        database = db
        legacy_table_names = False


class LinkCategory(BaseModel):
    channel = IntegerField()
    name = CharField()

    @classmethod
    def get_categories(cls, channel: int, category: str = None) -> ModelSelect:
        categories: ModelSelect = cls.select().where(LinkCategory.channel == channel)
        return categories.where(LinkCategory.name == category) if category else categories

    @classmethod
    def has_links(cls, channel: int, category: str = None) -> bool:
        for category in cls.get_categories(channel, category=category):
            if category.links.count() > 0:
                return True

        return False

    def append_field(self, embed: discord.Embed) -> None:
        value = ""
        for link in self.links:
            value += f"- [{link.title}]({link.link})\n"

        embed.add_field(name=self.name, value=value, inline=False)


class Link(BaseModel):
    link = CharField()
    title = CharField()
    category = ForeignKeyField(LinkCategory, backref='links')


db.create_tables([LinkCategory, Link], safe=True)
