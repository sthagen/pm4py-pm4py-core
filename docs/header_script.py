import glob
import re
from pathlib import Path


ENCODING_PATTERN = re.compile(r"#.*coding[:=]\s*[-\w.]+")
MOJIBAKE_REPLACEMENTS = {
    "â€“": "-",
    "â€”": "-",
}
DASH_TRANSLATION = str.maketrans({
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2015": "-",
})


def _consume_prefix(data: str) -> int:
    index = 0

    if data.startswith("\ufeff"):
        index = 1

    while True:
        if data.startswith("#!", index):
            line_end = data.find("\n", index)
            if line_end == -1:
                return len(data)
            index = line_end + 1
            continue

        line_end = data.find("\n", index)
        if line_end == -1:
            line_end = len(data)
        line = data[index:line_end]
        if ENCODING_PATTERN.match(line):
            if line_end < len(data):
                line_end += 1
            index = line_end
            continue

        break

    return index


def _extract_leading_docstring(data: str) -> str | None:
    header_start = _consume_prefix(data)
    while header_start < len(data) and data[header_start] in {" ", "\t", "\r", "\n"}:
        header_start += 1

    if not (data.startswith('"""', header_start) or data.startswith("'''", header_start)):
        return None

    quote = data[header_start:header_start + 3]
    header_end = data.find(quote, header_start + 3)
    if header_end == -1:
        return None

    return data[header_start + 3:header_end]


def _strip_wrapping_triple_quotes(data: str) -> str:
    stripped = data.strip()
    if len(stripped) >= 6 and (
        (stripped.startswith('"""') and stripped.endswith('"""'))
        or (stripped.startswith("'''") and stripped.endswith("'''"))
    ):
        return stripped[3:-3]
    return stripped


def _normalize_header(data: str) -> str:
    normalized = _strip_wrapping_triple_quotes(data).strip()
    for source, target in MOJIBAKE_REPLACEMENTS.items():
        normalized = normalized.replace(source, target)
    normalized = normalized.translate(DASH_TRANSLATION)
    return " ".join(
        re.sub(r"\s+", " ", line).strip()
        for line in normalized.splitlines()
        if line.strip()
    ).lower()


def _matches_license_header(data: str) -> bool:
    normalized = _normalize_header(data)
    return (
        "process intelligence solutions" in normalized
        and "gnu affero general public license" in normalized
    )


if __name__ == '__main__':
    script_dir = Path(__file__).resolve().parent
    license_header_raw = _strip_wrapping_triple_quotes(
        (script_dir / 'LICENSE_HEADER_GITHUB.txt').read_text(encoding='utf-8')
    ).strip()

    for filename in glob.iglob(str(script_dir.parent / 'pm4py' / '**' / '*.py'), recursive=True):
        with open(filename, 'r', encoding='utf-8') as original:
            data = original.read()

        current_header = _extract_leading_docstring(data)
        if current_header is not None and _matches_license_header(current_header):
            print('skipping: ' + filename)
            continue

        with open(filename, 'w', encoding='utf-8') as modified:
            print('adding license to: ' + filename)
            modified.write("'''\n" + license_header_raw + "\n'''\n" + data)
