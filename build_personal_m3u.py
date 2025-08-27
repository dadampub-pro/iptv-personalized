#!/usr/bin/env python3
"""
build_personal_m3u.py
=====================

This script reads an IPTV M3U playlist (such as the master playlist from
https://iptv-org.github.io/iptv/index.m3u) and produces a personalised
playlist structured for easier navigation in IPTV players like TiViMate Pro.

The personalised playlist organises channels into approximately 600 groups
based on a combination of continent, country and genre. Channels listed in
a favourites file are duplicated into a ★ Favorites group. The script can
also append a resolution indicator (UHD, FHD, HD, SD) to the channel name.

Usage:
    python build_personal_m3u.py --input index.m3u \
        --output personalised.m3u --favorites favorites.txt \
        --append_resolution_tag

Arguments:
    --input/-i: Path to the source M3U file (required).
    --output/-o: Path to write the personalised M3U file (required).
    --favorites/-f: Optional path to a text file containing one channel
        pattern per line. Patterns are treated as case-insensitive
        regular expressions. Channels matching any pattern will be added
        to a special ★ Favorites group.
    --append_resolution_tag: If provided, the script will append a
        resolution tag to the channel name, such as `[UHD]`, `[FHD]`,
        `[HD]` or `[SD]`. Tags are determined by inspecting the channel
        name and EXTINF metadata for common resolution indicators (e.g.
        2160 or 4k for UHD, 1080 for FHD, 720 for HD).

The script uses simple heuristic mappings to assign countries to
continents and normalise genre names. You can customise these mappings
by editing the dictionaries in the script.

Author: OpenAI Assistant
"""

import argparse
import os
import re
from typing import Dict, List, Optional, Tuple


# Mapping of ISO 3166-1 alpha-2 country codes to continents and human-readable
# country names. Only a subset of countries is included here. Feel free to
# extend this mapping or replace it entirely according to your needs. Unknown
# countries will be mapped to "기타" (Other).
COUNTRY_TO_CONTINENT: Dict[str, Tuple[str, str]] = {
    # Asia
    "KR": ("아시아", "대한민국"),
    "JP": ("아시아", "일본"),
    "CN": ("아시아", "중국"),
    "IN": ("아시아", "인도"),
    "ID": ("아시아", "인도네시아"),
    "SG": ("아시아", "싱가포르"),
    "VN": ("아시아", "베트남"),
    "TH": ("아시아", "태국"),
    "MY": ("아시아", "말레이시아"),
    "PH": ("아시아", "필리핀"),
    # Europe
    "GB": ("유럽", "영국"),
    "FR": ("유럽", "프랑스"),
    "DE": ("유럽", "독일"),
    "IT": ("유럽", "이탈리아"),
    "ES": ("유럽", "스페인"),
    "RU": ("유럽", "러시아"),
    "NL": ("유럽", "네덜란드"),
    "PL": ("유럽", "폴란드"),
    "PT": ("유럽", "포르투갈"),
    "SE": ("유럽", "스웨덴"),
    # North America
    "US": ("북미", "미국"),
    "CA": ("북미", "캐나다"),
    "MX": ("북미", "멕시코"),
    "CU": ("북미", "쿠바"),
    "DO": ("북미", "도미니카 공화국"),
    # South America
    "BR": ("남미", "브라질"),
    "AR": ("남미", "아르헨티나"),
    "CO": ("남미", "콜롬비아"),
    "CL": ("남미", "칠레"),
    "PE": ("남미", "페루"),
    # Oceania
    "AU": ("오세아니아", "호주"),
    "NZ": ("오세아니아", "뉴질랜드"),
    # Africa
    "ZA": ("아프리카", "남아프리카 공화국"),
    "EG": ("아프리카", "이집트"),
    "NG": ("아프리카", "나이지리아"),
    "KE": ("아프리카", "케냐"),
}

# Genre normalisation mapping. Keys are lower-case keywords or group titles
# extracted from the source playlist. Values are normalised genre names in
# English or Korean. Unknown genres will be mapped to "기타" (Other).
GENRE_MAP: Dict[str, str] = {
    "news": "뉴스",
    "sport": "스포츠",
    "sports": "스포츠",
    "movie": "영화/드라마",
    "movies": "영화/드라마",
    "film": "영화/드라마",
    "kids": "키즈",
    "children": "키즈",
    "music": "음악",
    "religion": "종교",
    "religious": "종교",
    "documentary": "다큐",
    "docu": "다큐",
    "lifestyle": "라이프스타일",
    "shopping": "쇼핑",
    "entertainment": "엔터테인먼트",
    "general": "엔터테인먼트",
}


def parse_favorites(fav_path: Optional[str]) -> List[re.Pattern]:
    """Read favourite channel patterns from a file and compile them.

    Each line in the file is treated as a case-insensitive regular
    expression. Empty lines and lines beginning with # are ignored.

    Returns a list of compiled regex patterns.
    """
    patterns: List[re.Pattern] = []
    if not fav_path:
        return patterns
    try:
        with open(fav_path, 'r', encoding='utf-8') as fav_file:
            for line in fav_file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                try:
                    patterns.append(re.compile(line, re.IGNORECASE))
                except re.error:
                    # Skip invalid regex patterns silently
                    pass
    except FileNotFoundError:
        # If the favourites file does not exist, ignore it
        pass
    return patterns


