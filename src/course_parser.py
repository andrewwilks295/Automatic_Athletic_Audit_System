from bs4 import BeautifulSoup
import re
from collections import defaultdict, namedtuple

CourseData = namedtuple("CourseData", ["subject", "number", "name", "credits"])


def extract_credits(text):
    text = text.lower()
    if match := re.search(r"(\d+)\s*-\s*(\d+)\s*credits?", text):
        return int(match.group(1))
    if match := re.search(r"(\d+)\s*or\s*(\d+)\s*credits?", text):
        return f"{match.group(1)} or {match.group(2)}"
    if match := re.search(r"(\d+)\s*credits?", text):
        return int(match.group(1))
    return "Unknown"


def normalize_group(tag):
    return ' '.join(tag.stripped_strings).strip()


def parse_course_structure_from_html(html):
    """
    Parses course requirements from catalog HTML into an in-memory structure.
    Returns a list of requirement groups/subgroups and their courses.
    """
    soup = BeautifulSoup(html, "html.parser")
    result = []
    course_pattern = re.compile(r"(\w+)\s+(\d+)\s+-\s+(.+)")

    current_h3 = None
    current_h4 = None
    current_group_type = "credits"
    choose_group_buffer = {}
    credit_groups = defaultdict(list)

    for tag in soup.find_all(['h3', 'h4', 'p', 'li']):
        if tag.name == 'h3':
            current_h3 = normalize_group(tag)
            current_group_type = "credits"
            current_h4 = None

        elif tag.name == 'p' and "one of the following" in tag.get_text().lower():
            current_group_type = "choose_dir"

        elif tag.name == 'h4':
            current_h4 = normalize_group(tag)
            if current_group_type == "choose_dir":
                if current_h3 not in choose_group_buffer:
                    choose_group_buffer[current_h3] = {
                        "type": "choose_dir",
                        "group_name": current_h3,
                        "subgroups": []
                    }
                choose_group_buffer[current_h3]["subgroups"].append({
                    "name": current_h4,
                    "credits": extract_credits(current_h4),
                    "courses": []
                })

        elif tag.name == 'li' and 'acalog-course' in tag.get("class", []):
            text = tag.get_text(separator=" ", strip=True)
            credits = extract_credits(text)
            course_options = text.split(" or ")

            for option in course_options:
                option = re.sub(r"\s+\d+\s+Credit\(s\)", "", option).strip()
                match = course_pattern.search(option)
                if match:
                    subject, number, name = match.groups()
                    course = CourseData(subject, number, name.strip(), credits)

                    if current_group_type == "choose_dir":
                        choose_group_buffer[current_h3]["subgroups"][-1]["courses"].append(course)
                    else:
                        credit_groups[current_h3].append(course)

    for name, courses in credit_groups.items():
        result.append({
            "type": "credits",
            "group_name": name,
            "credits": extract_credits(name),
            "courses": courses
        })

    result.extend(choose_group_buffer.values())
    return result
