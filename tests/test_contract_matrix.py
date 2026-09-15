import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = Path("/agent-root/workspace-main/kt_robotics/packaging/c-abi/contract-v1.2.json")


class ContractMatrixTests(unittest.TestCase):
    def test_every_frozen_symbol_is_mapped(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        symbols = {
            item["symbol"]
            for item in contract["functions"]
        }
        matrix = (ROOT / "docs/abi-contract-matrix.md").read_text(encoding="utf-8")
        mapped = set(re.findall(r"`(kt_[a-z0-9_]+)`", matrix))
        self.assertEqual(symbols, mapped)


if __name__ == "__main__":
    unittest.main()
