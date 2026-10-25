import configparser
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

source = Path(__file__).resolve().parents[1] / 'install.py'
spec = importlib.util.spec_from_file_location('installer', source)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

class InstallerTests(unittest.TestCase):
    def test_combined_install_preserves_local_authorization_and_disables_old_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / '.var/app' / installer.APP / 'config/discover_overlay/config.ini'
            config.parent.mkdir(parents=True)
            config.write_text('[cache]\naccess_token=local-test-value\n')
            startup = home / '.config/autostart'
            startup.mkdir(parents=True)
            (startup / 'discord.desktop').write_text('[Desktop Entry]\nName=Old Discord\n')
            with patch.object(Path, 'home', return_value=home), patch.object(installer.subprocess, 'run') as run, patch.object(installer.shutil, 'which', return_value=None), patch('sys.argv', ['install.py', '--combined', '--move-hotkey', '--autostart', '--monitor', 'DP-3']):
                installer.main()
            current = configparser.ConfigParser()
            current.read(config)
            self.assertEqual(current.get('cache', 'access_token'), 'local-test-value')
            self.assertEqual(current.get('main', 'monitor'), 'DP-3')
            self.assertEqual(current.getint('main', 'topalign'), 0)
            self.assertLess(current.getfloat('main', 'floating_h'), .04)
            self.assertTrue((home / '.var/app' / installer.APP / 'data/launch-discord.py').exists())
            self.assertIn('Hidden=true', (startup / 'discord.desktop').read_text())
            self.assertIn('Discord + Activity Overlay', (startup / 'discord-activity-overlay.desktop').read_text())
            shortcut = home / '.local/share/applications/discord-overlay-move.desktop'
            self.assertIn('X-KDE-Shortcuts=', shortcut.read_text())
            self.assertEqual(run.call_count, 1)

if __name__ == '__main__':
    unittest.main()
