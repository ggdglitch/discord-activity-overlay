"""Small activity-only extension for Discover Overlay; no Discord client changes."""
import copy
import json
import random
import time

def event_rows(rows, events, now):
    """Combine current members with temporary join/leave labels."""
    result = {row['id']: row for row in rows}
    for uid, event in events.items():
        if event['until'] <= now:
            continue
        row = copy.copy(result.get(uid, event['user']))
        name = row.get('nick') or row.get('username', 'Participant')
        row['nick'] = f"{name} · {event['kind']}"
        row['activity_until'] = event['until']
        if event['kind'] in ('left', 'connection lost'):
            row['speaking'] = False
        result[uid] = row
    return list(result.values())

def main():
    from gi.repository import GLib
    from discover_overlay.discord_connector import DiscordConnector
    from discover_overlay.voice_overlay import VoiceOverlayWindow
    from discover_overlay.discover_overlay import entrypoint, Discover
    original_args = Discover.do_args
    def do_args(self, data, normal_close=True):
        if not any(arg in data for arg in ('--activity-test', '--activity-test-40')):
            return original_args(self, data, normal_close)
        if getattr(self, '_activity_test_running', False):
            return
        connector = self.connection
        if not connector or not connector.authed:
            print('Activity test requires a connected overlay.', flush=True)
            return
        self._activity_test_running = True
        count = 40 if '--activity-test-40' in data else 1
        users = [{'id': f'local-overlay-test-{i}', 'username': f'Test Player {i+1:02}',
                  'avatar': None, 'mute': False, 'deaf': False,
                  'speaking': False, 'lastspoken': 0} for i in range(count)]
        def emit(evt):
            for user in users:
                payload = ({'user': user.copy(), 'nick': user['username']}
                           if evt.startswith('VOICE_STATE') else {'user_id': user['id']})
                connector.on_message(json.dumps({'cmd': 'DISPATCH', 'evt': evt, 'data': payload}))
            connector.update_overlays_from_data()
            print(f'Local {count}-person test: {evt}', flush=True)
            return False
        emit('VOICE_STATE_CREATE')
        active = set()
        tick_count = 0
        def random_speakers():
            nonlocal tick_count
            tick_count += 1
            chosen = set(random.sample(range(count), random.randint(1, min(5, count))))
            for index in active - chosen:
                connector.on_message(json.dumps({'cmd': 'DISPATCH', 'evt': 'SPEAKING_STOP',
                                                 'data': {'user_id': users[index]['id']}}))
            for index in chosen - active:
                connector.on_message(json.dumps({'cmd': 'DISPATCH', 'evt': 'SPEAKING_START',
                                                 'data': {'user_id': users[index]['id']}}))
            active.clear()
            active.update(chosen)
            connector.update_overlays_from_data()
            print(f'Random speakers: {len(chosen)} of {count}', flush=True)
            return tick_count < 12
        def begin_random():
            random_speakers()
            GLib.timeout_add(1500, random_speakers)
            return False
        GLib.timeout_add(6000, begin_random)
        GLib.timeout_add(25000, lambda: emit('SPEAKING_STOP'))
        GLib.timeout_add(29000, lambda: emit('VOICE_STATE_DELETE'))
        def finish():
            for user in users:
                uid = user['id']
                connector.userlist.pop(uid, None)
                connector._activity_events.pop(uid, None)
                if uid in connector.in_room:
                    connector.in_room.remove(uid)
            connector.list_altered = True
            connector.update_overlays_from_data()
            self._activity_test_running = False
            print(f'Local {count}-person test complete; real channel restored.', flush=True)
            return False
        GLib.timeout_add(35000, finish)
    Discover.do_args = do_args
    original_channel = DiscordConnector.set_channel
    def set_channel(self, channel, guild, need_req=True):
        if channel != self.current_voice:
            getattr(self, '_activity_events', {}).clear()
        return original_channel(self, channel, guild, need_req)
    DiscordConnector.set_channel = set_channel
    original_message = DiscordConnector.on_message
    original_rows = VoiceOverlayWindow.set_user_list
    original_draw = VoiceOverlayWindow.overlay_draw

    def on_message(self, message):
        data = json.loads(message)
        evt = data.get('evt')
        events = getattr(self, '_activity_events', {})
        self._activity_events = events
        departed = None
        previous_channel = self.current_voice
        payload = data.get('data') or {}
        event_channel = payload.get('channel_id') if isinstance(payload, dict) else None
        voice_event = evt in ('VOICE_STATE_CREATE', 'VOICE_STATE_DELETE')
        if voice_event and event_channel and event_channel != previous_channel:
            return
        user = data.get('data', {}).get('user', {}) if isinstance(data.get('data'), dict) else {}
        uid = user.get('id')
        if evt == 'VOICE_STATE_DELETE' and uid in self.in_room:
            departed = copy.copy(self.userlist.get(uid, user))
        original_message(self, message)
        if evt == 'VOICE_CONNECTION_STATUS':
            state = payload.get('state')
            prior = getattr(self, '_last_voice_state', None)
            self._last_voice_state = state
            if state == 'DISCONNECTED' and prior == 'VOICE_CONNECTED':
                def report_loss():
                    if (self.current_voice != previous_channel or self.current_voice == '0'
                            or self._last_voice_state != 'DISCONNECTED'):
                        return False
                    own_id = self.user.get('id')
                    participant = copy.copy(self.userlist.get(own_id, self.user))
                    participant.setdefault('avatar', None)
                    participant.setdefault('username', 'You')
                    for row in self.userlist.values():
                        row['speaking'] = False
                    events[own_id] = {'user': participant, 'kind': 'connection lost',
                                      'until': time.perf_counter() + 5}
                    self.list_altered = True
                    self.update_overlays_from_data()
                    def clear_loss():
                        if events.get(own_id, {}).get('kind') == 'connection lost':
                            events.pop(own_id, None)
                            self.list_altered = True
                            self.update_overlays_from_data()
                        return False
                    GLib.timeout_add(5100, clear_loss)
                    return False
                GLib.timeout_add(1500, report_loss)
            elif state in ('VOICE_CONNECTED', 'CONNECTED'):
                self._last_voice_state = 'VOICE_CONNECTED'
                for key in list(events):
                    if events[key]['kind'] == 'connection lost':
                        events.pop(key)
                self.list_altered = True
        own_departure = evt == 'VOICE_STATE_DELETE' and uid == self.user.get('id')
        if (evt in ('VOICE_CHANNEL_SELECT', 'READY') or self.current_voice == '0'
                or self.current_voice != previous_channel or own_departure):
            events.clear()
        elif evt in ('VOICE_STATE_CREATE', 'VOICE_STATE_DELETE') and uid:
            if evt == 'VOICE_STATE_CREATE' and uid in self.in_room:
                participant = copy.copy(self.userlist.get(uid, user))
                kind = 'joined'
            elif departed is not None:
                participant = departed
                kind = 'left'
            else:
                return
            events[uid] = {'user': participant, 'kind': kind, 'until': time.perf_counter() + 5}
            self.list_altered = True
            def expire():
                if events.get(uid, {}).get('until', 0) <= time.perf_counter():
                    events.pop(uid, None)
                    self.list_altered = True
                    self.update_overlays_from_data()
                return False
            GLib.timeout_add(5100, expire)

    def set_user_list(self, rows, altered):
        connector = self.discover.connection
        events = getattr(connector, '_activity_events', {})
        original_rows(self, event_rows(rows, events, time.perf_counter()), altered or bool(events))

    def overlay_draw(self, *args):
        # The existing speaking filter accepts recent activity via lastspoken.
        # Extend that timer only for temporary join/leave notices.
        now = time.perf_counter()
        for row in self.userlist:
            if row.get('activity_until', 0) > now:
                row['lastspoken'] = now
        return original_draw(self, *args)

    DiscordConnector.on_message = on_message
    VoiceOverlayWindow.set_user_list = set_user_list
    VoiceOverlayWindow.overlay_draw = overlay_draw
    entrypoint()

if __name__ == '__main__':
    main()
