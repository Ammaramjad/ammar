# MGBOX iOS VoIP token → MagicBox session

Copy these files into the existing Xcode project and upload the PHP/SQL to MagicBox.

## 1. Xcode

Replace the matching files in the Sngine iOS app:

- `SngineWebApp.swift`
- `ContentView.swift`

`static var voipToken` sits directly under `static var oneSignalUserId`.
PushKit now saves the hex token in `pushRegistry(_:didUpdate:for:)` and posts `.mgboxVoipTokenUpdated`.

`ContentView.swift` then sends that token to the logged-in website:

1. Appends `voip_token` / `onesignal_user_id` on the first WebView load.
2. POSTs them to `/voip_token.php` with the MagicBox session cookies after every page load, when the PushKit token arrives, and every 5 seconds until PHP returns `success`.

If you already have a custom `ContentView.swift`, keep your UI and copy only:

- `WebView.makeLaunchURL(from:)`
- `Coordinator.sendNativeTokensToWebsite()`
- the `.mgboxVoipTokenUpdated` observer
- the `didFinish` call to `sendNativeTokensToWebsite()`

## 2. MagicBox / Sngine server

1. Run `php/session_voip_token.sql` on the MagicBox database.
2. Upload `php/voip_token.php` to the site root next to `index.php` (`https://magicbox.mg/voip_token.php`).
3. Optional: paste `php/class-user-voip-snippet.php` into `includes/class-user.php` after the session is loaded so the first WebView query string is saved even before the POST runs.

## 3. Confirm it worked

On a real iPhone (PushKit does not issue tokens in the Simulator):

1. Open the app and log in.
2. Xcode console should print `MGBOX VOIP TOKEN:` then `MGBOX token inject status: sent`.
3. Safari Web Inspector / page console should show `MGBOX token saved`.
4. Database check:

```sql
SELECT session_id, user_id, session_voip_token, session_date
FROM users_sessions
WHERE session_voip_token IS NOT NULL
ORDER BY session_id DESC
LIMIT 10;
```
