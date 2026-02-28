#!/bin/bash

# Usage: ./run_on_device.sh [Scheme] [DeviceID]

set -euo pipefail

SCHEME="${1:-}"
DEVICE_ID="${2:-}"

CACHE_DIR="${HOME}/.build-cache/xcode-builder-skill.cache"
DEVICE_CACHE="$CACHE_DIR/last_device"
SCHEME_CACHE="$CACHE_DIR/last_scheme"
SCHEME_META_CACHE="$CACHE_DIR/last_scheme_meta"
mkdir -p "$CACHE_DIR"

has_xcode_container() {
    local dir="$1"
    find "$dir" -maxdepth 1 \( -name "*.xcworkspace" -o -name "*.xcodeproj" \) | grep -q .
}

resolve_project_dir() {
    local candidate=""

    if [ -n "${PROJECT_DIR:-}" ]; then
        candidate="$PROJECT_DIR"
        if [ ! -d "$candidate" ]; then
            echo "Error: PROJECT_DIR 不存在: $candidate"
            exit 1
        fi
        if has_xcode_container "$candidate"; then
            printf "%s\n" "$candidate"
            return 0
        fi
        echo "Error: PROJECT_DIR 下未找到 .xcworkspace 或 .xcodeproj: $candidate"
        exit 1
    fi

    candidate="$PWD"
    while [ "$candidate" != "/" ]; do
        if has_xcode_container "$candidate"; then
            printf "%s\n" "$candidate"
            return 0
        fi
        candidate="$(dirname "$candidate")"
    done

    candidate="$(git rev-parse --show-toplevel 2>/dev/null || true)"
    if [ -n "$candidate" ] && has_xcode_container "$candidate"; then
        printf "%s\n" "$candidate"
        return 0
    fi

    return 1
}

extract_schemes_from_list() {
    local list_output="$1"
    awk '
        /Schemes:/ { in_schemes=1; next }
        in_schemes && /^[[:space:]]*$/ { exit }
        in_schemes {
            gsub(/^[[:space:]]+/, "", $0)
            if (length($0) > 0) print $0
        }
    ' <<< "$list_output"
}

extract_app_target_settings() {
    local build_settings="$1"
    awk '
        function trim(s) {
            gsub(/^[ \t]+|[ \t]+$/, "", s)
            return s
        }
        function emit_if_app() {
            is_app = (product_type == "com.apple.product-type.application")
            if (!is_app && product_type == "" && wrapper_extension == "app") {
                is_app = 1
            }
            if (in_target && is_app) {
                print "APP_PATH=" app_path
                print "BUNDLE_ID=" bundle_id
                print "WRAPPER_EXTENSION=" wrapper_extension
                emitted = 1
                exit 0
            }
        }
        BEGIN {
            in_target = 0
            emitted = 0
            product_type = ""
            wrapper_extension = ""
            app_path = ""
            bundle_id = ""
        }
        /^Build settings for action .* and target / {
            emit_if_app()
            in_target = 1
            product_type = ""
            wrapper_extension = ""
            app_path = ""
            bundle_id = ""
            next
        }
        !in_target { next }
        /^[[:space:]]*PRODUCT_TYPE = / {
            value = $0
            sub(/^[^=]*=/, "", value)
            product_type = trim(value)
            next
        }
        /^[[:space:]]*WRAPPER_EXTENSION = / {
            value = $0
            sub(/^[^=]*=/, "", value)
            wrapper_extension = trim(value)
            next
        }
        /^[[:space:]]*CODESIGNING_FOLDER_PATH = / {
            value = $0
            sub(/^[^=]*=/, "", value)
            app_path = trim(value)
            next
        }
        /^[[:space:]]*PRODUCT_BUNDLE_IDENTIFIER = / {
            value = $0
            sub(/^[^=]*=/, "", value)
            bundle_id = trim(value)
            next
        }
        END {
            emit_if_app()
            if (!emitted) exit 1
        }
    ' <<< "$build_settings"
}

