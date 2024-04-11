import os
import networkx as nx
import time
import requests


REMOVE_DEPS_AT_END = True
UPDATE_DOCKERFILE = True
UPDATE_OTHER_FILES = True


def get_version(package):
    url = "https://pypi.org/project/" + package
    r = requests.get(url)
    res = r.text
    version = res.split("<p class=\"release__version\">")[1].split("</p>")[0].strip().split(" ")[0].strip()
    license = res.split("<p><strong>License:</strong>")[1].split("</p>")[0].strip()
    time.sleep(0.1)
    return package, url, version, license


if not os.path.exists("deps.txt"):
    os.system("pipdeptree -p pm4py >deps.txt")

F = open("deps.txt", "r")
content = F.readlines()
F.close()
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
deps = []
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
deps = sorted(deps, key=lambda x: x.lower())
if "cvxopt" in deps:
    del deps[deps.index("cvxopt")]
if "pm4py" in deps:
    del deps[deps.index("pm4py")]
packages = []
for x in deps:
    packages.append(get_version(x))


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

first_line_packages = ["deprecation", "packaging", "networkx", "graphviz", "six", "python-dateutil", "pytz", "tzdata", "intervaltree", "sortedcontainers"]
first_packages_line = ""
second_packages_line = ""
for x in packages:
    cont = x[0] + "==" + x[2] + " "
    if x[0] in first_line_packages:
        first_packages_line += cont
    else:
        second_packages_line += cont

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

stru = "".join(before_lines + ["RUN pip install " + x + "\n" for x in [first_packages_line, second_packages_line]] + after_lines)

if UPDATE_DOCKERFILE:
    F = open("../Dockerfile", "w")
    F.write(stru)
    F.close()
else:
    print(stru)

if REMOVE_DEPS_AT_END:
    os.remove("deps.txt")
