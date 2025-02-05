import requests
import csv
import os
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

def scrape_courses(url):
    data = "waffle"
    print(f"\nScraping course listings from: {url}")

    # Send a GET request to the website
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content
        soup = BeautifulSoup(response.text, "html.parser")

        # Find all course listings (li elements with class "acalog-course")
        course_elements = soup.find_all("li", class_="acalog-course")
        # Extract and print course names
        if course_elements:
            filename = f'{data}.csv'
            file_exists = os.path.exists(filename)
            print("\nFound Courses:\n----------------------------")
            courses = []
            if file_exists:
                print(f"'{filename}' already exists.")
            else:
                for index, course in enumerate(course_elements, start=1):
                    course_text = course.get_text(separator=" ", strip=True)  # Extract text with spaces
                    # print(type(course_text))
                    courses.append([course_text])
                    # print(f"{index}. {course_text}")  # Print course information
                with open(filename, 'w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerows(courses)
                    
                    # outrow = row # row is already a list
                    # outrow.append(output.split('\t'))
                    # csvout.writerow(outrow)
                    
                print(f"'{filename}' has been created.")
                
                # for course in courses:
                #     print(course)
        else:
            print("No course listings found.")
    else:
        print(f"Failed to fetch the page. Status code: {response.status_code}")
