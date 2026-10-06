#!/usr/bin/env python3
"""Require every selected current-run Java suite, with no failed/skipped tests."""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


NATIVE_SUITES = {
    'NativeAddressTemplateTest': 8,
    'NativePermissionFilterTest': 5,
    'NativeInvoiceRuntimeTest': 2,
    'NativeOrderModelTest': 4,
    'NativeBankCsvTest': 3,
    'NativeFinanceModelTest': 7,
}


def validate_suite(path, count):
    suite = ET.parse(path).getroot()
    assert int(suite.attrib['tests']) == count, f'{path.name}: expected {count} tests; {suite.attrib}'
    assert all(int(suite.attrib[k]) == 0 for k in ['errors', 'failures', 'skipped']), f'{path.name}: {suite.attrib}'
    return suite.attrib


def validate(host, module, results):
    upstream = host / 'modules/axelor-open-suite/axelor-base/build/test-results/test/TEST-com.axelor.apps.base.service.partner.registrationnumber.TestTaxNumberHelper.xml'
    suites = {'upstream-tests': validate_suite(upstream, 16)}
    for name, count in NATIVE_SUITES.items():
        suites['native-fixture-tests' if name == 'NativeAddressTemplateTest' else name] = validate_suite(
            module / 'build/full/test-results/test' / f'TEST-com.cencomun.core.{name}.xml', count)
    # Write receipts only after all mandatory suites have actually passed.
    results.mkdir(parents=True, exist_ok=True)
    for name, attributes in suites.items():
        (results / f'{name}.json').write_text(json.dumps(attributes, indent=2) + '\n')
        print(f'{attributes["name"]}: {attributes["tests"]} Java tests passed; DB acceptance requires Core execution')
    return suites


if __name__ == '__main__':
    validate(*map(Path, sys.argv[1:]))
