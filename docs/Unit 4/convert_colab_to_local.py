"""Convert the course's Colab notebooks to run locally in VS Code.

Changes per notebook (code cells only; markdown and outputs untouched):
  * `!pip install ...`              -> `%pip install ...` (installs into the active kernel)
  * `from google.colab import ...`  -> local stand-ins for `userdata` (reads .env) and `files` (no picker)
  * Colab "Secrets panel" error text -> points to the .env file
  * HF `login(token=token)`         -> only when HF_TOKEN is set (otherwise the cached `hf auth login` token is used)
Originals are copied to _colab_originals/ first.

Usage: python convert_colab_to_local.py <notebook folder> [backup folder]
  Converts every Copy_of_*.ipynb in <notebook folder>; already-converted notebooks are left unchanged.
"""
import glob
import json
import os
import re
import shutil
import sys

ROOT = sys.argv[1]
BACKUP = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "_colab_originals")

SHIM = '''# --- Local (VS Code) stand-ins for google.colab ---------------------------
from pathlib import Path
from dotenv import load_dotenv                      # load_dotenv: reads keys from the .env file next to this notebook
load_dotenv(Path.cwd() / ".env")

class userdata:  # replaces google.colab.userdata: reads the key from .env or an environment variable
    @staticmethod
    def get(name):
        value = os.environ.get(name)
        if not value:
            raise KeyError(f"{name} is not set in .env or the environment")
        return value

class files:  # replaces google.colab.files: VS Code has no upload picker, so files must sit in this folder
    @staticmethod
    def upload():
        print(f"   (local run) No upload picker here. Copy the file into: {Path.cwd()}")
        print("   Then run this cell again.")
        return {}
# ---------------------------------------------------------------------------
'''

SECRETS_MSG = re.compile(r"Open the 🔑 Secrets panel on the left, add OPENROUTER_API_KEY, \"\s*\n(\s*)\"switch on 'Notebook access', then run this cell again\.")


def convert_source(src):
    changes = []
    out = []
    shim_done = False
    for line in src.splitlines(keepends=True):
        stripped = line.lstrip()
        indent = line[: len(line) - len(stripped)]
        if stripped.startswith("!pip "):
            out.append(indent + "%" + stripped[1:])
            changes.append("!pip -> %pip")
        elif stripped.startswith("from google.colab import"):
            if not shim_done:
                out.append("import os\n" + SHIM)
                shim_done = True
                changes.append("google.colab -> local shim")
        elif re.match(r"login\(token=token\)", stripped):
            out.append(indent + "if token:  # (local run) skip when HF_TOKEN is unset; the token cached by `hf auth login` is used instead\n")
            out.append(indent + "    " + stripped)
            changes.append("guarded HF login")
        else:
            out.append(line)
    new = "".join(out)
    new, n = SECRETS_MSG.subn(r'Add OPENROUTER_API_KEY=<your key> to the .env file "\n\1"next to this notebook, then run this cell again.', new)
    if n:
        changes.append("secrets error message -> .env")
    return new, changes


def main():
    targets = sorted(glob.glob(os.path.join(ROOT, "Copy_of_*.ipynb")))
    os.makedirs(BACKUP, exist_ok=True)
    for path in targets:
        with open(path, encoding="utf-8") as f:
            nb = json.load(f)
        all_changes = []
        for cell in nb["cells"]:
            if cell["cell_type"] != "code":
                continue
            src = "".join(cell["source"])
            new, changes = convert_source(src)
            if changes:
                cell["source"] = new.splitlines(keepends=True)
                all_changes += changes
        name = os.path.basename(path)
        if not all_changes:
            print(f"-- unchanged: {name}")
            continue
        dest = os.path.join(BACKUP, name)
        if not os.path.exists(dest):
            shutil.copy2(path, dest)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
            f.write("\n")
        summary = {c: all_changes.count(c) for c in dict.fromkeys(all_changes)}
        print(f"OK {name}: {summary}")


main()
