import re
import pandas as pd
from collections import namedtuple
from rapidfuzz import process, fuzz
import unicodedata

from src.models import RequirementNode


def extract_credits(text, prefer="min"):
    """
    Extracts an integer credit value from a text string.
    prefer="min" -> choose the smallest of a range or "or" set
    prefer="max" -> choose the largest of a range or "or" set
    """
    text = text.lower()
    if match := re.search(r"(\d+)\s*-\s*(\d+)\s*credits?", text):
        nums = int(match.group(1)), int(match.group(2))
        return min(nums) if prefer == "min" else max(nums)
    if match := re.search(r"(\d+)\s*or\s*(\d+)\s*credits?", text):
        nums = int(match.group(1)), int(match.group(2))
        return min(nums) if prefer == "min" else max(nums)
    if match := re.search(r"(\d+)\s*credits?", text):
        return int(match.group(1))
    return None


CourseData = namedtuple("CourseData", ["subject", "number", "name", "credits"])


def match_major_name_web_to_registrar(web_name, major_code_df, scorer=fuzz.WRatio):
    """
    Match a major_name_web to the closest major_name_registrar using RapidFuzz.

    Returns:
        (major_code, major_name_registrar, score)
    """
    web_name = normalize_major_name_web(web_name)
    choices = major_code_df["major_name_registrar"].tolist()

    # Normalize registrar names for comparison
    normalized_choices = [normalize_major_name_registrar(c) for c in choices]

    match, score, idx = process.extractOne(web_name, normalized_choices, scorer=scorer)
    matched_row = major_code_df.iloc[idx]
    return matched_row["major_code"], matched_row["major_name_registrar"], score


def normalize_major_name_web(name):
    """
    Normalize catalog names scraped from the web.

    Examples:
        "Communication - Sports Communication Emphasis (B.A., B.S.)" → "Communication - Sports Communication"
        "Software Development (B.S.)" → "Software Development"
    """
    # Remove degree suffixes (e.g., "(B.S.)")
    name = re.sub(r"\s*\(.*?\)\s*$", "", name)

    # Remove known trailing descriptors
    name = re.sub(r"\b(Emphasis|Concentration|Track|Option|Pathway)\b", "", name, flags=re.IGNORECASE)

    return re.sub(r"\s+", " ", name).strip().lower()


def normalize_major_name_registrar(name):
    """
    Normalize registrar names from major_codes.csv for matching.

    Examples:
        "Sports Communication Concentration" → "Sports Communication"
        "Major in Software Development" → "Software Development"
    """
    # Remove "Major in" prefix and trailing keywords
    name = re.sub(r"^Major in\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(Emphasis|Concentration|Track|Option|Pathway)\b", "", name, flags=re.IGNORECASE)

    return re.sub(r"\s+", " ", name).strip().lower()


# Loading functions for major code lookup and total credits map

def load_major_code_lookup(path: str) -> pd.DataFrame:
    """
    Load and clean the unified major_codes.csv for fuzzy matching.
    """
    df = pd.read_csv(path)
    df = df.rename(columns={
        "Major Code": "major_code",
        "Major Name Registrar": "major_name_registrar"
    })[["major_code", "major_name_registrar"]]
    return df.dropna(subset=["major_code", "major_name_registrar"])


def prepare_django_inserts(parsed_tree, major_code, major_name_web, major_name_registrar, total_credits_required,
                           catalog_year):
    """
    Converts a nested requirement tree into flat Django model inserts.
    """

    major_record = {
        "major_code": major_code,
        "major_name_web": major_name_web,
        "major_name_registrar": major_name_registrar,
        "total_credits_required": total_credits_required,
        "catalog_year": catalog_year
    }

    courses = {}
    requirement_nodes = []
    node_courses = []

    def walk(node, parent_id=None):
        node_id = len(requirement_nodes)
        node_record = {
            "id": node_id,  # temporary ID for in-memory linkage
            "name": node.name,
            "type": node.type,
            "required_credits": node.required_credits,
            "parent_id": parent_id
        }
        requirement_nodes.append(node_record)

        # Handle courses
        for course in node.courses:
            course_id = f"{course.subject}-{course.number}"
            if course_id not in courses:
                courses[course_id] = {
                    "course_id": course_id,
                    "subject": course.subject,
                    "course_number": course.number,
                    "course_name": course.name,
                    "credits": course.credits
                }
            node_courses.append({
                "course_id": course_id,
                "node_id": node_id
            })

        # Recurse into children
        for child in node.children:
            walk(child, parent_id=node_id)

    for root in parsed_tree:
        walk(root)

    return {
        "major": major_record,
        "courses": list(courses.values()),
        "requirement_nodes": requirement_nodes,
        "node_courses": node_courses
    }


# for debugging requirement trees
def print_requirement_tree(major):
    roots = RequirementNode.objects.filter(major=major, parent__isnull=True)

    def print_node(node, depth=0):
        indent = "  " * depth
        print(f"{indent}- {node.name} [{node.type}] ({node.required_credits} credits)")

        # Show courses under this node
        courses = node.courses.all()
        for course in courses:
            print(f"{indent}  - {course.course_id}")

        # Recurse to children
        for child in node.children.all():
            print_node(child, depth + 1)

    for root in roots:
        print_node(root)
