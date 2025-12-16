# ATS Configuration for Development

**Issue Found:** ✅
Project uses `GENERATE_INFOPLIST_FILE = YES` - автогенерируемый Info.plist игнорирует наш файл!

---

## Solution 1: Manual Xcode Configuration (Fastest)

### Step 1: Disable Auto-Generated Info.plist

**In Xcode:**
1. Select **PulsePlate** project (blue icon)
2. Select **PulsePlate** target
3. **Build Settings** → Search for "Generate Info.plist"
4. Set `Generate Info.plist File` to **NO**

### Step 2: Point to Custom Info.plist

**Same Build Settings:**
1. Search for "Info.plist File"
2. Set `Info.plist File` to: `PulsePlate/Info.plist`

### Step 3: Verify ATS Settings

**Info.plist should contain:**
```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsLocalNetworking</key>
    <true/>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

---

## Solution 2: Add ATS to Build Settings (Alternative)

If you prefer keeping auto-generation:

**In Xcode:**
1. Target → Build Settings → "+" button → Add User-Defined Setting
2. Name: `INFOPLIST_KEY_NSAppTransportSecurity`
3. Value (for Debug config only):
```
<dict><key>NSAllowsLocalNetworking</key><true/><key>NSAllowsArbitraryLoads</key><true/></dict>
```

---

## Solution 3: Configuration-Specific (Production-Safe)

**Best practice for production:**

### Debug.xcconfig:
```
// Allow HTTP for local development
INFOPLIST_KEY_NSAppTransportSecurity[sdk=iphonesimulator*] = <dict><key>NSAllowsLocalNetworking</key><true/><key>NSAllowsArbitraryLoads</key><true/></dict>
INFOPLIST_KEY_NSAppTransportSecurity[sdk=iphoneos*] = <dict><key>NSAllowsLocalNetworking</key><true/><key>NSAllowsArbitraryLoads</key><true/></dict>
```

### Release.xcconfig:
```
// Production: restrict to specific domains
INFOPLIST_KEY_NSAppTransportSecurity = <dict><key>NSExceptionDomains</key><dict><key>api.pulseplate.com</key><dict><key>NSExceptionAllowsInsecureHTTPLoads</key><false/></dict></dict></dict>
```

---

## Quick Runtime Test (No Backend Needed)

Add to DebugToolsScreen to see exact error:

```swift
Section("Network Test") {
    Button("Test Backend Connection") {
        Task {
            do {
                let url = URL(string: "\(AppConfig.baseURL())/docs")!
                let (_, response) = try await URLSession.shared.data(from: url)
                if let http = response as? HTTPURLResponse {
                    print("✅ Connected: \(http.statusCode)")
                }
            } catch let error as NSError {
                print("❌ Error: \(error.localizedDescription)")
                // Look for "App Transport Security"
            }
        }
    }
}
```

**Expected errors:**
- ❌ `App Transport Security has blocked...` → ATS NOT configured
- ✅ `connection refused` / `offline` → ATS working, backend not running

---

## Recommended: Solution 1 (Manual Config)

**Why:**
- Full control over Info.plist
- Easy to add other keys later (permissions, etc.)
- Clear separation from auto-generated values

**Steps:**
1. Xcode → Target → Build Settings
2. `Generate Info.plist File` → **NO**
3. `Info.plist File` → **PulsePlate/Info.plist**
4. Clean Build Folder (⇧⌘K)
5. Build (⌘B)

---

## Verification Checklist

After applying Solution 1:

1. ✅ Build succeeds
2. ✅ Run app → Debug tab visible
3. ✅ Tap Shopping List → Check error message:
   - "connection refused" = ATS OK, backend needed
   - "App Transport Security" = ATS NOT applied
4. ✅ Start backend → should see list

---

## Current Status

- ✅ Info.plist created with ATS settings
- ⚠️ `GENERATE_INFOPLIST_FILE = YES` ignoring it
- 🔧 Need to apply Solution 1 in Xcode

**Next:** Apply Solution 1, then test!
