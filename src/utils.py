import re
import pandas as pd
from collections import namedtuple
from rapidfuzz import process, fuzz
import unicodedata


def extract_credits(text, prefer="min"):
    """
    Extracts an integer credit value from a text string.
    prefer="min" -> choose the smaller of a range or "or" set
    prefer="max" -> choose the larger of a range or "or" set
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


def clean_text(text):
    """
    Normalizes and strips out problematic unicode characters.
    """
    if not isinstance(text, str):
        return text
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return text.strip()


def parse_course_csv(file_path):
    """
    Parses a course CSV file into a list of CourseData.
    Tries utf-8 and falls back to ISO-8859-1 if needed.
    Logs rows that fail during parsing.
    """
    df = None
    try:
        df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip", engine="python")
    except UnicodeDecodeError:
        try:
            print(f"⚠️ Retrying {file_path.name} with ISO-8859-1 encoding...")
            df = pd.read_csv(file_path, encoding="ISO-8859-1", on_bad_lines="skip", engine="python")
        except Exception as e:
            print(f"❌ Failed to read file with fallback: {file_path}\n   → {e}")
            return []

    parsed = []
    for i, row in df.iterrows():
        try:
            subject = clean_text(row["Subject"])
            number = str(row["Course Number"]).strip()
            name = clean_text(row["Name"])
            credits = int(row["Credits"])
            parsed.append(CourseData(subject, number, name, credits))
        except Exception as e:
            print(f"⚠️ Row {i+1} in {file_path.name} failed to parse: {e}")
            print(f"   → Raw Row: {row.to_dict()}")
            continue

    return parsed


def split_courses_by_credit_blocks(courses, credit_blocks):
    """
    Splits a flat course list into subgroups based on target credit block totals.
    Returns a list of course lists, each corresponding to one block.
    Assumes course order matches intended grouping.
    """
    results = []
    remaining = courses[:]
    for target in credit_blocks:
        group = []
        total = 0
        while remaining and total < target:
            course = remaining.pop(0)
            group.append(course)
            total += course.credits
        if total != target:
            raise ValueError(f"Unable to match credit block: expected {target}, got {total}")
        results.append(group)
    if remaining:
        print("Warning: extra courses remaining after credit block split.")
    return results


def match_major_name_web_to_registrar(web_name, major_code_df, scorer=fuzz.token_sort_ratio):
    """
    Match a major_name_web to the closest major_name_registrar using RapidFuzz.

    Returns:
        (major_code, major_name_registrar, score)
    """
    web_name = normalize_major_name_web(web_name)
    choices = major_code_df["major_name_registrar"].tolist()
    match, score, idx = process.extractOne(web_name, [normalize_major_name_registrar(choice) for choice in choices], scorer=scorer)
    matched_row = major_code_df.iloc[idx]
    return matched_row["major_code"], match, score


def normalize_major_name_web(name):
    """
    Removes degree suffixes like (B.S.), (A.A.S.), etc. from a major name.

    Examples:
        "Exercise Science (B.S.)" → "Exercise Science"
        "Computer Science (B.A., B.S.)" → "Computer Science"
    """
    return re.sub(r"\s*\((.*?)\)\s*$", "", name).strip()


def normalize_major_name_registrar(name):
    """
    Normalizes the major name from the registrar by removing any extra spaces or special characters and the "Major in" prefix.
    """
    # Remove "Major in" prefix and any leading/trailing whitespace
    name = re.sub(r"^Major in\s+", "", name, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", name).strip()


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


def load_total_credits_map(csv_path):
    """
    Loads a total_credits.csv file and returns a dict:
    {
        "Exercise Science (B.S.)": 120,
        "Management (B.A., B.S.)": 135,
        ...
    }
    """
    df = pd.read_csv(csv_path)
    return dict(zip(df["Degree"].str.strip(), df["Total Credits"]))


def prepare_django_inserts(parsed_tree, major_code, major_name_web, major_name_registrar, total_credits_required, catalog_year):
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
            "name": node["name"],
            "type": node["type"],
            "required_credits": node.get("required_credits"),
            "parent_id": parent_id
        }
        requirement_nodes.append(node_record)

        # Handle courses
        for course in node.get("courses", []):
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
        for child in node.get("children", []):
            walk(child, parent_id=node_id)

    for root in parsed_tree:
        walk(root)

    return {
        "major": major_record,
        "courses": list(courses.values()),
        "requirement_nodes": requirement_nodes,
        "node_courses": node_courses
    }


