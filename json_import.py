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
                models.Link.create(link=link, title=title, category=db_category[0].id)


if __name__ == "__main__":
    """
    Make sure to create a database backup before you import data from json files.
    """
    # import_links("data/links.json")
