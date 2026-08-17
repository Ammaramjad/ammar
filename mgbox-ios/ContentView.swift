import SwiftUI
import WebKit
import UIKit

struct ContentView: View {

    var body: some View {

        WebView(
            urlString: WebView.magicBoxURLString
        )
        .ignoresSafeArea()
    }
}


// ======================================================
// MARK: - WKWebView
// ======================================================

struct WebView: UIViewRepresentable {

    static let magicBoxURLString =
        "https://magicbox.mg"

    static let voipTokenEndpointPath =
        "/voip_token.php"

    let urlString: String

    func makeCoordinator() -> Coordinator {

        Coordinator()
    }

    func makeUIView(context: Context) -> WKWebView {

        let configuration =
            WKWebViewConfiguration()

        configuration.allowsInlineMediaPlayback = true
        configuration.mediaTypesRequiringUserActionForPlayback = []
        configuration.allowsAirPlayForMediaPlayback = true
        configuration.allowsPictureInPictureMediaPlayback = true

        let userContentController =
            WKUserContentController()

        userContentController.add(
            context.coordinator,
            name: "mgboxToggleSpeaker"
        )

        userContentController.add(
            context.coordinator,
            name: "mgboxEndCall"
        )

        configuration.userContentController =
            userContentController

        let webView =
            WKWebView(
                frame: .zero,
                configuration: configuration
            )

        webView.navigationDelegate = context.coordinator
        webView.uiDelegate = context.coordinator
        webView.allowsBackForwardNavigationGestures = true
        webView.scrollView.keyboardDismissMode = .interactive

        if #available(iOS 16.4, *) {
            webView.isInspectable = true
        }

        context.coordinator.webView = webView
        context.coordinator.startObservers()

        if let url = Self.makeLaunchURL(from: urlString) {

            webView.load(
                URLRequest(url: url)
            )
        }

