import UIKit
import React
import React_RCTAppDelegate

@main
class AppDelegate: RCTAppDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
  ) -> Bool {
    self.moduleName = "MyNewslettersApp"
    self.initialProps = [:]
    
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  override func sourceURL(for bridge: RCTBridge) -> URL? {
    return self.bundleURL()
  }

  override func bundleURL() -> URL? {
#if DEBUG
    return RCTBundleURLProvider.sharedSettings().jsBundleURL(forBundleRoot: "index")
#else
    return Bundle.main.url(forResource: "main", withExtension: "jsbundle")
#endif
  }
  
  // Handle OAuth redirect when app is already running
  override func application(
    _ app: UIApplication,
    open url: URL,
    options: [UIApplication.OpenURLOptionsKey : Any] = [:]
  ) -> Bool {
    print("AppDelegate: Received URL redirect: \(url.absoluteString)")
    
    // Check if this is our OAuth redirect
    if url.scheme == "myletters" {
      print("AppDelegate: Processing myletters:// redirect")
      // Pass to React Native's Linking module
      if let rootViewController = self.window.rootViewController {
        print("AppDelegate: Sending URL to React Native Linking")
        RCTLinkingManager.application(app, open: url, options: options)
      }
      return true
    }
    
    // Let parent class handle other URLs
    return super.application(app, open: url, options: options)
  }
  
  // Handle OAuth redirect when app launches from URL
  override func application(
    _ application: UIApplication,
    continue userActivity: NSUserActivity,
    restorationHandler: @escaping ([UIUserActivityRestoring]?) -> Void
  ) -> Bool {
    print("AppDelegate: Received userActivity with type: \(userActivity.activityType)")
    
    if userActivity.activityType == NSUserActivityTypeBrowsingWeb,
       let url = userActivity.webpageURL {
      print("AppDelegate: Processing web activity URL: \(url.absoluteString)")
      
      // Check if this is our OAuth redirect
      if url.scheme == "myletters" {
        print("AppDelegate: Handling myletters:// from userActivity")
        RCTLinkingManager.application(application, continue: userActivity, restorationHandler: restorationHandler)
        return true
      }
    }
    
    return super.application(application, continue: userActivity, restorationHandler: restorationHandler)
  }
}
