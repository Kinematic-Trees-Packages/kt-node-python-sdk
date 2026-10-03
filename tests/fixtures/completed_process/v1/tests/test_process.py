import unittest

import ktnode as kt
from passthrough import Process


class CompletedProcessTests(unittest.TestCase):
    def test_explicit_lifecycle_callbacks(self) -> None:
        process = Process()
        self.assertIs(process.setup(None), kt.NextStep.CONTINUE)
        update = kt.ConfigUpdate(0, 1, [], {}, {}, [], 0)
        self.assertIs(
            process.config_update(None, update),
            kt.ConfigUpdateResult.ACCEPT,
        )
        self.assertIs(process.close(None), kt.NextStep.STOP)
        self.assertEqual(process.close_count, 1)
        self.assertEqual(process.calls, ["setup", "config_update", "close"])


if __name__ == "__main__":
    unittest.main()
