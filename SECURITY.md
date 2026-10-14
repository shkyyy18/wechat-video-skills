# Security and privacy

Do not post credentials, cookies, full private share URLs, OBS passwords or private recordings in issues. Provide a synthetic reproduction. Use GitHub private vulnerability reporting when enabled; otherwise request a private reporting route without exposing exploit details or secrets.

The adapter is loopback-only, disables environment proxies, refuses redirects, creates once, checks output paths and never asks to overwrite existing content. It does not set up upstream certificates/proxies or bypass OS protections. A local downloader has its own trust and access boundary; review it separately.

OBS must have authentication enabled, a private local config and a dedicated profile/scene. The timer attempts to stop its own recording on interruption. Abrupt process termination, connection loss, machine sleep or power failure may defeat cleanup; stop OBS manually if requested and retain MKV. Do not operate OBS concurrently with the recording helper.
