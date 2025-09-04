#!/usr/bin/env bash
set -euo pipefail

# iOS branding helper for macOS/Xcode projects.
# - Updates CFBundleDisplayName and CFBundleName in Info.plist
# - Creates/updates localized InfoPlist.strings with CFBundleDisplayName
# - Optionally updates Capacitor appName in capacitor.config.ts/json
#
# Usage:
#   scripts/ios_branding_update.sh \
#     --app-name "PulsePlate" \
#     [--bundle-id "com.yourco.pulseplate"] \
#     [--ios-root "ios/App/App"] \
#     [--locales "Base,en,ru"]

IOS_ROOT="ios/App/App"
APP_NAME=""
BUNDLE_ID=""
LOCALES="Base,en,ru"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ios-root)
      IOS_ROOT="$2"; shift 2 ;;
    --app-name)
      APP_NAME="$2"; shift 2 ;;
    --bundle-id)
      BUNDLE_ID="$2"; shift 2 ;;
    --locales)
      LOCALES="$2"; shift 2 ;;
    -h|--help)
      cat <<EOF
Usage: $0 --app-name "PulsePlate" [--bundle-id com.yourco.pulseplate] [--ios-root ios/App/App] [--locales Base,en,ru]
EOF
      exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$APP_NAME" ]]; then
  echo "--app-name is required" >&2
  exit 1
fi

PLIST="$IOS_ROOT/Info.plist"
if [[ ! -f "$PLIST" ]]; then
  echo "Info.plist not found at: $PLIST" >&2
  echo "Adjust --ios-root to match your Xcode target folder (e.g., ios/App/App)." >&2
  exit 1
fi

if ! command -v /usr/libexec/PlistBuddy >/dev/null 2>&1; then
  echo "PlistBuddy not available (macOS tool expected)." >&2
  exit 1
fi

echo "Updating CFBundleDisplayName and CFBundleName in $PLIST ..."
set +e
/usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName $APP_NAME" "$PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string $APP_NAME" "$PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleName $APP_NAME" "$PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleName string $APP_NAME" "$PLIST"
set -e

IFS=',' read -r -a LOC_ARR <<< "$LOCALES"
for loc in "${LOC_ARR[@]}"; do
  DIR="$IOS_ROOT/$loc.lproj"
  FILE="$DIR/InfoPlist.strings"
  mkdir -p "$DIR"
  if [[ ! -f "$FILE" ]]; then
    echo "Creating $FILE"
    cat > "$FILE" <<EOF
/* Localized app display name */
CFBundleDisplayName = "$APP_NAME";
EOF
  else
    # Update or append the key
    if grep -q "CFBundleDisplayName" "$FILE"; then
      # simple in-place replacement
      sed -i '' -E "s#CFBundleDisplayName\s*=\s*\".*\";#CFBundleDisplayName = \"$APP_NAME\";#" "$FILE"
    else
      echo "CFBundleDisplayName = \"$APP_NAME\";" >> "$FILE"
    fi
  fi
done

if [[ -n "$BUNDLE_ID" ]]; then
  echo "Note: Bundle Identifier typically set within Xcode project settings."
  echo "Set it in: TARGETS → Signing & Capabilities → Bundle Identifier → $BUNDLE_ID"
fi

# Optional: update Capacitor config if present
if [[ -f capacitor.config.ts ]]; then
  echo "Updating capacitor.config.ts appName ..."
  sed -i '' -E "s#appName:\s*'[^']*'#appName: '$APP_NAME'#" capacitor.config.ts || true
  sed -i '' -E "s#appName:\s*\"[^\"]*\"#appName: \"$APP_NAME\"#" capacitor.config.ts || true
fi
if [[ -f capacitor.config.json ]]; then
  echo "Updating capacitor.config.json appName ..."
  # Try to update appName key while preserving JSON structure
  python3 - <<PY || true
import json,sys
fn='capacitor.config.json'
data=json.load(open(fn))
data['appName'] = '$APP_NAME'
json.dump(data, open(fn,'w'), indent=2, ensure_ascii=False)
print('Updated appName in capacitor.config.json')
PY
fi

echo "Done. Next steps:"
echo "- In Xcode: rename Target & Scheme to $APP_NAME, update Product Name (Packaging)."
echo "- If using Capacitor: run 'npx cap sync ios' to sync config."
echo "- Build (⌘B) and run (⌘R) to verify Springboard label."

