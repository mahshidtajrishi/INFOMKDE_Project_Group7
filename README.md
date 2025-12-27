# Smart Recipe Knowledge Graph - Semantic Web Project

## 📁 Project Structure

```
recipe_knowledge_graph/
├── data/                          # Raw data from Spoonacular
│   └── sample_recipes.json        # Sample data (for testing)
├── scripts/
│   ├── fetch_spoonacular_data.py  # Script to fetch recipes from API
│   └── convert_to_rdf.py          # Script to convert JSON → RDF
├── output/
│   ├── recipes.ttl                # RDF output (Turtle format)
│   └── recipes.rdf                # RDF output (XML format)
└── README.md                      # This file
```

---

## 🚀 Quick Start (Step by Step)

### Step 1: Install Requirements

Make sure you have Python 3 installed, then run:

```bash
pip install rdflib requests
```

### Step 2: Get Spoonacular API Key (FREE)

1. Go to: https://spoonacular.com/food-api
2. Click "Start Now" → Create account
3. Go to Profile → Copy your API Key

### Step 3: Fetch Recipe Data

1. Open `scripts/fetch_spoonacular_data.py`
2. Replace `YOUR_API_KEY_HERE` with your actual API key
3. Run:

```bash
cd scripts
python fetch_spoonacular_data.py
```

This will save recipe data to `data/spoonacular_recipes_raw.json`

### Step 4: Convert to RDF

```bash
python convert_to_rdf.py
```

This creates:
- `output/recipes.ttl` - Human-readable RDF (Turtle format)
- `output/recipes.rdf` - Machine-readable RDF (XML format)

---

## 📊 Ontology Overview

### Classes (Types of Things)

| Class | Description |
|-------|-------------|
| `recipe:Recipe` | A food recipe |
| `recipe:Ingredient` | An ingredient used in recipes |
| `recipe:Cuisine` | Type of cuisine (Italian, Mexican, etc.) |
| `recipe:Diet` | Dietary category (vegetarian, vegan, gluten-free) |
| `recipe:NutritionInfo` | Nutritional information |

### Properties (Relationships)

| Property | Domain → Range | Description |
|----------|----------------|-------------|
| `recipe:hasIngredient` | Recipe → Ingredient | Links recipe to its ingredients |
| `recipe:hasCuisine` | Recipe → Cuisine | Links recipe to cuisine type |
| `recipe:hasDiet` | Recipe → Diet | Links recipe to dietary info |
| `recipe:hasNutrition` | Recipe → NutritionInfo | Links recipe to nutrition data |
| `recipe:title` | Recipe → String | Recipe name |
| `recipe:readyInMinutes` | Recipe → Integer | Preparation time |
| `recipe:servings` | Recipe → Integer | Number of servings |
| `recipe:calories` | NutritionInfo → Float | Calorie count |
| `recipe:protein` | NutritionInfo → Float | Protein in grams |

---

## 🔍 Example SPARQL Queries

Once you load the RDF into a triple store (like Apache Jena Fuseki), you can run queries:

### Query 1: Find all vegetarian recipes
```sparql
PREFIX recipe: <http://example.org/recipe/>

SELECT ?title WHERE {
    ?r a recipe:Recipe .
    ?r recipe:title ?title .
    ?r recipe:hasDiet recipe:diet_vegetarian .
}
```

### Query 2: Find recipes with less than 400 calories
```sparql
PREFIX recipe: <http://example.org/recipe/>

SELECT ?title ?calories WHERE {
    ?r a recipe:Recipe .
    ?r recipe:title ?title .
    ?r recipe:hasNutrition ?n .
    ?n recipe:calories ?calories .
    FILTER (?calories < 400)
}
```

### Query 3: Find all Italian recipes with their ingredients
```sparql
PREFIX recipe: <http://example.org/recipe/>
PREFIX cuisine: <http://example.org/cuisine/>

SELECT ?title ?ingredient WHERE {
    ?r a recipe:Recipe .
    ?r recipe:title ?title .
    ?r recipe:hasCuisine cuisine:italian .
    ?r recipe:hasIngredient ?ing .
    ?ing rdfs:label ?ingredient .
}
```

---

## 📋 Project Workflow (matches our flowchart)

```
┌─────────────────┐     ┌─────────────────┐
│  Spoonacular    │     │  Other Sources  │
│  API (JSON)     │     │  (if needed)    │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
    ┌────────────────────────────────┐
    │       RDF Mapping              │
    │  (convert_to_rdf.py)           │
    └────────────────┬───────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  Unified Knowledge    │
         │  Graph (recipes.ttl)  │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   Graph Database      │
         │   (Apache Jena)       │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  SPARQL Queries       │
         │  (Recommendation      │
         │   System)             │
         └───────────────────────┘
```

---

## 👥 Team Task Distribution

| Task | Status | Assigned To |
|------|--------|-------------|
| Data collection (Spoonacular) | ⬜ Not Started | |
| RDF Conversion Script | ✅ Done | Sanjana |
| Ontology Design | ✅ Done | Sanjana |
| SPARQL Queries | ⬜ Not Started | |
| Web UI / API | ⬜ Not Started | |
| Documentation | 🔄 In Progress | |

---

## 🛠️ Troubleshooting

**Problem: "No module named rdflib"**
→ Run: `pip install rdflib`

**Problem: API returns error 401**
→ Check your API key is correct and hasn't expired

**Problem: "No data found"**
→ Run `fetch_spoonacular_data.py` first before `convert_to_rdf.py`

---

## 📚 Resources

- [RDFLib Documentation](https://rdflib.readthedocs.io/)
- [Spoonacular API Docs](https://spoonacular.com/food-api/docs)
- [SPARQL Tutorial](https://www.w3.org/TR/sparql11-query/)
- [Turtle Syntax](https://www.w3.org/TR/turtle/)
