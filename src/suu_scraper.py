import os
import requests
import re
import csv
from bs4 import BeautifulSoup

from src.course_parser import parse_course_structure_from_html

catalog_years: dict[str, str] | None = None
base_url = "https://www.suu.edu/academics/catalog/"


def scrape_catalog_year(year, majors, major_code_df, threshold=85, dry_run=False):
    catalog_url = pull_catalog_year(year)
    all_programs_link = find_all_programs_link(catalog_url)

    for major_name_web in majors:
        print(f"\nProcessing: {major_name_web}")
        program_url = find_degree(all_programs_link, major_name_web)
        if program_url is None:
            print(f"ERROR: Could not find program for {major_name_web}")
            continue

        try:
            html = requests.get(program_url).text
            total_credits = fetch_total_credits(html)
            structure = parse_course_structure_from_html(html)

            # fuzzy match
            from src.utils import match_major_name_web_to_registrar, prepare_django_inserts, populate_catalog_from_payload

            major_code, major_name_registrar, score = match_major_name_web_to_registrar(major_name_web, major_code_df)

            if score < threshold:
                print(f"WARN: Skipping {major_name_web} due to low match score: {score}")
                continue

            payload = prepare_django_inserts(
                parsed_structure=structure,
                major_code=major_code,
                major_name_web=major_name_web,
                major_name_registrar=major_name_registrar,
                total_credits_required=total_credits
            )

            if not dry_run:
                populate_catalog_from_payload(payload)

            print(f"INFO: Successfully {'Parsed' if dry_run else 'Imported'}: {major_code} ({score}% confidence)")
            print(payload)

        except Exception as e:
            print(f"ERROR: Error while processing {major_name_web}: {e}")

def pull_catalog_year(year):
    print("\n\nStarting_catalog_year_test\n----------------------------")

    startup()

    if year in catalog_years:
        catoid = catalog_years[year]
        # Proceed using catoid and major as needed for further processing
        print(f"Using catoid {catoid} for catalog year {year}")
    else:
        print(f"Catalog year '{year}' not found! Available years: {list(catalog_years.keys())}")

    # Change this variable to select the desired catalog year
    selected_year = year  # this will pull from the students csv file !!!!!!!!!!!!!!!!!!!!

    # Get the corresponding `catoid`
    catoid = catalog_years.get(selected_year)

    if not catoid:
        print(f"Catalog year {selected_year} not found.")
    else:
        # Construct the catalog link
        catalog_url = f"https://catalog.suu.edu/index.php?catoid={catoid}"

        # Send a GET request
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(base_url, headers=headers)

        # Check if request was successful
        if response.status_code == 200:
            # Parse the HTML content
            soup = BeautifulSoup(response.text, "html.parser")

            # Find all links on the page
            links = {a.text.strip(): a["href"] for a in soup.find_all("a", href=True)}

            # Print the selected catalog link
            print(f"Selected Year: {selected_year}")
            print(f"Catalog URL: {catalog_url}")
            return catalog_url

        else:
            print(f"Failed to fetch the page. Status code: {response.status_code}")


