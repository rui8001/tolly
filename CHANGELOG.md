# Changelog

本项目的重要变化记录在此文件中，版本号遵循 [Semantic Versioning](https://semver.org/)。

## [Unreleased]

### Added

- Windows 托盘应用、单实例控制、失焦隐藏和托盘定位。
- 统一的本地 Python 数据引擎，以及 18 个 AI 编程工具采集器。
- 今日、昨日、周、月、年和全部用量聚合，并支持模型、项目和每日趋势视图。
- PyInstaller sidecar 打包；发布后的最终用户无需安装 Python。
- 匿名 Web 预览、隐私扫描、Windows CI、NSIS/MSI 发布工作流。

### Security

- 项目名称在进入界面前会移除用户名、主目录片段和长标识符。
- 默认只读取本地数据；网络行为和数据边界记录在隐私说明中。

[Unreleased]: https://github.com/rui8001/tolly/commits/main
