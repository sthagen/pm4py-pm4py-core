"""Refresh the stable dependency extra and the transitive license inventory.

Run this script from any directory after installing PM4Py and pipdeptree.
"""

import re
import subprocess
import tempfile
import time
from pathlib import Path

import networkx as nx
import requests
from packaging.version import InvalidVersion, Version

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LICENSE_FILE = Path(__file__).resolve().parent / "LICENSES_TRANSITIVE.md"
PYPROJECT_FILE = PROJECT_ROOT / "pyproject.toml"

UPDATE_LICENSE_FILE = True
UPDATE_PYPROJECT_STABLE = True
INCLUDE_BETAS = False
STABLE_TOOL_PACKAGES = ("setuptools", "wheel")


def get_version(package):
    url = "https://pypi.org/pypi/" + package + "/json"
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()

    # your debug dump
    #json.dump(data, open("temp2.txt", "w"), indent=2)

    # ---- license (same as before) ----
    license = "Unspecified"
    for classi in data["info"].get("classifiers", []):
        if classi.startswith("License ::"):
            license = classi.split(":: ")[-1]

    releases = data.get("releases", {})

    versions = []
    for s in releases:
        try:
            versions.append(Version(s))
        except InvalidVersion:
            # skip weird/non-PEP 440 tags
            continue

    if not versions:
        # fallback: behave like before, use info["version"]
        version = data["info"]["version"]
        time.sleep(0.1)
        return package, url, version, license

    versions.sort(reverse=True)

    # latest stable (non-pre-release)
    stable_versions = [v for v in versions if not v.is_prerelease]
    latest_stable = stable_versions[0] if stable_versions else None

    # latest beta/RC (pre-release; you can restrict to 'b' and 'rc')
    prereleases = [v for v in versions if v.is_prerelease]

    # Only beta and rc; drop alphas if you don't want them
    beta_rc_versions = [
        v for v in prereleases
        if v.pre is not None and v.pre[0] in ("b", "rc")
    ]
    latest_beta_rc = beta_rc_versions[0] if beta_rc_versions else None

    # ---- version choice logic with INCLUDE_BETAS ----
    if not INCLUDE_BETAS:
        # always stable if possible
        if latest_stable is not None:
            chosen = latest_stable
        else:
            # no stable versions, fall back to newest overall
            chosen = versions[0]
    else:
        # prefer beta/rc only if it is *newer* than latest stable
        if latest_beta_rc is not None and latest_stable is not None:
            chosen = max(latest_stable, latest_beta_rc)
        elif latest_beta_rc is not None:
            # no stable, but we do have beta/rc
            chosen = latest_beta_rc
        elif latest_stable is not None:
            chosen = latest_stable
        else:
            # extremely weird case: only unparseable vs; fall back
            chosen = versions[0]

    version = str(chosen)

    time.sleep(0.1)
    return package, url, version, license


def elaborate_single_python_package(package_name, deps, include_self=False):
    result = subprocess.run(
        ["pipdeptree", "-p", package_name],
        check=True,
        capture_output=True,
        text=True,
    )
    content = result.stdout.splitlines()

    G = nx.DiGraph()
    i = 1
    dep_level = {}
    blocked = False
    blocked_level = -1
    while i < len(content):
        #row = content[i].replace("└──", "- ").replace("├──", "- ").split("- ")
        #print(row)
        #level = round(len(row[0]) / 2)
        #dep = row[1].split(" ")[0]
        row = content[i].split(" ")
        row = [zz for zz in row if zz]
        dep = None
        level = None
        j = 0
        while j < len(row):
            if row[j].startswith("["):
                break
            j = j + 1
        j = j - 1
        dep = row[j]
        level = (j-1)
        if True:
            if blocked and blocked_level == level:
                blocked = False
            if dep == "pm4pycvxopt":
                blocked = True
                blocked_level = level
            if not blocked:
                dep_level[level] = dep
                if level > 1:
                    G.add_edge(dep_level[level - 1], dep_level[level])
                else:
                    G.add_node(dep_level[level])
        i = i + 1
    edges = list(G.edges)
    while len(edges) > 0:
        left = {x[0] for x in edges}
        right = {x[1] for x in edges}
        diff = sorted(right - left)
        for x in diff:
            if not x in deps:
                deps.append(x)
            G.remove_node(x)
        edges = list(G.edges)
    nodes = sorted(G.nodes)
    for x in nodes:
        if not x in deps:
            deps.append(x)

    if "cvxopt" in deps:
        del deps[deps.index("cvxopt")]

    if include_self and package_name not in deps:
        deps.append(package_name)

    deps = sorted(deps, key=lambda x: x.lower())

    return deps


