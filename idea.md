# Long John Silver (ljs) platform

- self-hosted webapp
- html+css+js frontend
- fastapi python backend
- Prowlarr server
- webdav and rclone
- torbox api

The purpose is to:

- have a simple front-end for searching torrents (hence prowlarr)
- trigger download and monitor the status (torbox api)
- use rclone to sync locally from torbox to local storage (webdav)
- clean and remove torrent from torbox

Requests:

- I want a cyber-pirate-punk styling. Minimal but ahrrr!
- responsive and mobile friendly
- lightweight and snappy
- small footprint
- single docker compose to spin up/down the entire system
