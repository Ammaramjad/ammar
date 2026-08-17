<?php

/**
 * Optional Sngine hook.
 *
 * Paste this inside includes/class-user.php after the user session is loaded
 * and $this->_logged_in is true. It saves voip_token from the first WebView
 * page load query string, matching how Sngine already stores OneSignal IDs.
 *
 * Do not upload this file as-is. It is a snippet only.
 */

if ($this->_logged_in && !empty($_GET['voip_token'])) {
  $voip_token = trim((string) $_GET['voip_token']);

  if (preg_match('/^[a-f0-9]{64}$/i', $voip_token)) {
    $session_id = 0;
    if (isset($this->_data['session_id'])) {
      $session_id = (int) $this->_data['session_id'];
    } elseif (isset($this->_data['user_session_id'])) {
      $session_id = (int) $this->_data['user_session_id'];
    }

    $user_id = isset($this->_data['user_id']) ? (int) $this->_data['user_id'] : 0;

    if ($session_id > 0 && $user_id > 0) {
      $db->query(
        sprintf(
          "UPDATE users_sessions SET session_voip_token = %s WHERE session_id = %s AND user_id = %s",
          secure(strtolower($voip_token)),
          secure($session_id, 'int'),
          secure($user_id, 'int')
        )
      );
    }
  }
}
