#!/bin/bash

set -euo pipefail

SCHEME="${1:-}"
CONFIGURATION="${CONFIGURATION:-Debug}"
CACHE_DIR="${HOME}/.build-cache/xcode-builder-skill.cache"
DEVICE_CACHE="${CACHE_DIR}/last_device"
SCHEME_CACHE="${CACHE_DIR}/last_scheme"
SCHEME_META_CACHE="${CACHE_DIR}/last_scheme_meta"
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

# 校验缓存的设备 ID 是否仍可用
validate_device_id() {
    local device_id="$1"
    [ -n "$device_id" ] && xcrun xctrace list devices 2>/dev/null | grep -q "$device_id"
}

# 读取设备缓存
resolve_cached_device() {
    local cached_id=""

    if [ -f "$DEVICE_CACHE" ]; then
        cached_id="$(cat "$DEVICE_CACHE" 2>/dev/null || true)"
        if validate_device_id "$cached_id"; then
            echo "$cached_id"
            return 0
        fi
    fi

    return 1
}

# 自动探测 workspace/project，优先 workspace
detect_container_args() {
    WORKSPACE="$(find . -maxdepth 1 -name "*.xcworkspace" | head -n 1)"
    PROJECT="$(find . -maxdepth 1 -name "*.xcodeproj" | head -n 1)"

    if [ -n "$WORKSPACE" ]; then
        CONTAINER_ARGS=(-workspace "$WORKSPACE")
        CONTAINER_REF="$WORKSPACE"
        return 0
    fi

    if [ -n "$PROJECT" ]; then
        CONTAINER_ARGS=(-project "$PROJECT")
        CONTAINER_REF="$PROJECT"
        return 0
    fi

    echo "Error: 未找到 .xcworkspace 或 .xcodeproj。"
    exit 1
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

scheme_has_installable_app_target() {
    local candidate="$1"
    local build_settings=""
    build_settings="$(
        xcodebuild "${CONTAINER_ARGS[@]}" -scheme "$candidate" -configuration "$CONFIGURATION" -destination "generic/platform=iOS" -showBuildSettings 2>/dev/null || true
    )"

    [ -n "$build_settings" ] || return 1
    extract_app_target_settings "$build_settings" >/dev/null 2>&1
}

# 自动探测可编译 app scheme（过滤常见测试/Pods scheme）
detect_scheme_if_needed() {
    local list_output=""
    local candidate=""
    local cached_scheme=""
    local preferred_scheme=""
    local cached_meta=""

    if [ -n "$SCHEME" ]; then
        if ! scheme_has_installable_app_target "$SCHEME"; then
            echo "Error: Scheme '$SCHEME' 未解析到 application target（PRODUCT_TYPE=com.apple.product-type.application）。"
            exit 1
        fi
        return 0
    fi

    preferred_scheme="$(preferred_scheme_from_container || true)"
    if [ -n "$preferred_scheme" ] && scheme_has_installable_app_target "$preferred_scheme"; then
        SCHEME="$preferred_scheme"
        echo "Using preferred scheme: $SCHEME"
        return 0
    fi

    if [ -f "$SCHEME_CACHE" ]; then
        cached_scheme="$(cat "$SCHEME_CACHE" 2>/dev/null || true)"
        cached_meta="$(cat "$SCHEME_META_CACHE" 2>/dev/null || true)"
        if [ -n "$cached_scheme" ] && [ "$cached_meta" = "$SCHEME_CONTEXT_KEY" ] && scheme_has_installable_app_target "$cached_scheme"; then
            SCHEME="$cached_scheme"
            echo "Cache Hit: 使用上次成功的 Scheme: $SCHEME"
            return 0
        fi
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
        echo "Error: 无法自动识别可安装 App 的 Scheme，请手动传入 App Scheme，例如: scripts/build.sh <AppScheme>"
        exit 1
    fi
}

# 计算源码快照指纹（mtime+size+path）
calculate_source_fingerprint() {
    local file_meta=""
    file_meta="$(
        find . \
            \( -name "*.xcodeproj" -o -name "*.xcworkspace" -o -name "Podfile.lock" -o -name "Package.resolved" -o -name "Package.swift" \
            -o -name "*.swift" -o -name "*.h" -o -name "*.m" -o -name "*.mm" -o -name "*.cpp" -o -name "*.c" \
            -o -name "*.storyboard" -o -name "*.xib" -o -name "*.plist" -o -name "*.xcconfig" \) \
            -not -path "*/.*" -not -path "*/build/*" -not -path "*/DerivedData/*" \
            -print0 | xargs -0 stat -f "%N|%m|%z" 2>/dev/null || true
    )"

    printf "%s\n" "$file_meta" | sort | shasum -a 256 | awk '{print $1}'
}

