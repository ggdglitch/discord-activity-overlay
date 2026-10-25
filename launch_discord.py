#!/usr/bin/env python3
"""Run native Discord and its activity overlay as one desktop application."""
import fcntl
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

APP = 'io.github.trigg.discover_overlay'

def discord_pids(proc=Path('/proc')):
    found = []
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid != os.getuid():
                continue
            args = (entry / 'cmdline').read_bytes().split(b'\0')
            exe = (entry / 'exe').resolve()
            if exe.name == 'Discord' and not any(a.startswith(b'--type=') for a in args):
                found.append(int(entry.name))
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
    return found

def native_command():
    bundled = Path.home() / '.local/share/discord-native/discord'
    if bundled.is_file():
        return str(bundled)
    command = shutil.which('discord')
    if command:
        return command
    raise RuntimeError('Native Discord was not found. Install Discord for Linux first.')

def main():
    command = native_command()
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
    lock = (runtime / 'discord-activity-launcher.lock').open('w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        subprocess.Popen([command, *sys.argv[1:]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    overlay = Path.home() / '.var/app' / APP / 'data/activity-overlay.py'
    if not overlay.is_file():
        raise RuntimeError('Activity overlay is not installed. Run install.py first.')
    state = Path.home() / '.local/state/discord-activity-overlay'
    state.mkdir(parents=True, exist_ok=True)
    with (state / 'launcher.log').open('a') as log:
        discord = subprocess.Popen([command, *sys.argv[1:]], stdout=log, stderr=log)
        for _ in range(60):
            if discord_pids():
                break
            if discord.poll() not in (None, 0):
                raise RuntimeError('Discord failed to start; see launcher.log.')
            time.sleep(1)
        else:
            raise RuntimeError('Discord did not start within 60 seconds.')
        running = subprocess.check_output(['flatpak', 'ps', '--columns=application'], text=True)
        if APP not in running.splitlines():
            subprocess.Popen(['flatpak', 'run', '--command=python', APP, str(overlay), '--minimized'], stdout=log, stderr=log)
        # Closing Discord's window can leave it running in the tray. Only Quit
        # Discord ends this session and closes the overlay.
        stop = False
        def stopping(signum, frame):
            nonlocal stop
            stop = True
        signal.signal(signal.SIGTERM, stopping)
        signal.signal(signal.SIGINT, stopping)
        try:
            while not stop and discord_pids():
                time.sleep(2)
        finally:
            subprocess.run(['flatpak', 'kill', APP], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == '__main__':
    main()
