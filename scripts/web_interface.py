import os
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import Optional, List
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, RDFS
import uvicorn


EMBEDDINGS = None
ENTITY_NAMES = None
ENTITY_TO_IDX = None

def load_embeddings():
    """Load pre-trained graph embeddings"""
    global EMBEDDINGS, ENTITY_NAMES, ENTITY_TO_IDX
    
    embeddings_path = os.path.join(os.path.dirname(__file__), "..", "output", "recipe_embeddings.npz")
    
    if os.path.exists(embeddings_path):
        try:
            data = np.load(embeddings_path, allow_pickle=True)
            EMBEDDINGS = data['embeddings']
            ENTITY_NAMES = data['entities']
            ENTITY_TO_IDX = {name: idx for idx, name in enumerate(ENTITY_NAMES)}
            print(f"✓ Loaded embeddings for {len(ENTITY_NAMES)} entities")
            return True
        except Exception as e:
            print(f"✗ Error loading embeddings: {e}")
            return False
    else:
        print(f"✗ Embeddings file not found: {embeddings_path}")
        return False

# Load embeddings on startup
load_embeddings()


def find_similar_entities(entity_name, top_k=5, entity_type=None):
    """Find entities similar to the given entity using embeddings"""
    global EMBEDDINGS, ENTITY_NAMES, ENTITY_TO_IDX
    
    if EMBEDDINGS is None:
        return []
    
    # Find the entity
    if entity_name not in ENTITY_TO_IDX:
        # Try partial match
        matches = [name for name in ENTITY_NAMES if entity_name.lower() in name.lower()]
        if matches:
            entity_name = matches[0]
        else:
            return []
    
    idx = ENTITY_TO_IDX[entity_name]
    entity_embedding = EMBEDDINGS[idx].reshape(1, -1)
    
    # Calculate similarities
    similarities = cosine_similarity(entity_embedding, EMBEDDINGS)[0]
    
    # Get top-k similar (excluding self)
    similar_indices = np.argsort(similarities)[::-1][1:top_k+10]  # Get extra to filter
    
    results = []
    for sim_idx in similar_indices:
        sim_name = ENTITY_NAMES[sim_idx]
        sim_score = similarities[sim_idx]
        
        # Filter by entity type if specified
        if entity_type == "recipe":
            if "recipe_" in sim_name.lower() or "Recipe" in sim_name:
                results.append({"name": sim_name, "similarity": float(sim_score)})
        elif entity_type == "ingredient":
            if "recipe_" not in sim_name.lower() and "Recipe" not in sim_name and "Cuisine" not in sim_name:
                results.append({"name": sim_name, "similarity": float(sim_score)})
        else:
            results.append({"name": sim_name, "similarity": float(sim_score)})
        
        if len(results) >= top_k:
            break
    
    return results




# FastAPI app
app = FastAPI(
    title="Recipe Knowledge Graph",
    description="A Semantic Web Recipe Recommendation System",
    version="1.0.0"
)

# Namespaces
RECIPE = Namespace("http://example.org/recipe/")
INGREDIENT = Namespace("http://example.org/ingredient/")
USDA = Namespace("http://example.org/usda/")


g = None


def load_knowledge_graph():
    """Load the RDF knowledge graph."""
    global g
    g = Graph()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Try loading the most complete RDF file available
    possible_files = [
        os.path.join(script_dir, "..", "output", "recipes_with_foodon.ttl"),
        os.path.join(script_dir, "..", "output", "recipes_with_usda.ttl"),
        os.path.join(script_dir, "..", "output", "recipes_integrated.ttl"),
        os.path.join(script_dir, "..", "output", "recipes_with_ontology.ttl"),
        os.path.join(script_dir, "..", "output", "recipes.ttl"),
    ]
    
    for path in possible_files:
        if os.path.exists(path):
            print(f"Loading: {path}")
            g.parse(path, format="turtle")
            print(f"Loaded {len(g)} triples")
            return
    
    print("WARNING: No RDF file found!")


def get_all_recipes():
    """Get all recipes from the knowledge graph."""
    query = """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX schema: <http://schema.org/>
    SELECT ?uri ?title ?time ?calories ?protein ?image
    WHERE {
        ?uri a recipe:Recipe .
        ?uri recipe:title ?title .
        OPTIONAL { ?uri recipe:readyInMinutes ?time }
        OPTIONAL { ?uri schema:image ?image }
        OPTIONAL { 
            ?uri recipe:hasNutrition ?n .
            ?n recipe:calories ?calories .
            ?n recipe:protein ?protein .
        }
    }
    ORDER BY ?title
    """
    
    results = g.query(query)
    recipes = []
    for row in results:
        recipes.append({
            "uri": str(row.uri),
            "title": str(row.title),
            "time": int(row.time) if row.time else None,
            "calories": float(row.calories) if row.calories else None,
            "protein": float(row.protein) if row.protein else None,
            "image": str(row.image) if row.image else None,
        })
    return recipes


