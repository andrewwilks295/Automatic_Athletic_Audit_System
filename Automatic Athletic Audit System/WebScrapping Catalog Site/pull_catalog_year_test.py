import requests
import find_all_programs_link
from bs4 import BeautifulSoup

print("\n\nStarting_catalog_year_test\n----------------------------")
# Base URL of SUU catalog
base_url = "https://www.suu.edu/academics/catalog/"

# Dictionary to map catalog years to their respective `catoid` values
catalog_years = {
    "2017-2018": '12', #format is different from Exercise Science (B.S.) it is Exercise Science, B.S.
    "2018-2019": '14',
    "2019-2020": '21',
    "2020-2021": '22',
    "2021-2022": "23",
    "2022-2023": "24",
    "2023-2024": "25",
    "2024-2025": "26"
}

# Change this variable to select the desired catalog year
selected_year = "2017-2018"

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
        find_all_programs_link.run(catalog_url)

    else:
        print(f"Failed to fetch the page. Status code: {response.status_code}")
