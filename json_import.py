import json

import models


def import_links(json_file: str) -> None:
    file = open(json_file, mode="r")
    links = json.load(file)

    for channel, categories in links.items():
        for category, links in categories.items():
            category = category.capitalize()
            db_category = models.LinkCategory.get_or_create(channel=int(channel), name=category)
            for title, link in links.items():
                link = link[1:-1] if link[0] == "<" and link[-1] == ">" else link
                models.Link.create(url=link, title=title, category=db_category[0].id)


def import_news(json_file: str) -> None:
    file = open(json_file, mode="r")
    news = json.load(file)

    for link, date in news.items():
        models.News.create(link=link, date=date)


def import_commands(json_file: str) -> None:
    file = open(json_file, mode="r")
    commands = json.load(file)

    for command, data in commands.items():
        db_command = models.Command.get_or_create(command=command, description=data["description"])
        for text in data["data"]:
            models.CommandText.create(text=text, command=db_command[0].id)


def import_courses(json_file: str) -> None:
    file = open(json_file, mode="r")
    courses = json.load(file)

    for course in courses:
        models.Course.get_or_create(name=course["name"], short=course["short"], url=course["url"],
                                    role_id=int(course["role"]))


if __name__ == "__main__":
    """
    Make sure to create a database backup before you import data from json files.
    """
    # import_links("data/links.json")
    # import_news("data/news.json")
    # import_commands("data/text_commands.json")
    # import_courses("data/courses_of_studies.json")
