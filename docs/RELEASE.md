# 微存 WeSave 0.1.0-preview.1

macOS / Windows 两个独立 Agent Skill，自动化调用本机下载接口保存授权的微信视频号视频；Windows 另提供 OBS 定时录制与 MP4 导出。

## 下载
- macOS：channels-video-macos-0.1.0-preview.1.zip
- Windows：channels-video-windows-0.1.0-preview.1.zip
- 用 SHA256SUMS 校验，解压后按安装说明放入 Agent 的 Skill 目录。

## 前提与状态
下载依赖自行评估并配置的 wx_channels_download v260907、Python 3.10+、FFmpeg/ffprobe。Windows 录制另需 OBS 与 Node.js 22.4+。

开发预览：本地26项Python和16项Node合成/工程测试通过，不代表真实微信下载验收。Mac 真机下载、Windows 原文件下载和新包 OBS 真微信回归尚待验证。OBS 输出是录制副本，不是无损原片。上游二进制不随包分发。

包含完整源代码、双语说明、依赖归属、媒体核验、任务续查、独立安装包与校验和。不安装证书、不改系统代理或保护设置。