def get_recipe_details(recipe_uri):
    """Get detailed information about a recipe."""
    # Basic info
    query = f"""
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX schema: <http://schema.org/>
    SELECT ?title ?time ?servings ?image ?sourceUrl
    WHERE {{
        <{recipe_uri}> recipe:title ?title .
        OPTIONAL {{ <{recipe_uri}> recipe:readyInMinutes ?time }}
        OPTIONAL {{ <{recipe_uri}> recipe:servings ?servings }}
        OPTIONAL {{ <{recipe_uri}> schema:image ?image }}
        OPTIONAL {{ <{recipe_uri}> recipe:sourceUrl ?sourceUrl }}
    }}
    """
    
    result = list(g.query(query))
    if not result:
        return None
    
    row = result[0]
    recipe_id = recipe_uri.split('_')[-1]   
    recipe = {
        "uri": recipe_uri,
        "id": recipe_id,                     
        "title": str(row.title),
        "time": int(row.time) if row.time else None,
        "servings": int(row.servings) if row.servings else None,
        "image": str(row.image) if row.image else None,
        "sourceUrl": str(row.sourceUrl) if row.sourceUrl else None,
    }
    
    # Get ingredients
    ing_query = f"""
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?name
    WHERE {{
        <{recipe_uri}> recipe:hasIngredient ?ing .
        ?ing rdfs:label ?name .
    }}
    """
    
    recipe["ingredients"] = [str(row.name) for row in g.query(ing_query)]
    
    # Get nutrition
    nut_query = f"""
    PREFIX recipe: <http://example.org/recipe/>
    
    SELECT ?calories ?protein ?fat ?carbs
    WHERE {{
        <{recipe_uri}> recipe:hasNutrition ?n .
        ?n recipe:calories ?calories .
        ?n recipe:protein ?protein .
        ?n recipe:fat ?fat .
        ?n recipe:carbohydrates ?carbs .
    }}
    """
    
    nut_result = list(g.query(nut_query))
    if nut_result:
        row = nut_result[0]
        recipe["nutrition"] = {
            "calories": float(row.calories) if row.calories else None,
            "protein": float(row.protein) if row.protein else None,
            "fat": float(row.fat) if row.fat else None,
            "carbs": float(row.carbs) if row.carbs else None,
        }
    
    # Get diets
    diet_query = f"""
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?name
    WHERE {{
        <{recipe_uri}> recipe:hasDiet ?diet .
        ?diet rdfs:label ?name .
    }}
    """
    
    recipe["diets"] = [str(row.name) for row in g.query(diet_query)]
    
    # Get cuisines
    cuisine_query = f"""
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?name
    WHERE {{
        <{recipe_uri}> recipe:hasCuisine ?cuisine .
        ?cuisine rdfs:label ?name .
    }}
    """
    
    recipe["cuisines"] = [str(row.name) for row in g.query(cuisine_query)]
    
    return recipe


def search_recipes(ingredient: str = None, diet: str = None, cuisine: str = None, 
                   max_calories: int = None, max_time: int = None):
    """Search recipes with various filters."""
    
    filters = []
    
    if ingredient:
        filters.append(f"""
            ?uri recipe:hasIngredient ?ing .
            ?ing rdfs:label ?ingName .
            FILTER (CONTAINS(LCASE(?ingName), LCASE("{ingredient}")))
        """)
    
    if diet:
        filters.append(f"""
            ?uri recipe:hasDiet ?diet .
            ?diet rdfs:label ?dietName .
            FILTER (CONTAINS(LCASE(?dietName), LCASE("{diet}")))
        """)
    
    if cuisine:
        filters.append(f"""
            ?uri recipe:hasCuisine ?cuisine .
            ?cuisine rdfs:label ?cuisineName .
            FILTER (CONTAINS(LCASE(?cuisineName), LCASE("{cuisine}")))
        """)
    
    if max_calories:
        filters.append(f"""
            ?uri recipe:hasNutrition ?n .
            ?n recipe:calories ?cal .
            FILTER (?cal <= {max_calories})
        """)
    
    if max_time:
        filters.append(f"""
            ?uri recipe:readyInMinutes ?time .
            FILTER (?time <= {max_time})
        """)
    
    filter_str = "\n".join(filters)
    
    query = f"""
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT DISTINCT ?uri ?title ?time ?calories ?protein ?image
    WHERE {{
        ?uri a recipe:Recipe .
        ?uri recipe:title ?title .
        OPTIONAL {{ ?uri recipe:readyInMinutes ?time }}
        OPTIONAL {{ ?uri recipe:image ?image }}
        OPTIONAL {{ 
            ?uri recipe:hasNutrition ?nut .
            ?nut recipe:calories ?calories .
            ?nut recipe:protein ?protein .
        }}
        {filter_str}
    }}
    ORDER BY ?title
    LIMIT 50
    """
    
    results = g.query(query)
    recipes = []
    for row in results:
        recipes.append({
            "uri": str(row.uri),
            "title": str(row.title),
            "time": int(row.time) if row.time else None,
            "calories": float(row.calories) if row.calories else None,
            "protein": float(row.protein) if row.protein else None,
            "image": str(row.image) if row.image else None,
        })
    return recipes


