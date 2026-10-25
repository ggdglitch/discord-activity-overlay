#!/usr/bin/env python3
"""Install the extension for the current user. No root privileges required."""
import argparse
import configparser
from pathlib import Path
import shutil
import subprocess

APP = 'io.github.trigg.discover_overlay'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--monitor', default='Any', help='Wayland output name, e.g. DP-3')
    parser.add_argument('--autostart', action='store_true')
    args = parser.parse_args()
    subprocess.run(['flatpak', 'info', APP], check=True, stdout=subprocess.DEVNULL)
    source = Path(__file__).resolve().parent
    root = Path.home() / '.var/app' / APP
    target = root / 'data/activity-overlay.py'
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.copy2(target, target.with_suffix('.py.backup'))
    shutil.copy2(source / 'activity_overlay.py', target)
    config = root / 'config/discover_overlay/config.ini'
    config.parent.mkdir(parents=True, exist_ok=True)
    current = configparser.ConfigParser(interpolation=None)
    if config.exists():
        shutil.copy2(config, config.with_suffix('.ini.backup'))
        config.with_suffix('.ini.backup').chmod(0o600)
        current.read(config)
    theme = configparser.ConfigParser(interpolation=None)
    theme.read(source / 'theme.ini')
    for section in theme.sections():
        if not current.has_section(section):
            current.add_section(section)
        for key, value in theme.items(section):
            current.set(section, key, value)
    current.set('main', 'monitor', args.monitor)
    with config.open('w') as handle:
        current.write(handle)
    config.chmod(0o600)
    command = f'/usr/bin/flatpak run --command=python {APP} "{target}" --minimized'
    desktop = '[Desktop Entry]\nType=Application\nName=Discord Activity Overlay\nExec=' + command + '\nTerminal=false\n'
    applications = Path.home() / '.local/share/applications'
    applications.mkdir(parents=True, exist_ok=True)
    (applications / 'discord-activity-overlay.desktop').write_text(desktop)
    if args.autostart:
        autostart = Path.home() / '.config/autostart'
        autostart.mkdir(parents=True, exist_ok=True)
        (autostart / 'discover-overlay.desktop').write_text(desktop)
    print('Installed. Quit an existing Discover Overlay instance, then launch Discord Activity Overlay.')
    print('Your existing Discord authorization remains local and is preserved.')

if __name__ == '__main__':
    main()
