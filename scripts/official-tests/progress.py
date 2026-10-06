"""Observe a native CI attempt without attaching, restarting, or exposing logs."""

import argparse
import collections
import datetime
import json
import re
from run import PRIVATE, OUT, parse_parallel_results, active_runners


def main(base):
    match = re.fullmatch(r'(frappe|erpnext)-ci-attempt-(\d+)', base)
    if not match:
        raise ValueError('Use an existing native CI attempt basename.')
    final = OUT / (base + '.json')
    if final.exists():
        data = json.loads(final.read_text())
        print(json.dumps({key: data.get(key) for key in
                          ['status', 'actual_tests_run', 'counts', 'command', 'exit_code']}, indent=2))
        return
    log = PRIVATE / (base + '.log')
    result = parse_parallel_results(log.read_text(), match[1])
    state = PRIVATE / (base + '-running.json')
    metadata = json.loads(state.read_text()) if state.exists() else {}
    native_pid = metadata.get('runner_pid')
    print(json.dumps({'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      'status': 'AWAITING_NATIVE_FINAL_RESULT', 'actual_tests_run': None,
                      'observed_result_events': result['observed_result_events'],
                      'observed_event_counts': dict(collections.Counter(c['status'] for c in result['cases'])),
                      'native_runner_observed_active': native_pid in active_runners(),
                      'site': metadata.get('site'), 'private_log_bytes': log.stat().st_size,
                      'note': 'Observed method events are not the final Tests count or whole-suite approval.'}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('attempt')
    main(parser.parse_args().attempt)
