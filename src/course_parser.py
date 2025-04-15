from bs4 import BeautifulSoup, Tag
import re
from typing import List, Optional, Generator
from dataclasses import dataclass, field

from src.models import RequirementNode


@dataclass
class CourseData:
    subject: str
    number: str
    name: str
    credits: int


@dataclass
class RequirementNodeData:
    name: str
    type: str  # 'credits' or 'choose'
    required_credits: Optional[int]
    courses: List[CourseData] = field(default_factory=list)
    children: List['RequirementNodeData'] = field(default_factory=list)


def walk_tree(nodes: List[RequirementNodeData]) -> Generator[RequirementNodeData, None, None]:
    for node in nodes:
        yield node
        if node.children:
            yield from walk_tree(node.children)


def extract_credits_from_text(text: str) -> Optional[int]:
    text = text.lower()
    if match := re.search(r"(\d+)\s*or\s*(\d+)\s*credits?", text):
        return max(int(match.group(1)), int(match.group(2)))
    if match := re.search(r"(\d+)\s*-\s*(\d+)\s*credits?", text):
        return int(match.group(1))
    if match := re.search(r"(\d+)\s*credits?", text):
        return int(match.group(1))
    return None


def parse_course_line(line: str) -> Optional[CourseData]:
    line = re.sub(r'\s+', ' ', line).strip()
    match = re.match(r"([A-Z]{2,4}) (\d{4}) - (.+?) (\d+)[ -]?Credit", line)
    if match:
        subject, number, name, credits = match.groups()
        return CourseData(subject, number, name.strip(), int(credits))
    return None


def apply_credit_fallbacks(nodes: List[RequirementNodeData]):
    for node in nodes:
        # Recurse first
        apply_credit_fallbacks(node.children)

        # Then apply fallback if needed
        if node.required_credits is None and node.courses:
            node.required_credits = sum(c.credits for c in node.courses)

        # Optionally apply to 'choose' parent nodes based on max child requirement
        if node.type == "choose" and node.required_credits is None and node.children:
            max_child_credits = max((child.required_credits or 0) for child in node.children)
            node.required_credits = max_child_credits


# Reuse the latest parser and add fallback at the end
def parse_course_structure_as_tree(html: str) -> List[RequirementNodeData]:
    soup = BeautifulSoup(html, "html.parser")
    root_nodes = []

    current_h2_node = None
    current_h3_node = None
    last_subgroup_node = None

    program_summary = soup.find('h2', string=re.compile("Program Summary", re.IGNORECASE))
    if not program_summary:
        return []

    for tag in program_summary.find_all_next():
        if not isinstance(tag, Tag):
            continue

        if tag.name == "h2":
            node = RequirementNodeData(
                name=tag.get_text(strip=True),
                type="credits",
                required_credits=extract_credits_from_text(tag.get_text()),
            )
            root_nodes.append(node)
            current_h2_node = node
            current_h3_node = None

        elif tag.name == "h3" and current_h2_node:
            node = RequirementNodeData(
                name=tag.get_text(strip=True),
                type="credits",
                required_credits=extract_credits_from_text(tag.get_text()),
            )

            # Look ahead for "choose one of the following"
            lookahead = tag
            for _ in range(4):
                lookahead = lookahead.find_next_sibling()
                if not lookahead:
                    break
                if lookahead.name == "p" and "one of the following" in lookahead.get_text().lower():
                    node.type = "choose"
                    break

            current_h2_node.children.append(node)
            current_h3_node = node
            last_subgroup_node = None

        elif tag.name == "h4" and current_h3_node and current_h3_node.type == "choose":
            node = RequirementNodeData(
                name=tag.get_text(strip=True),
                type="credits",
                required_credits=extract_credits_from_text(tag.get_text()),
            )
            current_h3_node.children.append(node)
            last_subgroup_node = node

        elif tag.name == "li" and 'acalog-course' in tag.get("class", []):
            course = parse_course_line(tag.get_text())
            if course:
                if current_h3_node and current_h3_node.type == "choose" and last_subgroup_node:
                    last_subgroup_node.courses.append(course)
                elif current_h3_node:
                    current_h3_node.courses.append(course)
                elif current_h2_node:
                    current_h2_node.courses.append(course)

    # Apply credit fallbacks at the end
    apply_credit_fallbacks(root_nodes)

    return root_nodes


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
