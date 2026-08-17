<?php

/**
 * MGBOX: save the iOS PushKit VoIP token onto the current Sngine session.
 *
 * Upload this file to the Sngine site root (same folder as index.php / bootloader.php).
 * The iOS WebView POSTs here with the logged-in MagicBox cookies.
 *
 * POST/GET:
 *   voip_token          64-char lowercase hex PushKit token
 *   onesignal_user_id   optional OneSignal subscription id
 */

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

require('bootloader.php');

if (!$user->_logged_in) {
  echo json_encode([
    'success' => false,
    'error' => true,
    'message' => 'not_logged_in',
  ]);
  return;
}

$voip_token = '';
if (isset($_POST['voip_token'])) {
  $voip_token = trim((string) $_POST['voip_token']);
} elseif (isset($_GET['voip_token'])) {
  $voip_token = trim((string) $_GET['voip_token']);
}

$onesignal_user_id = '';
if (isset($_POST['onesignal_user_id'])) {
  $onesignal_user_id = trim((string) $_POST['onesignal_user_id']);
} elseif (isset($_GET['onesignal_user_id'])) {
  $onesignal_user_id = trim((string) $_GET['onesignal_user_id']);
}

$session_id = 0;
if (isset($user->_data['session_id'])) {
  $session_id = (int) $user->_data['session_id'];
} elseif (isset($user->_data['user_session_id'])) {
  $session_id = (int) $user->_data['user_session_id'];
}

$user_id = 0;
if (isset($user->_data['user_id'])) {
  $user_id = (int) $user->_data['user_id'];
}

if ($session_id < 1 || $user_id < 1) {
  echo json_encode([
    'success' => false,
    'error' => true,
    'message' => 'no_session',
  ]);
  return;
}

$updated = false;

if ($voip_token !== '') {
  if (!preg_match('/^[a-f0-9]{64}$/i', $voip_token)) {
    echo json_encode([
      'success' => false,
      'error' => true,
      'message' => 'invalid_token',
    ]);
    return;
  }

  $voip_token = strtolower($voip_token);

  $db->query(
    sprintf(
      "UPDATE users_sessions SET session_voip_token = %s WHERE session_id = %s AND user_id = %s",
      secure($voip_token),
      secure($session_id, 'int'),
      secure($user_id, 'int')
    )
  );

  $updated = true;
}

if ($onesignal_user_id !== '') {
  if (preg_match('/^[a-zA-Z0-9-]{8,128}$/', $onesignal_user_id)) {
    $onesignal_column = null;
    $column_check = $db->query("SHOW COLUMNS FROM users_sessions LIKE 'session_onesignal_id'");
    if ($column_check && $column_check->num_rows > 0) {
      $onesignal_column = 'session_onesignal_id';
    } else {
      $column_check = $db->query("SHOW COLUMNS FROM users_sessions LIKE 'session_onesignal_user_id'");
      if ($column_check && $column_check->num_rows > 0) {
        $onesignal_column = 'session_onesignal_user_id';
      }
    }

    if ($onesignal_column) {
      $db->query(
        sprintf(
          "UPDATE users_sessions SET %s = %s WHERE session_id = %s AND user_id = %s",
          $onesignal_column,
          secure($onesignal_user_id),
          secure($session_id, 'int'),
          secure($user_id, 'int')
        )
      );
      $updated = true;
    }
  }
}

if (!$updated && $voip_token === '') {
  echo json_encode([
    'success' => false,
    'error' => true,
    'message' => 'missing_token',
  ]);
  return;
}

echo json_encode([
  'success' => true,
  'session_id' => $session_id,
  'user_id' => $user_id,
]);
