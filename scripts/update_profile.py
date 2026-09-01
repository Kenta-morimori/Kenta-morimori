"""Refresh the public GitHub profile README and its character portrait."""

from __future__ import annotations

import json
import os
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image, ImageEnhance


ACCOUNT = "Kenta-morimori"
PROFILE_REPOSITORY = f"{ACCOUNT}/{ACCOUNT}"
ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
PORTRAIT = ROOT / "assets" / "kenta-ascii-portrait.svg"
TERMINAL_PANEL = ROOT / "assets" / "profile-terminal.svg"
PORTRAIT.parent.mkdir(exist_ok=True)

PORTRAIT_BOX = (115, 0, 460, 410)
GRID_WIDTH, GRID_HEIGHT = 46, 48
CELL_WIDTH, CELL_HEIGHT = 10, 13
PALETTE = "@%#*+=-:. "


def api(path: str) -> object:
    token = os.environ["GITHUB_TOKEN"]
    request = Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request) as response:  # noqa: S310 -- fixed GitHub API host
        return json.load(response)


def download(url: str, destination: Path) -> None:
    with urlopen(url) as response:  # noqa: S310 -- avatar URL comes from GitHub API
        destination.write_bytes(response.read())


def write_portrait(source: Path) -> None:
    image = Image.open(source).convert("RGB").crop(PORTRAIT_BOX)
    image = ImageEnhance.Contrast(image).enhance(1.25)
    image = ImageEnhance.Color(image).enhance(1.15)
    image = image.resize((GRID_WIDTH, GRID_HEIGHT), Image.Resampling.LANCZOS)

    glyphs: list[str] = []
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            red, green, blue = image.getpixel((x, y))
            brightness = (red + green + blue) / 3
            glyph = PALETTE[min(len(PALETTE) - 1, int(brightness / 256 * len(PALETTE)))]
            if glyph == " ":
                continue
            color = "#{:02x}{:02x}{:02x}".format(
                min(255, int(red * 1.18 + 8)),
                min(255, int(green * 1.18 + 8)),
                min(255, int(blue * 1.18 + 8)),
            )
            glyphs.append(
                f'<text x="{x * CELL_WIDTH}" y="{(y + 1) * CELL_HEIGHT}" fill="{color}">{escape(glyph)}</text>'
            )

    width, height = GRID_WIDTH * CELL_WIDTH, GRID_HEIGHT * CELL_HEIGHT
    PORTRAIT.write_text(
        f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Color character portrait of Kenta Takemori">
  <rect width="100%" height="100%" rx="12" fill="#0d1117"/>
  <g font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="14" font-weight="700">{''.join(glyphs)}</g>
</svg>
''',
        encoding="utf-8",
    )


def public_activity(event: dict[str, object]) -> str:
    event_type = str(event.get("type", "Public activity")).removesuffix("Event")
    timestamp = str(event.get("created_at", ""))[:10]
    return f"{event_type} · {timestamp} UTC" if timestamp else event_type


def terminal_text(x: int, y: int, value: str, color: str, *, bold: bool = False, anchor: str = "start") -> str:
    weight = ' font-weight="700"' if bold else ""
    return f'<text x="{x}" y="{y}" fill="{color}" text-anchor="{anchor}"{weight}>{escape(value)}</text>'


def terminal_entry(y: int, label: str, value: str) -> str:
    return "".join(
        (
            terminal_text(28, y, label, "#e5a26b", bold=True),
            terminal_text(220, y, "....................", "#4b5361"),
            terminal_text(670, y, value, "#9ecbff", anchor="end"),
        )
    )


def write_terminal(profile: dict[str, object], repository: dict[str, object], event: dict[str, object]) -> None:
    updated = str(repository.get("updated_at", ""))[:10] + " UTC"
    lines = [
        terminal_text(28, 42, "Kenta-morimori@kyutech", "#9ecbff", bold=True),
        terminal_text(300, 42, "----------------------------------------", "#4b5361"),
        terminal_entry(84, "Institution:", "Kyushu Institute of Technology"),
        terminal_entry(116, "Research:", "ML, Biophysics"),
        terminal_entry(148, "Focus:", "Image & Time-Series Analysis"),
        terminal_text(28, 202, "- Contact ", "#c9d1d9"),
        terminal_text(145, 202, "----------------------------------------------------------", "#4b5361"),
        terminal_entry(236, "Email.University:", "takmori,kenta331@mail.kyutech.jp"),
        terminal_entry(268, "Email.Personal:", "takemori.kenta.official@gmail.com"),
        terminal_entry(300, "LinkedIn:", "kenta-takemori"),
        terminal_entry(332, "GitHub:", "Kenta-morimori"),
        terminal_text(28, 388, "- GitHub Status ", "#c9d1d9"),
        terminal_text(220, 388, "----------------------------------------------------", "#4b5361"),
        terminal_entry(422, "Public.Repos:", str(profile.get("public_repos", 0))),
        terminal_entry(454, "Latest.Project:", str(repository.get("name", "—"))),
        terminal_entry(486, "Last.Updated:", updated),
        terminal_entry(518, "Recent.Activity:", public_activity(event)),
    ]
    TERMINAL_PANEL.write_text(
        f'''<svg xmlns="http://www.w3.org/2000/svg" width="700" height="540" viewBox="0 0 700 540" role="img" aria-label="Terminal-style profile information for Kenta Takemori">
  <rect width="700" height="540" rx="12" fill="#0d1117"/>
  <rect x="1" y="1" width="698" height="538" rx="11" fill="none" stroke="#30363d"/>
  <g font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="20">{''.join(lines)}</g>
</svg>
''',
        encoding="utf-8",
    )


def first_non_profile_repository(repositories: list[object]) -> dict[str, object]:
    for repository in repositories:
        if isinstance(repository, dict) and repository.get("full_name") != PROFILE_REPOSITORY:
            return repository
    return {}


def first_non_profile_event(events: list[object]) -> dict[str, object]:
    for event in events:
        if not isinstance(event, dict):
            continue
        repo = event.get("repo")
        if isinstance(repo, dict) and repo.get("name") != PROFILE_REPOSITORY:
            return event
    return {}


def write_readme() -> None:
    README.write_text(
        f'''<table>
  <tr>
    <td valign="middle" width="40%" align="center">
      <img src="./assets/kenta-ascii-portrait.svg" width="355" alt="Color character portrait generated from Kenta Takemori's GitHub avatar" />
    </td>
    <td valign="middle" width="60%">
      <img src="./assets/profile-terminal.svg" width="620" alt="Terminal-style profile information" />
    </td>
  </tr>
</table>

---

<div align="center"><sub>Last refreshed automatically by GitHub Actions</sub></div>
''',
        encoding="utf-8",
    )


def main() -> None:
    profile = api(f"/users/{ACCOUNT}")
    repositories = api(f"/users/{ACCOUNT}/repos?sort=updated&per_page=100")
    events = api(f"/users/{ACCOUNT}/events/public?per_page=100")
    assert isinstance(profile, dict) and isinstance(repositories, list) and isinstance(events, list)
    repository = first_non_profile_repository(repositories)
    event = first_non_profile_event(events)

    avatar = ROOT / ".avatar.png"
    download(str(profile["avatar_url"]), avatar)
    write_portrait(avatar)
    avatar.unlink()
    write_terminal(profile, repository, event)
    write_readme()


if __name__ == "__main__":
    main()
