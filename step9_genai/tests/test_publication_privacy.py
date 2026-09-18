"""Regression checks for the manually reviewed Step 9 publication."""
import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT/'evidence/publication_manifest.json'
TEXT_SUFFIXES = {'.md', '.py', '.json', '.txt'}


def text_files():
    return [p for p in ROOT.rglob('*') if p.is_file() and p.suffix in TEXT_SUFFIXES]


class PublicationChecks(unittest.TestCase):
    def test_reviewed_inventory_and_hashes(self):
        manifest = json.loads(MANIFEST.read_text())['files']
        actual = {str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file()
                  and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts
                  and p != MANIFEST}
        self.assertEqual(actual, set(manifest))
        for relative, digest in manifest.items():
            self.assertEqual(hashlib.sha256((ROOT/relative).read_bytes()).hexdigest(), digest, relative)

    def test_no_credential_or_contact_patterns(self):
        patterns = [
            r'\bsk-[A-Za-z0-9_-]{20,}\b',
            r'\b(?:gh[opurs]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b',
            r'\bAKIA[0-9A-Z]{16}\b',
            r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
            r'\+63[ -]?9\d{2}[ -]?\d{3}[ -]?\d{4}\b',
            r'(?im)^\s*(?:api_key|password|access_token)\s*[:=]\s*[\x22\x27]?[^\s\x22\x27]{8,}',
        ]
        for path in text_files():
            content = path.read_text()
            for pattern in patterns:
                self.assertIsNone(re.search(pattern, content), str(path.relative_to(ROOT)))

    def test_no_dialogue_or_instruction_markers(self):
        patterns = [r'(?im)^\s*(?:system|assistant|user)\s*:',
                    r'(?im)^\s*you are (?:an? |the )',
                    r'<\|(?:im_start|im_end|system|assistant|user)\|>',
                    r'(?i)begin additional' + r' message']
        for path in text_files():
            for pattern in patterns:
                self.assertIsNone(re.search(pattern, path.read_text()), str(path.relative_to(ROOT)))

    def test_no_authoring_tool_identifiers(self):
        names = ['chat'+'gpt', 'co'+'dex', 'open'+'ai']
        for path in text_files():
            content = path.read_text()
            for name in names:
                self.assertNotIn(name, content.lower(), str(path.relative_to(ROOT)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
