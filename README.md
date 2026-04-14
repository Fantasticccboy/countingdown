# 倒计时（Flet 桌面版）

支持**多个相互独立的倒计时**：每项可填名称、**时/分/秒**（分、秒为 0–59），大号显示 **HH:MM:SS**；各自开始/暂停/继续/重置；至少保留一行，最多 20 个；空闲状态下可删除该行。桌面启动后主窗口会**尽量居中**（浏览器模式无效）。

**快捷时长**：每行有固定预设（5/10/15/25/30/45 分、1 时、90 分等）一键填入；另有 **「最近 HH:MM:SS」** 按钮，写入**全局**最近一次**成功点开始**的时长（保存在用户目录下 `~/.countdown_app/recents.json`，最多约 30 条，按总秒数去重）。

**桌面增强（非浏览器模式）**

- **系统通知**：倒计时结束时会尝试弹出 Toast（Windows 优先 `winotify`，否则 `plyer`）。若从未弹出，请在 Windows「设置 → 系统 → 通知」中允许本应用。
- **结束时的窗口**：有倒计时归零时会**临时置顶**并**前置窗口**，同时弹出结束对话框；点「确定」或关闭对话框后，**恢复**你在图钉里保存的置顶偏好（未开图钉则不再置顶）。
- **点击通知**：在 Windows 且 `winotify` 成功初始化时，通知正文可**点击**，用于重新显示并前置主窗口（依赖本机注册的 URL 协议，首次运行会写入注册表；打包 exe 时使用可执行文件路径）。
- **窗口位置**：移动或调整大小后约 0.35s 防抖写入 `~/.countdown_app/settings.json`；下次启动恢复；无记录时仍居中。
- **窗口置顶**：标题栏右侧 **图钉** 图标切换置顶，并写入设置。
- **关闭窗口**：点关闭时可选 **隐藏到托盘** 或 **退出应用**，并可勾选 **记住我的选择**；下次将直接按记忆执行。托盘菜单 **显示主窗口 / 退出**（在 **Windows** 等支持环境下显示托盘图标）。**托盘图标**会读取 **`assets/countdown.ico`**（或 `app.ico`），与窗口图标一致；打包时需带 `--add-data "assets;assets"`。**托盘图标左键单击**（pystray 的默认项）会唤起主窗口；右键仍可打开菜单。
- 新增依赖：`plyer`、`pystray`、`Pillow`；Windows 另需 `winotify`（见 `requirements.txt`）。

## 环境

- Python 3.11+（推荐 3.12/3.14）
- Windows（开发与打包目标）

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

若虚拟环境里没有 `pip`：

```powershell
python -m ensurepip --upgrade
```

## 运行

在仓库根目录：

```powershell
flet run src/countdown_app/main.py
```

或：

```powershell
python src/countdown_app/main.py
```

## 测试

```powershell
pytest tests/ -v
```

## 打包为 Windows 程序

`flet pack` 在 Windows 上对应 PyInstaller 的 **单文件（onefile）** 与 **目录（onedir）** 两种形态。**开发人员应先理解区别**，再选一种方式执行；给最终用户分发时，推荐优先 **单文件**（对方只拿一个 exe）。

### 开发人员须知：两种打包方式对比

| 方式 | `flet pack` 要点 | 产物位置 | 适合场景 | 备注 |
|------|------------------|----------|----------|------|
| **单文件 exe** | **不要**加 `--onedir`（默认 onefile） | **`dist\Countdown.exe`** 仅此一个文件 | **对外分发**、U 盘拷贝、只需发一个文件 | 首次启动会解压到临时目录，略慢；部分杀毒对单文件更敏感 |
| **目录模式** | 显式加 **`--onedir`** | **`dist\Countdown\`** 整个文件夹（含 `Countdown.exe`、`_internal` 等） | **本机反复调试**、需要直接查看 `_internal`、企业内网习惯「绿色文件夹」 | 启动通常更快；**必须整夹**拷贝，不能只拿 exe（见下「在无 Python 的电脑上运行」） |

**共同前提**（两种方式相同）：

- 在 **仓库根目录** 执行；已按上文「环境」安装依赖；建议先执行 `pip install pyinstaller`。
- 需要图标与 `assets` 资源时：使用 **`-i assets/countdown.ico`** 与 **`--add-data "assets;assets"`**（PowerShell 中分号需写在引号内）。
- 打包用电脑若从未缓存过 Flet 桌面，**首次打包**可能需要短暂联网；打好的 exe 在目标机一般可离线运行（见「不额外下载 Flet 桌面壳」）。

---

### 方式一：单文件 exe（推荐用于分发）

**目标**：只产生 **`dist\Countdown.exe`**，对方无需安装 Python。

```powershell
pip install pyinstaller