def get_all_diets():
    """Get all diet types."""
    query = """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT DISTINCT ?name (COUNT(?r) as ?num)
    WHERE {
        ?r recipe:hasDiet ?diet .
        ?diet rdfs:label ?name .
    }
    GROUP BY ?name
    ORDER BY DESC(?num)
    """
    return [(str(row.name), int(row.num)) for row in g.query(query)]


def get_all_cuisines():
    """Get all cuisine types."""
    query = """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT DISTINCT ?name (COUNT(?r) as ?num)
    WHERE {
        ?r recipe:hasCuisine ?cuisine .
        ?cuisine rdfs:label ?name .
    }
    GROUP BY ?name
    ORDER BY DESC(?num)
    """
    return [(str(row.name), int(row.num)) for row in g.query(query)]


def get_statistics():
    """Get knowledge graph statistics."""
    stats = {
        "total_triples": len(g),
        "recipes": 0,
        "ingredients": 0,
        "diets": 0,
        "cuisines": 0,
    }
    
    # Count recipes
    query = "SELECT (COUNT(?r) as ?num) WHERE { ?r a <http://example.org/recipe/Recipe> }"
    for row in g.query(query):
        stats["recipes"] = int(row.num)
    
    # Count ingredients
    query = "SELECT (COUNT(?i) as ?num) WHERE { ?i a <http://example.org/recipe/Ingredient> }"
    for row in g.query(query):
        stats["ingredients"] = int(row.num)
    
    return stats


def get_graph_data():
    """Get data for knowledge graph visualization."""
    nodes = []
    edges = []
    seen_nodes = set()
    
    # Get recipes and their ingredients (limit for performance)
    query = """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?recipe ?recipeTitle ?ingredient ?ingredientName
    WHERE {
        ?recipe a recipe:Recipe .
        ?recipe recipe:title ?recipeTitle .
        ?recipe recipe:hasIngredient ?ingredient .
        ?ingredient rdfs:label ?ingredientName .
    }
    LIMIT 200
    """
    
    for row in g.query(query):
        recipe_id = str(row.recipe).split("/")[-1]
        ing_id = str(row.ingredient).split("/")[-1]
        
        if recipe_id not in seen_nodes:
            nodes.append({
                "id": recipe_id,
                "label": str(row.recipeTitle)[:30],
                "type": "recipe",
                "color": "#4CAF50"
            })
            seen_nodes.add(recipe_id)
        
        if ing_id not in seen_nodes:
            nodes.append({
                "id": ing_id,
                "label": str(row.ingredientName)[:20],
                "type": "ingredient",
                "color": "#2196F3"
            })
            seen_nodes.add(ing_id)
        
        edges.append({
            "from": recipe_id,
            "to": ing_id
        })
    
    return {"nodes": nodes, "edges": edges}


