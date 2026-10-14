# Windows OBS 定时录制

前提：Windows、Node.js 22.4+、OBS（WebSocket v5）、Python、FFmpeg/ffprobe。此流程保存播放副本，耗时通常接近实际播放时长。

## 准备与短样本

1. 在 OBS 建立专用 Profile 与 Scene，例如 Channels Recording；记录名称。选择窗口捕获，定位用户授权的微信视频播放窗口。优先 Windows Graphics Capture；有黑屏就排查兼容性，不默认升级为整个桌面录制。
2. 只保留需要的应用音频源。关闭全局麦克风、摄像头及无关桌面音频，查看音量表；播放 3–5 秒样本并实际听检。系统扬声器回环可能没有微信声音，必须验证应用音频。
3. 输出格式选 MKV，使用新的输出目录和唯一命名。预先确认画布与视频范围，显示不要休眠，不要切换场景或 Profile；录制期间不要手动操作 OBS 的录制按钮。
4. OBS 工具 → WebSocket 服务器设置，启用认证。用你控制的本地文件写入 server_port 与 server_password；不要提交这个文件或公开端口。脚本仅连接 127.0.0.1。
5. 打开目标视频并定位起点；协调启动播放和录制。脚本只计时录制，不负责通用微信 UI 自动点击。可留前后余量，之后裁切。

配置结构（占位符需要替换；放在仓库外）：

    {"server_port":4455,"server_password":"REPLACE_LOCALLY"}

进入 Skill 文件夹，执行 60 秒录制：

    node scripts/record.mjs "C:/LocalConfig/obs-config.json" 60 "Channels Recording" "Channels Recording"

最后两个参数依次是 Scene 与 Profile。范围 1..14400 秒。脚本核对当前场景/配置，拒绝接管已有录制，然后启动、等待、停止并输出 MKV 路径。若连接丢失或进程被强杀，无法保证自动停止；遇到错误提示立即在 OBS 手动停止并保留 MKV。

## 导出与交付

保留 MKV。例：跳过前 2 秒、保留 30 秒、裁出 1280×720 的区域，源区域必须实际符合这些数字：

    python scripts/media.py "C:/VideoOutput/source.mkv" --output "C:/VideoOutput/copy.mp4" --start 2 --duration 30 --crop 1280:720:0:0

可省略 --crop 保留完整画面，省略 --duration 保留起点之后全部内容。输出必须是新文件；原声轨会重新编码 AAC，不可称无损音频。脚本检查音轨存在、时长、完整解码和哈希；实际听感、黑屏/遮挡与同步仍须播放检查。录制得到的文件标为 recording-copy。
