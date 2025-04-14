import requests
import re
from bs4 import BeautifulSoup


def get_catalog_years(base_url="https://www.suu.edu/academics/catalog/"):
    """
    Scrapes the catalog homepage for links containing catalog years.
    Returns a dictionary mapping catalog year strings (e.g., "2024-2025") to their catoid values.
    """
    response = requests.get(base_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    catalog_years = {}

    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        year_match = re.search(r"(\d{4}-\d{4})", text)
        if year_match:
            year_str = year_match.group(1)
            catoid_match = re.search(r"catoid=(\d+)", a['href'])
            if catoid_match:
                catalog_years[year_str] = catoid_match.group(1)
            else:
                print(f"No catoid found for year {year_str}")
    return catalog_years


def pull_catalog_year(year):
    """
    Given a catalog year like '2024-2025', returns the corresponding catalog URL.
    """
    catalog_years = get_catalog_years()
    catoid = catalog_years.get(year)
    if not catoid:
        raise ValueError(f"Catalog year '{year}' not found.")
    return f"https://catalog.suu.edu/index.php?catoid={catoid}"


def find_all_programs_link(catalog_url):
    response = requests.get(catalog_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    link = soup.find('a', string=lambda text: text and "All Programs" in text)
    if link:
        return f"https://catalog.suu.edu{link['href']}"
    raise ValueError("Could not find 'All Programs' link.")


def find_degree(all_programs_url, major):
    response = requests.get(all_programs_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    for a in soup.find_all('a', href=True):
        text = a.text.strip()
        if major.lower() in text.lower():
            href = a['href']
            return f"https://catalog.suu.edu/{href.lstrip('/')}"
    return None


def fetch_total_credits(html):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup.find_all('h2'):
        if "Total Credits" in tag.get_text():
            match = re.search(r'(\d+)', tag.get_text())
            if match:
                return int(match.group(1))
    print("WARN: Total credits not found in page — defaulting to 120.")
    return 120