preferred_scheme_from_container() {
    if [ -n "${WORKSPACE:-}" ]; then
        basename "$WORKSPACE" .xcworkspace
        return 0
    fi
    if [ -n "${PROJECT:-}" ]; then
        basename "$PROJECT" .xcodeproj
        return 0
    fi
    return 1
}

write_scheme_cache() {
    echo "$SCHEME" > "$SCHEME_CACHE"
    echo "$SCHEME_CONTEXT_KEY" > "$SCHEME_META_CACHE"
}

scheme_has_installable_app_target() {
    local candidate="$1"
    local build_settings=""
    build_settings="$(
        xcodebuild "${CONTAINER_ARGS[@]}" -scheme "$candidate" -destination "generic/platform=iOS" -showBuildSettings 2>/dev/null || true
    )"

    [ -n "$build_settings" ] || return 1
    extract_app_target_settings "$build_settings" >/dev/null 2>&1
}

validate_device_id() {
    local device_id="$1"
    [ -n "$device_id" ] && xcrun xctrace list devices 2>/dev/null | grep -q "$device_id"
}

extract_first_connected_device_id() {
    local devices="$1"
    awk '
        index($0, "Simulator") > 0 { next }
        {
            if (match($0, /[0-9A-F]{8}-[0-9A-F]{16}/)) {
                print substr($0, RSTART, RLENGTH)
                exit
            }
            if (match($0, /[0-9a-fA-F]{40}/)) {
                print substr($0, RSTART, RLENGTH)
                exit
            }
        }
    ' <<< "$devices"
}

detect_scheme_if_needed() {
    local list_output=""
    local candidate=""
    local cached_scheme=""
    local cached_meta=""
    local preferred_scheme=""

    if [ -n "$SCHEME" ]; then
        if ! scheme_has_installable_app_target "$SCHEME"; then
            echo "Error: Scheme '$SCHEME' 未解析到 application target（PRODUCT_TYPE=com.apple.product-type.application）。"
            exit 1
        fi
        return 0
    fi

    if [ -f "$SCHEME_CACHE" ]; then
        cached_scheme="$(cat "$SCHEME_CACHE" 2>/dev/null || true)"
        cached_meta="$(cat "$SCHEME_META_CACHE" 2>/dev/null || true)"
        if [ -n "$cached_scheme" ] && [ "$cached_meta" = "$SCHEME_CONTEXT_KEY" ] && scheme_has_installable_app_target "$cached_scheme"; then
            SCHEME="$cached_scheme"
            echo "Cache Hit: Using last scheme $SCHEME"
            return 0
        fi
    fi

    preferred_scheme="$(preferred_scheme_from_container || true)"
    if [ -n "$preferred_scheme" ] && scheme_has_installable_app_target "$preferred_scheme"; then
        SCHEME="$preferred_scheme"
        echo "Using preferred scheme: $SCHEME"
        return 0
    fi

    list_output="$(xcodebuild "${CONTAINER_ARGS[@]}" -list 2>/dev/null || true)"
    while IFS= read -r candidate; do
        [ -z "$candidate" ] && continue
        if [ "$candidate" = "Pods" ] || [ "${candidate#Pods-}" != "$candidate" ]; then
            continue
        fi
        if [[ "$candidate" == *"Tests" ]] || [[ "$candidate" == *"UITests" ]] || [[ "$candidate" == *" UI Tests" ]]; then
            continue
        fi

        if scheme_has_installable_app_target "$candidate"; then
            SCHEME="$candidate"
            break
        fi
    done < <(extract_schemes_from_list "$list_output")

    if [ -z "$SCHEME" ]; then
        echo "Error: 无法自动识别可安装 App 的 Scheme，请手动传入 App Scheme。"
        exit 1
    fi
}

PROJECT_DIR_RESOLVED="$(resolve_project_dir || true)"
if [ -z "$PROJECT_DIR_RESOLVED" ]; then
    echo "Error: 未定位到 Xcode 工程目录。可通过 PROJECT_DIR 指定。"
    exit 1
fi
cd "$PROJECT_DIR_RESOLVED"