def get_all_third_party_dependencies(package_name, deps, packages_dictio, include_self=False):
    deps = elaborate_single_python_package(package_name, deps, include_self=include_self)
    packages = []
    for x in deps:
        if x not in packages_dictio:
            packages_dictio[x] = get_version(x)
        packages.append(packages_dictio[x])
    return deps, packages


def add_stable_tool_packages(packages, packages_dictio):
    """Keep the build tools that were part of requirements_stable.txt."""
    package_names = {package[0].lower() for package in packages}
    for package_name in STABLE_TOOL_PACKAGES:
        if package_name.lower() not in package_names:
            if package_name not in packages_dictio:
                packages_dictio[package_name] = get_version(package_name)
            packages.append(packages_dictio[package_name])
    return sorted(packages, key=lambda package: package[0].lower())


def _toml_array_end(lines, start):
    """Return the final line of a TOML array assignment."""
    depth = 0
    saw_opening_bracket = False
    quote = None
    escaped = False

    for line_number in range(start, len(lines)):
        for character in lines[line_number]:
            if quote is not None:
                if escaped:
                    escaped = False
                elif quote == '"' and character == "\\":
                    escaped = True
                elif character == quote:
                    quote = None
                continue

            if character in ("'", '"'):
                quote = character
            elif character == "#":
                break
            elif character == "[":
                depth += 1
                saw_opening_bracket = True
            elif character == "]":
                depth -= 1
                if depth < 0:
                    raise ValueError("Invalid TOML array while locating the stable extra")

        if saw_opening_bracket and depth == 0:
            return line_number

    raise ValueError("The stable optional-dependency array is not closed")


def _stable_extra_lines(packages, newline):
    requirements = sorted(
        (f"{package[0]}=={package[2]}" for package in packages),
        key=str.lower,
    )
    return [
        f"stable = [{newline}",
        *(f'    "{requirement}",{newline}' for requirement in requirements),
        f"]{newline}",
    ]


def update_pyproject_stable(pyproject_file, packages):
    """Replace or add the stable extra without rewriting unrelated TOML."""
    pyproject_file = Path(pyproject_file)
    contents = pyproject_file.read_text(encoding="utf-8")
    newline = "\r\n" if "\r\n" in contents else "\n"
    lines = contents.splitlines(keepends=True)

    section_start = None
    section_end = len(lines)
    for line_number, line in enumerate(lines):
        if line.strip() == "[project.optional-dependencies]":
            section_start = line_number
            break
    if section_start is None:
        raise ValueError("pyproject.toml has no [project.optional-dependencies] section")

    for line_number in range(section_start + 1, len(lines)):
        stripped = lines[line_number].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section_end = line_number
            break

    stable_start = None
    for line_number in range(section_start + 1, section_end):
        if re.match(r"^stable\s*=", lines[line_number].strip()):
            stable_start = line_number
            break

    replacement = _stable_extra_lines(packages, newline)
    if stable_start is not None:
        stable_end = _toml_array_end(lines, stable_start)
        updated_lines = lines[:stable_start] + replacement + lines[stable_end + 1:]
    else:
        insert_at = section_end
        while insert_at > section_start + 1 and not lines[insert_at - 1].strip():
            insert_at -= 1
        updated_lines = (
            lines[:insert_at]
            + replacement
            + [newline]
            + lines[section_end:]
        )

    temporary_file = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=pyproject_file.parent,
            prefix=f".{pyproject_file.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.writelines(updated_lines)
            temporary_file = Path(temporary.name)
        temporary_file.chmod(pyproject_file.stat().st_mode)
        temporary_file.replace(pyproject_file)
    finally:
        if temporary_file is not None and temporary_file.exists():
            temporary_file.unlink()


def update_license_file(license_file, packages):
    with Path(license_file).open("w", encoding="utf-8") as file:
        file.write("""# PM4Py Third Party Dependencies

PM4Py depends on third party libraries to implement some functionality. This document describes which libraries
PM4Py depends upon. This is a best effort attempt to describe the library's dependencies, it is subject to change as
libraries are added/removed.

| Name | URL | License | Version |
| --------------------------- | ------------------------------------------------------------ | --------------------------- | ------------------- |
""")
        file.writelines(
            (
                f"| {package[0].strip()} | {package[1].strip()} | "
                f"{package[3].strip()} | {package[2].strip()} |\n"
            )
            for package in packages
        )


def main():
    deps = []
    packages_dictio = {}
    deps, packages = get_all_third_party_dependencies(
        "pm4py", deps, packages_dictio, include_self=False
    )
    packages = add_stable_tool_packages(packages, packages_dictio)

    if UPDATE_PYPROJECT_STABLE:
        update_pyproject_stable(PYPROJECT_FILE, packages)
    if UPDATE_LICENSE_FILE:
        update_license_file(LICENSE_FILE, packages)


if __name__ == "__main__":
    main()