flet pack src/countdown_app/main.py `
  --name Countdown `
  -y `
  -i assets/countdown.ico `
  --add-data "assets;assets"
```

- 若暂无 `assets\countdown.ico`，可去掉 `-i assets/countdown.ico` 一行（窗口/exe 图标则使用默认）。
- **切勿**在本命令中加入 `--onedir`。

---

### 方式二：目录模式（`--onedir`，推荐用于开发调试）

**目标**：产生 **`dist\Countdown\`** 完整目录，便于排查依赖、对比 `_internal` 内容。

```powershell
pip install pyinstaller

flet pack src/countdown_app/main.py `
  --name Countdown `
  --onedir `
  -y `
  -i assets/countdown.ico `
  --add-data "assets;assets"
```

- 分发时必须拷贝 **整个 `Countdown` 文件夹**，不能只复制其中的 `Countdown.exe`。

---

### 不额外下载 Flet 桌面壳（离线、单文件均可）

`flet pack` 会把当前机已缓存的 Flet 桌面客户端打进包内（`flet_desktop/app/...`）。本应用在 **`import flet` 之前** 若检测到 PyInstaller 打包环境且包内存在 `flet.exe`，会自动设置 **`FLET_VIEW_PATH`** 指向该目录，**不再**在用户目录无缓存时去 GitHub 下载 `flet-windows.zip`。

因此：**正确使用 `flet pack` 生成的 exe** 分发到无网机器时，一般**不需要**再安装其他程序，也**不必**再下载 Flet 壳。  
（未打包、用 `python` 直接跑源码时，若本机无 `~/.flet/client` 缓存，仍可能首次下载，属开发环境正常行为。）

### 在无 Python 的电脑上运行（常见：提示找不到 `_internal` / `python314.dll`）

**仅适用于目录模式（`--onedir`）**：生成的是**一整包目录**，不是「只拿一个 exe」：

