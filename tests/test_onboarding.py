"""Valida a conformidade das regras de arquivos do repositório."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.check_staged import allowed


class OnboardingTests(unittest.TestCase):
    def test_repository_policy(self):
        """Bloqueia arquivos binários pesados, ambientes virtuais e segredos."""
        for name in ('data/sample/a.py', 'x.NPZ', '.env', '.env.local', 'report.csv', 'node_modules/x.md', 'x.zip'):
            self.assertFalse(allowed(name), name)

        """Permite arquivos de código e documentação padrão."""
        for name in ('scripts/train_v6.py', 'reports/training/sixth_training_report.md', '.env.example'):
            self.assertTrue(allowed(name), name)


if __name__ == '__main__':
    unittest.main()
