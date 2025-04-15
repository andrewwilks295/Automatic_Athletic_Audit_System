
import requests
from django.test import TestCase

from src.course_parser import parse_course_structure_as_tree
from src.data import populate_catalog_from_payload
from src.models import RequirementNode
from src.suu_scraper import pull_catalog_year, find_all_programs_link, find_degree
from src.utils import load_major_code_lookup, match_major_name_web_to_registrar, prepare_django_inserts, print_requirement_tree


class CatalogDBTest(TestCase):
    def setUp(self):
        print("Running CatalogDBTest setUp")

    def test_parent_links_saved_in_db(self):
        year = "2024-2025"
        catalog_year = int(year[:4] + "30")
        major_name_web = "Exercise Science (B.S.)"

        # Prepare HTML and parsed tree
        catalog_url = pull_catalog_year(year)
        programs_url = find_all_programs_link(catalog_url)
        degree_url = find_degree(programs_url, major_name_web)
        html = requests.get(degree_url + "&print").text
        parsed_tree = parse_course_structure_as_tree(html)

        # Generate payload
        major_code_df = load_major_code_lookup("major_codes.csv")
        major_code, major_name_registrar, _ = match_major_name_web_to_registrar(major_name_web, major_code_df)

        payload = prepare_django_inserts(
            parsed_tree=parsed_tree,
            major_code=major_code,
            major_name_web=major_name_web,
            major_name_registrar=major_name_registrar,
            total_credits_required=120,
            catalog_year=catalog_year
        )

        # Insert into DB
        result = populate_catalog_from_payload(payload)
        print_requirement_tree(result["major"])

        # Now verify parent links exist
        has_links = RequirementNode.objects.filter(parent__isnull=False).exists()
        total_nodes = RequirementNode.objects.count()

        self.assertGreater(total_nodes, 0, "No nodes were inserted.")
        self.assertTrue(has_links, "No nodes have parent relationships saved in DB.")

        print(f"✅ Inserted {total_nodes} nodes, with parent relationships correctly set.")

    def test_no_orphaned_nodes(self):
        # This must run after a catalog is populated
        orphans = RequirementNode.objects.filter(
            parent__isnull=False
        ).exclude(
            parent__in=RequirementNode.objects.all()
        )

        self.assertEqual(orphans.count(), 0, f"❌ Found {orphans.count()} orphaned nodes with invalid parent_id.")
        print("✅ No orphaned nodes found.")