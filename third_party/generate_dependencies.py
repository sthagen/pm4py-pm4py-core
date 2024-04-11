import os
import networkx as nx
import time
import requests


REMOVE_DEPS_AT_END = True
UPDATE_DOCKERFILE = True
UPDATE_OTHER_FILES = True
INCLUDE_BETAS = False


def get_version(package):
    url = "https://pypi.org/project/" + package
    r = requests.get(url)
    res0 = r.text
    res = res0.split("<p class=\"release__version\">")[1:]
    version = ""
    i = 0
    while i < len(res):
        if "pre-release" not in res[i] or INCLUDE_BETAS:
            version = res[i].split("</p>")[0].strip().split(" ")[0].strip()
            break
        i = i + 1
    license0 = res0.split("<p><strong>License:</strong>")[1].split("</p>")[0].strip()
    license0 = license0.replace("(c)", "").split(" (")

    license = license0[0]
    for i in range(1, len(license0)):
        if "..." not in license0[i]:
            license += " (" + license0[i]

    time.sleep(0.1)
    return package, url, version, license


def elaborate_single_python_package(package_name, deps):
    if not os.path.exists("deps.txt"):
        os.system("pipdeptree -p "+package_name+" >deps.txt")

    F = open("deps.txt", "r")
    content = F.readlines()
    F.close()

    if REMOVE_DEPS_AT_END:
        os.remove("deps.txt")

    G = nx.DiGraph()
    i = 1
    dep_level = {}
    blocked = False
    blocked_level = -1
    while i < len(content):
        row = content[i].split("- ")
        level = round(len(row[0]) / 2)
        dep = row[1].split(" ")[0]
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
        left = set(x[0] for x in edges)
        right = set(x[1] for x in edges)
        diff = sorted([x for x in right if x not in left])
        for x in diff:
            if not x in deps:
                deps.append(x)
            G.remove_node(x)
        edges = list(G.edges)
    nodes = sorted(list(G.nodes))
    for x in nodes:
        if not x in deps:
            deps.append(x)

    if "cvxopt" in deps:
        del deps[deps.index("cvxopt")]
    if "pm4py" in deps:
        del deps[deps.index("pm4py")]
    deps = sorted(deps, key=lambda x: x.lower())

    return deps


def get_all_third_party_dependencies(package_name, deps, packages_dictio):
    deps = elaborate_single_python_package(package_name, deps)
    packages = []
    for x in deps:
        if x not in packages_dictio:
            packages_dictio[x] = get_version(x)
        packages.append(packages_dictio[x])
    return deps, packages


deps = []
packages_dictio = {}
deps, packages = get_all_third_party_dependencies("pm4py", deps, packages_dictio)

if UPDATE_OTHER_FILES:
    F = open("../requirements_complete.txt", "w")
    for x in packages:
        F.write("%s\n" % (x[0]))
    F.close()
    F = open("../requirements_stable.txt", "w")
    for x in packages:
        F.write("%s==%s\n" % (x[0], x[2]))
    F.close()
    F = open("LICENSES_TRANSITIVE.md", "w")
    F.write("""# PM4Py Third Party Dependencies
    
    PM4Py depends on third party libraries to implement some functionality. This document describes which libraries
    PM4Py depends upon. This is a best effort attempt to describe the library's dependencies, it is subject to change as
    libraries are added/removed.
    
    | Name | URL | License | Version |
    | --------------------------- | ------------------------------------------------------------ | --------------------------- | ------------------- |
    """)
    for x in packages:
        F.write("| %s | %s | %s | %s |\n" % (x[0].strip(), x[1].strip(), x[3].strip(), x[2].strip()))
    F.close()

deps, packages = get_all_third_party_dependencies("scikit-learn", deps, packages_dictio)

first_line_packages = ["deprecation", "packaging", "networkx", "graphviz", "six", "python-dateutil", "pytz", "tzdata", "intervaltree", "sortedcontainers"]
second_line_packages = ["pydotplus", "pyparsing", "tqdm", "colorama", "cycler", "joblib", "threadpoolctl"]

first_packages_line = ""
second_packages_line = ""
third_packages_line = ""
for x in packages:
    cont = x[0] + "==" + x[2] + " "
    if x[0] in first_line_packages:
        first_packages_line += cont
    elif x[0] in second_line_packages:
        second_packages_line += cont
    else:
        third_packages_line += cont

F = open("../Dockerfile", "r")
dockerfile_contents = F.readlines()
F.close()

before_lines = []
after_lines = []
found_line = False

i = 0
while i < len(dockerfile_contents):
    if dockerfile_contents[i].startswith("RUN pip install") and not "-U" in dockerfile_contents[i]:
        found_line = True
    elif found_line:
        after_lines.append(dockerfile_contents[i])
    else:
        before_lines.append(dockerfile_contents[i])
    i = i + 1

stru = "".join(before_lines + ["RUN pip install " + x + "\n" for x in [first_packages_line, second_packages_line, third_packages_line]] + after_lines)
stru = stru.strip() + "\n"

if UPDATE_DOCKERFILE:
    F = open("../Dockerfile", "w")
    F.write(stru)
    F.close()
else:
    print(stru)
