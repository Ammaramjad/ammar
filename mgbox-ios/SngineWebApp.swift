import SwiftUI
import OneSignalFramework
import PushKit
import CallKit
import AVFoundation
import UserNotifications

@main
struct SngineWebApp: App {

    @UIApplicationDelegateAdaptor(AppDelegate.self)
    var appDelegate

    var body: some Scene {

        WindowGroup {

            ContentView()
        }
    }
}


extension Notification.Name {

    static let mgboxAnswerCall =
        Notification.Name("mgboxAnswerCall")

    static let mgboxEndCall =
        Notification.Name("mgboxEndCall")

    static let mgboxVoipTokenUpdated =
        Notification.Name("mgboxVoipTokenUpdated")
}


// ======================================================
// MARK: - APP DELEGATE
// ======================================================

class AppDelegate:
    NSObject,
    UIApplicationDelegate,
    PKPushRegistryDelegate,
    CXProviderDelegate {


    // ==================================================
    // MARK: Missed Call Notification
    // ==================================================

    private func showMissedCallNotification() {

        let content =
            UNMutableNotificationContent()

        content.title =
            "Missed Call"

        content.body =
            "Missed call from \(currentCallerName ?? "MGBOX User")"

        content.sound =
            .default


        let request =
            UNNotificationRequest(
                identifier:
                    "mgbox-missed-\(UUID().uuidString)",
                content:
                    content,
                trigger:
                    nil
            )


        UNUserNotificationCenter
            .current()
            .add(request) { error in

                if let error {

                    print(
                        "Missed call notification error: \(error.localizedDescription)"
                    )

                } else {

                    print(
                        "MGBOX missed call notification created"
                    )
                }
            }
    }


    // ==================================================
    // MARK: OneSignal Normal Push Notifications
    // ==================================================

    static let oneSignalAppId =
        "becdaedf-2113-40e9-a884-006765233cbe"

    static var oneSignalUserId: String?
    static var voipToken: String?


    // ==================================================
    // MARK: PushKit / CallKit
    // ==================================================

    private var voipRegistry: PKPushRegistry?

    private var currentCallUUID: UUID?
    private var currentCallURL: String?
    private var currentCallType: String?
    private var currentCallerName: String?
    private var currentCallID: String?

    // Tracks whether incoming call was actually answered
    private var currentCallWasAnswered = false
    private var speakerEnabled = false


    // ==================================================
    // MARK: CallKit Provider
    // ==================================================

    lazy var callProvider: CXProvider = {

        let configuration =
            CXProviderConfiguration(
                localizedName: "MGBOX"
            )

        configuration.supportsVideo = true

        configuration.maximumCallsPerCallGroup = 1
        configuration.maximumCallGroups = 1

        // If later you add a ringtone file:
        //
        // configuration.ringtoneSound = "MGBOXRingtone.caf"

        let provider =
            CXProvider(configuration: configuration)

        provider.setDelegate(
            self,
            queue: .main
        )

        return provider
    }()


    // ==================================================
    // MARK: App Launch
    // ==================================================

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions:
        [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {

        print("================================")
        print("MGBOX APPLICATION STARTED")
        print("================================")

        // ==================================================
        // ONESIGNAL NORMAL NOTIFICATIONS
        // ==================================================

        setupOneSignal(
            launchOptions: launchOptions
        )

        // ==================================================
        // PUSHKIT VOIP
        // ==================================================

        setupPushKit()

        // ==================================================
        // INITIALIZE CALLKIT
        // ==================================================

        _ = callProvider

        return true
    }


    // ==================================================
    // MARK: OneSignal Setup
    // ==================================================

    private func setupOneSignal(
        launchOptions:
        [UIApplication.LaunchOptionsKey: Any]?
    ) {

        OneSignal.Debug.setLogLevel(.LL_VERBOSE)

        OneSignal.initialize(
            AppDelegate.oneSignalAppId,
            withLaunchOptions: launchOptions
        )

        OneSignal.Notifications.requestPermission(
            { accepted in

                print("================================")
                print(
                    "Notification permission: \(accepted)"
                )

                DispatchQueue.main.asyncAfter(
                    deadline: .now() + 3
                ) {

                    let subscription =
                        OneSignal.User.pushSubscription

                    print("OneSignal Subscription ID:")

                    print(
                        subscription.id ??
                        "NO SUBSCRIPTION ID"
                    )

                    print("Normal APNs Push Token:")

                    print(
                        subscription.token ??
                        "NO PUSH TOKEN"
                    )

                    print("Opted In:")

                    print(subscription.optedIn)

                    AppDelegate.oneSignalUserId =
                        subscription.id

                    print("================================")
                }

            },
            fallbackToSettings: true
        )
    }


    // ==================================================
    // MARK: PushKit Setup
    // ==================================================

    private func setupPushKit() {

        print("Starting PushKit registration...")

        let registry =
            PKPushRegistry(queue: .main)

        registry.delegate = self

        registry.desiredPushTypes = [
            .voIP
        ]

        voipRegistry = registry
    }


    // ==================================================
    // MARK: Receive VoIP Token
    // ==================================================

    func pushRegistry(
        _ registry: PKPushRegistry,
        didUpdate pushCredentials: PKPushCredentials,
        for type: PKPushType
    ) {

        guard type == .voIP else {
            return
        }

        let token =
            pushCredentials.token
                .map {
                    String(
                        format: "%02x",
                        $0
                    )
                }
                .joined()


        // Save PushKit token so WebView can send it
        // to the logged-in MagicBox session.
        AppDelegate.voipToken =
            token


        print("")
        print("================================")
        print("MGBOX VOIP TOKEN:")
        print(token)
        print("================================")
        print("")

        print(
            "MGBOX VOIP TOKEN SAVED IN APPDELEGATE"
        )

        NotificationCenter.default.post(
            name: .mgboxVoipTokenUpdated,
            object: nil,
            userInfo: [
                "voip_token": token
            ]
        )
    }


    // ==================================================
    // MARK: VoIP Token Invalidated
    // ==================================================

    func pushRegistry(
        _ registry: PKPushRegistry,
        didInvalidatePushTokenFor type: PKPushType
    ) {

        guard type == .voIP else {
            return
        }

        print("================================")
        print("MGBOX VOIP TOKEN INVALIDATED")
        print("================================")

        AppDelegate.voipToken = nil

        /*
          Later tell the Sngine server to remove
          the old VoIP token.
        */
    }


    // ==================================================
    // MARK: Incoming VoIP Push
    // ==================================================

    func pushRegistry(
        _ registry: PKPushRegistry,
        didReceiveIncomingPushWith payload:
        PKPushPayload,
        for type: PKPushType,
        completion: @escaping () -> Void
    ) {

        guard type == .voIP else {

            completion()

            return
        }

        print("")
        print("================================")
        print("INCOMING MGBOX VOIP PUSH")
        print(payload.dictionaryPayload)
        print("================================")
        print("")

        let root = payload.dictionaryPayload

        var data: [AnyHashable: Any] = root

        // OneSignal wraps custom VoIP data inside:
        // custom -> a
        if let custom = root["custom"] as? [AnyHashable: Any],
           let additionalData = custom["a"] as? [AnyHashable: Any] {

            data = additionalData

        } else if let custom = root["custom"] as? [String: Any],
                  let additionalData = custom["a"] as? [String: Any] {

            data = Dictionary(
                uniqueKeysWithValues:
                    additionalData.map { (AnyHashable($0.key), $0.value) }
            )
        }

        // ==================================================
        // Read incoming call information
        // ==================================================

        let callerName =
            data["caller_name"] as? String
            ?? "MGBOX User"

        let callType =
            data["call_type"] as? String
            ?? "audio"

        let callURL =
            data["call_url"] as? String

        let callID =
            data["call_id"] as? String

        let uuidString =
            data["call_uuid"] as? String

        // ==================================================
        // Create Call UUID
        // ==================================================

        let callUUID: UUID

        if let uuidString,
           let uuid = UUID(
                uuidString: uuidString
           ) {

            callUUID = uuid

        } else {

            callUUID = UUID()
        }

        // ==================================================
        // Save current call
        // ==================================================

        currentCallUUID =
            callUUID

        currentCallURL =
            callURL

        currentCallType =
            callType.lowercased()

        currentCallerName =
            callerName

        currentCallID =
            callID

        // New incoming call has not been answered yet
        currentCallWasAnswered = false

        // ==================================================
        // CallKit update
        // ==================================================

        let update =
            CXCallUpdate()

        update.remoteHandle =
            CXHandle(
                type: .generic,
                value: callerName
            )

        update.localizedCallerName =
            callerName

        update.hasVideo =
            callType.lowercased()
            == "video"

        update.supportsHolding = false

        update.supportsGrouping = false

        update.supportsUngrouping = false

        update.supportsDTMF = false

        // ==================================================
        // IMPORTANT:
        // Report incoming VoIP call immediately
        // ==================================================

        callProvider.reportNewIncomingCall(
            with: callUUID,
            update: update
        ) { [weak self] error in

            if let error {

                print(
                    "CallKit incoming call error:"
                )

                print(
                    error.localizedDescription
                )

                self?.clearCurrentCall()

            } else {

                print(
                    "================================"
                )

                print(
                    "\(callType.uppercased()) CALL DISPLAYED"
                )

                print(
                    "Caller: \(callerName)"
                )

                print(
                    "UUID: \(callUUID.uuidString)"
                )

                print(
                    "================================"
                )
            }

            completion()
        }
    }


    // ==================================================
    // MARK: Answer Call
    // ==================================================

    func provider(
        _ provider: CXProvider,
        perform action: CXAnswerCallAction
    ) {

        currentCallWasAnswered = true

        print("==============================")
        print("MGBOX CALL ANSWERED")
        print("Call ID: \(currentCallID ?? "none")")
        print("Call type: \(currentCallType ?? "audio")")
        print("Call URL: \(currentCallURL ?? "none")")
        print("==============================")

        let session = AVAudioSession.sharedInstance()

        do {

            try session.setCategory(
                .playAndRecord,
                mode: .voiceChat,
                options: [
                    .allowBluetoothHFP
                ]
            )

            // Do not use loudspeaker by default
            try session.overrideOutputAudioPort(.none)

            speakerEnabled = false

            print("MGBOX answer route prepared for receiver/Bluetooth")
            printCurrentAudioRoute()

        } catch {

            print(
                "MGBOX answer audio configuration error: \(error.localizedDescription)"
            )
        }

        NotificationCenter.default.post(
            name: .mgboxAnswerCall,
            object: nil,
            userInfo: [
                "call_id": currentCallID ?? "",
                "call_url": currentCallURL ?? "",
                "call_type": currentCallType ?? "audio"
            ]
        )

        action.fulfill()
    }


    // ==================================================
    // MARK: End / Decline Call
    // ==================================================

    func provider(
        _ provider: CXProvider,
        perform action: CXEndCallAction
    ) {

        print("==============================")
        print("MGBOX CALL ENDED")
        print("Call ID: \(currentCallID ?? "none")")
        print("Answered: \(currentCallWasAnswered)")
        print("==============================")

        // If the incoming call was never answered,
        // create a persistent missed-call notification.
        if !currentCallWasAnswered {

            showMissedCallNotification()

            print(
                "MGBOX MISSED CALL NOTIFICATION CREATED"
            )
        }

        NotificationCenter.default.post(
            name: .mgboxEndCall,
            object: nil,
            userInfo: [
                "call_id": currentCallID ?? ""
            ]
        )

        currentCallUUID = nil
        currentCallURL = nil
        currentCallID = nil
        currentCallType = nil
        currentCallerName = nil

        currentCallWasAnswered = false
        speakerEnabled = false

        action.fulfill()
    }


    // ==================================================
    // MARK: CallKit Audio Activated
    // ==================================================

    func provider(
        _ provider: CXProvider,
        didActivate audioSession: AVAudioSession
    ) {

        print("================================")
        print("MGBOX CALLKIT AUDIO ACTIVATED")
        print("================================")

        do {

            try audioSession.setCategory(
                .playAndRecord,
                mode: .voiceChat,
                options: [
                    .allowBluetoothHFP
                ]
            )

            // IMPORTANT:
            // Incoming calls must NOT start on loudspeaker.
            try audioSession.overrideOutputAudioPort(.none)

            try audioSession.setActive(true)

            // Keep internal speaker state synchronized
            speakerEnabled = false

            print("MGBOX call audio active")
            print("MGBOX default output = receiver/Bluetooth")

            printCurrentAudioRoute()

        } catch {

            print(
                "Audio activation error: \(error.localizedDescription)"
            )
        }
    }


    // ==================================================
    // MARK: CallKit Audio Deactivated
    // ==================================================

    func provider(
        _ provider: CXProvider,
        didDeactivate audioSession: AVAudioSession
    ) {

        print("CallKit audio session deactivated")

        do {

            try audioSession.setActive(
                false,
                options: .notifyOthersOnDeactivation
            )

        } catch {

            print(
                "Audio deactivation error: \(error.localizedDescription)"
            )
        }
    }


    // ==================================================
    // MARK: CallKit Provider Reset
    // ==================================================

    func providerDidReset(
        _ provider: CXProvider
    ) {

        print(
            "CallKit provider RESET"
        )

        clearCurrentCall()
    }


    // ==================================================
    // MARK: Configure VoIP Audio
    // ==================================================

    private func configureCallAudioSession() {

        let audioSession =
            AVAudioSession.sharedInstance()

        do {

            try audioSession.setCategory(
                .playAndRecord,
                mode: .voiceChat,
                options: [
                    .allowBluetoothHFP
                ]
            )

            print(
                "MGBOX call audio session configured"
            )

            printCurrentAudioRoute()

        } catch {

            print(
                "Audio configuration error:"
            )

            print(
                error.localizedDescription
            )
        }
    }


    // ==================================================
    // MARK: Speaker ON
    // ==================================================

    func enableSpeaker() {

        let session =
            AVAudioSession.sharedInstance()

        do {

            try session.overrideOutputAudioPort(
                .speaker
            )

            speakerEnabled = true

            print(
                "================================"
            )

            print(
                "MGBOX SPEAKER ON"
            )

            print(
                "================================"
            )

            printCurrentAudioRoute()

        } catch {

            print(
                "Speaker ON error:"
            )

            print(
                error.localizedDescription
            )
        }
    }


    // ==================================================
    // MARK: Speaker OFF
    // ==================================================

    func disableSpeaker() {

        let session =
            AVAudioSession.sharedInstance()

        do {

            try session.overrideOutputAudioPort(
                .none
            )

            speakerEnabled = false

            print(
                "================================"
            )

            print(
                "MGBOX SPEAKER OFF"
            )

            print(
                "Receiver/Bluetooth automatic routing"
            )

            print(
                "================================"
            )

            printCurrentAudioRoute()

        } catch {

            print(
                "Speaker OFF error:"
            )

            print(
                error.localizedDescription
            )
        }
    }


    // ==================================================
    // MARK: Toggle Speaker
    // ==================================================

    func toggleSpeaker() {

        if speakerEnabled {

            disableSpeaker()

        } else {

            enableSpeaker()
        }
    }


    // ==================================================
    // MARK: Print Current Audio Route
    // ==================================================

    private func printCurrentAudioRoute() {

        let session =
            AVAudioSession.sharedInstance()

        print("")
        print("================================")
        print("CURRENT MGBOX AUDIO ROUTE")
        print("================================")

        for input in session.currentRoute.inputs {

            print("INPUT:")
            print(
                "\(input.portName) - \(input.portType.rawValue)"
            )
        }

        for output in session.currentRoute.outputs {

            print("OUTPUT:")
            print(
                "\(output.portName) - \(output.portType.rawValue)"
            )

            if output.portType == .builtInSpeaker {

                print("🔊 ROUTE = LOUDSPEAKER")

            } else if output.portType == .builtInReceiver {

                print("📞 ROUTE = EARPIECE / RECEIVER")

            } else if output.portType == .bluetoothHFP {

                print("🎧 ROUTE = BLUETOOTH")

            } else {

                print(
                    "ROUTE = \(output.portType.rawValue)"
                )
            }
        }

        print(
            "SYSTEM OUTPUT VOLUME: \(session.outputVolume)"
        )

        print("================================")
        print("")
    }


    // ==================================================
    // MARK: Clear Current Call
    // ==================================================

    private func clearCurrentCall() {

        currentCallUUID = nil
        currentCallURL = nil
        currentCallType = nil
        currentCallerName = nil
        currentCallID = nil
        currentCallWasAnswered = false
        speakerEnabled = false
    }


    // ==================================================
    // MARK: Remote Call Ended
    // ==================================================

    func remoteCallEnded() {

        guard let uuid = currentCallUUID else {

            print(
                "MGBOX: no active CallKit call to end"
            )

            return
        }

        // Save this BEFORE clearing current call
        let wasAnswered = currentCallWasAnswered
        let callerName = currentCallerName ?? "MGBOX User"

        print("")
        print("================================")
        print("MGBOX REMOTE CALL ENDED")
        print("Call ID: \(currentCallID ?? "none")")
        print("Caller: \(callerName)")
        print("Answered: \(wasAnswered)")
        print("================================")
        print("")

        // Tell CallKit that the OTHER side ended/cancelled the call
        callProvider.reportCall(
            with: uuid,
            endedAt: Date(),
            reason: .remoteEnded
        )

        // If the iPhone user never answered,
        // leave a missed-call notification
        if !wasAnswered {

            showMissedCallNotification()

            print(
                "MGBOX MISSED CALL NOTIFICATION CREATED"
            )
        }

        // Release all native call state
        clearCurrentCall()
    }


    // ==================================================
    // MARK: Programmatically End Current Call
    // ==================================================

    func endCurrentCall() {

        guard let uuid =
            currentCallUUID else {

            print(
                "No active MGBOX call"
            )

            return
        }

        print("")
        print("================================")
        print("MGBOX REQUESTING LOCAL CALL END")
        print("Call ID: \(currentCallID ?? "none")")
        print("UUID: \(uuid.uuidString)")
        print("================================")
        print("")

        let endAction =
            CXEndCallAction(
                call: uuid
            )

        let transaction =
            CXTransaction(
                action: endAction
            )

        let controller =
            CXCallController()

        controller.request(
            transaction
        ) { error in

            if let error {

                print(
                    "Unable to end call:"
                )

                print(
                    error.localizedDescription
                )

            } else {

                print(
                    "MGBOX call end requested"
                )
            }
        }
    }
}
