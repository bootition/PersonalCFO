# 外部工具二进制（不入 git）

本目录放三个 Windows 二进制。**它们不随仓库分发**（`.gitignore` 已排除），
需要自己下载 —— 下载后各许可证的分发与声明义务才不会落到你身上，详见 `THIRD-PARTY-NOTICES.md`。

一键获取：`powershell -File scripts/bootstrap.ps1`（会自动下载 + 校验大小 + 解压）。

| 工具 | 版本 | 放置路径 | 官方下载 |
|---|---|---|---|
| hledger | 1.52.3 | `tools/hledger-bin/hledger.exe` | https://github.com/plaintextaccounting/hledger/releases/download/1.52.3/hledger-windows-x64.zip |
| double-entry-generator | v2.15.1 | `tools/double-entry-generator.exe` | https://github.com/deb-sig/double-entry-generator/releases/download/v2.15.1/double-entry-generator_Windows_x86_64.tar.gz |
| Paisa（PersonalCFO fork） | v0.7.6 + 本项目改造 | `vendor/paisa/paisa.exe` | **见下** |

## paisa.exe 从哪来

界面不是上游 Paisa，而是本项目的 fork（中文化 + Wealthfolio 化 + 初始化向导 + CFO 工具）。
获取方式二选一：

1. **下载预编译（推荐）**：到 `PersonalCFO-paisa` 仓库的 Releases 页下载 `paisa.exe`，
   放到 `vendor\paisa\paisa.exe`。
   > 若该 Release 暂不可用，请用下面的自行构建。

2. **自行构建**（需要 Go 1.24+ 与 Node 20+）：
   ```powershell
   cd vendor\paisa
   npm ci
   npm run build          # 产出 web/static（注意：prebuild 会先清空产物，跨平台可用）
   go build -o paisa.exe .
   ```
   Windows 上首次构建建议设置国内代理：`$env:GOPROXY = "https://goproxy.cn,direct"`。

> `paisa-cli-windows-amd64.exe` 是**上游官方 CLI**，**不含**本 fork 的界面改造，
> 只能用于命令行场景，不能替代 UI。

## 其它

- 下载大文件断线时：`curl -sL -C - --retry 3 -o <file> <url>` 续传。
- `README.deg.md` / `README.deg.en.md` / `LICENSE` 是 double-entry-generator 官方发行包
  自带的文档与许可证（Apache-2.0），随仓库分发以满足其声明义务。
- `zoneinfo.zip` 是本项目自己生成的（Windows 无系统 tzdata，deg 解析时区需要；
  Go 的 zoneinfo 不支持 deflate，所以用 `ZIP_STORED` 打包）。重建脚本见 `scripts/gen-zoneinfo.py`。
- HTML→PDF 需要系统已安装 Edge 或 Chrome；程序会自动探测以下位置（不再硬编码单一 32 位路径）：
  - `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`
  - `C:\Program Files\Microsoft\Edge\Application\msedge.exe`
  - `C:\Program Files\Google\Chrome\Application\chrome.exe`
  - `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`
