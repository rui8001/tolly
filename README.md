# Tolly for Windows

[![CI](https://github.com/rui8001/tolly/actions/workflows/ci.yml/badge.svg)](https://github.com/rui8001/tolly/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Tolly 是一个本地优先的 Windows 系统托盘应用，用来汇总 AI 编程工具写入本机的 Token 用量，并按公开 API 价格估算成本。

项目受到 macOS 开源项目 [Tokei](https://github.com/cclank/tokei) 的产品方向启发。部分本地日志采集规则和价格映射依据其 MIT 实现重构；Windows 外壳、界面资源和交互实现使用独立名称并重新设计。Tolly 不是 Tokei 的官方 Windows 版本，也不代表任何模型或工具服务商。

## 当前能力

- 支持 18 个 AI 编程工具的 JSONL / SQLite 本地日志采集。
- 今日、昨日、本周、上周、本月、本年与全部用量。
- 按模型、项目、每日趋势与年度回顾聚合。
- Windows 托盘弹窗：单实例、失焦隐藏、托盘定位、手动/定时刷新。
- 本地设置与自定义周预算；不会把估算预算展示成服务商真实配额。
- 发布包使用 PyInstaller sidecar，最终用户不需要安装 Python。

成本只是按价格表计算的估值，不是账单、订阅余额或服务商配额。

## 目录

```text
tally-engine/   唯一的 Python 数据引擎与测试
tally-win/      Vite 前端与 Tauri 2 Windows 外壳
docs/           架构、隐私与发布检查清单
```

Windows 目录不再保存引擎副本。开发模式调用 `../tally-engine`，发布模式调用随安装包分发的 `tally-engine` sidecar，因此采集规则只有一份源码。

## 开发

前置条件：Python 3.10+、Node.js 20+、pnpm 11、Rust stable，以及带“使用 C++ 的桌面开发”组件的 Visual Studio Build Tools。

```powershell
# 引擎
cd tally-engine
python -m unittest discover -s tests -v
python -m engine --json

# Web 预览（只读匿名样例）
cd ../tally-win
pnpm install --frozen-lockfile
pnpm dev

# 或生成可直接双击打开的单文件预览
pnpm preview:build
# 打开 tally-win/preview-dist/index.html

# 桌面开发
$env:TALLY_PYTHON = "C:\path\to\python.exe" # Python 不在 PATH 时
pnpm tauri dev
```

在 Windows 上也可以直接双击仓库根目录的 `start-preview.cmd`。它只会调用项目本地安装的 Vite，并固定使用 `127.0.0.1:1420`；如果端口被旧进程占用会明确报错，不会悄悄显示旧页面。不要用通用静态服务器直接托管 `tally-win/src`，因为源码中的模块依赖需要由 Vite 解析。

依赖安装完成后，双击仓库根目录的 `start-desktop-dev.cmd` 可启动读取本机真实日志的 Tauri 开发版。脚本会先检查 MSVC、Node.js、Rust、Python 和前端依赖，缺项时给出明确提示。

发布构建还需要安装引擎构建依赖：

```powershell
python -m pip install -e "./tally-engine[build]"
cd tally-win
pnpm build
```

`pnpm build` 会先构建 Vite 前端和 PyInstaller sidecar，再由 Tauri 生成 NSIS/MSI 安装包。

成功后可在 `tally-win/src-tauri/target/release/bundle/nsis/` 和 `bundle/msi/` 找到安装包。安装包内置冻结后的数据引擎，最终用户不需要安装 Python。带 `v*` 的 Git 标签会触发 GitHub Actions 构建并上传版本化安装包，可用于手动覆盖升级；签名自动更新器将在仓库地址、签名公钥和回滚策略确定后再启用。

## 隐私

默认采集、聚合和设置保存均在本机完成。只有显式运行 `python -m engine update-prices` 或主动开启 Grok 实时配额功能时才会发起网络请求。详情见 [隐私说明](docs/PRIVACY.md)。

仓库中的 `sample_usage.json` 是人工编写的匿名数据。`scripts/check-privacy.mjs` 和 CI 会阻止常见个人主目录路径混入数据文件。

## 开源与归属

本项目代码采用 [MIT License](LICENSE)。第三方组件、上游参考关系和归属说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。维护者发布版本前应完成 [发布检查清单](docs/RELEASE_CHECKLIST.md)。

版本变化记录见 [CHANGELOG.md](CHANGELOG.md)，维护者发布流程见 [docs/RELEASING.md](docs/RELEASING.md)。欢迎通过 [CONTRIBUTING.md](CONTRIBUTING.md) 参与，安全与隐私问题请按 [SECURITY.md](SECURITY.md) 私下报告。
