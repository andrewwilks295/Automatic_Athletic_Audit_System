import requests
import find_credit_requirements_h3
from bs4 import BeautifulSoup

def run(url, major):
    print("\n\nStarting find_degree.py\n----------------------------")
    print(f"Fetching degree programs from: {url}")

    # Target degree name to search for
    target_degree = major #this will change to reading from a csv file but will need to have some conversion from EXSC

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
            find_credit_requirements_h3.run(full_url)
            print("\n\n\n\n")
            find_credit_requirements_h3.scrape_courses(full_url)
    else:
        print(f"Failed to fetch the page. Status code: {response.status_code}")
