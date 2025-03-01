import requests
import find_degree
from bs4 import BeautifulSoup

# URL to scrape
def run(url, major, year):
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
            find_degree.run(full_url, major, year)
        else:
            print("No link with 'All Programs' found.")
    else:
        print(f"Failed to fetch the page. Status code: {response.status_code}")