# 读取产物目录用于跳过构建判断
resolve_app_path() {
    local build_settings=""
    local app_info=""

    build_settings="$(
        xcodebuild "${CONTAINER_ARGS[@]}" -scheme "$SCHEME" -configuration "$CONFIGURATION" -destination "$DESTINATION" -showBuildSettings 2>/dev/null || true
    )"
    [ -n "$build_settings" ] || return 1

    app_info="$(extract_app_target_settings "$build_settings" 2>/dev/null || true)"
    [ -n "$app_info" ] || return 1

    awk -F'=' '$1=="APP_PATH" { print $2; exit }' <<< "$app_info"
}

# 尝试准备 xcbeautify，不可用时回退原生日志
prepare_xcbeautify() {
    if command -v xcbeautify >/dev/null 2>&1; then
        USE_XCBEAUTIFY=1
        return 0
    fi

    if command -v brew >/dev/null 2>&1; then
        echo "xcbeautify 未安装，尝试通过 Homebrew 安装..."
        if brew install xcbeautify >/dev/null 2>&1; then
            USE_XCBEAUTIFY=1
            return 0
        fi
        echo "Warning: xcbeautify 安装失败，回退到原生 xcodebuild 输出。"
    else
        echo "Warning: 未检测到 Homebrew，回退到原生 xcodebuild 输出。"
    fi

    USE_XCBEAUTIFY=0
}

PROJECT_DIR_RESOLVED="$(resolve_project_dir || true)"
if [ -z "$PROJECT_DIR_RESOLVED" ]; then
    echo "Error: 未定位到 Xcode 工程目录。可通过 PROJECT_DIR 指定。"
    exit 1
fi
cd "$PROJECT_DIR_RESOLVED"

detect_container_args
SCHEME_CONTEXT_KEY="$(printf "%s|%s\n" "$(pwd)" "$CONTAINER_REF" | shasum -a 256 | awk '{print $1}')"
detect_scheme_if_needed

DESTINATION="generic/platform=iOS"
if CACHED_ID="$(resolve_cached_device)"; then
    DESTINATION="platform=iOS,id=${CACHED_ID}"
fi

SOURCE_FINGERPRINT="$(calculate_source_fingerprint)"
CONTEXT_FINGERPRINT="$(
    {
        echo "pwd=$(pwd)"
        echo "container=${CONTAINER_REF}"
        echo "scheme=${SCHEME}"
        echo "configuration=${CONFIGURATION}"
        echo "destination=${DESTINATION}"
        echo "xcode=$(xcodebuild -version | tr '\n' ' ')"
    } | shasum -a 256 | awk '{print $1}'
)"
CURRENT_HASH="$(printf "%s|%s\n" "$SOURCE_FINGERPRINT" "$CONTEXT_FINGERPRINT" | shasum -a 256 | awk '{print $1}')"

BUILD_KEY="$(printf "%s|%s|%s|%s|%s\n" "$(pwd)" "${CONTAINER_REF}" "${SCHEME}" "${CONFIGURATION}" "${DESTINATION}" | shasum -a 256 | awk '{print $1}')"
HASH_FILE="${CACHE_DIR}/xcode_builder_${BUILD_KEY}.hash"

OLD_HASH=""
[ -f "$HASH_FILE" ] && OLD_HASH="$(cat "$HASH_FILE")"

if [ "$CURRENT_HASH" = "$OLD_HASH" ]; then
    APP_PATH="$(resolve_app_path || true)"
    if [ -n "$APP_PATH" ] && [ -d "$APP_PATH" ] && [[ "$APP_PATH" == *.app ]]; then
        write_scheme_cache
        echo "Cache Hit: 跳过构建。Scheme=${SCHEME}, Destination=${DESTINATION}"
        exit 0
    fi
fi

prepare_xcbeautify

echo "开始构建: Scheme=${SCHEME}, Configuration=${CONFIGURATION}, Destination=${DESTINATION}"
if [ "$USE_XCBEAUTIFY" -eq 1 ]; then
    if xcodebuild "${CONTAINER_ARGS[@]}" -scheme "$SCHEME" -configuration "$CONFIGURATION" -destination "$DESTINATION" build | xcbeautify --quieter; then
        echo "$CURRENT_HASH" > "$HASH_FILE"
        write_scheme_cache
        echo "Build successful."
    else
        echo "Build failed."
        exit 1
    fi
else
    if xcodebuild "${CONTAINER_ARGS[@]}" -scheme "$SCHEME" -configuration "$CONFIGURATION" -destination "$DESTINATION" build; then
        echo "$CURRENT_HASH" > "$HASH_FILE"
        write_scheme_cache
        echo "Build successful."
    else
        echo "Build failed."
        exit 1
    fi
fi
