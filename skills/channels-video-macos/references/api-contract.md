# 下载参数与输出契约

对照上游 tag v260907；接口漂移时应停止，更新适配并重新测试。

- GET /api/channels/parse_sph?url=...：解析授权的微信分享地址。拒绝普通外部 URL。
- POST /api/v1/download_task/create：单个 objects 元素，platform=wxchannels、build_from_fetch=true、content=上一步 data、download_dir=绝对路径、config.existing_action=skip、auto_start=true。创建仅一次；逐项校验 code 和 id。
- GET /api/v1/download_task/detail?id=...：0等待、1准备、2下载、3暂停、4合并、5完成、6失败、7取消。暂停/失败/取消立即返回错误；未知状态不当作成功。
- HTTP 200 不代表业务成功；外层 code 和嵌套 errCode 均检查。
- file_type=video 的结果必须真实存在、非空、解析后的绝对路径位于授权目录中，且可由 FFmpeg 解码。最终 JSON 区分 mode=download 与 mode=recording-copy。

默认轮询 600 秒，范围 1..86400；间隔默认2秒，范围0.1..60。OBS 录制时长 1..14400 秒。检查报告可能包含本地路径，只用于本地交付，不自动上传。

文件存在、技术解码成功、用户听感验收和公开使用权是独立状态。脚本不会假装完成后两项。