# 1. Handle Device ID with Caching
if [ -z "$DEVICE_ID" ] && [ -f "$DEVICE_CACHE" ]; then
    CACHED_ID="$(cat "$DEVICE_CACHE" 2>/dev/null || true)"
    if validate_device_id "$CACHED_ID"; then
        DEVICE_ID="$CACHED_ID"
        echo "Cache Hit: Using last connected device $DEVICE_ID"
    fi
fi

if [ -z "$DEVICE_ID" ]; then
    echo "Searching for connected iOS devices..."
    DEVICES="$(xcrun xctrace list devices 2>/dev/null || true)"
    DEVICE_ID="$(extract_first_connected_device_id "$DEVICES")"

    if [ -n "$DEVICE_ID" ]; then
        echo "$DEVICE_ID" > "$DEVICE_CACHE"
    else
        echo "Error: No physical iOS device found."
        exit 1
    fi
fi

# 2. Handle Scheme and Workspace
WORKSPACE="$(find . -maxdepth 1 -name "*.xcworkspace" | head -n 1)"
PROJECT="$(find . -maxdepth 1 -name "*.xcodeproj" | head -n 1)"

CONTAINER_ARGS=()
if [ -n "$WORKSPACE" ]; then
    CONTAINER_ARGS=(-workspace "$WORKSPACE")
elif [ -n "$PROJECT" ]; then
    CONTAINER_ARGS=(-project "$PROJECT")
else
    echo "Error: 未找到 .xcworkspace 或 .xcodeproj。"
    exit 1
fi
SCHEME_CONTEXT_KEY="$(printf "%s|%s\n" "$(pwd)" "${WORKSPACE:-$PROJECT}" | shasum -a 256 | awk '{print $1}')"

detect_scheme_if_needed
write_scheme_cache
echo "$DEVICE_ID" > "$DEVICE_CACHE"

XCODE_ARGS=("${CONTAINER_ARGS[@]}" -scheme "$SCHEME" -destination "platform=iOS,id=$DEVICE_ID")

echo "Targeting Device: $DEVICE_ID, Scheme: $SCHEME"
echo "Locating build products..."

if ! BUILD_SETTINGS="$(xcodebuild "${XCODE_ARGS[@]}" -showBuildSettings 2>&1)"; then
    echo "Error: 无法获取 Build Settings。请检查 DeviceID、Scheme、签名配置。"
    echo "$BUILD_SETTINGS"
    exit 1
fi

if ! APP_INFO="$(extract_app_target_settings "$BUILD_SETTINGS" 2>/dev/null)"; then
    echo "Error: Scheme '$SCHEME' 未解析到可安装 App target。"
    exit 1
fi

APP_PATH=""
BUNDLE_ID=""
WRAPPER_EXTENSION=""
while IFS='=' read -r key value; do
    case "$key" in
        APP_PATH) APP_PATH="$value" ;;
        BUNDLE_ID) BUNDLE_ID="$value" ;;
        WRAPPER_EXTENSION) WRAPPER_EXTENSION="$value" ;;
    esac
done <<< "$APP_INFO"

if [ "$WRAPPER_EXTENSION" != "app" ] || [[ "$APP_PATH" != *.app ]]; then
    echo "Error: Scheme '$SCHEME' 不是可安装 App 目标（WRAPPER_EXTENSION=$WRAPPER_EXTENSION, APP_PATH=$APP_PATH）。"
    exit 1
fi

if [ -z "$BUNDLE_ID" ] || [ "$BUNDLE_ID" = "NO" ]; then
    echo "Error: 无法解析 PRODUCT_BUNDLE_IDENTIFIER（当前值: '$BUNDLE_ID'）。"
    exit 1
fi

if [ ! -d "$APP_PATH" ]; then
    echo "Error: App bundle not found at $APP_PATH"
    echo "Diagnostic: Ensure you built with the same workspace/scheme/destination."
    exit 1
fi

# 3. Install and Launch
echo "Installing $BUNDLE_ID to device..."
if ! xcrun devicectl device install app --device "$DEVICE_ID" "$APP_PATH"; then
    echo "Installation failed."
    exit 1
fi

echo "Launching $BUNDLE_ID..."
xcrun devicectl device process launch --device "$DEVICE_ID" "$BUNDLE_ID"
