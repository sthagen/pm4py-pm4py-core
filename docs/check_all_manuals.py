import os
import pm4py
import traceback


os.chdir("..")
files = [x for x in os.listdir("docs/") if x.endswith(".md") and "_" in x]
for f in files:
    F = open(os.path.join("docs", f), "r", encoding="utf-8")
    content = F.read()
    F.close()
    print(f)

    content = content.split("```python")[1:]

    for idx, c in enumerate(content):
        print(f, idx, len(content)-1)
        c = c.split("```")[0]
        try:
            exec(c)
        except:
            traceback.print_exc()
