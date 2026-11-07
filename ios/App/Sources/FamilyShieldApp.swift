import SwiftUI
import UIKit

@main
struct FamilyShieldApp: App {
    @UIApplicationDelegateAdaptor(PushAppDelegate.self) private var push
    @State private var model = AppModel()

    var body: some Scene {
        WindowGroup {
            RootView(model: model)
        }
    }
}
