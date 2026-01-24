import json
from pathlib import Path

file1 = Path("data/spoonacular_recipes_raw.json")      # 15 recipes
file2 = Path("data/spoonacular_recipes_raw_30.json")   # 30 recipes
output = Path("data/spoonacular_recipes_raw_merged.json")

def load(file):
    with open(file, encoding="utf-8") as f:
        return json.load(f)["results"]

recipes1 = load(file1)
recipes2 = load(file2)

merged = {}
for r in recipes1 + recipes2:
    rid = r.get("id")
    if rid is not None:
        merged[rid] = r   

final_data = {
    "results": list(merged.values()),
    "meta": {
        "source": "Spoonacular API",
        "merged_from": [file1.name, file2.name],
        "total_recipes": len(merged)
    }
}

with open(output, "w", encoding="utf-8") as f:
    json.dump(final_data, f, indent=2, ensure_ascii=False)

print(f" Total unique recipes: {len(merged)}")