"""Verify only the original failing schema subcase with native assertions.

This is not a reexecution of the randomized 20-DocType official test. It
preserves that test's first native assertion/validator and never edits sources.
"""
import json
import os
import re
from run import BENCH, OUT, SuiteLock, active_runners


def main():
    with SuiteLock():
        assert not active_runners()
        os.chdir(BENCH / 'sites')
        import frappe
        frappe.init('ccm-upstream-frappe-residual.test'); frappe.connect()
        try:
            frappe.set_user('Administrator')
            from frappe.tests.test_db_update import TestDBUpdateSanityChecks
            case = TestDBUpdateSanityChecks('test_no_unnecessary_migrates')
            doctype = 'Automation Trigger Queue'
            frappe.reload_doctype(doctype, force=True)
            status, queries = 'PASS', []
            try:
                with case.assertQueryCount(0, query_type=('alter',)):
                    frappe.reload_doctype(doctype, force=True)
            except AssertionError as error:
                status = 'FAIL'
                # Only these exact native DDL statements are publishable.
                queries = [q for q in str(error).splitlines()
                           if re.fullmatch(r'ALTER TABLE `tabAutomation Trigger Queue` '
                              r'(DROP INDEX `unique_dedup_key`|ADD UNIQUE INDEX '
                              r'`unique_dedup_key` \(`dedup_key`\))', q)]
                assert len(queries) == 2
            data = {'scope': 'Original failing DocType subcase only; not the randomized official method',
                    'official_method_reexecuted': False, 'status': status,
                    'site': frappe.local.site, 'doctype': doctype,
                    'native_assertion': 'assertQueryCount(0, query_type=(alter,))',
                    'native_ddl': queries, 'native_query_count': len(queries),
                    'random_order_or_assertion_modified': False,
                    'upstream_sources_or_fixture_modified': False,
                    'classification': 'DEMONSTRATED_NATIVE_SCHEMA_INDEX_CONTRACT'}
            with (OUT / 'residual-schema-subcase.json').open('x') as stream:
                stream.write(json.dumps(data, indent=2) + '\n')
            print(json.dumps(data))
        finally:
            frappe.destroy()


if __name__ == '__main__': main()