# HTML Templates
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Recipe Knowledge Graph</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/vis-network@9.1.2/dist/vis-network.min.js"></script>
    <style>
        :root {
            --primary-color: #4CAF50;
            --secondary-color: #2196F3;
            --accent-color: #FF9800;
        }
        
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        .navbar {
            background: rgba(255, 255, 255, 0.95) !important;
            box-shadow: 0 2px 20px rgba(0,0,0,0.1);
        }
        
        .navbar-brand {
            font-weight: bold;
            color: var(--primary-color) !important;
        }
        
        .card {
            border: none;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            overflow: hidden;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 50px rgba(0,0,0,0.2);
        }
        
        .recipe-card img {
            height: 200px;
            width: 100%;
            object-fit: cover;
            background-color: #e9ecef;
        }
        
        .recipe-card {
            height: 100%;
            display: flex;
            flex-direction: column;
        }    
        
        .recipe-card .card-body {
             flex: 1;
             display: flex;
             flex-direction: column;
             justify-content: space-between;
             padding: 1.5rem;
        }
        
        

        .badge-diet {
            background: var(--primary-color);
            margin: 2px;
        }
        
        .badge-cuisine {
            background: var(--secondary-color);
            margin: 2px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white;
            text-align: center;
            padding: 2rem;
        }
        
        .stat-card h2 {
            font-size: 3rem;
            font-weight: bold;
        }
        
        .search-box {
            background: white;
            border-radius: 15px;
            padding: 2rem;
            margin-bottom: 2rem;
        }
        
        .btn-search {
            background: var(--primary-color);
            border: none;
            padding: 0.75rem 2rem;
            font-weight: bold;
        }
        
        .btn-search:hover {
            background: #45a049;
        }
        
        #graph-container {
            height: 500px;
            background: white;
            border-radius: 15px;
            overflow: hidden;
        }
        
        .hero-section {
            padding: 4rem 0;
            text-align: center;
            color: white;
        }
        
        .hero-section h1 {
            font-size: 3rem;
            font-weight: bold;
            margin-bottom: 1rem;
        }
        
        .hero-section p {
            font-size: 1.25rem;
            opacity: 0.9;
        }
        
        .nutrition-badge {
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            margin: 0.25rem;
            font-size: 0.85rem;
        }
        
        .nutrition-calories { background: #ffebee; color: #c62828; }
        .nutrition-protein { background: #e3f2fd; color: #1565c0; }
        .nutrition-time { background: #fff3e0; color: #ef6c00; }
        
        .filter-section {
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        
        footer {
            background: rgba(0,0,0,0.2);
            color: white;
            padding: 2rem 0;
            margin-top: 3rem;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-light">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-utensils me-2"></i>Recipe Knowledge Graph
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/"><i class="fas fa-home me-1"></i>Home</a>
                <a class="nav-link" href="/search"><i class="fas fa-search me-1"></i>Search</a>
                <a class="nav-link" href="/similar">Similar</a> 
                <a class="nav-link" href="/graph"><i class="fas fa-project-diagram me-1"></i>Graph</a>
                <a class="nav-link" href="/stats"><i class="fas fa-chart-bar me-1"></i>Stats</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {{content}}
    </div>


    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""


@app.on_event("startup")
async def startup_event():
    """Load knowledge graph on startup."""
    load_knowledge_graph()


@app.get("/", response_class=HTMLResponse)
async def home():
    """Home page with statistics and featured recipes."""
    stats = get_statistics()
    recipes = get_all_recipes()[:6]  # Featured recipes
    diets = get_all_diets()[:5]
    cuisines = get_all_cuisines()[:5]
    
    content = f"""
    <div class="hero-section">
        <h1><i class="fas fa-utensils me-3"></i>Recipe Knowledge Graph</h1>
        <p>A Semantic Web-powered Recipe Recommendation System</p>
        <p class="mt-3">
            <span class="badge bg-light text-dark p-2 m-1"><i class="fas fa-database me-1"></i>{stats['total_triples']:,} Triples</span>
            <span class="badge bg-light text-dark p-2 m-1"><i class="fas fa-book-open me-1"></i>{stats['recipes']} Recipes</span>
            <span class="badge bg-light text-dark p-2 m-1"><i class="fas fa-carrot me-1"></i>{stats['ingredients']} Ingredients</span>
        </p>
    </div>
    
    <div class="row mb-4">
        <div class="col-md-4">
            <div class="card stat-card">
                <h2>{stats['total_triples']:,}</h2>
                <p><i class="fas fa-database me-2"></i>RDF Triples</p>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card stat-card">
                <h2>{stats['recipes']}</h2>
                <p><i class="fas fa-book-open me-2"></i>Recipes</p>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card stat-card">
                <h2>{stats['ingredients']}</h2>
                <p><i class="fas fa-carrot me-2"></i>Ingredients</p>
            </div>
        </div>
    </div>
    
    <div class="card search-box">
        <h4><i class="fas fa-search me-2"></i>Quick Search</h4>
        <form action="/search" method="get" class="row g-3 mt-2">
            <div class="col-md-4">
                <input type="text" class="form-control" name="ingredient" placeholder="Ingredient (e.g., chicken)">
            </div>
            <div class="col-md-3">
                <select class="form-select" name="diet">
                    <option value="">Any Diet</option>
                    {"".join(f'<option value="{d[0]}">{d[0]} ({d[1]})</option>' for d in diets)}
                </select>
            </div>
            <div class="col-md-3">
                <select class="form-select" name="cuisine">
                    <option value="">Any Cuisine</option>
                    {"".join(f'<option value="{c[0]}">{c[0]} ({c[1]})</option>' for c in cuisines)}
                </select>
            </div>
            <div class="col-md-2">
                <button type="submit" class="btn btn-search text-white w-100">
                    <i class="fas fa-search me-1"></i>Search
                </button>
            </div>
        </form>
    </div>
    
    <h3 class="text-white mb-4"><i class="fas fa-star me-2"></i>Featured Recipes</h3>
    <div class="row">
        {"".join(f'''
        <div class="col-md-4 mb-4">
            <div class="card recipe-card">
                <img src="{r['image'] if r['image'] and r['image'].startswith('http') else 'https://placehold.co/400x200/667eea/ffffff?text=Recipe'}" class="card-img-top" alt="{r['title']}" onerror="this.src='https://placehold.co/400x200/667eea/ffffff?text=Recipe'">
                <div class="card-body">
                    <h5 class="card-title">{r['title'][:40]}{"..." if len(r['title']) > 40 else ""}</h5>
                    <div class="mb-2">
                        {f'<span class="nutrition-badge nutrition-time"><i class="fas fa-clock me-1"></i>{r["time"]} min</span>' if r['time'] else ''}
                        {f'<span class="nutrition-badge nutrition-calories"><i class="fas fa-fire me-1"></i>{r["calories"]:.0f} kcal</span>' if r['calories'] else ''}
                        {f'<span class="nutrition-badge nutrition-protein"><i class="fas fa-drumstick-bite me-1"></i>{r["protein"]:.0f}g protein</span>' if r['protein'] else ''}
                    </div>
                    <a href="/recipe/{r['uri'].split('/')[-1]}" class="btn btn-outline-success btn-sm">View Details</a>
                </div>
            </div>
        </div>
        ''' for r in recipes)}
    </div>
    
    <div class="row mt-4">
        <div class="col-md-6">
            <div class="card p-4">
                <h4><i class="fas fa-leaf me-2 text-success"></i>Diet Types</h4>
                <div class="mt-3">
                    {"".join(f'<a href="/search?diet={d[0]}" class="badge badge-diet text-white m-1 p-2 text-decoration-none">{d[0]} ({d[1]})</a>' for d in diets)}
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card p-4">
                <h4><i class="fas fa-globe me-2 text-primary"></i>Cuisines</h4>
                <div class="mt-3">
                    {"".join(f'<a href="/search?cuisine={c[0]}" class="badge badge-cuisine text-white m-1 p-2 text-decoration-none">{c[0]} ({c[1]})</a>' for c in cuisines)}
                </div>
            </div>
        </div>
    </div>
    """
    
    return HTML_TEMPLATE.replace("{{content}}", content)


@app.get("/search", response_class=HTMLResponse)
async def search_page(
    ingredient: str = None,
    diet: str = None,
    cuisine: str = None,
    max_calories: int = None,
    max_time: int = None
):
    """Search page with filters."""
    recipes = search_recipes(ingredient, diet, cuisine, max_calories, max_time)
    diets = get_all_diets()
    cuisines = get_all_cuisines()
    
    # Build active filters display
    active_filters = []
    if ingredient:
        active_filters.append(f'Ingredient: "{ingredient}"')
    if diet:
        active_filters.append(f'Diet: "{diet}"')
    if cuisine:
        active_filters.append(f'Cuisine: "{cuisine}"')
    if max_calories:
        active_filters.append(f'Max {max_calories} kcal')
    if max_time:
        active_filters.append(f'Max {max_time} min')
    
    filter_display = " + ".join(active_filters) if active_filters else "All Recipes"
    
    content = f"""
    <h2 class="text-white mb-4"><i class="fas fa-search me-2"></i>Search Recipes</h2>
    
    <div class="card search-box">
        <form action="/search" method="get" class="row g-3">
            <div class="col-md-3">
                <label class="form-label">Ingredient</label>
                <input type="text" class="form-control" name="ingredient" value="{ingredient or ''}" placeholder="e.g., chicken, tomato">
            </div>
            <div class="col-md-2">
                <label class="form-label">Diet</label>
                <select class="form-select" name="diet">
                    <option value="">Any</option>
                    {"".join(f'<option value="{d[0]}" {"selected" if d[0] == diet else ""}>{d[0]}</option>' for d in diets)}
                </select>
            </div>
            <div class="col-md-2">
                <label class="form-label">Cuisine</label>
                <select class="form-select" name="cuisine">
                    <option value="">Any</option>
                    {"".join(f'<option value="{c[0]}" {"selected" if c[0] == cuisine else ""}>{c[0]}</option>' for c in cuisines)}
                </select>
            </div>
            <div class="col-md-2">
                <label class="form-label">Max Calories</label>
                <input type="number" class="form-control" name="max_calories" value="{max_calories or ''}" placeholder="e.g., 500">
            </div>
            <div class="col-md-2">
                <label class="form-label">Max Time (min)</label>
                <input type="number" class="form-control" name="max_time" value="{max_time or ''}" placeholder="e.g., 30">
            </div>
            <div class="col-md-1 d-flex align-items-end">
                <button type="submit" class="btn btn-search text-white w-100">
                    <i class="fas fa-search"></i>
                </button>
            </div>
        </form>
    </div>
    
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h4 class="text-white mb-0">{filter_display}</h4>
        <span class="badge bg-white text-dark p-2">{len(recipes)} recipes found</span>
    </div>
    
    <div class="row">
        {"".join(f'''
        <div class="col-md-4 mb-4">
            <div class="card recipe-card">
                <img src="{r['image'] if r['image'] and r['image'].startswith('http') else 'https://placehold.co/400x200/667eea/ffffff?text=Recipe'}" class="card-img-top" alt="{r['title']}" onerror="this.src='https://placehold.co/400x200/667eea/ffffff?text=Recipe'">
                <div class="card-body">
                    <h5 class="card-title">{r['title'][:40]}{"..." if len(r['title']) > 40 else ""}</h5>
                    <div class="mb-2">
                        {f'<span class="nutrition-badge nutrition-time"><i class="fas fa-clock me-1"></i>{r["time"]} min</span>' if r['time'] else ''}
                        {f'<span class="nutrition-badge nutrition-calories"><i class="fas fa-fire me-1"></i>{r["calories"]:.0f} kcal</span>' if r['calories'] else ''}
                    </div>
                    <a href="/recipe/{r['uri'].split('/')[-1]}" class="btn btn-outline-success btn-sm">View Details</a>
                </div>
            </div>
        </div>
        ''' for r in recipes) if recipes else '<div class="col-12"><div class="card p-4 text-center"><p class="mb-0">No recipes found. Try different filters!</p></div></div>'}
    </div>
    """
    
    return HTML_TEMPLATE.replace("{{content}}", content)


@app.get("/recipe/{recipe_id}", response_class=HTMLResponse)
async def recipe_detail(recipe_id: str):
    """Recipe detail page."""
    recipe_uri = f"http://example.org/recipe/{recipe_id}"
    recipe = get_recipe_details(recipe_uri)
    
    if not recipe:
        return HTML_TEMPLATE.replace("{{content}}", "<h2>Recipe not found</h2>")
    
    content = f"""
    <div class="row">
        <div class="col-md-6">
           <img src="{recipe.get('image') if recipe.get('image') and recipe.get('image').startswith('http') else 'https://placehold.co/600x400/667eea/ffffff?text=Recipe'}" onerror="this.src='https://placehold.co/600x400/667eea/ffffff?text=Recipe'"
                 class="img-fluid rounded shadow" alt="{recipe['title']}">
        </div>
        <div class="col-md-6">
            <div class="card p-4">
                <h2>{recipe['title']}</h2>
                
                <div class="mt-3">
                    {f'<span class="nutrition-badge nutrition-time"><i class="fas fa-clock me-1"></i>{recipe["time"]} minutes</span>' if recipe.get('time') else ''}
                    {f'<span class="nutrition-badge nutrition-calories"><i class="fas fa-users me-1"></i>{recipe["servings"]} servings</span>' if recipe.get('servings') else ''}
                </div>
                
                {f'''
                <div class="mt-3">
                    <h5>Diets</h5>
                    {"".join(f'<span class="badge badge-diet text-white m-1">{d}</span>' for d in recipe.get('diets', []))}
                </div>
                ''' if recipe.get('diets') else ''}
                
                {f'''
                <div class="mt-3">
                    <h5>Cuisines</h5>
                    {"".join(f'<span class="badge badge-cuisine text-white m-1">{c}</span>' for c in recipe.get('cuisines', []))}
                </div>
                ''' if recipe.get('cuisines') else ''}
                
                {f'''
                <div class="mt-4">
                    <h5>Nutrition (per serving)</h5>
                    <div class="row text-center mt-3">
                        <div class="col-3">
                            <div class="p-2 bg-light rounded">
                                <strong>{recipe["nutrition"]["calories"]:.0f}</strong><br>
                                <small>Calories</small>
                            </div>
                        </div>
                        <div class="col-3">
                            <div class="p-2 bg-light rounded">
                                <strong>{recipe["nutrition"]["protein"]:.0f}g</strong><br>
                                <small>Protein</small>
                            </div>
                        </div>
                        <div class="col-3">
                            <div class="p-2 bg-light rounded">
                                <strong>{recipe["nutrition"]["carbs"]:.0f}g</strong><br>
                                <small>Carbs</small>
                            </div>
                        </div>
                        <div class="col-3">
                            <div class="p-2 bg-light rounded">
                                <strong>{recipe["nutrition"]["fat"]:.0f}g</strong><br>
                                <small>Fat</small>
                            </div>
                        </div>
                    </div>
                </div>
                ''' if recipe.get('nutrition') else ''}
                
                <a href="https://spoonacular.com/recipes/{recipe['title'].lower().replace(' ', '-')}-{recipe_uri.split('_')[-1]}" target="_blank" class="btn btn-success mt-4"><i class="fas fa-external-link-alt me-2"></i>View Original Recipe</a>
            </div>
        </div>
    </div>
    
    <div class="row mt-4">
        <div class="col-12">
            <div class="card p-4">
                <h4><i class="fas fa-carrot me-2"></i>Ingredients ({len(recipe.get('ingredients', []))})</h4>
                <div class="row mt-3">
                    {"".join(f'<div class="col-md-4 mb-2"><i class="fas fa-check text-success me-2"></i>{ing}</div>' for ing in recipe.get('ingredients', []))}
                </div>
            </div>
        </div>
    </div>
    
    <div class="mt-3">
        <a href="/" class="btn btn-outline-light"><i class="fas fa-arrow-left me-2"></i>Back to Home</a>
        <a href="/search" class="btn btn-outline-light"><i class="fas fa-search me-2"></i>Search Recipes</a>
    </div>
    """
    
    return HTML_TEMPLATE.replace("{{content}}", content)

@app.get("/api/similar/{entity_name}")
async def get_similar_entities(entity_name: str, top_k: int = 5, entity_type: str = None):
    """API endpoint to find similar entities"""
    results = find_similar_entities(entity_name, top_k, entity_type)
    return {"entity": entity_name, "similar": results}

@app.get("/similar", response_class=HTMLResponse)
async def similar_page(request: Request):
    """Similarity search page"""
    
    # Get list of recipes for dropdown
    recipes = get_all_recipes()
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Find Similar Recipes - Recipe Knowledge Graph</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            body {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; color: white; }}
            .navbar {{ background: rgba(0,0,0,0.3) !important; }}
            .card {{ background: rgba(255,255,255,0.1); border: none; backdrop-filter: blur(10px); }}
            .form-select, .form-control {{ background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: white; }}
            .form-select option {{ background: #1a1a2e; color: white; }}
            .btn-primary {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; }}
            .btn-primary:hover {{ background: linear-gradient(135deg, #764ba2 0%, #667eea 100%); }}
            .result-card {{ background: linear-gradient(135deg, rgba(102,126,234,0.2) 0%, rgba(118,75,162,0.2) 100%); 
                          border-radius: 15px; padding: 20px; margin: 10px 0; transition: transform 0.3s; }}
            .result-card:hover {{ transform: translateY(-5px); }}
            .similarity-bar {{ height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden; }}
            .similarity-fill {{ height: 100%; background: linear-gradient(90deg, #667eea, #764ba2); border-radius: 4px; }}
            .similarity-score {{ font-size: 1.5rem; font-weight: bold; color: #667eea; }}
        </style>
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark">
            <div class="container">
                <a class="navbar-brand" href="/"><i class="fas fa-utensils me-2"></i>Recipe Knowledge Graph</a>
                <div class="navbar-nav ms-auto">
                    <a class="nav-link" href="/">Home</a>
                    <a class="nav-link" href="/search">Search</a>
                    <a class="nav-link active" href="/similar">Similar</a>
                    <a class="nav-link" href="/graph">Graph</a>
                    <a class="nav-link" href="/stats">Stats</a>
                </div>
            </div>
        </nav>
        
        <div class="container py-5">
            <div class="text-center mb-5">
                <h1><i class="fas fa-magic me-3"></i>Find Similar Recipes</h1>
                <p class="lead">Using Graph Embeddings (PyKEEN/RotatE)</p>
            </div>
            
            <div class="row justify-content-center">
                <div class="col-md-8">
                    <div class="card p-4 mb-4">
                        <h5><i class="fas fa-search me-2"></i>Select a Recipe</h5>
                        <div class="row g-3 mt-2">
                            <div class="col-md-8">
                                <select id="recipeSelect" class="form-select">
                                    <option value="">-- Select a recipe --</option>
                                    {"".join(f'<option value="{r.get("uri", "").split("/")[-1] if r.get("uri") else ""}">{r.get("title", "Unknown")}</option>' for r in recipes)}
                                </select>
                            </div>
                            <div class="col-md-4">
                                <button onclick="findSimilar()" class="btn btn-primary w-100">
                                    <i class="fas fa-search me-2"></i>Find Similar
                                </button>
                            </div>
                        </div>
                        
                        <div class="mt-4">
                            <h6>Or search by ingredient:</h6>
                            <div class="row g-3">
                                <div class="col-md-8">
                                    <input type="text" id="ingredientInput" class="form-control" placeholder="e.g., chicken, garlic, tomato">
                                </div>
                                <div class="col-md-4">
                                    <button onclick="findSimilarIngredient()" class="btn btn-primary w-100">
                                        <i class="fas fa-leaf me-2"></i>Find Similar
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div id="results"></div>
                    
                
                </div>
            </div>
        </div>
        
        <script>
            async function findSimilar() {{
                const select = document.getElementById('recipeSelect');
                const entity = select.value;
                if (!entity) {{
                    alert('Please select a recipe');
                    return;
                }}
                
                const resultsDiv = document.getElementById('results');
                resultsDiv.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin fa-2x"></i><p>Finding similar recipes...</p></div>';
                
                try {{
                    const response = await fetch(`/api/similar/${{entity}}?top_k=5&entity_type=recipe`);
                    const data = await response.json();
                    displayResults(data, 'recipe');
                }} catch (error) {{
                    resultsDiv.innerHTML = '<div class="alert alert-danger">Error finding similar recipes</div>';
                }}
            }}
            
            async function findSimilarIngredient() {{
                const input = document.getElementById('ingredientInput');
                const entity = input.value.trim();
                if (!entity) {{
                    alert('Please enter an ingredient');
                    return;
                }}
                
                const resultsDiv = document.getElementById('results');
                resultsDiv.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin fa-2x"></i><p>Finding similar ingredients...</p></div>';
                
                try {{
                    const response = await fetch(`/api/similar/${{entity}}?top_k=5&entity_type=ingredient`);
                    const data = await response.json();
                    displayResults(data, 'ingredient');
                }} catch (error) {{
                    resultsDiv.innerHTML = '<div class="alert alert-danger">Error finding similar ingredients</div>';
                }}
            }}
            
            function displayResults(data, type) {{
                const resultsDiv = document.getElementById('results');
                
                if (!data.similar || data.similar.length === 0) {{
                    resultsDiv.innerHTML = '<div class="alert alert-warning">No similar items found</div>';
                    return;
                }}
                
                let html = `<h4 class="mb-3"><i class="fas fa-list me-2"></i>Similar to: ${{data.entity}}</h4>`;
                
                data.similar.forEach((item, index) => {{
                    const percentage = (item.similarity * 100).toFixed(1);
                    const name = item.name.split('/').pop().replace('recipe_', 'Recipe ').replace(/_/g, ' ');
                    
                    html += `
                         <div class="result-card" style="cursor: pointer;" onclick="window.location.href='/recipe/${{item.name.split('/').pop()}}'">
                           <div class="d-flex justify-content-between align-items-center">
                                <div>
                                     <span class="badge bg-primary me-2">#${{index + 1}}</span>
                                     <strong>${{name}}</strong>
                                </div>
                                <div class="similarity-score">${{percentage}}%</div>
                           </div>
                           <div class="similarity-bar mt-2">
                                 <div class="similarity-fill" style="width: ${{percentage}}%"></div>
                            </div>
                          </div>
                    `;
                }});
                
                resultsDiv.innerHTML = html;
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/graph", response_class=HTMLResponse)
async def graph_page():
    """Knowledge graph visualization page."""
    graph_data = get_graph_data()
    
    content = f"""
    <h2 class="text-white mb-4"><i class="fas fa-project-diagram me-2"></i>Knowledge Graph Visualization</h2>
    
    <div class="card p-3 mb-3">
        <div class="row align-items-center">
            <div class="col-md-8">
                <p class="mb-0">
                    <span class="badge bg-success p-2 me-2"><i class="fas fa-circle me-1"></i>Recipes</span>
                    <span class="badge bg-primary p-2 me-2"><i class="fas fa-circle me-1"></i>Ingredients</span>
                    <span class="text-muted">Drag to explore • Scroll to zoom • Click nodes for details</span>
                </p>
            </div>
            <div class="col-md-4 text-end">
                <span class="badge bg-secondary p-2">{len(graph_data['nodes'])} nodes • {len(graph_data['edges'])} edges</span>
            </div>
        </div>
    </div>
    
    <div id="graph-container" class="card"></div>
    
    <script>
        var nodes = new vis.DataSet({json.dumps(graph_data['nodes'])});
        var edges = new vis.DataSet({json.dumps(graph_data['edges'])});
        
        var container = document.getElementById('graph-container');
        var data = {{ nodes: nodes, edges: edges }};
        var options = {{
            nodes: {{
                shape: 'dot',
                size: 16,
                font: {{ size: 12, color: '#333' }},
                borderWidth: 2,
                shadow: true
            }},
            edges: {{
                width: 1,
                color: {{ color: '#ccc', highlight: '#4CAF50' }},
                smooth: {{ type: 'continuous' }}
            }},
            physics: {{
                stabilization: {{ iterations: 100 }},
                barnesHut: {{
                    gravitationalConstant: -2000,
                    springLength: 100
                }}
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 100
            }}
        }};
        
        var network = new vis.Network(container, data, options);
        
        network.on("click", function(params) {{
            if (params.nodes.length > 0) {{
                var nodeId = params.nodes[0];
                var node = nodes.get(nodeId);
                if (node.type === 'recipe') {{
                    window.location.href = '/recipe/' + nodeId;
                }}
            }}
        }});
    </script>
    """
    
    return HTML_TEMPLATE.replace("{{content}}", content)


@app.get("/stats", response_class=HTMLResponse)
async def stats_page():
    """Statistics page."""
    stats = get_statistics()
    diets = get_all_diets()
    cuisines = get_all_cuisines()
    
    content = f"""
    <h2 class="text-white mb-4"><i class="fas fa-chart-bar me-2"></i>Knowledge Graph Statistics</h2>
    
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card stat-card">
                <h2>{stats['total_triples']:,}</h2>
                <p><i class="fas fa-database me-2"></i>Total Triples</p>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card">
                <h2>{stats['recipes']}</h2>
                <p><i class="fas fa-book-open me-2"></i>Recipes</p>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card">
                <h2>{stats['ingredients']}</h2>
                <p><i class="fas fa-carrot me-2"></i>Ingredients</p>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card">
                <h2>4</h2>
                <p><i class="fas fa-link me-2"></i>Data Sources</p>
            </div>
        </div>
    </div>
    
    <div class="row">
        <div class="col-md-6">
            <div class="card p-4">
                <h4><i class="fas fa-leaf me-2 text-success"></i>Recipes by Diet</h4>
                <table class="table mt-3">
                    <thead>
                        <tr><th>Diet Type</th><th>Count</th><th>%</th></tr>
                    </thead>
                    <tbody>
                        {"".join(f'<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[1]/stats["recipes"]*100:.1f}%</td></tr>' for d in diets)}
                    </tbody>
                </table>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card p-4">
                <h4><i class="fas fa-globe me-2 text-primary"></i>Recipes by Cuisine</h4>
                <table class="table mt-3">
                    <thead>
                        <tr><th>Cuisine</th><th>Count</th><th>%</th></tr>
                    </thead>
                    <tbody>
                        {"".join(f'<tr><td>{c[0]}</td><td>{c[1]}</td><td>{c[1]/stats["recipes"]*100:.1f}%</td></tr>' for c in cuisines)}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    """
    
    return HTML_TEMPLATE.replace("{{content}}", content)
            

# API Endpoints (for programmatic access)
@app.get("/api/recipes")
async def api_recipes(limit: int = 20):
    """API endpoint to get recipes."""
    return get_all_recipes()[:limit]


@app.get("/api/search")
async def api_search(
    ingredient: str = None,
    diet: str = None,
    cuisine: str = None,
    max_calories: int = None,
    max_time: int = None
):
    """API endpoint to search recipes."""
    return search_recipes(ingredient, diet, cuisine, max_calories, max_time)


@app.get("/api/stats")
async def api_stats():
    """API endpoint to get statistics."""
    return get_statistics()


if __name__ == "__main__":
    print("=" * 70)
    print("RECIPE KNOWLEDGE GRAPH WEB INTERFACE")
    print("=" * 70)
    print("\nStarting server...")
    
    print("=" * 70)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)