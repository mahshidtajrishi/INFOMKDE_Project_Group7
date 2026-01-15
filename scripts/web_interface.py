"""
Web Interface for Recipe Knowledge Graph using FastAPI and Fuseki
Requirements:
1. Start Fuseki: fuseki-server.bat --update --mem /recipes
2. Load data via http://localhost:3030 UI or curl command
3. Run this script: python web_interface_fuseki.py
"""

import os
import json
import requests
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import uvicorn


# ============================================================================
# CONFIGURATION
# ============================================================================

FUSEKI_URL = "http://localhost:3030"
DATASET = "/recipes"
SPARQL_ENDPOINT = f"{FUSEKI_URL}{DATASET}/sparql"
UPDATE_ENDPOINT = f"{FUSEKI_URL}{DATASET}/update"
DATA_ENDPOINT = f"{FUSEKI_URL}{DATASET}/data"


# ============================================================================
# EMBEDDINGS
# ============================================================================

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
            print(f"Loaded embeddings for {len(ENTITY_NAMES):,} entities")
            return True
        except Exception as e:
            print(f"Error loading embeddings: {e}")
            return False
    return False


def find_similar_entities(entity_name, top_k=5, entity_type=None):
    """Find similar entities using embeddings"""
    global EMBEDDINGS, ENTITY_NAMES, ENTITY_TO_IDX
    
    if EMBEDDINGS is None:
        return []
    
    matched_entity = None
    
    if entity_name in ENTITY_TO_IDX:
        matched_entity = entity_name
    else:
        if entity_type == "recipe":
            full_uri = f"http://example.org/food/recipe/{entity_name}"
            if full_uri in ENTITY_TO_IDX:
                matched_entity = full_uri
        elif entity_type == "ingredient":
            ing_name = entity_name.lower().replace(' ', '_')
            full_uri = f"http://example.org/food/ingredient/{ing_name}"
            if full_uri in ENTITY_TO_IDX:
                matched_entity = full_uri
        
        if matched_entity is None:
            matches = [name for name in ENTITY_NAMES if entity_name.lower() in name.lower()]
            if matches:
                if entity_type == "recipe":
                    recipe_matches = [m for m in matches if '/food/recipe/' in m]
                    if recipe_matches:
                        matched_entity = recipe_matches[0]
                elif entity_type == "ingredient":
                    ing_matches = [m for m in matches if '/food/ingredient/' in m]
                    if ing_matches:
                        matched_entity = ing_matches[0]
                else:
                    matched_entity = matches[0]
    
    if matched_entity is None:
        return []
    
    idx = ENTITY_TO_IDX[matched_entity]
    entity_embedding = EMBEDDINGS[idx].reshape(1, -1)
    similarities = cosine_similarity(entity_embedding, EMBEDDINGS)[0]
    
    if entity_type == "recipe":
        indices = [i for i, name in enumerate(ENTITY_NAMES) if '/food/recipe/' in name and i != idx]
        if not indices:
            return []
        sims = sorted([(i, similarities[i]) for i in indices], key=lambda x: x[1], reverse=True)
        similar_indices = [i for i, _ in sims[:top_k]]
    elif entity_type == "ingredient":
        indices = [i for i, name in enumerate(ENTITY_NAMES) if '/food/ingredient/' in name and i != idx]
        if not indices:
            return []
        sims = sorted([(i, similarities[i]) for i in indices], key=lambda x: x[1], reverse=True)
        similar_indices = [i for i, _ in sims[:top_k]]
    else:
        similar_indices = np.argsort(similarities)[::-1][1:top_k+1]
    
    return [{"name": ENTITY_NAMES[i], "similarity": float(similarities[i])} for i in similar_indices]


# ============================================================================
# FUSEKI SPARQL FUNCTIONS
# ============================================================================

