---
name: ios-device-runner
description: Use when installing or launching an iOS app on a physical device from command line, or reproducing and verifying fixes on real hardware.
---

# ios-device-runner

## Overview

`scripts/run_on_device.sh` 用于真机 `install + launch`，支持：
- 自动定位工程目录（向上查找或用 `PROJECT_DIR` 指定）
- 自动发现并缓存最近设备（`last_device`）
- 自动识别可安装 App scheme（优先复用 `last_scheme`）
- 仅从 application target 提取 `APP_PATH` 和 `BUNDLE_ID`，避免多 target 误取

## When To Use

- 需要在真机安装并拉起 App。
- 需要复现只在真机出现的问题。
- 需要在多 scheme 工程里稳定运行指定 App target。

## Recommended Flow

先 build，再 run：

```bash
# 在 xcode-builder skill 目录
scripts/build.sh "<AppScheme>"
```

```bash
# 在 ios-device-runner skill 目录
scripts/run_on_device.sh "<AppScheme>" "<DeviceID>"
```

## Quick Start

自动选设备 + 自动选 scheme：

```bash
scripts/run_on_device.sh
```

指定 scheme：

```bash
scripts/run_on_device.sh "<AppScheme>"
```

指定 scheme + device：

```bash
scripts/run_on_device.sh "<AppScheme>" "<DeviceID>"
```

如果当前目录不在工程树下：

```bash
PROJECT_DIR="<project-dir>" scripts/run_on_device.sh "<AppScheme>" "<DeviceID>"
```

## Quick Reference

| 目标 | 命令 |
| --- | --- |
| 自动运行 | `scripts/run_on_device.sh` |
| 指定 Scheme | `scripts/run_on_device.sh "<AppScheme>"` |
| 指定设备 | `scripts/run_on_device.sh "<AppScheme>" "<DeviceID>"` |
| 指定工程目录 | `PROJECT_DIR="<project-dir>" scripts/run_on_device.sh "<AppScheme>" "<DeviceID>"` |
| 列设备 | `xcrun xctrace list devices` |
| 清理缓存 | `rm -f "$HOME/.build-cache/xcode-builder-skill.cache/last_{device,scheme}"` |

## Common Failures

- `Error: No physical iOS device found.`：
  - 设备未连接、未解锁或未信任
  - 处理：先 `xcrun xctrace list devices` 验证

- `Error: 无法获取 Build Settings`：
  - 常见于 DeviceID 无效、签名配置错误、scheme 不可用
  - 处理：先用 `xcodebuild -showBuildSettings` 单独验证

- `Error: Scheme '...' 未解析到可安装 App target`：
  - scheme 对应 extension/test，不是 application
  - 处理：切换到 App scheme

- `Error: App bundle not found at ...`：
  - 尚未为对应 scheme/destination 生成 `.app`
  - 处理：先执行 `xcode-builder` 构建
