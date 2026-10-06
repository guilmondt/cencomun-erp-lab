"""Run a bounded sequence via the pinned native CI runner, without editing it."""
import os
import sys
from pathlib import Path

app, site, *modules = sys.argv[1:]
from run import ALLOWED_SITES
if app not in ('frappe', 'erpnext') or site not in ALLOWED_SITES:
    raise ValueError('Only explicitly allowed official apps/sites are accepted.')
os.chdir('/workspace/.local/frappe-integral/official-bench/sites')
import frappe
from frappe.parallel_test_runner import ParallelTestRunner

runner = ParallelTestRunner(app, site, total_builds=1, build_number=1, lightmode=app == 'erpnext')
available = {app + '.' + str(Path(path).relative_to(frappe.get_app_path(app))).replace('/', '.').strip('.') + '.' + Path(filename).stem: (path, filename)
             for path, filename in runner.test_file_list
             if any(str(Path(path) / filename).endswith(m.replace('.', '/') + '.py') for m in modules)}
if set(available) != set(modules):
    raise ValueError('Select existing official modules only: ' + str(set(modules) - set(available)))
runner.test_file_list = [available[module] for module in modules]
runner.setup_and_run()
