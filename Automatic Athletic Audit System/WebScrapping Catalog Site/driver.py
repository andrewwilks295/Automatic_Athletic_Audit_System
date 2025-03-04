import os
from typing import List

import pull_catalog_year_test

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
            if os.path.exists(f"./{year}/{major.replace('/',',')}.csv"):
                print(f"Skipping {year}/{major}")
                continue
            # else scrape it
            pull_catalog_year_test.run(year, major)


main()
