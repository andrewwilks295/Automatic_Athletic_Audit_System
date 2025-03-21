import requests
import find_all_programs_link
import re
from bs4 import BeautifulSoup

# def run(year, major):
#     print("\n\nStarting_catalog_year_test\n----------------------------")
#     # Base URL of SUU catalog
#     base_url = "https://www.suu.edu/academics/catalog/"

#     # Dictionary to map catalog years to their respective `catoid` values
#     catalog_years = {
#         "2017-2018": '12', #format is different from Exercise Science (B.S.) it is Exercise Science, B.S.
#         "2018-2019": '14',
#         "2019-2020": '21',
#         "2020-2021": '22',
#         "2021-2022": "23",
#         "2022-2023": "24",
#         "2023-2024": "25",
#         "2024-2025": "26"
#     }

import re
import requests
from bs4 import BeautifulSoup


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


catalog_years: dict[str, str] | None = None
base_url = "https://www.suu.edu/academics/catalog/"


def startup():
    global catalog_years
    if catalog_years is None:
        catalog_years = get_catalog_years(base_url)
        print("Catalog years found:", catalog_years)


def run(year, major):
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
            find_all_programs_link.run(catalog_url, major, year)

        else:
            print(f"Failed to fetch the page. Status code: {response.status_code}")
