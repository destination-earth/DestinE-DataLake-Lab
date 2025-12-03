import sys
import os
import json


with open('issue_body.txt') as f:
    body = f.read()

print("Full Issue Body:")
print(body)

fields = {
    "Repository URL": "",
    "Cookbook Title in capital letters": "",
}

lines = body.splitlines()
current_label = None

for line in lines:
    line = line.strip().lstrip("#").strip()
    if line in fields:
        current_label = line
    elif current_label and line:
        fields[current_label] = line
        current_label = None

repo_url = fields["Repository URL"]
root_path = fields["Cookbook Title in capital letters"]

print(f"Extracted Fields:")
print(f"→ Repo URL     : {repo_url}")
print(f"→ Cookbook Title in capital letters    : {root_path}")

if not root_path:
    print("ERROR: Root Path could not be extracted aborting.")
    raise ValueError("Error: Root Path could not be extracted.")

with open(os.environ['GITHUB_ENV'], 'a') as env_file:
    env_file.write(f"REPO_URL={repo_url}\n")
    env_file.write(f"ROOT_PATH={root_path}\n")

REGISTRY = "cookbooks.json"

registry = []
if os.path.exists(REGISTRY):
    try:
        with open(REGISTRY, "r", encoding="utf-8") as f:
            registry = json.load(f)
    except Exception:
        registry = []

registry = [e for e in registry if e.get("root_path") != root_path]
registry.append({
    "repo_url": repo_url,
    "root_path": root_path
})

with open(REGISTRY, "w", encoding="utf-8") as f:
    json.dump(registry, f, indent=2, ensure_ascii=False)

print(f"{root_path} in {REGISTRY} gespeichert.")