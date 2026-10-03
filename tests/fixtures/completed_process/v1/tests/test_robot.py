import unittest

from ktnode import ConfigUpdate, ConfigUpdateResult, NextStep
from passthrough import Robot


class CompletedRobotTests(unittest.TestCase):
    def test_explicit_lifecycle_callbacks(self) -> None:
        robot = Robot()
        self.assertIs(robot.setup(None), NextStep.CONTINUE)
        update = ConfigUpdate(0, 1, [], {}, {}, [], 0)
        self.assertIs(robot.config_update(None, update), ConfigUpdateResult.ACCEPT)
        self.assertIs(robot.close(None), NextStep.STOP)
        self.assertEqual(robot.close_count, 1)
        self.assertEqual(robot.calls, ["setup", "config_update", "close"])


if __name__ == "__main__":
    unittest.main()
