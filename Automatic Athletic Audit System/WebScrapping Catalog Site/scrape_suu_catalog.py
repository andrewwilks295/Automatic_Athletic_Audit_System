import os
import requests
import re
import csv
from bs4 import BeautifulSoup

catalog_years: dict[str, str] | None = None
base_url = "https://www.suu.edu/academics/catalog/"

years = [
    "2024-2025",
    "2023-2024",
    "2022-2023",
    "2021-2022",
]

with open('../../majors.txt', 'r') as f:
    majors = [x.strip() for x in f.readlines()]


def main():
    global years, majors
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
            # scrape_h2_h3(full_url) this gets the header requirements which I don't think we need but might as well
            # keep the code
            scrape_courses(full_url, year)

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


def find_degree(url, major):
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
        else:
            return full_url
    else:
        print(f"Failed to fetch the page. Status code: {response.status_code}")


def scrape_h2_h3(url):
    print(f"\nScraping H3 tags from: {url}")

    # Send a GET request to the website
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content
        soup = BeautifulSoup(response.text, "html.parser")

        # Find all <h3> elements
        h3_tags = soup.find_all("h3")
        # h2_tags = soup.find_all("h2")

        # Print the extracted <h3> content
        if h3_tags:
            print("\nFound <h3> tags:\n----------------------------")
            for index, tag in enumerate(h3_tags, start=1):
                print(f"{index}. {tag.get_text(strip=True)}")  # Extract and print text inside <h3>
        else:
            print("No <h3> tags found.")

        # if h2_tags:
        #     print("\nFound <h2> tags:\n----------------------------")
        #     for index, tag in enumerate(h2_tags, start=1):
        #         print(f"{index}. {tag.get_text(strip=True)}")  # Extract and print text inside <h3>
        # else:
        #     print("No <h3> tags found.")
    else:
        print(f"Failed to fetch the page. Status code: {response.status_code}")


def scrape_courses(url, year):
    print(f"\nScraping course listings from: {url}")

    # Send a GET request to the website
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract page title for naming the CSV
        h1_tags = soup.find_all("h1")
        title = h1_tags[0].get_text(strip=True) if h1_tags else "Unknown_Title"

        # Find all course listings
        course_elements = soup.find_all("li", class_="acalog-course")

        if course_elements:
            # Get the directory where this script is located
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Define the folder path within the script's directory
            school_year_folder = os.path.join(current_dir, year)
            # Check if the folder exists; if not, create it
            if not os.path.exists(school_year_folder):
                os.makedirs(school_year_folder)
                print(f"Created folder: {school_year_folder}")
            else:
                print(f"Folder already exists: {school_year_folder}")

            # Define the CSV file path within the school year folder
            filename = f"{title}.csv"

            # sanitize filename
            filename = filename.replace("/", ",")

            csv_file_path = os.path.join(school_year_folder, filename)

            file_exists = os.path.exists(csv_file_path)

            print("\nFound Courses:\n----------------------------")
            courses = []

            if file_exists:
                print(f"'{csv_file_path}' already exists.")
            else:
                for course in course_elements:
                    course_text = course.get_text(separator=" ", strip=True)

                    # Split by " or " to handle multiple course options
                    course_options = course_text.split(" or ")

                    # Extract only the numeric credit value
                    credit_match = re.search(r"(\d+)\sCredit\(s\)", course_text)
                    credits = credit_match.group(1) if credit_match else "Unknown"

                    for option in course_options:
                        # Remove "Credit(s)" from the course name if present
                        option = re.sub(r"\s\d+\sCredit\(s\)", "", option).strip()

                        # Regex pattern to extract subject, course number, and name
                        pattern = re.compile(r"(\w+)\s(\d+)\s-\s(.+)")
                        match = pattern.search(option)

                        if match:
                            subject, course_number, name = match.groups()
                            courses.append([subject, course_number, name, credits])

                # Write courses data to CSV in the designated folder
                with open(csv_file_path, "w", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow(["Subject", "Course Number", "Name", "Credits"])
                    writer.writerows(courses)

                print(f"'{csv_file_path}' has been created successfully.")

        else:
            print("No course listings found.")
    else:
        print(f"Failed to fetch the page. Status code: {response.status_code}")


main()
