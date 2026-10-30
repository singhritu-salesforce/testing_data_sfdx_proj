import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model
from rules import RULES
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = ["# testing_data_sfdx_proj\n",
"SFDX project with complex validation rules. Each of the 14 rules nests 6-9 levels deep and packs 11+ distinct functions and mixes logical, text, math, date/time, picklist, regex, CASE and VLOOKUP functions. Every function in the allowed list is used at least once. See [COVERAGE.md](COVERAGE.md).\n",
"## Deploy\n","```\nsf project deploy start --dry-run -d force-app -o <alias>   # validate first\nsf project deploy start -d force-app -o <alias>\nsf org assign permset -n Full_Access -o <alias>\n```\nUse a scratch org or sandbox. Not meant for production.\n",
"## Objects\n"]
import glob
for o in sorted(os.listdir(os.path.join(root, "force-app/main/default/objects"))):
    n = len(glob.glob(os.path.join(root, "force-app/main/default/objects", o, "fields", "*.xml")))
    L.append(f"- `{o}` ({n} fields)")
L.append(f"\n## Validation rules ({len(RULES)})\n")
cur = None
for r in sorted(RULES, key=lambda r: (r['obj'], r['name'])):
    if r['obj'] != cur: cur = r['obj']; L.append(f"\n### {cur}\n")
    L.append(f"- `{r['name']}` [{r['group']}]: {r['desc']}")
L.append("\n## Tooling\n\n- `tools/generate.py`: regenerates metadata from `tools/model.py` and `tools/rules_*.py`.\n- `tools/verify.py`: static checks (XML, parens, allowed functions, field refs, coverage). `--coverage` rewrites COVERAGE.md.\n")
open(os.path.join(root, "README.md"), "w").write("\n".join(L))
