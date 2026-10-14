# 安装与使用

## 1. 选择系统安装包

下载对应 ZIP 并与同一 Release 的 SHA256SUMS 对照。Windows 可用 Get-FileHash -Algorithm SHA256；macOS 可用 shasum -a 256。解压后应得到一个含 SKILL.md、scripts/、references/ 的文件夹。

把整个文件夹放入你所用 Agent 客户端支持的 Skill 目录，并按该客户端要求刷新/加载。不同客户端的路径与自动发现规则不同；不要把此包当作微信插件、OBS 插件或独立桌面 App。包里没有安装程序。

## 2. 准备环境

共同需要 Python 3.10+、FFmpeg 和 ffprobe；工具可以在 PATH，也可以通过 --ffmpeg 和 --ffprobe 指定可执行文件绝对路径。Windows 常用 python，Mac 常用 python3。

下载模式另外依赖 ltaoo/wx_channels_download v260907。自行从该项目官方发布渠道选择正确 CPU/系统包，核对其校验和并阅读许可与安装说明。其配置可能涉及证书和代理，因此本 Skill 不自动安装或更改这些设置。若当前系统阻止运行，先停止并报告；不要关闭系统保护。上游依赖不是本仓库的成品保证。

确认本地 API 监听在 127.0.0.1:2022（可改为其他回环端口），当前微信内容可访问。不要把未认证 API 开到公网。Skill 仅接受数值回环地址，禁用环境 HTTP 代理并拒绝 API 重定向。

进入 Skill 目录后：

    python scripts/download.py --url "https://weixin.qq.com/sph/REPLACE_WITH_REAL_LINK" --out-dir "C:/VideoOutput"

Mac 示例：

    python3 scripts/download.py --url "https://weixin.qq.com/sph/REPLACE_WITH_REAL_LINK" --out-dir "$HOME/Movies/Channels"

成功创建后先输出 task_id，再输出经核验的文件。默认仅轮询 600 秒；解析/创建各有 20 秒请求上限，媒体探测 30 秒，完整解码 600 秒。超时不会删除或取消上游任务。随后可用 --resume-id TASK_ID 代替 --url，配合同一输出目录继续查询。

创建响应丢失时不要盲目再次创建：到上游任务列表检查现有 ID。已存在内容使用 skip 策略，不请求覆盖；若旧任务的路径在另一目录，核验会停止，需你选择正确的授权目录。

## 3. Windows 录制备用流程

Windows 包内 recording.md 提供完整前置检查和命令。先准备 OBS 专用场景与应用音频，再运行定时录制。不会自动把下载失败转换成录制，也不会偷偷接管正在进行的录制。

## 4. 卸载

删除你安装的 Skill 文件夹即可。输出视频、OBS 配置和独立上游程序不会被删除；它们由各自工具管理。本 Skill 不安装系统服务，不改启动项。
