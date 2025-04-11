import os
import requests
import re
import csv
from bs4 import BeautifulSoup

catalog_years: dict[str, str] | None = None
base_url = "https://www.suu.edu/academics/catalog/"

years = [
    "2024-2025",
]

with open('majors.txt', 'r') as f:
    majors = [x.strip() for x in f.readlines()]


def main():
    global years, majors
    # year = "2024-2025"
    # major = "Exercise Science (B.S.)"
    for year in years:
        for major in majors:
            # if we already have it, skip it
            if os.path.exists(f"./{year}/{major.replace('/', ',')}.csv"):
                print(f"Skipping {year}/{major}")
                continue
            # else scrape it
            catalog_url = pull_catalog_year(year)
            all_programs_link = find_all_programs_link(catalog_url)
            full_url = find_degree(all_programs_link, major)
            # scrape_h2_h3(full_url) #this gets the header requirements which I don't think we need but might as well
            # keep the code
            if full_url is None:
                print(f"Could not find {major} in {year}")
                continue
            scrape_total_credits(full_url, year, major)
            scrape_courses(full_url, year, major)
            
def main_tester():
    # global years, majors
    year = "2024-2025"
    major = "Exercise Science (B.S.)"

    if os.path.exists(f"./{year}/{major.replace('/', ',')}.csv"):
        print(f"Skipping {year}/{major}")
    # else scrape it
    catalog_url = pull_catalog_year(year)
    all_programs_link = find_all_programs_link(catalog_url)
    full_url = find_degree(all_programs_link, major)
    # scrape_h2_h3(full_url) #this gets the header requirements which I don't think we need but might as well
    # keep the code
    scrape_courses(full_url, year, major)
    scrape_total_credits(full_url, year, major)

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


def scrape_courses(url, year, major):
    print(f"\nScraping course listings from: {url}")
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Failed to fetch the page. Status code: {response.status_code}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    degree_name = sanitize(major.replace("/", ","))
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(current_dir, year, degree_name)
    os.makedirs(base_path, exist_ok=True)

    current_h3 = None
    current_h4 = None
    current_h5 = None
    course_map = {}

    for tag in soup.find_all(['h3', 'h4', 'h5', 'li']):
        raw_text = ' '.join(tag.stripped_strings)

        if tag.name == 'h3':
            if 'acalog-location' in tag.get('class', []):
                continue
            current_h3 = shorten_heading(tag)
            current_h4 = None
            current_h5 = None

        elif tag.name == 'h4':
            current_h4 = shorten_heading(tag)
            current_h5 = None

        elif tag.name == 'h5':
            current_h5 = shorten_heading(tag)

        elif tag.name == 'li' and 'acalog-course' in tag.get('class', []):
            credits = extract_credits(tag.get_text())
            course_text = tag.get_text(separator=" ", strip=True)
            course_options = course_text.split(" or ")
            pattern = re.compile(r"(\w+)\s(\d+)\s-\s(.+)")

            for option in course_options:
                option = re.sub(r"\s\d+\sCredit\(s\)", "", option).strip()
                match = pattern.search(option)
                if match:
                    subject, course_number, name = match.groups()
                    row = [subject, course_number, name, credits]

                    folder = os.path.join(base_path, current_h3 or "General")
                    if current_h4:
                        folder = os.path.join(folder, current_h4)
                    if current_h5:
                        folder = os.path.join(folder, current_h5)

                    os.makedirs(folder, exist_ok=True)
                    filename = os.path.join(folder, f"{sanitize(current_h5 or current_h4 or current_h3 or 'General')}.csv")

                    if filename not in course_map:
                        course_map[filename] = []
                    course_map[filename].append(row)

    for filepath, rows in course_map.items():
        with open(filepath, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Subject", "Course Number", "Name", "Credits"])
            writer.writerows(rows)
        print(f"Saved {len(rows)} course(s) to {filepath}")
        
def scrape_total_credits(url, year, major):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    for tag in soup.find_all('h2'):
        if "Total Credits" in tag.get_text():
            match = re.search(r'(\d+)', tag.get_text())
            if match:
                total_credits = int(match.group(1))

                # Prepare file path
                degree_name = major.replace("/", ",")
                current_dir = os.path.dirname(os.path.abspath(__file__))
                folder_path = os.path.join(current_dir, year)
                os.makedirs(folder_path, exist_ok=True)
                csv_path = os.path.join(folder_path, "total_credits.csv")

                # Check if file exists to avoid writing the header multiple times
                file_exists = os.path.exists(csv_path)

                # Write to CSV (append mode)
                with open(csv_path, "a", newline="") as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(["Degree", "Total Credits"])
                    writer.writerow([major, total_credits])

                print(f"Saved total credits for {major} to {csv_path}")
                return total_credits

    print("Total credits not found.")
    return None




main()
# main_tester()
