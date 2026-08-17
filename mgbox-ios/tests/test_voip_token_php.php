<?php
/**
 * Standalone checks for voip_token.php validation rules.
 * Does not boot Sngine; it only verifies token/format logic.
 */

function mgbox_is_valid_voip_token($token) {
  return is_string($token) && preg_match('/^[a-f0-9]{64}$/i', $token) === 1;
}

function mgbox_is_valid_onesignal_id($id) {
  return is_string($id) && preg_match('/^[a-zA-Z0-9-]{8,128}$/', $id) === 1;
}

$failures = 0;

function expect($label, $actual, $expected) {
  global $failures;
  if ($actual !== $expected) {
    fwrite(STDERR, "FAIL: {$label} expected " . var_export($expected, true) . " got " . var_export($actual, true) . PHP_EOL);
    $failures++;
  } else {
    echo "PASS: {$label}\n";
  }
}

expect('64 hex token', mgbox_is_valid_voip_token(str_repeat('ab', 32)), true);
expect('uppercase hex token', mgbox_is_valid_voip_token(str_repeat('AB', 32)), true);
expect('short token', mgbox_is_valid_voip_token('abc123'), false);
expect('empty token', mgbox_is_valid_voip_token(''), false);
expect('non-hex token', mgbox_is_valid_voip_token(str_repeat('g', 64)), false);
expect('onesignal uuid', mgbox_is_valid_onesignal_id('becdaedf-2113-40e9-a884-006765233cbe'), true);
expect('onesignal too short', mgbox_is_valid_onesignal_id('abc'), false);

$php = file_get_contents(__DIR__ . '/../php/voip_token.php');
expect('endpoint updates session_voip_token', str_contains($php, 'session_voip_token'), true);
expect('endpoint requires login', str_contains($php, 'not_logged_in'), true);
expect('endpoint updates users_sessions', str_contains($php, 'UPDATE users_sessions'), true);

if ($failures > 0) {
  exit(1);
}

echo "All PHP VoIP token checks passed\n";
