"""Official Doctor network recovery must not manufacture a validation result."""

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRELOAD = ROOT / "scripts/expo_doctor_fetch.cjs"


class DoctorNetworkTests(unittest.TestCase):
    def run_node(self, script):
        subprocess.run(
            ["node", "-e", script, str(PRELOAD)], cwd=ROOT, check=True, capture_output=True
        )

    def test_only_public_legacy_schema_get_uses_real_official_response(self):
        self.run_node("""
const assert = require('node:assert/strict');
const schemaURL = 'https://exp.host/--/api/v2/project/configuration/schema/57.0.0';
const calls = [];
const response = new Response('{"data":{"schema":{"type":"object"}}}');
global.fetch = async (input) => { calls.push(String(input));
  if (calls.length === 1) throw new TypeError('network'); return response; };
require(process.argv[1]);
(async () => {
  assert.equal(await fetch(schemaURL), response);
  assert.deepEqual(calls, ['https://exp.host/--/api/v2/project/configuration/schema/57.0.0',
    'https://api.expo.dev/v2/project/configuration/schema/57.0.0']);
})();
""")

    def test_other_paths_private_headers_methods_and_errors_never_fallback(self):
        self.run_node("""
const assert = require('node:assert/strict');
const schemaURL = 'https://exp.host/--/api/v2/project/configuration/schema/57.0.0';
const network = new TypeError('network'); let count = 0;
global.fetch = async () => { count++; throw network; };
require(process.argv[1]);
(async () => {
  for (const [url, init] of [
    ['https://exp.host/other', undefined],
    ['https://exp.host/--/api/v2/project/configuration/schema/57.0.0?secret=x', undefined],
    [schemaURL, { method: 'POST' }],
    [schemaURL, { headers: { Authorization: 'synthetic' } }],
    [schemaURL, { headers: { Cookie: 'synthetic' } }],
    ['https://other.example/--/api/v2/project/configuration/schema/57.0.0', undefined],
  ]) await assert.rejects(fetch(url, init), (error) => error === network);
  assert.equal(count, 6);
})();
""")

    def test_http_failures_and_failed_official_fallback_are_not_success(self):
        self.run_node("""
const assert = require('node:assert/strict');
const schemaURL = 'https://exp.host/--/api/v2/project/configuration/schema/57.0.0'; let count = 0;
const unavailable = new Response('', { status: 503 });
global.fetch = async () => { count++; return unavailable; };
require(process.argv[1]);
(async () => {
  assert.equal(await fetch(schemaURL), unavailable);
  assert.equal(count, 1);
  delete require.cache[require.resolve(process.argv[1])];
  const failure = new TypeError('network');
  global.fetch = async () => { throw failure; };
  require(process.argv[1]);
  await assert.rejects(fetch(schemaURL), (error) => error === failure);
})();
""")
