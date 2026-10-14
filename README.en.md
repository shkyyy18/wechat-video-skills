# WeSave — WeChat Video Skills

Automate saving WeChat Channels videos with separate macOS and Windows Agent Skills.

**Development preview:** the local downloader API integration has not passed live end-to-end acceptance on either OS. The Windows package additionally provides a bounded OBS recording workflow. A recording is a re-encoded playback copy, not the original download.

[中文](README.md) · [Installation](docs/INSTALL.md) · [Compatibility](docs/COMPATIBILITY.md)

[Download the macOS or Windows package](https://github.com/shkyyy18/wechat-video-skills/releases/tag/v0.1.0-preview.1) · [Project page](https://shkyyy18.github.io/wechat-video-skills/). Each ZIP is self-contained; checksums accompany the archives. A compatible agent reads SKILL.md and invokes the included scripts.

The download path uses a separately configured ltaoo/wx_channels_download v260907 local runtime: resolve share URL, create once, poll by task ID, validate local paths, decode the output and report SHA256. It requires Python 3.10+, FFmpeg and ffprobe. A share URL alone does not establish a usable logged-in runtime.

Windows fallback requires OBS with authenticated local WebSocket v5 and Node.js 22.4+. The user or agent prepares a dedicated profile/scene, window capture and application audio, then runs the bounded recorder and media finalizer. The recorder does not navigate arbitrary WeChat UI or automatically start playback. Keep the source MKV.

Run python tools/build.py first. Use python -m unittest discover -s tests -v and node --test tests/obs.test.mjs for synthetic checks; python tools/build.py produces OS-specific ZIPs. CI defines Windows and macOS runners; a workflow file alone is not evidence that cloud CI passed.

Original code/docs: MIT. Upstream downloader: MIT plus Commons Clause; not bundled. OBS/FFmpeg have independent licenses. No affiliation with Tencent/WeChat/OBS. This project does not install certificates, change proxies or weaken OS protections. Save only content you are authorized to retain.
