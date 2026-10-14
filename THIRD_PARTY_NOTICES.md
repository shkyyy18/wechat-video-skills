# Third-party dependencies and attribution

This repository contains original workflow instructions and adapter scripts. It does not bundle upstream binaries, certificates, cookies, patched downloaders, or media.

- ltaoo/wx_channels_download, API pinned for inspection to v260907, release dated 2026-09-07: https://github.com/ltaoo/wx_channels_download . Its LICENSE is MIT with Commons Clause v1.0, not unrestricted MIT. The upstream no-selling restriction applies to that software; this repository does not grant rights to redistribute or commercialize it.
- OBS Studio: https://obsproject.com/ . Recording/capture is provided by OBS, not invented by this Skill. Consult OBS's GPL licensing for the version you install.
- OBS WebSocket v5 protocol: https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md . The original lightweight client here uses SHA256 challenge authentication and connects to loopback only.
- FFmpeg/ffprobe: https://ffmpeg.org/legal.html . License depends on build configuration; obtain separately and follow its terms.
- Python and Node.js are installed separately. This repository uses their standard libraries only at runtime.

API evidence: upstream internal/api/routes.go, internal/database/model/download_task.go, internal/adapter/wxchannels/convert.go and docs/public/openapi/download_task at tag v260907. No upstream implementation source is redistributed here.
