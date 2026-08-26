# Tolly Windows desktop

This directory contains only the Vite UI, Tauri 2 shell, and release-sidecar build script. Collector code lives exclusively in `../tally-engine`.

```bash
pnpm install --frozen-lockfile
pnpm web:build      # Tauri 使用的常规 Web 构建
pnpm preview:build  # 生成可直接双击的 preview-dist/index.html
pnpm verify         # validates the live engine contract without writing it
pnpm tauri dev      # calls ../tally-engine through Python
pnpm build          # freezes the engine sidecar and builds NSIS/MSI installers
```

Windows 浏览器预览可从仓库根目录双击 `start-preview.cmd`。不要用通用静态服务器直接托管 `src/`；它无法解析前端模块依赖，页面会停在加载状态。若主脚本未启动，页面现在会显示明确的启动错误和正确入口。

Set `TALLY_PYTHON` when Python is not on PATH. A release build requires `pip install -e "../tally-engine[build]"`, Rust stable, and Visual Studio Build Tools with the C++ desktop workload.

Desktop failures are surfaced to the UI. Synthetic `src/sample_usage.json` is used only by browser preview and is never a production fallback.
