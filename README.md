# Personalised IPTV Playlist Builder

This repository provides a script and automation workflow for generating a
personalised IPTV playlist from the community-maintained [IPTV‑ORG](https://github.com/iptv-org/iptv)
master list. The goal is to organise the thousands of available channels
into a more manageable structure based on geographic region, country and
content genre, with optional features like resolution tagging and favourites.

## Features

- **600‐group structure**: Channels are grouped by continent, country and
  genre (e.g. `아시아 - 대한민국 - 뉴스`), yielding roughly 600 groups for
  easier navigation in players like TiViMate Pro.
- **Favourites**: Channels matching patterns in `favorites.txt` are
  duplicated into a special `★ Favorites` group at the top of the list.
- **Resolution tags**: Optionally append `[UHD]`, `[FHD]`, `[HD]` or
  `[SD]` to channel names based on simple heuristics.
- **Daily automation**: A GitHub Actions workflow fetches the latest
  master playlist, runs the build script and commits the updated
  personalised playlist to the repository.

## Getting Started

1. **Install Python** (3.8+ recommended). No external dependencies are
   required.
2. Download the IPTV‑ORG master playlist, e.g.:
   ```sh
   curl -L -o index.m3u https://iptv-org.github.io/iptv/index.m3u
   ```
3. Run the build script:
   ```sh
   python build_personal_m3u.py --input index.m3u --output docs/personalised.m3u \
       --favorites favorites.txt --append_resolution_tag
   ```
4. Import the generated `docs/personalised.m3u` into your IPTV player.

### Customising

- **Favourites**: Edit `favorites.txt`, adding one channel name or
  regular expression per line. Matching is case-insensitive and uses
  Python's regular expression syntax.
- **Country and continent mapping**: Modify `COUNTRY_TO_CONTINENT` in
  `build_personal_m3u.py` to change how country codes are mapped to
  continents and human-readable names. Unknown codes default to `기타`.
- **Genre normalisation**: Adjust `GENRE_MAP` in `build_personal_m3u.py`
  to refine how original group titles are mapped to standard genres.
- **Resolution tags**: The `--append_resolution_tag` flag controls
  whether `[UHD]`, `[FHD]`, `[HD]` or `[SD]` is appended to channel
  names. Resolution detection is heuristic; adjust the patterns in
  `detect_resolution_tag` if needed.

## GitHub Actions Workflow

The workflow defined in `.github/workflows/build.yml` automatically:

1. Checks out the repository.
2. Installs Python.
3. Downloads the latest `index.m3u` from IPTV‑ORG.
4. Runs the build script to produce `docs/personalised.m3u`.
5. Commits and pushes the updated `personalised.m3u` if changes are
   detected.

The schedule is set to run daily at 00:20 KST (15:20 UTC). You can
trigger the workflow manually from the Actions tab in GitHub.

## Publishing via GitHub Pages

If you enable GitHub Pages (Settings → Pages → Branch: `main`, Folder:
`/docs`) the personalised playlist will be available at:

```
https://<USERNAME>.github.io/<REPOSITORY>/personalised.m3u
```

Alternatively, you can use the raw file URL for your IPTV player:

```
https://raw.githubusercontent.com/<USERNAME>/<REPOSITORY>/main/docs/personalised.m3u
```

Replace `<USERNAME>` and `<REPOSITORY>` with your GitHub username and
repository name, respectively. Import this URL into TiViMate Pro or your
preferred IPTV player to access your personalised channel list.

## License

This repository is provided under the MIT License. IPTV‑ORG's content is
licensed separately; please ensure you comply with all applicable laws and
terms of service when using third‑party streams.