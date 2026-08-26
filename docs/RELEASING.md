# 发布流程

Tolly 使用语义化版本。正式发布由 `vX.Y.Z` 标签触发，GitHub Actions 会在干净的 Windows runner 中测试、构建 NSIS/MSI，并随 Release 上传 `SHA256SUMS.txt`。

## 1. 准备版本

1. 完成 `docs/RELEASE_CHECKLIST.md`，尤其是干净 Windows 环境中的安装、升级、卸载和托盘行为测试。
2. 同步修改以下版本号：
   - `tally-win/package.json`
   - `tally-win/src-tauri/tauri.conf.json`
   - `tally-win/src-tauri/Cargo.toml`
   - `tally-engine/pyproject.toml`
3. 运行 `cargo check --manifest-path tally-win/src-tauri/Cargo.toml` 更新并验证 `Cargo.lock`。
4. 将 `CHANGELOG.md` 的 Unreleased 内容整理到带发布日期的版本小节。
5. 运行完整检查：

```powershell
node scripts/check-version.mjs
node scripts/check-privacy.mjs
cd tally-engine
python -m unittest discover -s tests -v
cd ../tally-win
pnpm install --frozen-lockfile
pnpm check
cargo fmt --manifest-path src-tauri/Cargo.toml -- --check
cargo check --manifest-path src-tauri/Cargo.toml
```

## 2. 创建发布

先把发布提交合并到 `main`，并确认该提交的 CI 全部通过。然后从同一提交创建并推送标签：

```powershell
git tag -a v0.1.0 -m "Tolly v0.1.0"
git push origin v0.1.0
```

工作流会拒绝与源码版本号不一致的标签。成功后，检查 Release 中是否只有 NSIS、MSI 和 SHA-256 校验和文件，并在一台未安装 Python 的干净 Windows 10/11 环境复验下载产物。

## 3. 签名与升级

`SHA256SUMS.txt` 用于校验下载完整性，不能替代 Windows Authenticode 签名。配置可信代码签名证书之前，安装包会显示发布者未知；不要把自动更新器开放给用户。签名、更新公钥和回滚策略准备完成后，再把自动升级作为独立功能发布。

发现已发布版本有问题时，保留原标签和产物以便审计，修复后发布新的补丁版本，不覆盖已有版本。
