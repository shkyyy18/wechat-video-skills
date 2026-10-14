# 微存 WeSave

[![CI](https://github.com/shkyyy18/wechat-video-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/shkyyy18/wechat-video-skills/actions/workflows/ci.yml)

**让 AI 按你的系统自动化下载、核验和保存微信视频号视频。** macOS 与 Windows 各有独立 Skill 安装包；下载通道依赖已配置的本机上游运行时。Windows 另提供 OBS 定时录制备用流程。

> 开发预览版 0.1.0-preview.1。两个安装包已设计为独立交付；Mac 真机和 Windows 原文件下载尚未完成端到端验收。录制生成的是重新编码的播放副本，不是服务器原文件，也不保证无损。

[English](README.en.md) · [安装](docs/INSTALL.md) · [兼容与验收](docs/COMPATIBILITY.md) · [质量检查](docs/QUALITY.md) · [来源与依赖](THIRD_PARTY_NOTICES.md)

## 按系统选包

| 系统 | Skill 文件夹 / ZIP | 主要功能 |
|---|---|---|
| macOS | channels-video-macos | 本机下载 API → 等待任务 → 文件/声轨/时长/解码/哈希核验 |
| Windows | channels-video-windows | 同一下载流程；另含 OBS 窗口与应用音频录制、定时停止、裁切导出 |

[下载 macOS / Windows 安装包](https://github.com/shkyyy18/wechat-video-skills/releases/tag/v0.1.0-preview.1) · [项目介绍页](https://shkyyy18.github.io/wechat-video-skills/)。Release 附 SHA256SUMS。不要把整个仓库当成单个 Skill 安装。仓库的 skills/ 目录也可直接按系统选用。

## 你可以这样说

- “把这个微信视频号链接保存到我指定的文件夹，完成后检查视频能否播放。”
- “上次任务超时了，用任务编号继续检查，不要重复下载。”
- Windows：“这个视频下载接口不可用，用 OBS 录制当前已打开的视频 60 秒，保存成 MP4 副本。”

Agent 先检查系统、工具和本机运行时，再执行对应流程。分享链接不能替代微信登录、可播放状态及上游环境准备。

## 自动化范围

下载模式：调用 ltaoo/wx_channels_download 的本地接口，创建任务、等待完成、读取本地文件并做媒体检查。分享链接解析、媒体获取及必要解密由上游实现。本项目不含上游二进制或解密算法。

Windows 录制模式：OBS 捕获窗口和应用音频；脚本控制开始/停止；FFmpeg 裁切、编码；Skill 指导前置检查与交付。需要提前选择专用 OBS 场景与配置、确认音频、打开可播放视频；计时器不会自行定位或点击任意微信界面。

普通用户也可以手动用 OBS 做相同录制。Skill 的价值是可重复的操作流程、错误处理和结果检查，核心录制能力来自 OBS。

## 快速开始

先阅读安装说明，安装 Python 3.10+ 与 FFmpeg/ffprobe。下载模式需要你已经评估并配置好的上游本地运行时；Windows 录制还需要 Node.js 22.4+ 和 OBS WebSocket v5。

进入你选的 Skill 文件夹后查看参数（Mac 可用 python3）：

    python scripts/download.py --help

CLI 的 --help 列出参数。成功输出包含模式、文件路径、时长、音轨数、SHA256 和解码结果。音轨存在不等于声音清晰或声画同步；交付前仍应播放检查。

## 开发与测试

先运行 python tools/build.py，再运行 python -m unittest discover -s tests -v 和 node --test tests/obs.test.mjs。运行 python tools/build.py 生成两个 ZIP 和 SHA256SUMS。合成素材测试不访问微信、不使用账号，不能替代真机验收。

## 许可与边界

本仓库原创脚本和文档使用 MIT 许可。上游下载器的 MIT + Commons Clause 许可单独适用；OBS、FFmpeg 的许可也独立适用，参见依赖声明。本项目不隶属于腾讯、微信或 OBS。

仅处理你有权保存的内容；不自动安装证书、修改代理、关闭系统保护或绕过访问限制。问题反馈请使用模板并去除账号、Cookie、分享参数、凭据和私人视频。
