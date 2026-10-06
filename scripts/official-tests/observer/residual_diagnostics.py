"""Opt-in read-only observations for the authorized residual IDs.

Never publish exception messages, credentials, mail contents or DB rows.
Trace only native backup/email/schema frames; do not replace their behavior.
"""
import os
import sys


def trace(frame, event, arg, emit):
    path = frame.f_code.co_filename
    if not path.endswith(('frappe/utils/backups.py',
                          'frappe/email/receive.py',
                          'frappe/email/doctype/email_account/email_account.py',
                          'frappe/tests/test_db_update.py')):
        return False
    if event == 'exception':
        exc = arg[1]
        filename = getattr(exc, 'filename', None)
        home = os.path.expanduser('~')
        emit('residual_native_exception', frame={'file': path,
             'line': frame.f_lineno, 'function': frame.f_code.co_name},
             exception=type(exc).__name__, errno=getattr(exc, 'errno', None),
             filename_under_home=bool(filename and
                 os.path.commonpath([os.path.abspath(filename), home]) == home))
    return True


def profile(frame, event, arg, emit):
    path, name = frame.f_code.co_filename, frame.f_code.co_name
    if event not in ('call', 'return'):
        return
    if path.endswith('frappe/email/doctype/email_account/email_account.py') and name in (
            'receive', 'get_inbound_mails', 'notify_unreplied'):
        f = sys.modules.get('frappe')
        doc = frame.f_locals.get('self')
        emit('residual_email_state', operation=name+'_'+event,
             mute_emails=bool(f.flags.mute_emails),
             incoming_enabled=doc.get('enable_incoming') if doc else None,
             imap_enabled=doc.get('use_imap') if doc else None,
             imap_folders=[{'folder': row.folder_name, 'append_to': row.append_to}
                           for row in doc.get('imap_folder', [])] if doc else [],
             result_count=len(arg) if isinstance(arg, (tuple, list)) else None)
