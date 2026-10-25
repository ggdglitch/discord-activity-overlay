import ast
import copy
import importlib.util
import json
from pathlib import Path
import time
from types import SimpleNamespace
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'activity_overlay.py'
spec = importlib.util.spec_from_file_location('activity_overlay', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ActivityTests(unittest.TestCase):
    def test_notice_expires_without_mutating_live_member(self):
        user = {'id': 'friend', 'username': 'Friend', 'speaking': True}
        events = {'friend': {'user': user, 'kind': 'left', 'until': 15}}
        shown = module.event_rows([user], events, 10)
        self.assertEqual(shown[0]['nick'], 'Friend · left')
        self.assertFalse(shown[0]['speaking'])
        self.assertTrue(user['speaking'])
        self.assertNotIn('nick', user)
        self.assertEqual(module.event_rows([], events, 16), [])

    def setUp(self):
        self.callbacks = []
        self.original_calls = []
        tree = ast.parse(SOURCE.read_text())
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        self.functions = {'json': json, 'copy': copy, 'time': time,
            'original_message': lambda *a: self.original_calls.append(a),
            'original_channel': lambda obj, channel, guild, need_req: setattr(obj, 'current_voice', channel),
            'GLib': SimpleNamespace(timeout_add=lambda ms, fn: self.callbacks.append(fn))}
        for name in ('set_channel', 'on_message'):
            node = next(n for n in main.body if isinstance(n, ast.FunctionDef) and n.name == name)
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), 'exec'), self.functions)
        self.connector = SimpleNamespace(current_voice='current', user={'id': 'me', 'username': 'Me'},
            in_room=['me'], userlist={'me': {'id': 'me', 'username': 'Me', 'speaking': False}},
            _activity_events={}, _last_voice_state='VOICE_CONNECTED', update_overlays_from_data=lambda: None)

    def emit(self, event, payload):
        self.functions['on_message'](self.connector, json.dumps({'evt': event, 'data': payload}))

    def test_self_departure_is_quiet(self):
        self.connector._activity_events['me'] = {'kind': 'joined'}
        self.emit('VOICE_STATE_DELETE', {'user': {'id': 'me'}})
        self.assertEqual(self.connector._activity_events, {})

    def test_channel_switch_clears_notices(self):
        self.connector._activity_events['friend'] = {'kind': 'left'}
        self.functions['set_channel'](self.connector, 'next', 'guild')
        self.assertEqual(self.connector._activity_events, {})

    def test_old_channel_event_is_ignored(self):
        self.emit('VOICE_STATE_DELETE', {'channel_id': 'old', 'user': {'id': 'friend'}})
        self.assertFalse(self.original_calls)
        self.assertEqual(self.connector._activity_events, {})

    def test_connection_loss_creates_notice(self):
        self.emit('VOICE_CONNECTION_STATUS', {'state': 'DISCONNECTED'})
        self.callbacks.pop(0)()
        self.assertEqual(self.connector._activity_events['me']['kind'], 'connection lost')

    def test_channel_switch_cancels_pending_loss_notice(self):
        self.emit('VOICE_CONNECTION_STATUS', {'state': 'DISCONNECTED'})
        self.connector.current_voice = 'next'
        self.callbacks.pop(0)()
        self.assertEqual(self.connector._activity_events, {})

    def test_recovery_cancels_pending_loss_notice(self):
        self.emit('VOICE_CONNECTION_STATUS', {'state': 'DISCONNECTED'})
        self.emit('VOICE_CONNECTION_STATUS', {'state': 'VOICE_CONNECTED'})
        self.callbacks.pop(0)()
        self.assertEqual(self.connector._activity_events, {})

if __name__ == '__main__':
    unittest.main()
