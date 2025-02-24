import requests
import csv
import os
import re
from bs4 import BeautifulSoup


def run(url):
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
        h2_tags = soup.find_all("h2")

        # Print the extracted <h3> content
        if h3_tags:
            print("\nFound <h3> tags:\n----------------------------")
            for index, tag in enumerate(h3_tags, start=1):
                print(f"{index}. {tag.get_text(strip=True)}")  # Extract and print text inside <h3>
        else:
            print("No <h3> tags found.")
            
        if h2_tags:
            print("\nFound <h2> tags:\n----------------------------")
            for index, tag in enumerate(h2_tags, start=1):
                print(f"{index}. {tag.get_text(strip=True)}")  # Extract and print text inside <h3>
        else:
            print("No <h3> tags found.")
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





