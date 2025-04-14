from src.models import MajorMapping


def delete_majors(catalog_year: int = None):
    """
    Deletes all majors and their associated nodes/courses.
    Optionally filter by catalog year (e.g., 202430).
    """
    if catalog_year:
        majors = MajorMapping.objects.filter(catalog_year=catalog_year)
        count = majors.count()
        majors.delete()
        print(f"Deleted {count} majors from catalog year {catalog_year}")
    else:
        count = MajorMapping.objects.count()
        MajorMapping.objects.all().delete()
        print(f"Deleted ALL {count} majors from all catalog years")
