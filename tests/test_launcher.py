import importlib.util
from pathlib import Path
import tempfile
import unittest

source = Path(__file__).resolve().parents[1] / 'launch_discord.py'
spec = importlib.util.spec_from_file_location('launcher', source)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)

class LauncherTests(unittest.TestCase):
    def test_only_main_discord_process_is_tracked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for pid, binary, args in [('1', 'Discord', b'Discord\0'),
                    ('2', 'Discord', b'Discord\0--type=renderer\0'),
                    ('3', 'Other', b'Other\0')]:
                process = root / pid
                process.mkdir()
                (process / 'exe').symlink_to(root / 'binaries' / binary)
                (process / 'cmdline').write_bytes(args)
            self.assertEqual(launcher.discord_pids(root), [1])

if __name__ == '__main__':
    unittest.main()
