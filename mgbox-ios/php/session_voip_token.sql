-- Add a per-device VoIP token column to the current MagicBox/Sngine session.
-- Run this once against the MagicBox database.

ALTER TABLE `users_sessions`
  ADD COLUMN `session_voip_token` VARCHAR(64) NULL DEFAULT NULL;

CREATE INDEX `idx_session_voip_token`
  ON `users_sessions` (`session_voip_token`);