def match_favorite(name: str, patterns: List[re.Pattern]) -> bool:
    """Return True if the channel name matches any favourite pattern."""
    for pat in patterns:
        if pat.search(name):
            return True
    return False


def detect_resolution_tag(text: str) -> str:
    """Detect the likely resolution of a channel from its metadata or name.

    Returns one of "UHD", "FHD", "HD" or "SD". The function looks for
    common numeric and textual markers associated with each resolution.
    """
    # Normalize text for easier matching
    lower = text.lower()
    # UHD / 4K
    # Match both bare numbers and numbers followed by 'p'. Word boundaries
    # are avoided to allow matches like '1080p' or '2160p'.
    if re.search(r'(2160p?|4k|uhd)', lower):
        return "UHD"
    # FHD (Full HD / 1080)
    if re.search(r'(1080p?|fhd|full[\s_-]?hd)', lower):
        return "FHD"
    # HD (720)
    if re.search(r'(720p?|hd)', lower):
        return "HD"
    # Default
    return "SD"


def normalise_genre(original: str) -> str:
    """Normalise a genre string using GENRE_MAP.

    If the original string (lowercased) contains any of the keys in
    GENRE_MAP as a substring, return the corresponding value. Otherwise
    return "기타".
    """
    if not original:
        return "기타"
    lower = original.lower()
    for key, value in GENRE_MAP.items():
        if key in lower:
            return value
    return "기타"


def build_personalised_playlist(
    input_path: str,
    output_path: str,
    fav_patterns: List[re.Pattern],
    append_res_tag: bool,
) -> None:
    """Process the input M3U and write the personalised output M3U."""
    with open(input_path, 'r', encoding='utf-8', errors='ignore') as infile:
        lines = infile.readlines()

    out_lines: List[str] = []
    out_lines.append('#EXTM3U')
    i = 0
    while i < len(lines):
        line = lines[i].rstrip('\n')
        if not line.startswith('#EXTINF'):
            i += 1
            continue
        extinf = line
        url = lines[i + 1].strip() if i + 1 < len(lines) else ''
        i += 2
        # Extract tvg-name
        name_match = re.search(r',([^,]*)$', extinf)
        if not name_match:
            continue
        name = name_match.group(1).strip()
        # Extract country code(s)
        cc_match = re.search(r'tvg-country="([^"]+)"', extinf)
        country_codes = cc_match.group(1).split(';') if cc_match else ['']
        cc = country_codes[0] if country_codes else ''
        continent, country_name = COUNTRY_TO_CONTINENT.get(cc, ("기타", cc or "기타"))
        # Extract original group title / category
        cat_match = re.search(r'group-title="([^"]+)"', extinf)
        original_cat = cat_match.group(1) if cat_match else ''
        genre = normalise_genre(original_cat)
        # Determine final group
        group_title = f"{continent} - {country_name} - {genre}"
        # Determine resolution tag
        res_tag = detect_resolution_tag(extinf + ' ' + name)
        final_name = name
        if append_res_tag:
            final_name = f"{name} [{res_tag}]"
        # Prepare EXTINF line with new group-title and possibly new name
        def replace_or_append_group(ext: str, new_group: str) -> str:
            if 'group-title="' in ext:
                return re.sub(r'group-title="[^"]*"', f'group-title="{new_group}"', ext)
            else:
                return ext.replace('#EXTINF', f'#EXTINF group-title="{new_group}"')

        # Add to favourites group if matching
        if match_favorite(name, fav_patterns):
            fav_extinf = replace_or_append_group(extinf, '★ Favorites')
            fav_extinf = re.sub(r',[^,]*$', f',{final_name}', fav_extinf)
            out_lines.append(fav_extinf)
            out_lines.append(url)
        # Add to main group
        new_extinf = replace_or_append_group(extinf, group_title)
        new_extinf = re.sub(r',[^,]*$', f',{final_name}', new_extinf)
        out_lines.append(new_extinf)
        out_lines.append(url)

    # Ensure output directory exists
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as outfile:
        outfile.write('\n'.join(out_lines))


def main():
    parser = argparse.ArgumentParser(
        description='Build a personalised M3U playlist with continent/country/genre grouping.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('-i', '--input', required=True, help='Input M3U file path')
    parser.add_argument('-o', '--output', required=True, help='Output M3U file path')
    parser.add_argument('-f', '--favorites', help='Path to favourites list (regex patterns)')
    parser.add_argument('--append_resolution_tag', action='store_true', help='Append resolution tag to channel names')
    args = parser.parse_args()

    fav_patterns = parse_favorites(args.favorites)
    build_personalised_playlist(
        input_path=args.input,
        output_path=args.output,
        fav_patterns=fav_patterns,
        append_res_tag=args.append_resolution_tag,
    )


if __name__ == '__main__':
    main()