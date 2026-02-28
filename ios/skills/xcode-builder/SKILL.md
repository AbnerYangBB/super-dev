---
name: xcode-builder
description: Use when compiling Xcode projects, diagnosing xcodebuild failures, or validating that a scheme resolves to an installable iOS app target.
---

# xcode-builder

## Overview

`scripts/build.sh` 是通用 iOS 构建入口，支持：
- 自动定位工程目录（向上查找或用 `PROJECT_DIR` 指定）
- 自动识别 `.xcworkspace/.xcodeproj`（优先 workspace）
- 自动筛选可安装 App scheme（基于 `PRODUCT_TYPE=com.apple.product-type.application`）
- 复用构建缓存与设备缓存（`$HOME/.build-cache/xcode-builder-skill.cache`）
- 成功构建后写入 `last_scheme`，供 `ios-device-runner` 复用

## When To Use

- 需要快速验证某次改动是否仍可编译。
- 需要命令行定位 `xcodebuild` 的 scheme/container 配置问题。
- 需要让后续真机运行流程复用同一 scheme。

## Quick Start

在 skill 目录执行：

```bash
scripts/build.sh
```

指定 scheme：

```bash
scripts/build.sh "<AppScheme>"
```

指定 configuration：

```bash
CONFIGURATION=Release scripts/build.sh "<AppScheme>"
```

若当前目录不在工程树下，传入工程目录：

```bash
PROJECT_DIR="<project-dir>" scripts/build.sh "<AppScheme>"
```

## Quick Reference

| 目标 | 命令 |
| --- | --- |
| 默认构建 | `scripts/build.sh` |
| 指定 Scheme | `scripts/build.sh "<AppScheme>"` |
| Release 构建 | `CONFIGURATION=Release scripts/build.sh "<AppScheme>"` |
| 指定工程目录 | `PROJECT_DIR="<project-dir>" scripts/build.sh "<AppScheme>"` |
| 查看可用 Scheme | `xcodebuild -list -workspace <YourWorkspace>.xcworkspace` |
| 清理 scheme 缓存 | `rm -f "$HOME/.build-cache/xcode-builder-skill.cache/last_scheme"` |

## Success Criteria

以下之一均视为任务执行成功:

1. 成功编译
2. 命中了编译缓存(说明代码变动未影响构建结果)

## Common Failures

- `Error: 未定位到 Xcode 工程目录`：
  - 当前目录不在工程树内，且未设置 `PROJECT_DIR`
  - 处理：设置 `PROJECT_DIR` 指向包含 `.xcworkspace/.xcodeproj` 的目录

- `Error: Scheme '...' 未解析到 application target`：
  - 传入了 extension/test scheme，非可安装 App
  - 处理：传入 App scheme，或先 `xcodebuild -list` 确认

- `workspace ... does not contain a scheme named ...`：
  - scheme 名称错误或 container 选错
  - 处理：核对 workspace/project 与 scheme 名称
