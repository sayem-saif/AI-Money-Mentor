import re

with open("templates/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Find all name attributes
matches = re.findall(r'name\s*=\s*["\']([^"\']+)["\']', html)
names = set(matches)

print("Found form field names:")
for name in sorted(names):
    print(f"  - {name}")

# Also check for problematic quotes
with open("templates/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
    
for i, line in enumerate(lines[40:60], start=40):
    if "input" in line and "name" in line:
        print(f"Line {i}: {repr(line[:100])}")