def get_catalog_years(base_url):
    """
    Scrapes the catalog homepage for links containing catalog years.
    Returns a dictionary mapping catalog year strings (e.g., "2024-2025") to their catoid values.
    """
    response = requests.get(base_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    catalog_years = {}

    # Find all links on the page
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        # Use re.search to find a pattern like "2024-2025" anywhere in the text
        year_match = re.search(r"(\d{4}-\d{4})", text)
        if year_match:
            year_str = year_match.group(1)
            # Look for the catoid in the href (e.g., ?catoid=26)
            catoid_match = re.search(r"catoid=(\d+)", a['href'])
            if catoid_match:
                catalog_years[year_str] = catoid_match.group(1)
            else:
                print(f"No catoid found in link for year {year_str}")
    return catalog_years


def startup():
    global catalog_years
    if catalog_years is None:
        catalog_years = get_catalog_years(base_url)
        print("Catalog years found:", catalog_years)


def find_all_programs_link(url):
    print("\n\nStarting find_all_programs_link.py\n----------------------------")
    # url = pull_catalog_year_test.catalog_url

    # Send a GET request
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the link with the text "All Programs"
        link = soup.find('a', string=lambda text: text and "All Programs" in text)

        if link:
            # Extract the href attribute and print the full URL
            href = link['href']
            full_url = f"https://catalog.suu.edu{href}"
            print(f"Found Link: {full_url}")
            return full_url
        else:
            print("No link with 'All Programs' found.")
    else:
        print(f"Failed to fetch the page. Status code: {response.status_code}")


def find_degree(url, major) -> str | None:
    print("\n\nStarting find_degree.py\n----------------------------")
    print(f"Fetching degree programs from: {url}")

    # Target degree name to search for
    target_degree = major  # this will change to reading from a csv file but will need to have some conversion from EXSC

    # Send a GET request
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    # Check if request was successful
    if response.status_code == 200:
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all links related to degree programs
        degree_links = soup.find_all('a', href=True)

        found = False
        print("\nSearching for degree program...\n----------------------------")
        for link in degree_links:
            text = link.text.strip()
            href = link['href']

            # Ensure proper URL formatting
            if href.startswith("http"):
                full_url = href  # Absolute URL
            else:
                full_url = f"https://catalog.suu.edu/{href.lstrip('/')}"

            # Look for the specific degree name
            if target_degree.lower() in text.lower():
                print(f"Found '{target_degree}': {full_url}")
                found = True
                break  # Stop searching once we find the first match

        if not found:
            print(f"Degree '{target_degree}' not found.")
            return None  # No match found
        else:
            return full_url
    else:
        print(f"Failed to fetch the page. Status code: {response.status_code}")


def extract_credits(text):
    text = text.lower()

    match = re.search(r"(\d+)\s*-\s*(\d+)\s*credits?", text)
    if match:
        # print("Dash match:", match.groups())
        return int(match.group(1))

    match = re.search(r"(\d+)\s*or\s*(\d+)\s*credits?", text)
    if match:
        # print("Or match:", match.groups())
        return f"{match.group(1)} or {match.group(2)}"

    match = re.search(r"(\d+)\s*credits?", text)
    if match:
        # print("Single credit match:", match.group(1))
        return int(match.group(1))

    return "Unknown"


def sanitize(text, max_len=45):
    text = re.sub(r'[<>:"/\\|?*]', '', text)
    return text[:max_len].strip()

def shorten_heading(tag):
    parts = list(tag.stripped_strings)
    selected = None

    # Prefer the last one with 'Credits'
    for s in reversed(parts):
        if 'credit' in s.lower():
            selected = s
            break
    else:
        selected = parts[-1] if parts else "General"

    words = selected.split()
    short_part = ' '.join(words[:2])

    # Handle "or" credits explicitly
    or_match = re.search(r'(\d+\s*or\s*\d+)\s*credits?', selected, re.IGNORECASE)
    dash_match = re.search(r'(\d+)\s*-\s*(\d+)\s*credits?', selected, re.IGNORECASE)
    single_match = re.search(r'(\d+)\s*credits?', selected, re.IGNORECASE)

    if or_match:
        credit_part = f"({or_match.group(1)} Credits)"
    elif dash_match:
        credit_part = f"({dash_match.group(1)} Credits)"
    elif single_match:
        credit_part = f"({single_match.group(1)} Credits)"
    else:
        credit_part = None

    return sanitize(f"{short_part} {credit_part}" if credit_part else short_part)


def fetch_and_parse_structure(url):
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch program page: {url}")
    return parse_course_structure_from_html(response.text)

        
def fetch_total_credits(html):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup.find_all('h2'):
        if "Total Credits" in tag.get_text():
            match = re.search(r'(\d+)', tag.get_text())
            if match:
                return int(match.group(1))
    print("WARN: Total credits not found in page — defaulting to 120.")
    return 120  # Default value if not found