- **必须**把 **`dist\Countdown\` 整个文件夹**拷到目标电脑（或打成 zip 解压后保持结构不变），其中至少包含：
  - **`Countdown.exe`**
  - 与 exe **同级**的 **`_internal\`** 目录（内有 Python 运行时、`python314.dll` 等，版本号随你打包所用的 Python 变化）
- **不要**只复制 `Countdown.exe` 到别处而不带 `_internal`，否则启动时会按相对路径查找 `_internal\...`，从而报错。
- 若使用**快捷方式**，请将「起始位置」设为 **`Countdown.exe` 所在文件夹**。
- 杀毒软件可能隔离或删除 `_internal` 内文件，若异常请把该目录加入信任或恢复被删文件。
- 若目标机**完全无法访问外网**：请使用本仓库打包后的 exe（已内置 `FLET_VIEW_PATH` 逻辑，见上节「不额外下载 Flet 桌面壳」）。若仍失败，再查杀毒是否删改 `_internal` 或解压失败。

若你希望用**更稳妥的 Python 版本**再打包（例如 3.12 LTS），可在该版本下新建 venv 后执行 `flet pack`，以减小与极新 Python 版本相关的偶发问题。

**若你使用的是单文件 exe**：不应再出现「缺少同级 `_internal`」问题；若仍报错，多半是杀毒拦截解压；Flet 壳下载问题见上节（打包产物应已离线可用）。

### exe 与窗口左上角使用同一图标

左上角默认图标来自 Flet 自带的 `flet.exe` 内嵌资源；你的 `Countdown.exe` 由 PyInstaller 生成，**不会自动共用**那张图。若要一致：

1. 在 **`assets/`** 下放图标文件，二选一即可（优先使用前者）：**`countdown.ico`** 或 **`app.ico`**（多尺寸 `.ico` 更稳妥）。  
   - 可与当前 Flet 窗口图标接近：在本机打开  
     `%USERPROFILE%\.flet\client\` 下形如 `flet-desktop-full-0.84.0\flet\flet.exe`，用 [Resource Hacker](http://www.angusj.com/resourcehacker/) 等工具从中**导出图标**（注意 Flet 的许可与商标要求）；或直接使用你自己设计的图标。  
2. 开发运行：程序会自动检测上述文件并设置 `page.window.icon`（仅 Windows）。  
3. 打包时同时指定图标并打入资源目录（与上文 **方式一 / 方式二** 中的 `-i`、`--add-data` 写法一致）。**PowerShell 里 `--add-data` 的分号要加引号**；`-i` 与 `assets` 内文件名一致即可。

这样 **exe 文件图标**（`-i`）与 **窗口标题栏图标**（代码读取打包后的 `assets/*.ico`）一致。

### 打包后图标仍未变（资源管理器 / 任务栏）

1. **必须用 `flet pack ... -i ...` 完整打包**  
   不要单独运行 `pyinstaller Countdown.spec`。后者**不会**执行 Flet 对 **`flet.exe`** 的图标替换；而**任务栏、窗口**实际由随包分发的 `flet_desktop\app\flet\flet.exe` 负责，只有 `flet pack` 会在打包过程中打出 `Updating Flet View icon` 并改写该文件。  
   **资源管理器里的 `Countdown.exe`** 图标来自 PyInstaller 的 `-i`；若这里不对，检查 `-i` 路径、并删除 `dist\Countdown` 后重打。

2. **确认打包日志**  
   终端里应出现类似 `Updating Flet View icon` / `Copying icons from`。若没有，说明未带上 `-i` 或打包流程异常。

3. **Windows 图标缓存**  
   即使已嵌入新图标，系统仍可能显示旧图。可尝试：把 `Countdown.exe` **改名**再运行、取消任务栏固定后重新打开、或**注销/重启**后再看。

4. **程序内标题栏**  
   应用会在启动后再次设置 `page.window.icon`（使用打包目录内的 `assets\*.ico`）。若仍不对，确认 `--add-data "assets;assets"` 已带上，且 `_internal\assets\` 下存在 `countdown.ico`。

首次打包若提示缺少 PyInstaller：

```powershell
pip install pyinstaller
```

## 桌面客户端下载失败（ContentTooShortError）

首次运行桌面模式时，Flet 会从 GitHub 下载 `flet-windows.zip`（约几十 MB）。若报错 `retrieval incomplete` / `ContentTooShortError`，说明**下载被中断**，可按下面顺序处理：

1. **多试几次**：网络恢复后重新运行同一条启动命令。
2. **稳定访问 GitHub**：必要时使用可访问 GitHub 的网络或代理（公司网络常有限速/中断）。
3. **指定本地或镜像地址**（任选其一）  
   用浏览器下载完整包 [flet-windows.zip（v0.84.0 发行页）](https://github.com/flet-dev/flet/releases/download/v0.84.0/flet-windows.zip)，保存到本机后设置环境变量再运行（路径改成你的实际文件）：

   ```powershell
   $env:FLET_CLIENT_URL = "file:///C:/path/to/flet-windows.zip"
   python src/countdown_app/main.py
   ```

   `FLET_CLIENT_URL` 会替换默认的 GitHub 下载地址（见 `flet_desktop` 源码说明）。

4. **临时用浏览器跑界面（不调桌面壳）**：

   ```powershell
   $env:COUNTDOWN_FLET_WEB = "1"
   python src/countdown_app/main.py
   ```

   会在本机浏览器里打开页面，适合开发调试；正式桌面 exe 仍建议先解决 zip 下载问题。

5. **用 GitHub 文件加速前缀下载桌面客户端**（本仓库已支持自动拼接）  
   若你使用自建或第三方的「GitHub 发行文件加速」服务，在启动前设置**仅根 URL 前缀**即可，无需手写完整 `FLET_CLIENT_URL`。下例仅为格式占位，请换成你实际使用的镜像根地址（不要照抄示例域名）：

   ```powershell
   $env:FLET_GITHUB_PROXY = "https://example.com"
   python src/countdown_app/main.py
   ```

   也可用 `COUNTDOWN_GITHUB_PROXY`，二者等价（优先读 `FLET_GITHUB_PROXY`）。  
   若已设置完整的 `FLET_CLIENT_URL`，则**不会**再自动拼接。

   **说明**：当前自动拼接仅支持 **Windows / macOS** 的默认包名；Linux 包名与发行版相关，请自行设置整条 `FLET_CLIENT_URL`。

### HTTP 403（Forbidden）

很多镜像 / CDN 会拒绝 Python 默认的 `Python-urllib/x.x` **User-Agent**。本仓库在启动桌面模式前会自动把 `urllib.request.urlretrieve` 换成带 **Chrome UA** 的实现；一般可消除 403。

若仍 403，可尝试：

- 自定义 UA：`$env:FLET_DOWNLOAD_USER_AGENT = "你的浏览器里复制的 User-Agent"`
- 关闭补丁对比排查：`$env:FLET_SKIP_DOWNLOAD_UA_PATCH = "1"`（通常会更糟，仅作对比）
- 仍不行则换镜像或用浏览器下载 zip 后设 `FLET_CLIENT_URL` 为本地 `file:///...`（见上文）。
