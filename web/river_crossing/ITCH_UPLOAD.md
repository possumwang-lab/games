# River Crossing Web Build

Upload this file to itch.io:

`build/river_crossing_itch_web.zip`

This zip includes both `river_crossing.apk` and `river_crossing.tar.gz`. Some
itch.io embeds are served from an itch CDN host instead of an `.itch.zone` host,
and pygbag's generated loader may choose either archive depending on that host.

Recommended itch.io settings:

- Kind of project: `HTML`
- Upload: `build/river_crossing_itch_web.zip`
- Check: `This file will be played in the browser`
- Viewport dimensions: `1100 x 620`
- Enable fullscreen button: optional

To rebuild the web zip after changing the game:

```powershell
Copy-Item -LiteralPath ..\..\river_crossing_game.py -Destination .\river_crossing_game.py -Force
python -m pygbag --archive .
```
