from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]


class StartScriptTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="linux practice ")
        self.project = Path(self.temp.name) / "project with spaces"
        shutil.copytree(ROOT, self.project, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.log"))
        self.script = self.project / "start.sh"
        self.process = None

    def tearDown(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.temp.cleanup()

    def test_starter_requires_execute_permission(self):
        self.assertEqual(stat.S_IMODE((ROOT / "start.sh").stat().st_mode) & 0o111, 0)
        with self.assertRaises(PermissionError):
            subprocess.run([str(self.script)], cwd=self.project, check=True)

    def test_changed_config_logging_and_graceful_stop(self):
        (self.project / "config/app.conf").write_text("APP_NAME=devops-test\n")
        self.script.chmod(0o744)
        self.process = subprocess.Popen([str(self.script)], cwd=self.project)
        log = self.project / "logs/app.log"
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            if log.exists() and "event=heartbeat" in log.read_text():
                break
            time.sleep(0.05)
        self.assertIsNone(self.process.poll())
        self.assertIn(f"app=devops-test pid={self.process.pid} event=heartbeat", log.read_text())
        self.process.terminate()
        self.assertEqual(self.process.wait(timeout=5), 0)
        contents = log.read_text()
        self.assertIn("event=stopped", contents)
        time.sleep(2.2)
        self.assertEqual(log.read_text(), contents)

    def test_empty_name_is_reported(self):
        (self.project / "config/app.conf").write_text("APP_NAME=\n")
        result = subprocess.run(["bash", str(self.script)], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 1)
        self.assertIn("APP_NAME", result.stderr)

    def test_name_is_data_not_shell_code(self):
        (self.project / "config/app.conf").write_text("APP_NAME=$(touch injected)\n")
        self.script.chmod(0o744)
        self.process = subprocess.Popen([str(self.script)], cwd=self.project)
        log = self.project / "logs/app.log"
        deadline = time.monotonic() + 5
        while not log.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertIn("app=$(touch injected)", log.read_text())
        self.assertFalse((self.project / "injected").exists())


if __name__ == "__main__":
    unittest.main()
