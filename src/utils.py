import re
import pandas as pd
from collections import namedtuple, deque
from rapidfuzz import process, fuzz


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
    Returns a dictionary with major_code, base_major_code, major_name_registrar, and score.
    """
    web_name = normalize_major_name_web(web_name)

    # Create a list of tuples: (index, normalized_name, major_code, is_concentration, base_major_code)
    enriched = []
    current_base_code = None
    for idx, row in major_code_df.iterrows():
        name = normalize_major_name_registrar(row["Major Name Registrar"])
        code = row["Major Code"]
        is_conc = "concentration" in name.lower()
        if not is_conc:
            current_base_code = code
        enriched.append({
            "index": idx,
            "normalized_name": name,
            "major_code": code,
            "is_concentration": is_conc,
            "base_major_code": current_base_code
        })

    # Match against all normalized registrar names
    match, score, idx = process.extractOne(
        query=web_name,
        choices=[row["normalized_name"] for row in enriched],
        scorer=scorer
    )

    matched_row = enriched[idx]
    raw_row = major_code_df.iloc[matched_row["index"]]

    return {
        "major_code": matched_row["major_code"],
        "base_major_code": matched_row["base_major_code"],
        "major_name_registrar": raw_row["Major Name Registrar"],
        "score": score
    }


def normalize_major_name_web(name):
    return re.sub(r"\s*\((.*?)\)\s*$", "", name).strip()

def normalize_major_name_registrar(name):
    name = re.sub(r"^Major in\s+", "", name, flags=re.IGNORECASE)
    name = name.strip()
    return re.sub(r"\s+", " ", name)


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


from src.course_parser import walk_tree

def prepare_django_inserts(parsed_tree, match_result, major_name_web, total_credits_required, catalog_year):
    """
    Converts a parsed tree into a payload for populate_catalog_from_payload().
    Accepts match_result from match_major_name_web_to_registrar(), which includes
    both major_code and base_major_code.
    """
    requirement_nodes = []
    node_courses = []
    course_set = set()

    id_counter = 0
    node_id_map = {}

    queue = deque([(node, None) for node in parsed_tree])

    while queue:
        node, parent_id = queue.popleft()

        node_id = id_counter
        node_id_map[id(node)] = node_id
        id_counter += 1

        # Convert RequirementNodeData → dict for DB
        requirement_nodes.append({
            "id": node_id,
            "parent_id": parent_id,
            "name": node.name,
            "type": node.type,
            "required_credits": node.required_credits
        })

        for course in node.courses:
            course_id = f"{course.subject}-{course.number}"
            course_set.add(course_id)
            node_courses.append({
                "node_id": node_id,
                "course_id": course_id
            })

        for child in node.children:
            queue.append((child, node_id))

    # Build Course entries
    course_data = []
    for cid in sorted(course_set):
        subj, num = cid.split("-")
        for node in walk_tree(parsed_tree):
            for course in node.courses:
                if course.subject == subj and course.number == num:
                    course_data.append({
                        "course_id": cid,
                        "subject": course.subject,
                        "course_number": course.number,
                        "course_name": course.name,
                        "credits": course.credits
                    })
                    break

    # Final payload
    return {
        "major": {
            "major_code": match_result["major_code"],
            "base_major_code": match_result["base_major_code"],
            "major_name_web": major_name_web,
            "major_name_registrar": match_result["major_name_registrar"],
            "total_credits_required": total_credits_required,
            "catalog_year": catalog_year
        },
        "courses": course_data,
        "requirement_nodes": requirement_nodes,
        "node_courses": node_courses
    }


def normalize_catalog_term(term: int) -> int:
    """
    Given a catalog term like 202510 (Spring) or 202520 (Summer),
    normalize it to the associated Fall term (e.g., 202430).
    """
    year = term // 100
    season = term % 100
    if season in (10, 20):  # Spring or Summer
        return (year - 1) * 100 + 30
    return term  # Already a Fall term