        return webView
    }

    func updateUIView(
        _ webView: WKWebView,
        context: Context
    ) {

        context.coordinator.webView = webView
    }


    // ==================================================
    // MARK: Launch URL
    // Append tokens on first load so PHP can save them
    // as soon as the MagicBox session cookie exists.
    // ==================================================

    static func makeLaunchURL(
        from urlString: String
    ) -> URL? {

        guard var components =
            URLComponents(string: urlString)
        else {
            return URL(string: urlString)
        }

        var items =
            components.queryItems ?? []

        if let oneSignalId = AppDelegate.oneSignalUserId,
           !oneSignalId.isEmpty {

            items.removeAll {
                $0.name == "onesignal_user_id"
            }

            items.append(
                URLQueryItem(
                    name: "onesignal_user_id",
                    value: oneSignalId
                )
            )
        }

        if let voipToken = AppDelegate.voipToken,
           !voipToken.isEmpty {

            items.removeAll {
                $0.name == "voip_token"
            }

            items.append(
                URLQueryItem(
                    name: "voip_token",
                    value: voipToken
                )
            )
        }

        if !items.isEmpty {
            components.queryItems = items
        }

        return components.url
    }


    // ==================================================
    // MARK: Coordinator
    // ==================================================

    final class Coordinator:
        NSObject,
        WKNavigationDelegate,
        WKUIDelegate,
        WKScriptMessageHandler {

        weak var webView: WKWebView?

        private var observers: [NSObjectProtocol] = []
        private var tokenTimer: Timer?
        private var lastSentVoipToken: String?
        private var lastSentOneSignalId: String?

        deinit {

            stopObservers()
        }

        func startObservers() {

            stopObservers()

            let center = NotificationCenter.default

            observers.append(
                center.addObserver(
                    forName: .mgboxVoipTokenUpdated,
                    object: nil,
                    queue: .main
                ) { [weak self] _ in

                    print(
                        "MGBOX ContentView received voip token update"
                    )

                    self?.sendNativeTokensToWebsite()
                }
            )

            observers.append(
                center.addObserver(
                    forName: .mgboxAnswerCall,
                    object: nil,
                    queue: .main
                ) { [weak self] notification in

                    self?.handleAnsweredCall(notification)
                }
            )

            observers.append(
                center.addObserver(
                    forName: .mgboxEndCall,
                    object: nil,
                    queue: .main
                ) { [weak self] notification in

                    self?.handleEndedCall(notification)
                }
            )

            tokenTimer = Timer.scheduledTimer(
                withTimeInterval: 5,
                repeats: true
            ) { [weak self] _ in

                self?.sendNativeTokensToWebsite()
            }
        }

        func stopObservers() {

            let center = NotificationCenter.default

            for observer in observers {
                center.removeObserver(observer)
            }

            observers.removeAll()
            tokenTimer?.invalidate()
            tokenTimer = nil
        }


        // ==================================================
        // MARK: Send VoIP + OneSignal tokens to website
        // Uses the WebView's logged-in MagicBox cookies.
        // ==================================================

        func sendNativeTokensToWebsite() {

            guard let webView else {
                return
            }

            let host =
                webView.url?.host?.lowercased() ?? ""

            guard host.contains("magicbox.mg") else {
                return
            }

            let voipToken =
                AppDelegate.voipToken ?? ""

            let oneSignalId =
                AppDelegate.oneSignalUserId ?? ""

            guard !voipToken.isEmpty || !oneSignalId.isEmpty else {
                return
            }

            if voipToken == lastSentVoipToken,
               oneSignalId == lastSentOneSignalId {

                return
            }

            let endpoint =
                WebView.voipTokenEndpointPath

            let js = """
            (function() {
                var voipToken = \(Self.jsString(voipToken));
                var oneSignalId = \(Self.jsString(oneSignalId));
                var endpoint = \(Self.jsString(endpoint));

                if (!voipToken && !oneSignalId) {
                    return "missing";
                }

                if (
                    (window.__mgboxVoipTokenSaved || "") === voipToken &&
                    (window.__mgboxOneSignalIdSaved || "") === oneSignalId
                ) {
                    return "already-saved";
                }

                if (window.__mgboxVoipTokenSending) {
                    return "in-flight";
                }

                window.MGBOX_VOIP_TOKEN = voipToken;
                window.MGBOX_ONESIGNAL_ID = oneSignalId;
                window.__mgboxVoipTokenSending = true;

                var body = [];

                if (voipToken) {
                    body.push(
                        "voip_token=" + encodeURIComponent(voipToken)
                    );
                }

                if (oneSignalId) {
                    body.push(
                        "onesignal_user_id=" + encodeURIComponent(oneSignalId)
                    );
                }

                fetch(endpoint, {
                    method: "POST",
                    credentials: "include",
                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                    body: body.join("&")
                }).then(function(response) {
                    return response.json();
                }).then(function(json) {
                    window.__mgboxVoipTokenSending = false;
                    if (json && json.success) {
                        window.__mgboxVoipTokenSaved = voipToken;
                        window.__mgboxOneSignalIdSaved = oneSignalId;
                        console.log("MGBOX token saved", json);
                    } else {
                        console.log("MGBOX token not saved yet", json);
                    }
                }).catch(function(error) {
                    window.__mgboxVoipTokenSending = false;
                    console.log("MGBOX token save error", error);
                });

                return "sent";
            })();
            """

            webView.evaluateJavaScript(js) { [weak self] result, error in

                if let error {

                    print(
                        "MGBOX token inject error: \(error.localizedDescription)"
                    )

                    return
                }

                let status =
                    result as? String ?? "unknown"

                print(
                    "MGBOX token inject status: \(status)"
                )

                // Only stop retrying after the website confirms the save.
                // "sent" just means the POST started; login may not exist yet.
                if status == "already-saved" {

                    self?.lastSentVoipToken = voipToken
                    self?.lastSentOneSignalId = oneSignalId
                }
            }
        }

        private static func jsString(
            _ value: String
        ) -> String {

            let escaped =
                value
                    .replacingOccurrences(of: "\\", with: "\\\\")
                    .replacingOccurrences(of: "\"", with: "\\\"")
                    .replacingOccurrences(of: "\n", with: "\\n")

            return "\"\(escaped)\""
        }


        // ==================================================
        // MARK: CallKit → WebView
        // ==================================================

        private func handleAnsweredCall(
            _ notification: Notification
        ) {

            guard let webView else {
                return
            }

            let userInfo =
                notification.userInfo ?? [:]

            let callURLString =
                userInfo["call_url"] as? String ?? ""

            let callID =
                userInfo["call_id"] as? String ?? ""

            let callType =
                userInfo["call_type"] as? String ?? "audio"

            print("================================")
            print("MGBOX WEBVIEW OPENING ANSWERED CALL")
            print("Call ID: \(callID)")
            print("Call type: \(callType)")
            print("Call URL: \(callURLString)")
            print("================================")

            if let callURL = URL(string: callURLString),
               !callURLString.isEmpty {

                webView.load(
                    URLRequest(url: callURL)
                )
            }
        }

        private func handleEndedCall(
            _ notification: Notification
        ) {

            let callID =
                notification.userInfo?["call_id"] as? String ?? ""

            print(
                "MGBOX WEBVIEW CALL ENDED: \(callID)"
            )

            let js = """
            (function() {
                try {
                    if (typeof window.mgboxNativeCallEnded === "function") {
                        window.mgboxNativeCallEnded(\(Self.jsString(callID)));
                    }
                    window.dispatchEvent(
                        new CustomEvent("mgbox-end-call", {
                            detail: { call_id: \(Self.jsString(callID)) }
                        })
                    );
                } catch (error) {
                    console.log("MGBOX end-call JS error", error);
                }
            })();
            """

            webView?.evaluateJavaScript(js, completionHandler: nil)
        }


        // ==================================================
        // MARK: WKNavigationDelegate
        // ==================================================

        func webView(
            _ webView: WKWebView,
            didFinish navigation: WKNavigation!
        ) {

            print(
                "MGBOX page loaded: \(webView.url?.absoluteString ?? "none")"
            )

            lastSentVoipToken = nil
            lastSentOneSignalId = nil
            sendNativeTokensToWebsite()
        }

        func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction,
            decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
        ) {

            guard let url = navigationAction.request.url else {

                decisionHandler(.allow)
                return
            }

            let scheme =
                url.scheme?.lowercased() ?? ""

            if scheme == "http" || scheme == "https" || scheme == "about" {

                decisionHandler(.allow)
                return
            }

            UIApplication.shared.open(url, options: [:], completionHandler: nil)
            decisionHandler(.cancel)
        }


        // ==================================================
        // MARK: WKUIDelegate
        // ==================================================

        func webView(
            _ webView: WKWebView,
            createWebViewWith configuration: WKWebViewConfiguration,
            for navigationAction: WKNavigationAction,
            windowFeatures: WKWindowFeatures
        ) -> WKWebView? {

            if navigationAction.targetFrame == nil,
               let url = navigationAction.request.url {

                webView.load(
                    URLRequest(url: url)
                )
            }

            return nil
        }

        func webView(
            _ webView: WKWebView,
            requestMediaCapturePermissionFor origin: WKSecurityOrigin,
            initiatedByFrame frame: WKFrameInfo,
            type: WKMediaCaptureType,
            decisionHandler: @escaping (WKPermissionDecision) -> Void
        ) {

            decisionHandler(.grant)
        }


        // ==================================================
        // MARK: JS → Native
        // ==================================================

        func userContentController(
            _ userContentController: WKUserContentController,
            didReceive message: WKScriptMessage
        ) {

            let appDelegate =
                UIApplication.shared.delegate as? AppDelegate

            switch message.name {

            case "mgboxToggleSpeaker":
                appDelegate?.toggleSpeaker()

            case "mgboxEndCall":
                appDelegate?.endCurrentCall()

            default:
                break
            }
        }
    }
}

#Preview {
    ContentView()
}