def sparql_query(query_string):
    """Execute SPARQL query against Fuseki endpoint."""
    try:
        response = requests.post(
            SPARQL_ENDPOINT,
            data={"query": query_string},
            headers={"Accept": "application/sparql-results+json"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for binding in data.get("results", {}).get("bindings", []):
                row = {}
                for var, val in binding.items():
                    row[var] = val.get("value")
                results.append(row)
            return results
        else:
            print(f"SPARQL Error: {response.status_code} - {response.text}")
            return []
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to Fuseki. Is it running?")
        print(f"Expected endpoint: {SPARQL_ENDPOINT}")
        return []
    except Exception as e:
        print(f"SPARQL Error: {e}")
        return []


def check_fuseki_connection():
    """Check if Fuseki is running and has data."""
    try:
        response = requests.get(f"{FUSEKI_URL}/$/ping", timeout=5)
        if response.status_code == 200:
            # Check if dataset has data
            results = sparql_query("SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }")
            if results:
                count = int(results[0].get('count', 0))
                return True, count
            return True, 0
        return False, 0
    except:
        return False, 0


# ============================================================================
# DATA ACCESS FUNCTIONS
# ============================================================================

def get_statistics():
    """Get knowledge graph statistics."""
    stats = {
        "total_triples": 0,
        "recipes": 0,
        "ingredients": 0,
        "videos": 0,
        "dbpedia_links": 0,
        "wikidata_links": 0,
        "foodon_links": 0,
    }
    
    # Total triples
    results = sparql_query("SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }")
    if results:
        stats["total_triples"] = int(results[0].get('count', 0))
    
    # Recipes
    results = sparql_query("""
        PREFIX food: <http://data.lirmm.fr/ontologies/food#>
        SELECT (COUNT(?r) as ?count) WHERE { ?r a food:Recipe }
    """)
    if results:
        stats["recipes"] = int(results[0].get('count', 0))
    
    # Ingredients
    results = sparql_query("""
        PREFIX food: <http://data.lirmm.fr/ontologies/food#>
        SELECT (COUNT(?i) as ?count) WHERE { ?i a food:Ingredient }
    """)
    if results:
        stats["ingredients"] = int(results[0].get('count', 0))
    
    # Videos
    results = sparql_query("""
        PREFIX schema: <https://schema.org/>
        SELECT (COUNT(?v) as ?count) WHERE { ?r schema:video ?v }
    """)
    if results:
        stats["videos"] = int(results[0].get('count', 0))
    
    # External links
    results = sparql_query("""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT ?target WHERE { ?s owl:sameAs ?target }
    """)
    for row in results:
        target = row.get('target', '')
        if "dbpedia.org" in target:
            stats["dbpedia_links"] += 1
        elif "wikidata.org" in target:
            stats["wikidata_links"] += 1
        elif "obolibrary.org" in target:
            stats["foodon_links"] += 1
    
    return stats


def get_all_recipes(limit=100):
    """Get recipes."""
    query = f"""
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX schema: <https://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT DISTINCT ?uri ?title ?time ?calories ?protein ?image ?video
    WHERE {{
        ?uri a food:Recipe .
        OPTIONAL {{ ?uri schema:name ?title }}
        OPTIONAL {{ ?uri rdfs:label ?label }}
        OPTIONAL {{ ?uri schema:totalTime ?time }}
        OPTIONAL {{ ?uri schema:image ?image }}
        OPTIONAL {{ ?uri schema:video ?video }}
        OPTIONAL {{ 
            ?uri schema:nutrition ?n .
            ?n schema:calories ?calories .
            ?n schema:proteinContent ?protein .
        }}
    }}
    ORDER BY ?title
    LIMIT {limit}
    """
    
    results = sparql_query(query)
    recipes = []
    for row in results:
        recipes.append({
            "uri": row.get('uri', ''),
            "title": row.get('title') or row.get('label') or 'Untitled Recipe',
            "time": int(float(row['time'])) if row.get('time') else None,
            "calories": float(row['calories']) if row.get('calories') else None,
            "protein": float(row['protein']) if row.get('protein') else None,
            "image": row.get('image'),
            "has_video": bool(row.get('video')),
        })
    return recipes


def get_featured_recipes():
    """Get featured recipes from all three sources: MealDB, Spoonacular, RecipesNLG."""
    featured = []
    
    # MealDB recipes (have videos)
    mealdb_query = """
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX schema: <https://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT DISTINCT ?uri ?title ?time ?calories ?protein ?image ?video
    WHERE {
        ?uri a food:Recipe .
        ?uri schema:video ?video .
        OPTIONAL { ?uri schema:name ?title }
        OPTIONAL { ?uri rdfs:label ?label }
        OPTIONAL { ?uri schema:totalTime ?time }
        OPTIONAL { ?uri schema:image ?image }
        OPTIONAL { 
            ?uri schema:nutrition ?n .
            ?n schema:calories ?calories .
            ?n schema:proteinContent ?protein .
        }
    }
    LIMIT 2
    """
    
    # Spoonacular recipes (have nutrition data and images, no video)
    spoonacular_query = """
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX schema: <https://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT DISTINCT ?uri ?title ?time ?calories ?protein ?image ?video
    WHERE {
        ?uri a food:Recipe .
        ?uri schema:nutrition ?n .
        ?n schema:calories ?calories .
        ?uri schema:image ?image .
        FILTER NOT EXISTS { ?uri schema:video ?v }
        OPTIONAL { ?uri schema:name ?title }
        OPTIONAL { ?uri rdfs:label ?label }
        OPTIONAL { ?uri schema:totalTime ?time }
        OPTIONAL { ?n schema:proteinContent ?protein }
    }
    LIMIT 2
    """
    
    # RecipesNLG recipes (no nutrition, no video, no image typically)
    recipesnlg_query = """
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX schema: <https://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    
    SELECT DISTINCT ?uri ?title ?time ?image ?video
    WHERE {
        ?uri a food:Recipe .
        ?uri dcterms:source ?source .
        FILTER(CONTAINS(STR(?source), "Gathered"))
        FILTER NOT EXISTS { ?uri schema:video ?v }
        FILTER NOT EXISTS { ?uri schema:nutrition ?n }
        OPTIONAL { ?uri schema:name ?title }
        OPTIONAL { ?uri rdfs:label ?label }
        OPTIONAL { ?uri schema:totalTime ?time }
        OPTIONAL { ?uri schema:image ?image }
    }
    LIMIT 2
    """
    
    for query in [mealdb_query, spoonacular_query, recipesnlg_query]:
        results = sparql_query(query)
        for row in results:
            featured.append({
                "uri": row.get('uri', ''),
                "title": row.get('title') or row.get('label') or 'Untitled Recipe',
                "time": int(float(row['time'])) if row.get('time') else None,
                "calories": float(row['calories']) if row.get('calories') else None,
                "protein": float(row['protein']) if row.get('protein') else None,
                "image": row.get('image'),
                "has_video": bool(row.get('video')),
            })
    
    return featured


def get_recipe_details(recipe_id):
    """Get full recipe details by ID - handles different URI formats."""
    
    # First, try to find the recipe by ID pattern
    find_query = f"""
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX schema: <https://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?uri WHERE {{
        ?uri a food:Recipe .
        FILTER(CONTAINS(STR(?uri), "{recipe_id}"))
    }}
    LIMIT 1
    """
    
    uri_results = sparql_query(find_query)
    if not uri_results:
        return None
    
    recipe_uri = uri_results[0].get('uri')
    if not recipe_uri:
        return None
    
    query = f"""
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX schema: <https://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    
    SELECT ?title ?time ?servings ?image ?sourceUrl ?video ?instructions ?source ?mainPage
    WHERE {{
        <{recipe_uri}> a food:Recipe .
        OPTIONAL {{ <{recipe_uri}> schema:name ?title }}
        OPTIONAL {{ <{recipe_uri}> rdfs:label ?label }}
        OPTIONAL {{ <{recipe_uri}> schema:totalTime ?time }}
        OPTIONAL {{ <{recipe_uri}> schema:recipeYield ?servings }}
        OPTIONAL {{ <{recipe_uri}> schema:image ?image }}
        OPTIONAL {{ <{recipe_uri}> schema:url ?sourceUrl }}
        OPTIONAL {{ <{recipe_uri}> schema:mainEntityOfPage ?mainPage }}
        OPTIONAL {{ <{recipe_uri}> schema:video ?video }}
        OPTIONAL {{ <{recipe_uri}> schema:recipeInstructions ?instructions }}
        OPTIONAL {{ <{recipe_uri}> dcterms:source ?source }}
        BIND(COALESCE(?title, ?label, "Untitled") AS ?displayTitle)
    }}
    LIMIT 1
    """
    
    results = sparql_query(query)
    if not results:
        return None
    
    row = results[0]
    
    # Get the best available source URL
    source_url = row.get('sourceUrl') or row.get('mainPage')
    # Check if dcterms:source contains a URL (starts with http)
    if not source_url and row.get('source') and str(row.get('source', '')).startswith('http'):
        source_url = row.get('source')
    
    recipe = {
        "uri": recipe_uri,
        "id": recipe_id,
        "title": row.get('title') or row.get('label') or 'Untitled Recipe',
        "time": int(float(row['time'])) if row.get('time') else None,
        "servings": int(float(row['servings'])) if row.get('servings') else None,
        "image": row.get('image'),
        "sourceUrl": source_url,
        "video": row.get('video'),
        "instructions": row.get('instructions'),
        "source": row.get('source'),
    }
    
    # Ingredients
    ing_query = f"""
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?name WHERE {{
        <{recipe_uri}> food:ingredient ?ing .
        ?ing rdfs:label ?name .
    }}
    """
    recipe["ingredients"] = [r['name'] for r in sparql_query(ing_query) if r.get('name')]
    
    # Nutrition
    nut_query = f"""
    PREFIX schema: <https://schema.org/>
    SELECT ?calories ?protein ?fat ?carbs WHERE {{
        <{recipe_uri}> schema:nutrition ?n .
        OPTIONAL {{ ?n schema:calories ?calories }}
        OPTIONAL {{ ?n schema:proteinContent ?protein }}
        OPTIONAL {{ ?n schema:fatContent ?fat }}
        OPTIONAL {{ ?n schema:carbohydrateContent ?carbs }}
    }}
    """
    nut_results = sparql_query(nut_query)
    if nut_results:
        n = nut_results[0]
        recipe["nutrition"] = {
            "calories": float(n['calories']) if n.get('calories') else None,
            "protein": float(n['protein']) if n.get('protein') else None,
            "fat": float(n['fat']) if n.get('fat') else None,
            "carbs": float(n['carbs']) if n.get('carbs') else None,
        }
    
    # Diets
    diet_query = f"""
    PREFIX schema: <https://schema.org/>
    SELECT ?diet WHERE {{ <{recipe_uri}> schema:suitableForDiet ?diet }}
    """
    recipe["diets"] = [r['diet'].split('/')[-1].replace('_', ' ') for r in sparql_query(diet_query) if r.get('diet')]
    
    # Cuisines
    cuisine_query = f"""
    PREFIX schema: <https://schema.org/>
    SELECT ?cuisine WHERE {{ <{recipe_uri}> schema:recipeCuisine ?cuisine }}
    """
    recipe["cuisines"] = [r['cuisine'].split('/')[-1].replace('_', ' ') for r in sparql_query(cuisine_query) if r.get('cuisine')]
    
    return recipe


def search_recipes(name=None, ingredient=None, diet=None, cuisine=None, 
                   max_calories=None, max_time=None, limit=50):
    """Search recipes with filters."""
    
    filters = []
    
    if name:
        filters.append(f'FILTER(CONTAINS(LCASE(STR(?title)), LCASE("{name}")))')
    
    if ingredient:
        filters.append(f"""
            ?uri food:ingredient ?ing .
            ?ing rdfs:label ?ingName .
            FILTER(CONTAINS(LCASE(?ingName), LCASE("{ingredient}")))
        """)
    
    if diet:
        filters.append(f"""
            ?uri schema:suitableForDiet ?diet .
            FILTER(CONTAINS(LCASE(STR(?diet)), LCASE("{diet}")))
        """)
    
    if cuisine:
        filters.append(f"""
            ?uri schema:recipeCuisine ?cuisine .
            FILTER(CONTAINS(LCASE(STR(?cuisine)), LCASE("{cuisine}")))
        """)
    
    if max_calories:
        filters.append(f"""
            ?uri schema:nutrition ?nutFilter .
            ?nutFilter schema:calories ?calFilter .
            FILTER(?calFilter <= {max_calories})
        """)
    
    if max_time:
        filters.append(f"FILTER(?time <= {max_time})")
    
    filter_str = "\n".join(filters)
    
    query = f"""
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX schema: <https://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT DISTINCT ?uri ?title ?time ?calories ?protein ?image ?video
    WHERE {{
        ?uri a food:Recipe .
        OPTIONAL {{ ?uri schema:name ?title }}
        OPTIONAL {{ ?uri rdfs:label ?title }}
        OPTIONAL {{ ?uri schema:totalTime ?time }}
        OPTIONAL {{ ?uri schema:image ?image }}
        OPTIONAL {{ ?uri schema:video ?video }}
        OPTIONAL {{ 
            ?uri schema:nutrition ?nut .
            ?nut schema:calories ?calories .
            ?nut schema:proteinContent ?protein .
        }}
        {filter_str}
    }}
    ORDER BY ?title
    LIMIT {limit}
    """
    
    results = sparql_query(query)
    return [{
        "uri": row.get('uri', ''),
        "title": row.get('title', 'Untitled'),
        "time": int(row['time']) if row.get('time') else None,
        "calories": float(row['calories']) if row.get('calories') else None,
        "protein": float(row['protein']) if row.get('protein') else None,
        "image": row.get('image'),
        "has_video": bool(row.get('video')),
    } for row in results]


def get_all_diets():
    """Get diet types with counts."""
    query = """
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX schema: <https://schema.org/>
    SELECT ?diet (COUNT(?r) as ?count)
    WHERE {
        ?r a food:Recipe .
        ?r schema:suitableForDiet ?diet .
    }
    GROUP BY ?diet
    ORDER BY DESC(?count)
    """
    return [(r['diet'].split('/')[-1].replace('_', ' '), int(r['count'])) 
            for r in sparql_query(query) if r.get('diet')]


def get_all_cuisines():
    """Get cuisine types with counts."""
    query = """
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX schema: <https://schema.org/>
    SELECT ?cuisine (COUNT(?r) as ?count)
    WHERE {
        ?r a food:Recipe .
        ?r schema:recipeCuisine ?cuisine .
    }
    GROUP BY ?cuisine
    ORDER BY DESC(?count)
    """
    return [(r['cuisine'].split('/')[-1].replace('_', ' '), int(r['count'])) 
            for r in sparql_query(query) if r.get('cuisine')]


def get_graph_data():
    """Get data for visualization."""
    query = """
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX schema: <https://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?recipe ?recipeTitle ?ingredient ?ingredientName
    WHERE {
        ?recipe a food:Recipe .
        OPTIONAL { ?recipe schema:name ?recipeTitle }
        ?recipe food:ingredient ?ingredient .
        ?ingredient rdfs:label ?ingredientName .
    }
    LIMIT 200
    """
    
    results = sparql_query(query)
    nodes, edges, seen = [], [], set()
    
    for row in results:
        recipe_id = row.get('recipe', '').split('/')[-1]
        ing_id = row.get('ingredient', '').split('/')[-1]
        
        if recipe_id and recipe_id not in seen:
            nodes.append({
                "id": recipe_id,
                "label": (row.get('recipeTitle') or recipe_id)[:30],
                "type": "recipe",
                "color": "#10B981"
            })
            seen.add(recipe_id)
        
        if ing_id and ing_id not in seen:
            nodes.append({
                "id": ing_id,
                "label": (row.get('ingredientName') or ing_id)[:20],
                "type": "ingredient",
                "color": "#6366F1"
            })
            seen.add(ing_id)
        
        if recipe_id and ing_id:
            edges.append({"from": recipe_id, "to": ing_id})
    
    return {"nodes": nodes, "edges": edges}


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(title="Recipe Knowledge Graph", description="Powered by Apache Jena Fuseki", version="3.0.0")


# ============================================================================
# HTML TEMPLATE
# ============================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Recipe Knowledge Graph</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/vis-network@9.1.2/dist/vis-network.min.js"></script>
    <style>
        :root {
            --primary: #10B981;
            --primary-dark: #059669;
            --secondary: #6366F1;
            --accent: #F59E0B;
            --dark: #111827;
            --dark-light: #1F2937;
            --gray: #6B7280;
            --gray-light: #9CA3AF;
            --light: #F9FAFB;
            --white: #FFFFFF;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', sans-serif;
            background: var(--dark);
            color: var(--light);
            min-height: 100vh;
        }
        
        .navbar {
            background: rgba(17, 24, 39, 0.95) !important;
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(255,255,255,0.05);
            padding: 1rem 0;
        }
        
        .navbar-brand { font-weight: 700; font-size: 1.25rem; color: var(--white) !important; }
        .nav-link { color: var(--gray-light) !important; font-weight: 500; font-size: 0.9rem; padding: 0.5rem 1rem !important; }
        .nav-link:hover { color: var(--white) !important; }
        
        .card {
            background: var(--dark-light);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 16px;
            overflow: hidden;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .card:hover { transform: translateY(-4px); box-shadow: 0 20px 40px rgba(0,0,0,0.3); }
        .card-static:hover { transform: none; box-shadow: none; }
        
        .recipe-card { height: 100%; display: flex; flex-direction: column; }
        .recipe-card img { height: 200px; width: 100%; object-fit: cover; background: var(--dark); }
        .recipe-card .card-body { flex: 1; display: flex; flex-direction: column; justify-content: space-between; padding: 1.5rem; }
        .recipe-card .card-title { font-weight: 600; font-size: 1.1rem; color: var(--white); margin-bottom: 0.75rem; }
        
        .stat-card {
            background: linear-gradient(135deg, #10B981 0%, #6366F1 100%);
            text-align: center;
            padding: 2rem 1.5rem;
            border: none;
        }
        .stat-card h2 { font-size: 2.5rem; font-weight: 700; color: var(--white); margin-bottom: 0.25rem; }
        .stat-card p { color: rgba(255,255,255,0.8); font-size: 0.9rem; font-weight: 500; margin: 0; }
        
        .tag { display: inline-block; padding: 0.35rem 0.75rem; border-radius: 6px; font-size: 0.75rem; font-weight: 500; margin: 0.15rem; }
        .tag-primary { background: rgba(16, 185, 129, 0.15); color: var(--primary); }
        .tag-secondary { background: rgba(99, 102, 241, 0.15); color: var(--secondary); }
        .tag-accent { background: rgba(245, 158, 11, 0.15); color: var(--accent); }
        .tag-dark { background: rgba(255,255,255,0.1); color: var(--gray-light); }
        
        .info-badge { display: inline-flex; align-items: center; padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.85rem; font-weight: 500; margin: 0.25rem; }
        .info-badge-time { background: rgba(245, 158, 11, 0.1); color: var(--accent); }
        .info-badge-calories { background: rgba(239, 68, 68, 0.1); color: #EF4444; }
        
        .btn-primary-custom { background: var(--primary); border: none; color: var(--white); font-weight: 600; padding: 0.75rem 1.5rem; border-radius: 10px; transition: all 0.2s; }
        .btn-primary-custom:hover { background: var(--primary-dark); color: var(--white); transform: translateY(-2px); }
        
        .btn-outline-custom { background: transparent; border: 1px solid rgba(255,255,255,0.2); color: var(--white); font-weight: 500; padding: 0.5rem 1rem; border-radius: 8px; }
        .btn-outline-custom:hover { background: rgba(255,255,255,0.1); border-color: rgba(255,255,255,0.3); color: var(--white); }
        
        .form-control, .form-select { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; color: var(--white); padding: 0.75rem 1rem; }
        .form-control:focus, .form-select:focus { background: rgba(255,255,255,0.08); border-color: var(--primary); box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15); color: var(--white); }
        .form-control::placeholder { color: var(--gray); }
        .form-select option { background: var(--dark-light); color: var(--white); }
        .form-label { font-size: 0.85rem; font-weight: 500; color: var(--gray-light); margin-bottom: 0.5rem; }
        
        .search-box { background: var(--dark-light); border-radius: 20px; padding: 2rem; border: 1px solid rgba(255,255,255,0.05); }
        
        .hero-section { padding: 4rem 0 3rem; text-align: center; }
        .hero-section h1 { font-size: 2.75rem; font-weight: 700; margin-bottom: 0.75rem; }
        .hero-section .subtitle { font-size: 1.1rem; color: var(--gray-light); }
        .hero-section .team-credit { font-size: 0.85rem; color: var(--gray); margin-top: 1rem; }
        
        .section-title { font-size: 1.5rem; font-weight: 600; color: var(--white); margin-bottom: 1.5rem; }
        
        .external-links { display: flex; flex-wrap: wrap; gap: 0.75rem; }
        .external-link-badge { display: inline-flex; align-items: center; padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.8rem; font-weight: 500; }
        .external-link-badge.dbpedia { background: rgba(59, 130, 246, 0.15); color: #3B82F6; }
        .external-link-badge.wikidata { background: rgba(168, 85, 247, 0.15); color: #A855F7; }
        .external-link-badge.foodon { background: rgba(16, 185, 129, 0.15); color: var(--primary); }
        
        #graph-container { height: 500px; background: var(--dark-light); border-radius: 16px; border: 1px solid rgba(255,255,255,0.05); }
        
        .nutrition-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-top: 1rem; }
        .nutrition-item { background: rgba(255,255,255,0.03); border-radius: 12px; padding: 1rem; text-align: center; }
        .nutrition-item .value { font-size: 1.5rem; font-weight: 700; color: var(--white); }
        .nutrition-item .label { font-size: 0.75rem; color: var(--gray); text-transform: uppercase; }
        
        .video-container { border-radius: 12px; overflow: hidden; margin-top: 1.5rem; }
        
        .source-badge { display: inline-flex; padding: 0.35rem 0.75rem; border-radius: 6px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
        .source-badge.mealdb { background: rgba(245, 158, 11, 0.15); color: var(--accent); }
        .source-badge.spoonacular { background: rgba(16, 185, 129, 0.15); color: var(--primary); }
        .source-badge.recipesnlg { background: rgba(99, 102, 241, 0.15); color: var(--secondary); }
        
        .table { color: var(--light); }
        .table thead th { border-bottom-color: rgba(255,255,255,0.1); font-weight: 600; font-size: 0.85rem; color: var(--gray-light); }
        .table td { border-bottom-color: rgba(255,255,255,0.05); padding: 1rem 0.75rem; }
        
        .placeholder-img { background: linear-gradient(135deg, var(--dark-light), var(--dark)); display: flex; align-items: center; justify-content: center; color: var(--gray); font-weight: 500; }
        
        footer { background: rgba(0,0,0,0.3); padding: 2rem 0; margin-top: 4rem; border-top: 1px solid rgba(255,255,255,0.05); }
        footer p { color: var(--gray); font-size: 0.85rem; margin: 0; }
        
        .fuseki-badge { background: linear-gradient(135deg, #E85D04, #DC2F02); color: white; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.7rem; font-weight: 600; margin-left: 0.5rem; }
        
        .status-indicator { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
        .status-online { background: #10B981; box-shadow: 0 0 8px #10B981; }
        .status-offline { background: #EF4444; box-shadow: 0 0 8px #EF4444; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg">
        <div class="container">
            <a class="navbar-brand" href="/">Recipe Knowledge Graph <span class="fuseki-badge">Fuseki</span></a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/">Home</a>
                <a class="nav-link" href="/search">Search</a>
                <a class="nav-link" href="/similar">Similar</a>
                <a class="nav-link" href="/graph">Graph</a>
                <a class="nav-link" href="/stats">Stats</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {{content}}
    </div>

    <footer>
        <div class="container text-center">
            <p>Recipe Knowledge Graph - INFOMKDE Project - Group 7 - Powered by Apache Jena Fuseki</p>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""


# ============================================================================
# ROUTES
# ============================================================================

@app.on_event("startup")
async def startup():
    load_embeddings()
    connected, count = check_fuseki_connection()
    if connected:
        print(f"Connected to Fuseki! Dataset has {count:,} triples")
    else:
        print("WARNING: Cannot connect to Fuseki!")
        print(f"Make sure Fuseki is running at {FUSEKI_URL}")
        print("Start with: fuseki-server.bat --update --mem /recipes")


@app.get("/", response_class=HTMLResponse)
async def home():
    stats = get_statistics()
    recipes = get_featured_recipes()  # Gets 2 from each source
    diets = get_all_diets()[:5]
    cuisines = get_all_cuisines()[:5]
    
    total_external = stats['dbpedia_links'] + stats['wikidata_links'] + stats['foodon_links']
    connected, _ = check_fuseki_connection()
    status_class = "status-online" if connected else "status-offline"
    status_text = "Connected" if connected else "Disconnected"
    
    content = f"""
    <div class="hero-section">
        <h1>Recipe Knowledge Graph</h1>
        <p class="subtitle">A Semantic Recipe Recommendation System</p>
        <p class="team-credit">by Group 7</p>
        <p class="mt-2"><span class="status-indicator {status_class}"></span><small style="color: var(--gray-light);">Fuseki: {status_text}</small></p>
        
        <div class="mt-4">
            <span class="tag tag-dark">{stats['total_triples']:,} Triples</span>
            <span class="tag tag-dark">{stats['recipes']:,} Recipes</span>
            <span class="tag tag-dark">{stats['ingredients']:,} Ingredients</span>
            <span class="tag tag-dark">{total_external} External Links</span>
        </div>
    </div>
    
    <div class="row g-4 mb-5">
        <div class="col-md-3"><div class="card stat-card"><h2>{stats['total_triples']:,}</h2><p>RDF Triples</p></div></div>
        <div class="col-md-3"><div class="card stat-card"><h2>{stats['recipes']:,}</h2><p>Recipes</p></div></div>
        <div class="col-md-3"><div class="card stat-card"><h2>{stats['ingredients']:,}</h2><p>Ingredients</p></div></div>
        <div class="col-md-3"><div class="card stat-card"><h2>{stats['videos']}</h2><p>Video Tutorials</p></div></div>
    </div>
    
    <div class="card card-static p-4 mb-5">
        <h5 class="mb-3" style="color: var(--white); font-weight: 600;">Linked External Knowledge Bases</h5>
        <div class="external-links">
            <span class="external-link-badge dbpedia">DBpedia: {stats['dbpedia_links']} links</span>
            <span class="external-link-badge wikidata">Wikidata: {stats['wikidata_links']} links</span>
            <span class="external-link-badge foodon">FoodOn: {stats['foodon_links']} links</span>
        </div>
    </div>
    
    <div class="search-box mb-5">
        <h5 style="color: var(--white); font-weight: 600; margin-bottom: 1.5rem;">Quick Search</h5>
        <form action="/search" method="get" class="row g-3">
            <div class="col-md-3"><input type="text" class="form-control" name="name" placeholder="Recipe name..."></div>
            <div class="col-md-2"><input type="text" class="form-control" name="ingredient" placeholder="Ingredient..."></div>
            <div class="col-md-2">
                <select class="form-select" name="diet">
                    <option value="">Any Diet</option>
                    {"".join(f'<option value="{d[0]}">{d[0]}</option>' for d in diets)}
                </select>
            </div>
            <div class="col-md-2">
                <select class="form-select" name="cuisine">
                    <option value="">Any Cuisine</option>
                    {"".join(f'<option value="{c[0]}">{c[0]}</option>' for c in cuisines)}
                </select>
            </div>
            <div class="col-md-3"><button type="submit" class="btn btn-primary-custom w-100">Search</button></div>
        </form>
    </div>
    
    <h3 class="section-title">Featured Recipes</h3>
    <div class="row g-4 mb-5">
        {"".join(f'''
        <div class="col-md-4">
            <div class="card recipe-card">
                <img src="{r['image'] if r.get('image') and str(r['image']).startswith('http') else ''}" alt="{r['title']}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                <div class="placeholder-img" style="height: 200px; display: none;">No Image</div>
                <div class="card-body">
                    <h5 class="card-title">{str(r.get('title', 'Untitled'))[:45]}</h5>
                    <div class="mb-3">
                        {f"<span class='info-badge info-badge-time'>{r['time']} min</span>" if r.get('time') else ''}
                        {f"<span class='info-badge info-badge-calories'>{r['calories']:.0f} kcal</span>" if r.get('calories') else ''}
                    </div>
                    <a href="/recipe/{r['uri'].split('/')[-1]}" class="btn btn-outline-custom">View Details</a>
                </div>
            </div>
        </div>
        ''' for r in recipes) if recipes else '<div class="col-12"><div class="card card-static p-5 text-center"><p style="color: var(--gray);">No recipes found. Is Fuseki running?</p></div></div>'}
    </div>
    
    <div class="row g-4">
        <div class="col-md-6">
            <div class="card card-static p-4">
                <h5 style="color: var(--white); font-weight: 600; margin-bottom: 1rem;">Diet Types</h5>
                <div>{"".join(f'<a href="/search?diet={d[0]}" class="tag tag-primary text-decoration-none">{d[0]} ({d[1]})</a>' for d in diets)}</div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card card-static p-4">
                <h5 style="color: var(--white); font-weight: 600; margin-bottom: 1rem;">Cuisines</h5>
                <div>{"".join(f'<a href="/search?cuisine={c[0]}" class="tag tag-secondary text-decoration-none">{c[0]} ({c[1]})</a>' for c in cuisines)}</div>
            </div>
        </div>
    </div>
    """
    
    return HTML_TEMPLATE.replace("{{content}}", content)


@app.get("/search", response_class=HTMLResponse)
async def search_page(name: Optional[str] = None, ingredient: Optional[str] = None, 
                      diet: Optional[str] = None, cuisine: Optional[str] = None,
                      max_calories: Optional[str] = None, max_time: Optional[str] = None):
    max_cal = int(max_calories) if max_calories and max_calories.strip() else None
    max_t = int(max_time) if max_time and max_time.strip() else None
    
    recipes = search_recipes(name, ingredient, diet, cuisine, max_cal, max_t)
    diets = get_all_diets()
    cuisines = get_all_cuisines()
    
    active_filters = []
    if name: active_filters.append(f'Name: "{name}"')
    if ingredient: active_filters.append(f'Ingredient: "{ingredient}"')
    if diet: active_filters.append(f'Diet: "{diet}"')
    if cuisine: active_filters.append(f'Cuisine: "{cuisine}"')
    if max_cal: active_filters.append(f'Max {max_cal} kcal')
    if max_t: active_filters.append(f'Max {max_t} min')
    filter_display = " + ".join(active_filters) if active_filters else "All Recipes"
    
    content = f"""
    <h2 class="section-title mb-4">Search Recipes</h2>
    
    <div class="search-box mb-4">
        <form action="/search" method="get" class="row g-3">
            <div class="col-md-2"><label class="form-label">Recipe Name</label><input type="text" class="form-control" name="name" value="{name or ''}" placeholder="e.g., curry"></div>
            <div class="col-md-2"><label class="form-label">Ingredient</label><input type="text" class="form-control" name="ingredient" value="{ingredient or ''}" placeholder="e.g., chicken"></div>
            <div class="col-md-2"><label class="form-label">Diet</label><select class="form-select" name="diet"><option value="">Any</option>{"".join(f'<option value="{d[0]}" {"selected" if d[0]==diet else ""}>{d[0]}</option>' for d in diets)}</select></div>
            <div class="col-md-2"><label class="form-label">Cuisine</label><select class="form-select" name="cuisine"><option value="">Any</option>{"".join(f'<option value="{c[0]}" {"selected" if c[0]==cuisine else ""}>{c[0]}</option>' for c in cuisines)}</select></div>
            <div class="col-md-1"><label class="form-label">Max Cal</label><input type="number" class="form-control" name="max_calories" value="{max_calories or ''}" placeholder="500"></div>
            <div class="col-md-1"><label class="form-label">Max Time</label><input type="number" class="form-control" name="max_time" value="{max_time or ''}" placeholder="30"></div>
            <div class="col-md-2 d-flex align-items-end"><button type="submit" class="btn btn-primary-custom w-100">Search</button></div>
        </form>
    </div>
    
    <div class="d-flex justify-content-between align-items-center mb-4">
        <p style="color: var(--gray-light); margin: 0;">{filter_display}</p>
        <span class="tag tag-dark">{len(recipes)} recipes found</span>
    </div>
    
    <div class="row g-4">
        {"".join(f'''
        <div class="col-md-4">
            <div class="card recipe-card">
                <img src="{r['image'] if r.get('image') and str(r['image']).startswith('http') else ''}" alt="{r['title']}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                <div class="placeholder-img" style="height: 200px; display: none;">No Image</div>
                <div class="card-body">
                    <h5 class="card-title">{str(r.get('title', 'Untitled'))[:45]}</h5>
                    <div class="mb-3">
                        {f"<span class='info-badge info-badge-time'>{r['time']} min</span>" if r.get('time') else ''}
                        {f"<span class='info-badge info-badge-calories'>{r['calories']:.0f} kcal</span>" if r.get('calories') else ''}
                        {"<span class='tag tag-accent'>Video</span>" if r.get('has_video') else ''}
                    </div>
                    <a href="/recipe/{r['uri'].split('/')[-1]}" class="btn btn-outline-custom">View Details</a>
                </div>
            </div>
        </div>
        ''' for r in recipes) if recipes else '<div class="col-12"><div class="card card-static p-5 text-center"><p style="color: var(--gray);">No recipes found.</p></div></div>'}
    </div>
    """
    
    return HTML_TEMPLATE.replace("{{content}}", content)


@app.get("/recipe/{recipe_id}", response_class=HTMLResponse)
async def recipe_detail(recipe_id: str):
    recipe = get_recipe_details(recipe_id)
    
    if not recipe:
        return HTML_TEMPLATE.replace("{{content}}", '<div class="card card-static p-5 text-center"><h2 style="color: var(--white);">Recipe not found</h2></div>')
    
    video_embed = ""
    if recipe.get('video') and 'youtube.com' in str(recipe.get('video', '')):
        video_id = recipe['video'].split('watch?v=')[1].split('&')[0] if 'watch?v=' in recipe['video'] else ''
        if video_id:
            video_embed = f'''
            <div class="video-container mt-4">
                <h5 style="color: var(--white); font-weight: 600; margin-bottom: 1rem;">Video Tutorial</h5>
                <div class="ratio ratio-16x9"><iframe src="https://www.youtube.com/embed/{video_id}" title="Recipe Video" allowfullscreen style="border-radius: 12px;"></iframe></div>
            </div>
            '''
    
    instructions_html = f'''
    <div class="card card-static p-4 mt-4">
        <h5 style="color: var(--white); font-weight: 600; margin-bottom: 1rem;">Instructions</h5>
        <div style="color: var(--gray-light); line-height: 1.8; white-space: pre-line;">{recipe['instructions']}</div>
    </div>
    ''' if recipe.get('instructions') else ''
    
    source_badge = '<span class="source-badge mealdb">MealDB</span>' if recipe.get('video') else \
                   '<span class="source-badge recipesnlg">RecipesNLG</span>' if 'Gathered' in str(recipe.get('source', '')) else \
                   '<span class="source-badge spoonacular">Spoonacular</span>'
    
    nutrition_html = ""
    if recipe.get('nutrition') and recipe['nutrition'].get('calories'):
        n = recipe['nutrition']
        cal_val = f"{n['calories']:.0f}" if n.get('calories') else "0"
        prot_val = f"{n['protein']:.0f}" if n.get('protein') else "0"
        carb_val = f"{n['carbs']:.0f}" if n.get('carbs') else "0"
        fat_val = f"{n['fat']:.0f}" if n.get('fat') else "0"
        nutrition_html = f'''
        <div class="mt-4">
            <h5 style="color: var(--white); font-weight: 600;">Nutrition (per serving)</h5>
            <div class="nutrition-grid">
                <div class="nutrition-item"><div class="value">{cal_val}</div><div class="label">Calories</div></div>
                <div class="nutrition-item"><div class="value">{prot_val}g</div><div class="label">Protein</div></div>
                <div class="nutrition-item"><div class="value">{carb_val}g</div><div class="label">Carbs</div></div>
                <div class="nutrition-item"><div class="value">{fat_val}g</div><div class="label">Fat</div></div>
            </div>
        </div>
        '''
    
    diets_html = ('<div class="mb-3"><h6 style="color: var(--gray-light);">Diets</h6>' + 
                  "".join(f'<span class="tag tag-primary">{d}</span>' for d in recipe.get("diets", [])) + '</div>') if recipe.get('diets') else ''
    
    cuisines_html = ('<div class="mb-3"><h6 style="color: var(--gray-light);">Cuisines</h6>' + 
                     "".join(f'<span class="tag tag-secondary">{c}</span>' for c in recipe.get("cuisines", [])) + '</div>') if recipe.get('cuisines') else ''
    
    content = f"""
    <div class="row g-4">
        <div class="col-md-5">
            <img src="{recipe.get('image') if recipe.get('image') and str(recipe['image']).startswith('http') else ''}" alt="{recipe['title']}" class="img-fluid" style="border-radius: 16px; width: 100%;" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
            <div class="placeholder-img" style="height: 350px; border-radius: 16px; display: none;">No Image</div>
            {video_embed}
        </div>
        <div class="col-md-7">
            <div class="card card-static p-4">
                <div class="d-flex justify-content-between align-items-start mb-3">
                    <h2 style="color: var(--white); font-weight: 700;">{recipe['title']}</h2>
                    {source_badge}
                </div>
                <div class="mb-3">
                    {f'<span class="info-badge info-badge-time">{recipe["time"]} minutes</span>' if recipe.get('time') else ''}
                    {f'<span class="info-badge" style="background: rgba(16, 185, 129, 0.1); color: var(--primary);">{recipe["servings"]} servings</span>' if recipe.get('servings') else ''}
                </div>
                {diets_html}
                {cuisines_html}
                {nutrition_html}
                <div class="mt-4">
                    {f'<a href="{recipe["video"]}" target="_blank" class="btn btn-primary-custom me-2">Watch Video</a>' if recipe.get('video') else ''}
                    {f'<a href="{recipe["sourceUrl"]}" target="_blank" class="btn btn-primary-custom me-2">View Original Recipe</a>' if recipe.get('sourceUrl') and not recipe.get('video') else ''}
                    <a href="/" class="btn btn-outline-custom">Back</a>
                </div>
            </div>
        </div>
    </div>
    
    <div class="card card-static p-4 mt-4">
        <h5 style="color: var(--white); font-weight: 600; margin-bottom: 1rem;">Ingredients ({len(recipe.get('ingredients', []))})</h5>
        <div class="row">{"".join(f'<div class="col-md-4 mb-2" style="color: var(--gray-light);">{ing}</div>' for ing in recipe.get('ingredients', []))}</div>
    </div>
    
    {instructions_html}
    """
    
    return HTML_TEMPLATE.replace("{{content}}", content)


@app.get("/api/similar/{entity_name}")
async def api_similar(entity_name: str, top_k: int = 5, entity_type: str = None):
    return {"entity": entity_name, "similar": find_similar_entities(entity_name, top_k, entity_type)}


@app.get("/similar", response_class=HTMLResponse)
async def similar_page(request: Request):
    recipes = get_all_recipes(limit=500)
    
    content = f"""
    <div class="text-center mb-5">
        <h1 style="color: var(--white); font-weight: 700;">Find Similar Recipes</h1>
        <p style="color: var(--gray-light);">Using Graph Embeddings (PyKEEN/RotatE)</p>
    </div>
    
    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="card card-static p-4 mb-4">
                <h5 style="color: var(--white); font-weight: 600; margin-bottom: 1.5rem;">Select a Recipe</h5>
                <div class="row g-3">
                    <div class="col-md-8">
                        <select id="recipeSelect" class="form-select">
                            <option value="">-- Select a recipe --</option>
                            {"".join(f'<option value="{r.get("uri", "").split("/")[-1]}">{r.get("title", "Unknown")}</option>' for r in recipes if r.get("uri"))}
                        </select>
                    </div>
                    <div class="col-md-4"><button onclick="findSimilar()" class="btn btn-primary-custom w-100">Find Similar</button></div>
                </div>
                <div class="mt-4">
                    <h6 style="color: var(--gray-light);">Or search by ingredient:</h6>
                    <div class="row g-3">
                        <div class="col-md-8"><input type="text" id="ingredientInput" class="form-control" placeholder="e.g., chicken, garlic"></div>
                        <div class="col-md-4"><button onclick="findSimilarIngredient()" class="btn btn-primary-custom w-100">Find Similar</button></div>
                    </div>
                </div>
            </div>
            <div id="results"></div>
        </div>
    </div>
    
    <script>
        async function findSimilar() {{
            const entity = document.getElementById('recipeSelect').value;
            if (!entity) {{ alert('Please select a recipe'); return; }}
            document.getElementById('results').innerHTML = '<p style="color: var(--gray-light); text-align: center;">Finding similar recipes...</p>';
            try {{
                const response = await fetch(`/api/similar/${{entity}}?top_k=5&entity_type=recipe`);
                const data = await response.json();
                displayResults(data);
            }} catch (error) {{
                document.getElementById('results').innerHTML = '<p style="color: #EF4444; text-align: center;">Error</p>';
            }}
        }}
        
        async function findSimilarIngredient() {{
            const entity = document.getElementById('ingredientInput').value.trim();
            if (!entity) {{ alert('Please enter an ingredient'); return; }}
            document.getElementById('results').innerHTML = '<p style="color: var(--gray-light); text-align: center;">Finding similar ingredients...</p>';
            try {{
                const response = await fetch(`/api/similar/${{entity}}?top_k=5&entity_type=ingredient`);
                const data = await response.json();
                displayResults(data);
            }} catch (error) {{
                document.getElementById('results').innerHTML = '<p style="color: #EF4444; text-align: center;">Error</p>';
            }}
        }}
        
        function displayResults(data) {{
            const resultsDiv = document.getElementById('results');
            if (!data.similar || data.similar.length === 0) {{
                resultsDiv.innerHTML = '<div class="card card-static p-4 text-center" style="color: var(--accent);">No similar items found</div>';
                return;
            }}
            let html = `<h5 style="color: var(--white); font-weight: 600; margin-bottom: 1rem;">Similar to: ${{data.entity}}</h5>`;
            data.similar.forEach((item, index) => {{
                const percentage = (item.similarity * 100).toFixed(1);
                const name = item.name.split('/').pop().replace(/_/g, ' ');
                html += `
                    <div class="card card-static p-3 mb-2" style="cursor: pointer;" onclick="window.location.href='/recipe/${{item.name.split('/').pop()}}'">
                        <div class="d-flex justify-content-between align-items-center">
                            <div><span class="tag tag-secondary me-2">#${{index + 1}}</span><strong style="color: var(--white);">${{name}}</strong></div>
                            <span style="color: var(--primary); font-weight: 700;">${{percentage}}%</span>
                        </div>
                        <div style="height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; margin-top: 0.75rem;">
                            <div style="height: 100%; width: ${{percentage}}%; background: linear-gradient(90deg, var(--primary), var(--secondary)); border-radius: 3px;"></div>
                        </div>
                    </div>
                `;
            }});
            resultsDiv.innerHTML = html;
        }}
    </script>
    """
    
    return HTML_TEMPLATE.replace("{{content}}", content)


@app.get("/graph", response_class=HTMLResponse)
async def graph_page():
    graph_data = get_graph_data()
    
    content = f"""
    <h2 class="section-title mb-4">Knowledge Graph Visualization</h2>
    <div class="card card-static p-3 mb-4">
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <span class="tag tag-primary">Recipes</span>
                <span class="tag tag-secondary">Ingredients</span>
                <span style="color: var(--gray); font-size: 0.85rem; margin-left: 1rem;">Drag to explore / Scroll to zoom</span>
            </div>
            <span class="tag tag-dark">{len(graph_data['nodes'])} nodes / {len(graph_data['edges'])} edges</span>
        </div>
    </div>
    <div id="graph-container"></div>
    <script>
        var nodes = new vis.DataSet({json.dumps(graph_data['nodes'])});
        var edges = new vis.DataSet({json.dumps(graph_data['edges'])});
        var container = document.getElementById('graph-container');
        var data = {{ nodes: nodes, edges: edges }};
        var options = {{
            nodes: {{ shape: 'dot', size: 16, font: {{ size: 12, color: '#9CA3AF' }}, borderWidth: 2, shadow: true }},
            edges: {{ width: 1, color: {{ color: '#374151', highlight: '#10B981' }}, smooth: {{ type: 'continuous' }} }},
            physics: {{ stabilization: {{ iterations: 100 }}, barnesHut: {{ gravitationalConstant: -2000, springLength: 100 }} }},
            interaction: {{ hover: true, tooltipDelay: 100 }}
        }};
        var network = new vis.Network(container, data, options);
        network.on("click", function(params) {{
            if (params.nodes.length > 0) {{
                var nodeId = params.nodes[0];
                var node = nodes.get(nodeId);
                if (node.type === 'recipe') window.location.href = '/recipe/' + nodeId;
            }}
        }});
    </script>
    """
    
    return HTML_TEMPLATE.replace("{{content}}", content)


@app.get("/stats", response_class=HTMLResponse)
async def stats_page():
    stats = get_statistics()
    diets = get_all_diets()
    cuisines = get_all_cuisines()
    
    content = f"""
    <h2 class="section-title mb-4">Knowledge Graph Statistics</h2>
    <div class="row g-4 mb-5">
        <div class="col-md-3"><div class="card stat-card"><h2>{stats['total_triples']:,}</h2><p>Total Triples</p></div></div>
        <div class="col-md-3"><div class="card stat-card"><h2>{stats['recipes']:,}</h2><p>Recipes</p></div></div>
        <div class="col-md-3"><div class="card stat-card"><h2>{stats['ingredients']:,}</h2><p>Ingredients</p></div></div>
        <div class="col-md-3"><div class="card stat-card"><h2>5</h2><p>Data Sources</p></div></div>
    </div>
    <div class="row g-4">
        <div class="col-md-6">
            <div class="card card-static p-4">
                <h5 style="color: var(--white); font-weight: 600; margin-bottom: 1rem;">Recipes by Diet</h5>
                <table class="table"><thead><tr><th>Diet</th><th>Count</th><th>%</th></tr></thead>
                <tbody>{"".join(f'<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[1]/max(stats["recipes"],1)*100:.1f}%</td></tr>' for d in diets)}</tbody></table>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card card-static p-4">
                <h5 style="color: var(--white); font-weight: 600; margin-bottom: 1rem;">Recipes by Cuisine</h5>
                <table class="table"><thead><tr><th>Cuisine</th><th>Count</th><th>%</th></tr></thead>
                <tbody>{"".join(f'<tr><td>{c[0]}</td><td>{c[1]}</td><td>{c[1]/max(stats["recipes"],1)*100:.1f}%</td></tr>' for c in cuisines)}</tbody></table>
            </div>
        </div>
    </div>
    <div class="card card-static p-4 mt-4">
        <h5 style="color: var(--white); font-weight: 600; margin-bottom: 1rem;">Data Sources</h5>
        <div class="external-links">
            <span class="external-link-badge dbpedia">Spoonacular API</span>
            <span class="external-link-badge foodon">USDA FoodData</span>
            <span class="external-link-badge wikidata">FoodOn Ontology</span>
            <span class="external-link-badge dbpedia">DBpedia</span>
            <span class="external-link-badge wikidata">Wikidata</span>
        </div>
    </div>
    """
    
    return HTML_TEMPLATE.replace("{{content}}", content)


# API Endpoints
@app.get("/api/recipes")
async def api_recipes(limit: int = 20):
    return get_all_recipes(limit=limit)

@app.get("/api/search")
async def api_search(name: str = None, ingredient: str = None, diet: str = None, 
                     cuisine: str = None, max_calories: str = None, max_time: str = None):
    max_cal = int(max_calories) if max_calories and max_calories.strip() else None
    max_t = int(max_time) if max_time and max_time.strip() else None
    return search_recipes(name, ingredient, diet, cuisine, max_cal, max_t)

@app.get("/api/stats")
async def api_stats():
    return get_statistics()


if __name__ == "__main__":
    print("=" * 70)
    print("RECIPE KNOWLEDGE GRAPH - FUSEKI EDITION")
    print("=" * 70)
    print(f"\nFuseki endpoint: {SPARQL_ENDPOINT}")
    print("\nMake sure Fuseki is running with your data loaded!")
    print("Start Fuseki: fuseki-server.bat --update --mem /recipes")
    print("\nStarting web server on http://localhost:8000")
    print("=" * 70)
    
    uvicorn.run(app, host="127.0.0.1", port=8000)