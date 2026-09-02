# Changelog

本项目的重要变化记录在此文件中，版本号遵循 [Semantic Versioning](https://semver.org/)。

## [Unreleased]

### Added

- English project overview and a privacy-safe real-user testing guide, Issue form, and zero-based public results ledger.
- Codex for Open Source evidence ledger and a time-boxed public application-readiness roadmap.
- Reviewable upstream provenance record with the fixed Tokei revision and identical pricing-data hash.
- Windows release-install smoke workflow that downloads the tagged MSI, verifies its checksum, checks the bundled sidecar, launches with Python removed from `PATH`, and uninstalls on a clean runner.

## [1.2.0] - 2026-09-02

### Added

- 豆包工作从本地 SDK 日志统计可验证的对话调用次数，并明确区分调用、Token 与积分口径。

### Changed

- 余额进度条改为四档渐变：充足时沿用工具主色，低于 50%、30%、10% 后依次变为黄、橙、红。
- 项目页跟随当前所选周期，只显示该周期有用量的项目，并按真实工作目录合并 Codex、千问办公和 WorkBuddy 记录。

### Fixed

- 修复 Codex 日期目录被误识别成项目，以及项目页固定展示全部历史数据的问题。
- 修复零成本项目的用量占比条无法显示的问题。

## [1.1.0] - 2026-08-28

### Added

- 显示服务商明确提供的周余额或剩余积分；支持 Codex 通用 7 天额度与千问办公可选本机额度查询。
- 新增千问办公本地对话 Token 估算、WorkBuddy 今日积分消耗和豆包工作可靠性检测。

### Changed

- 卡片右上区域用于余额或今日积分消耗，缓存命中统一为中文“命中”，统计图标跟随各工具品牌色。
- 设置页改为卡片显示、刷新频率和隐私额度开关，不再允许手工填写预算或余额。

### Fixed

- 托盘面板会按当前显示器工作区和 DPI 留出安全边距，不再越过屏幕右侧或任务栏。
- Windows 桌面窗口与页面内容统一使用 8px 裁剪圆角，消除透明窗口边缘的圆角错位。
- 修复紧凑窗口内容超出后无法向下滚动的问题。
- Codex 额度改为读取设置页同源的账户“通用使用限额”；严格忽略 Spark 等模型专属额度，并按窗口时长识别周额度。
- 修正 Codex 缓存 Token 被重复计入输入、成本和命中率分母的问题；过期通用额度不再回退为模型专属额度。
- 千问办公和豆包工作改为仅在当前周期存在实际用量时显示，不再因仅检测到本地数据而常驻。
- 将原生白色滚动条替换为融入深色界面的细滚动条。

## [1.0.0] - 2026-08-26

### Added

- Windows 托盘应用、单实例控制、失焦隐藏和托盘定位。
- 统一的本地 Python 数据引擎，以及 18 个 AI 编程工具采集器。
- 今日、昨日、周、月、年和全部用量聚合，并支持模型、项目和每日趋势视图。
- PyInstaller sidecar 打包；发布后的最终用户无需安装 Python。
- 匿名 Web 预览、隐私扫描、Windows CI、NSIS/MSI 发布工作流。

### Security

- 项目名称在进入界面前会移除用户名、主目录片段和长标识符。
- 默认只读取本地数据；网络行为和数据边界记录在隐私说明中。

[Unreleased]: https://github.com/rui8001/tolly/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/rui8001/tolly/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/rui8001/tolly/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/rui8001/tolly/releases/tag/v1.0.0
