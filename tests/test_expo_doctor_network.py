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
  if (calls.length === 1) throw new TypeError('network', {cause: {code: 'ENOTFOUND'}});
  return response; };
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
const network = new TypeError('network', {cause: {code: 'ECONNRESET'}}); let count = 0;
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
  const failure = new TypeError('network', {cause: {code: 'ETIMEDOUT'}});
  global.fetch = async () => { throw failure; };
  require(process.argv[1]);
  await assert.rejects(fetch(schemaURL), (error) => error === failure);
})();
""")

    def test_tls_abort_unknown_and_custom_transport_do_not_fallback(self):
        self.run_node("""
const assert = require('node:assert/strict');
const url = 'https://exp.host/--/api/v2/project/configuration/schema/57.0.0';
let failure, count = 0;
global.fetch = async () => { count++; throw failure; };
require(process.argv[1]);
(async () => {
  for (const code of ['CERT_HAS_EXPIRED', 'DEPTH_ZERO_SELF_SIGNED_CERT',
    'ERR_TLS_CERT_ALTNAME_INVALID', 'ABORT_ERR', undefined]) {
    failure = new TypeError('failure', {cause: {code}});
    await assert.rejects(fetch(url), (e) => e === failure);
  }
  failure = new TypeError('network', {cause: {code: 'ENOTFOUND'}});
  for (const init of [{dispatcher: {}}, {agent: {}}, {credentials: 'include'}])
    await assert.rejects(fetch(url, init), (e) => e === failure);
  assert.equal(count, 8);
})();
""")

    def test_request_private_headers_and_url_credentials_do_not_fallback(self):
        self.run_node("""
const assert = require('node:assert/strict');
const url = 'https://exp.host/--/api/v2/project/configuration/schema/57.0.0';
const failure = new TypeError('network', {cause: {code: 'ENOTFOUND'}});
let count = 0;
global.fetch = async () => { count++; throw failure; };
require(process.argv[1]);
(async () => {
  for (const name of ['Authorization', 'Cookie']) {
    const request = new Request(url, {headers: {[name]: 'synthetic'}});
    await assert.rejects(fetch(request, {headers: {}}), (e) => e === failure);
  }
  await assert.rejects(fetch(url.replace('exp.host', 'synthetic@exp.host')),
    (e) => e === failure);
  assert.equal(count, 3);
})();
""")
