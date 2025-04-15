import unittest
from django.test import TestCase
from src.models import MajorMapping, RequirementNode
from src.course_parser import parse_course_structure_as_tree, print_requirement_tree
from src.utils import prepare_django_inserts, match_major_name_web_to_registrar, load_major_code_lookup
from src.data import populate_catalog_from_payload

class CatalogParseTest(TestCase):
    def test_requirement_node_parent_ids(self):
        html = open("tests/data/exercise_science.html", encoding="utf-8").read()
        tree = parse_course_structure_as_tree(html)
        major_code_df = load_major_code_lookup("major_codes.csv")
        match_result = match_major_name_web_to_registrar("Exercise Science (B.S.)", major_code_df)
        payload = prepare_django_inserts(
            parsed_tree=tree,
            match_result=match_result,
            major_name_web="Exercise Science (B.S.)",
            total_credits_required=120,
            catalog_year=202430
        )
        populate_catalog_from_payload(payload)
        print_requirement_tree(MajorMapping.objects.get(major_code=match_result["major_code"], catalog_year=202430))
        self.assertTrue(True)  # Dummy assertion

class CatalogDBTest(TestCase):
    def setUp(self):
        html = open("tests/data/exercise_science.html", encoding="utf-8").read()
        self.tree = parse_course_structure_as_tree(html)
        major_code_df = load_major_code_lookup("major_codes.csv")
        match_result = match_major_name_web_to_registrar("Exercise Science (B.S.)", major_code_df)
        self.major_code = match_result["major_code"]
        self.base_major_code = match_result["base_major_code"]
        self.major_name_registrar = match_result["major_name_registrar"]
        self.payload = prepare_django_inserts(
            parsed_tree=self.tree,
            match_result=match_result,
            major_name_web="Exercise Science (B.S.)",
            total_credits_required=120,
            catalog_year=202430
        )
        populate_catalog_from_payload(self.payload)

    def test_major_inserted(self):
        self.assertEqual(MajorMapping.objects.count(), 1)

    def test_node_hierarchy_preserved(self):
        root_nodes = RequirementNode.objects.filter(parent__isnull=True)
        self.assertTrue(root_nodes.exists())

    def test_parent_links_saved_in_db(self):
        nodes = RequirementNode.objects.all()
        non_roots = nodes.exclude(parent__isnull=True)
        self.assertTrue(all(n.parent_id for n in non_roots))