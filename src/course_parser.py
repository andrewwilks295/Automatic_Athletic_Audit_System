from bs4 import BeautifulSoup
import re
from collections import namedtuple

from src.utils import extract_credits

CourseData = namedtuple("CourseData", ["subject", "number", "name", "credits"])


def normalize_heading(tag):
    return ' '.join(tag.stripped_strings).strip()


def parse_course_structure_as_tree(html):
    """
    Parses a print-friendly version of the catalog into a nested requirement node tree.
    Automatically chooses max credit values for 'choose' type groups.
    """
    soup = BeautifulSoup(html, "html.parser")
    course_pattern = re.compile(r"(\w+)\s+(\d+)\s+-\s+(.+)")
    root_nodes = []

    current_node = None
    current_subnode = None
    current_type = "credits"

    from src.utils import extract_credits  # assuming it is defined in src.utils

    for tag in soup.find_all(["h2", "h3", "p", "li"]):
        if tag.name == "h2":
            heading = ' '.join(tag.stripped_strings).strip()
            current_type = "credits"
            current_node = {
                "name": heading,
                "type": "credits",
                "required_credits": extract_credits(heading, prefer="min"),
                "courses": [],
                "children": []
            }
            root_nodes.append(current_node)
            current_subnode = None

        elif tag.name == "p" and "one of the following" in tag.get_text().lower():
            current_type = "choose"

        elif tag.name == "h3" and current_node:
            heading = ' '.join(tag.stripped_strings).strip()
            prefer = "max" if current_type == "choose" else "min"
            current_subnode = {
                "name": heading,
                "type": "credits",
                "required_credits": extract_credits(heading, prefer=prefer),
                "courses": [],
                "children": []
            }
            current_node["type"] = current_type  # upgrade parent type to "choose" if needed
            current_node["required_credits"] = extract_credits(current_node["name"], prefer="max") if current_type == "choose" else extract_credits(current_node["name"], prefer="min")
            current_node["children"].append(current_subnode)

        elif tag.name == "li" and "acalog-course" in tag.get("class", []):
            text = tag.get_text(separator=" ", strip=True)
            credits = extract_credits(text, prefer="min")
            course_options = text.split(" or ")

            for option in course_options:
                option = re.sub(r"\s+\d+\s+Credit\(s\)", "", option).strip()
                match = course_pattern.search(option)
                if match:
                    subject, number, name = match.groups()
                    course = CourseData(subject, number, name.strip(), credits)
                    if current_subnode:
                        current_subnode["courses"].append(course)
                    elif current_node:
                        current_node["courses"].append(course)

    return root_nodes
