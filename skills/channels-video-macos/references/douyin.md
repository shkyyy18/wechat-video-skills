# 抖音网页媒体获取

这是 Agent + 已授权浏览器 + 本地脚本流程；不是只给分享链接就能独立运行的下载 API。适用于当前可正常播放、播放器暴露可保存 HTTPS 媒体的单条视频。微信仍是主入口，抖音是第二平台。

## 浏览器步骤

1. 用本轮可用且获准的浏览器打开用户给的抖音链接；从实际最终页面取得 https://www.douyin.com/video/数字ID，不猜ID，不扫描账号或Cookie。
2. 核对标题、作品ID、正在播放的画面及播放器时长。必须选当前作品的 video 元素，不按预加载顺序配对。
3. 记录下载入口状态：available 仅在看到可用下载按钮时使用；explicitly_disabled 仅在看到明确禁止下载提示时使用；没找到按钮或浮层没加载用 not_observed。缺少下载按钮不证明作者禁用，能拿到文件也不证明作者授权转载。
4. 读取该 video 元素的 currentSrc 与 duration 等 DOM 媒体属性。只接受正常播放得到的媒体，不读取隐藏应用状态、不逆向签名、不修改下载开关、不访问未授权浏览器资料。遇到登录、验证码、付费或访问拒绝即停止。
5. 有浏览器媒体下载工具时，可保存该 video 元素并把实际返回路径交给脚本；工具名和语法以当前客户端文档为准。否则将正常观察到的 HTTPS 媒体地址写入私有 evidence JSON，脚本只支持 douyinvod.com 子域且 __vid 必须匹配作品ID，不猜地址、不去掉签名参数。
6. 运行 scripts/douyin.py，核验媒体完整解码、音轨、时长，保留原文件。输出是播放器提供的媒体，不是 OBS 录屏，也不承诺作者上传母版、最高画质或无水印。

## evidence JSON（纯合成示例，不可直接下载）

    {
      "source_url": "https://www.douyin.com/video/1234567890123456789",
      "title": "Synthetic example",
      "media_url": "https://v.example.douyinvod.com/synthetic?__vid=1234567890123456789",
      "duration_seconds": 20,
      "ui_download_status": "not_observed",
      "ui_evidence": "No reliable download label observed",
      "access_gate": "none"
    }

真实 evidence 含临时媒体地址，保留本地且不要进 Git、投稿或公开日志；不要求Cookie。作者明确禁用与仅未显示下载入口需分别记录，不能为了凑两类验收而改标签。

## 调用

    python scripts/douyin.py --evidence LOCAL_EVIDENCE_JSON --output ABSOLUTE_NEW_MP4

如浏览器已保存：

    python scripts/douyin.py --evidence LOCAL_EVIDENCE_JSON --browser-file BROWSER_DOWNLOAD_PATH --output ABSOLUTE_NEW_MP4

Mac 使用 python3。两种方式均需 FFmpeg/ffprobe，可用 --ffmpeg 和 --ffprobe 指定路径。输出不可覆盖，原浏览器下载文件保留。网络模式不自动重试；临时URL过期可在同一授权页面重新观察一次，遇权限限制不能换通道规避。

当前单文件上限2GiB；网络连接/单次读取超时20秒，传输目标期限120秒（在分块读取之间检查，阻塞读取最多再延迟20秒）；媒体完整解码上限600秒。音轨缺失、时长不符或解码失败不发布成品。

## 验收边界

当前已有 Windows 环境两条真实可播放网页视频保存、含音轨与完整解码检查；不代表已经覆盖作者允许和禁止下载两类设置，也不代表 Mac 微信/抖音真机验收。需实际播放检查才能标记 browser_check=passed，音轨检查不能冒充主观听审。公共仓库仅保存方法和合成测试，不附第三方视频。
