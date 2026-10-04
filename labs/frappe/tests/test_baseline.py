"""DB-free checks for the app's installable Frappe registration contract."""

import importlib
import unittest
from importlib import resources


class AppRegistrationTests(unittest.TestCase):
    def test_app_and_module_can_be_imported_without_a_site(self):
        app = importlib.import_module("cencomun_erp")
        module = importlib.import_module("cencomun_erp.cencomun_erp")
        self.assertTrue(app.__version__)
        self.assertIsNotNone(module.__file__)

    def test_hooks_register_the_app_and_erpnext_prerequisite(self):
        hooks = importlib.import_module("cencomun_erp.hooks")
        self.assertEqual(hooks.app_name, "cencomun_erp")
        self.assertEqual(hooks.required_apps, ["erpnext"])
        self.assertEqual(hooks.app_title, "Cencomun ERP")

    def test_module_declaration_resolves_to_packaged_module(self):
        root = resources.files("cencomun_erp")
        modules = root.joinpath("modules.txt").read_text().splitlines()
        self.assertEqual(modules, ["Cencomun ERP"])
        for module in modules:
            directory = root.joinpath(module.lower().replace(" ", "_"))
            self.assertTrue(directory.joinpath("__init__.py").is_file())
            self.assertTrue(directory.joinpath(".frappe").is_file())

    def test_empty_migration_manifest_can_be_read(self):
        patches = resources.files("cencomun_erp").joinpath("patches.txt").read_text()
        entries = [line.strip() for line in patches.splitlines() if line.strip()]
        self.assertEqual(entries, ["[pre_model_sync]", "[post_model_sync]"])

    def test_asset_directory_survives_packaging(self):
        root = resources.files("cencomun_erp")
        self.assertTrue(root.joinpath("public").is_dir())
        self.assertTrue(root.joinpath("templates", "pages", "__init__.py").is_file())


if __name__ == "__main__":
    unittest.main()
