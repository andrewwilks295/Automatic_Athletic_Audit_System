import re
import pandas as pd
from collections import namedtuple
from rapidfuzz import process, fuzz

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
    web_name = normalize_major_name_web(web_name)

    choices = major_code_df.apply(normalize_major_name_registrar, axis=1).tolist()
    match, score, idx = process.extractOne(web_name, choices, scorer=scorer)

    matched_row = major_code_df.iloc[idx]
    return matched_row["Major Code"], match, score


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


def normalize_major_name_registrar(row: pd.Series) -> str:
    """
    Normalizes and combines base major name with concentration name (if applicable).
    """
    registrar_name = re.sub(r"^Major in\s+", "", row["Major Name Registrar"], flags=re.IGNORECASE).strip()
    base_name = re.sub(r"^Major in\s+", "", row.get("base_major_name", ""), flags=re.IGNORECASE).strip()

    # Combine for concentrations
    if "Concentration" in registrar_name and base_name:
        registrar_name = f"{base_name} - {registrar_name}"

    return re.sub(r"\s+", " ", registrar_name).strip()


# Loading functions for major code lookup

def load_major_code_lookup(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return annotate_major_code_base_names(df)


def annotate_major_code_base_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a 'base_major_name' column to the major_code_df for concentration rows.
    """
    base_name = None
    result = []

    for _, row in df.iterrows():
        registrar_name = row["Major Name Registrar"]
        if "Concentration" not in registrar_name:
            base_name = registrar_name  # update current major
        result.append({**row, "base_major_name": base_name})

    return pd.DataFrame(result)


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
