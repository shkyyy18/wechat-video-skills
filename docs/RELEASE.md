# 微存 WeSave 0.1.0-preview.2

微信视频号仍是主卖点；本版为 Mac、Windows 两个 Skill 加入抖音正常可播放网页媒体的获取流程。

- 微信：保留本机下载API与Windows OBS备用流程，原文件下载验收仍待完成。
- 抖音：授权浏览器定位视频 → douyin.py获取或接收已下载文件 → 作品ID、时长、音轨、完整解码与哈希核验。
- 已在Windows保存两条真实网页视频并通过技术媒体检查；不含第三方视频，不宣称可下载任意受限内容。
- 两条样本的作者允许/禁止下载设置尚未核实，不能当成两类都已通过。Mac真实浏览器获取仍待验收。
- 需要Agent浏览器能力、Python3.10+、FFmpeg/ffprobe；抖音路径不依赖微信下载器，也不使用OBS录屏。

下载对应系统ZIP，核对SHA256SUMS后安装。先前preview.1仍保留。工程测试计划：38项Python+16项Node，结果以本版GitHub Actions为准。
