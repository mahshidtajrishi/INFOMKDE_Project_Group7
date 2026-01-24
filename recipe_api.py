import os
import json
from typing import Optional, List, Dict, Any
from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, RDFS, OWL

# Namespaces
FOOD = Namespace("http://data.lirmm.fr/ontologies/food#")
SCHEMA = Namespace("https://schema.org/")
DCTERMS = Namespace("http://purl.org/dc/terms/")

# Global graph
g = None


def load_graph(file_path: str = None) -> Graph:
    
    global g
    
    if g is not None and len(g) > 0:
        return g
    
    g = Graph()
    
    if file_path is None:
       
        script_dir = os.path.dirname(os.path.abspath(__file__))
        possible_files = [
            os.path.join(script_dir, "..", "output", "recipe_kg_complete.ttl"),
            os.path.join(script_dir, "..", "recipe_kg_complete.ttl"),
            os.path.join(script_dir, "output", "recipe_kg_complete.ttl"),
            os.path.join(script_dir, "..", "output", "recipe_recommendation_with_OWL.ttl"),
            os.path.join(script_dir, "..", "output", "unified_recipes_v3_normalized.ttl"),
        ]
        
        for path in possible_files:
            if os.path.exists(path):
                file_path = path
                break
    
    if file_path and os.path.exists(file_path):
        print(f"Loading knowledge graph from: {file_path}")
        g.parse(file_path, format="turtle")
        print(f"Loaded {len(g):,} triples")
    else:
        print("ERROR: No knowledge graph file found!")
    
    return g




def get_statistics() -> Dict[str, Any]:
    load_graph()
    
    stats = {
        "total_triples": len(g),
        "recipes": 0,
        "ingredients": 0,
        "videos": 0,
        "recipes_with_instructions": 0,
        "external_links": {
            "dbpedia": 0,
            "wikidata": 0,
            "foodon": 0,
            "total": 0
        },
        "data_sources": {}
    }
    
    # Count recipes
    query = "SELECT (COUNT(DISTINCT ?r) as ?count) WHERE { ?r a <http://data.lirmm.fr/ontologies/food#Recipe> }"
    for row in g.query(query):
        stats["recipes"] = int(row[0])
    
    # Count ingredients
    query = "SELECT (COUNT(DISTINCT ?i) as ?count) WHERE { ?i a <http://data.lirmm.fr/ontologies/food#Ingredient> }"
    for row in g.query(query):
        stats["ingredients"] = int(row[0])
    
    # Count videos
    query = "PREFIX schema: <https://schema.org/> SELECT (COUNT(?v) as ?count) WHERE { ?r schema:video ?v }"
    for row in g.query(query):
        stats["videos"] = int(row[0])
    
    # Count recipes with instructions
    query = "PREFIX schema: <https://schema.org/> SELECT (COUNT(?i) as ?count) WHERE { ?r schema:recipeInstructions ?i }"
    for row in g.query(query):
        stats["recipes_with_instructions"] = int(row[0])
    
    # Count external links
    for s, p, o in g.triples((None, OWL.sameAs, None)):
        target = str(o)
        if "dbpedia.org" in target:
            stats["external_links"]["dbpedia"] += 1
        elif "wikidata.org" in target:
            stats["external_links"]["wikidata"] += 1
        elif "obolibrary.org" in target:
            stats["external_links"]["foodon"] += 1
    
    stats["external_links"]["total"] = (
        stats["external_links"]["dbpedia"] + 
        stats["external_links"]["wikidata"] + 
        stats["external_links"]["foodon"]
    )
    
    # Count by data source
    source_query = """
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    SELECT ?source (COUNT(?r) as ?count) WHERE {
        ?r a food:Recipe .
        OPTIONAL { ?r dcterms:source ?source }
    }
    GROUP BY ?source
    """
    for row in g.query(source_query):
        source_name = str(row.source) if row.source else "Unknown"
        stats["data_sources"][source_name] = int(row[1])
    
    return stats




def get_all_recipes(limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    load_graph()
    
    query = f"""
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX schema: <https://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT DISTINCT ?uri ?title ?time ?image ?video
    WHERE {{
        ?uri a food:Recipe .
        OPTIONAL {{ ?uri schema:name ?title }}
        OPTIONAL {{ ?uri rdfs:label ?label }}
        OPTIONAL {{ ?uri schema:totalTime ?time }}
        OPTIONAL {{ ?uri schema:image ?image }}
        OPTIONAL {{ ?uri schema:video ?video }}
        BIND(COALESCE(?title, ?label, "Untitled") AS ?name)
    }}
    ORDER BY ?title
    LIMIT {limit}
    OFFSET {offset}
    """
    
    recipes = []
    for row in g.query(query):
        recipe = {
            "uri": str(row.uri),
            "id": str(row.uri).split("/")[-1],
            "title": str(row.title) if row.title else "Untitled",
            "time": int(row.time) if row.time else None,
            "image": str(row.image) if row.image else None,
            "has_video": bool(row.video),
            "video_url": str(row.video) if row.video else None
        }
        recipes.append(recipe)
    
    return {
        "success": True,
        "count": len(recipes),
        "limit": limit,
        "offset": offset,
        "recipes": recipes
    }


def get_recipe_by_id(recipe_id: str) -> Dict[str, Any]:
    load_graph()
    
    # Construct URI if just ID provided
    if not recipe_id.startswith("http"):
        recipe_uri = f"http://example.org/food/recipe/{recipe_id}"
    else:
        recipe_uri = recipe_id
    
    # Main recipe query
    query = f"""
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX schema: <https://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    
    SELECT ?title ?time ?servings ?image ?video ?instructions ?source ?url
    WHERE {{
        <{recipe_uri}> a food:Recipe .
        OPTIONAL {{ <{recipe_uri}> schema:name ?title }}
        OPTIONAL {{ <{recipe_uri}> rdfs:label ?title }}
        OPTIONAL {{ <{recipe_uri}> schema:totalTime ?time }}
        OPTIONAL {{ <{recipe_uri}> schema:recipeYield ?servings }}
        OPTIONAL {{ <{recipe_uri}> schema:image ?image }}
        OPTIONAL {{ <{recipe_uri}> schema:video ?video }}
        OPTIONAL {{ <{recipe_uri}> schema:recipeInstructions ?instructions }}
        OPTIONAL {{ <{recipe_uri}> dcterms:source ?source }}
        OPTIONAL {{ <{recipe_uri}> schema:url ?url }}
    }}
    """
    
    result = list(g.query(query))
    if not result:
        return {"success": False, "error": "Recipe not found", "recipe_id": recipe_id}
    
    row = result[0]
    
    recipe = {
        "uri": recipe_uri,
        "id": recipe_uri.split("/")[-1],
        "title": str(row.title) if row.title else "Untitled",
        "time_minutes": int(row.time) if row.time else None,
        "servings": int(row.servings) if row.servings else None,
        "image": str(row.image) if row.image else None,
        "video": str(row.video) if row.video else None,
        "instructions": str(row.instructions) if row.instructions else None,
        "source": str(row.source) if row.source else None,
        "url": str(row.url) if row.url else None,
        "ingredients": [],
        "nutrition": None,
        "diets": [],
        "cuisines": []
    }
    
    # Get ingredients
    ing_query = f"""
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?ing ?name
    WHERE {{
        <{recipe_uri}> food:ingredient ?ing .
        OPTIONAL {{ ?ing rdfs:label ?name }}
    }}
    """
    
    for row in g.query(ing_query):
        ing = {
            "uri": str(row.ing),
            "id": str(row.ing).split("/")[-1],
            "name": str(row.name) if row.name else str(row.ing).split("/")[-1].replace("_", " ")
        }
        recipe["ingredients"].append(ing)
    
    # Get nutrition
    nut_query = f"""
    PREFIX schema: <https://schema.org/>
    
    SELECT ?calories ?protein ?fat ?carbs
    WHERE {{
        <{recipe_uri}> schema:nutrition ?n .
        OPTIONAL {{ ?n schema:calories ?calories }}
        OPTIONAL {{ ?n schema:proteinContent ?protein }}
        OPTIONAL {{ ?n schema:fatContent ?fat }}
        OPTIONAL {{ ?n schema:carbohydrateContent ?carbs }}
    }}
    """
    
    nut_result = list(g.query(nut_query))
    if nut_result and any(nut_result[0]):
        row = nut_result[0]
        recipe["nutrition"] = {
            "calories": float(row.calories) if row.calories else None,
            "protein_g": float(row.protein) if row.protein else None,
            "fat_g": float(row.fat) if row.fat else None,
            "carbohydrates_g": float(row.carbs) if row.carbs else None
        }
    
    # Get diets
    diet_query = f"""
    PREFIX schema: <https://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?diet ?name
    WHERE {{
        <{recipe_uri}> schema:suitableForDiet ?diet .
        OPTIONAL {{ ?diet rdfs:label ?name }}
    }}
    """
    
    for row in g.query(diet_query):
        diet_name = str(row.name) if row.name else str(row.diet).split("/")[-1].replace("_", " ")
        recipe["diets"].append({"uri": str(row.diet), "name": diet_name})
    
    # Get cuisines
    cuisine_query = f"""
    PREFIX schema: <https://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?cuisine ?name
    WHERE {{
        <{recipe_uri}> schema:recipeCuisine ?cuisine .
        OPTIONAL {{ ?cuisine rdfs:label ?name }}
    }}
    """
    
    for row in g.query(cuisine_query):
        cuisine_name = str(row.name) if row.name else str(row.cuisine).split("/")[-1].replace("_", " ")
        recipe["cuisines"].append({"uri": str(row.cuisine), "name": cuisine_name})
    
    return {"success": True, "recipe": recipe}


def search_recipes(
    ingredient: str = None,
    diet: str = None,
    cuisine: str = None,
    max_time: int = None,
    has_video: bool = None,
    limit: int = 50
) -> Dict[str, Any]:
    load_graph()
    
    filters = []
    
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
    
    if max_time:
        filters.append(f"""
            ?uri schema:totalTime ?time .
            FILTER(?time <= {max_time})
        """)
    
    if has_video:
        filters.append("?uri schema:video ?video .")
    
    filter_str = "\n".join(filters)
    
    query = f"""
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX schema: <https://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT DISTINCT ?uri ?title ?time ?image ?video
    WHERE {{
        ?uri a food:Recipe .
        OPTIONAL {{ ?uri schema:name ?title }}
        OPTIONAL {{ ?uri rdfs:label ?title }}
        OPTIONAL {{ ?uri schema:totalTime ?time }}
        OPTIONAL {{ ?uri schema:image ?image }}
        OPTIONAL {{ ?uri schema:video ?video }}
        {filter_str}
    }}
    ORDER BY ?title
    LIMIT {limit}
    """
    
    recipes = []
    for row in g.query(query):
        recipe = {
            "uri": str(row.uri),
            "id": str(row.uri).split("/")[-1],
            "title": str(row.title) if row.title else "Untitled",
            "time_minutes": int(row.time) if row.time else None,
            "image": str(row.image) if row.image else None,
            "has_video": bool(row.video),
            "video_url": str(row.video) if row.video else None
        }
        recipes.append(recipe)
    
    return {
        "success": True,
        "count": len(recipes),
        "filters": {
            "ingredient": ingredient,
            "diet": diet,
            "cuisine": cuisine,
            "max_time": max_time,
            "has_video": has_video
        },
        "recipes": recipes
    }


def get_recipes_with_videos(limit: int = 100) -> Dict[str, Any]:
    load_graph()
    
    query = f"""
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX schema: <https://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?uri ?title ?video ?image
    WHERE {{
        ?uri a food:Recipe ;
             schema:video ?video .
        OPTIONAL {{ ?uri schema:name ?title }}
        OPTIONAL {{ ?uri rdfs:label ?title }}
        OPTIONAL {{ ?uri schema:image ?image }}
    }}
    ORDER BY ?title
    LIMIT {limit}
    """
    
    recipes = []
    for row in g.query(query):
        recipe = {
            "uri": str(row.uri),
            "id": str(row.uri).split("/")[-1],
            "title": str(row.title) if row.title else "Untitled",
            "video_url": str(row.video),
            "image": str(row.image) if row.image else None
        }
        recipes.append(recipe)
    
    return {
        "success": True,
        "count": len(recipes),
        "recipes": recipes
    }



def get_all_ingredients(limit: int = 500) -> Dict[str, Any]:
    load_graph()
    
    query = f"""
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX schema: <https://schema.org/>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    
    SELECT DISTINCT ?uri ?name ?dbpedia ?wikidata ?foodon
    WHERE {{
        ?uri a food:Ingredient .
        OPTIONAL {{ ?uri rdfs:label ?name }}
        OPTIONAL {{ 
            ?uri owl:sameAs ?dbpedia .
            FILTER(CONTAINS(STR(?dbpedia), "dbpedia.org"))
        }}
        OPTIONAL {{ 
            ?uri owl:sameAs ?wikidata .
            FILTER(CONTAINS(STR(?wikidata), "wikidata.org"))
        }}
        OPTIONAL {{ 
            ?uri owl:sameAs ?foodon .
            FILTER(CONTAINS(STR(?foodon), "obolibrary.org"))
        }}
    }}
    ORDER BY ?name
    LIMIT {limit}
    """
    
    ingredients = []
    for row in g.query(query):
        ing = {
            "uri": str(row.uri),
            "id": str(row.uri).split("/")[-1],
            "name": str(row.name) if row.name else str(row.uri).split("/")[-1].replace("_", " "),
            "external_links": {}
        }
        if row.dbpedia:
            ing["external_links"]["dbpedia"] = str(row.dbpedia)
        if row.wikidata:
            ing["external_links"]["wikidata"] = str(row.wikidata)
        if row.foodon:
            ing["external_links"]["foodon"] = str(row.foodon)
        
        ingredients.append(ing)
    
    return {
        "success": True,
        "count": len(ingredients),
        "ingredients": ingredients
    }


def get_ingredient_by_id(ingredient_id: str) -> Dict[str, Any]:
    load_graph()
    
    # Construct URI
    if not ingredient_id.startswith("http"):
        ingredient_uri = f"http://example.org/food/ingredient/{ingredient_id}"
    else:
        ingredient_uri = ingredient_id
    
    # Get ingredient info
    query = f"""
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX schema: <https://schema.org/>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    
    SELECT ?name ?dbpedia ?wikidata ?foodon ?nutrition
    WHERE {{
        <{ingredient_uri}> a food:Ingredient .
        OPTIONAL {{ <{ingredient_uri}> rdfs:label ?name }}
        OPTIONAL {{ 
            <{ingredient_uri}> owl:sameAs ?dbpedia .
            FILTER(CONTAINS(STR(?dbpedia), "dbpedia.org"))
        }}
        OPTIONAL {{ 
            <{ingredient_uri}> owl:sameAs ?wikidata .
            FILTER(CONTAINS(STR(?wikidata), "wikidata.org"))
        }}
        OPTIONAL {{ 
            <{ingredient_uri}> owl:sameAs ?foodon .
            FILTER(CONTAINS(STR(?foodon), "obolibrary.org"))
        }}
        OPTIONAL {{ <{ingredient_uri}> schema:nutrition ?nutrition }}
    }}
    """
    
    result = list(g.query(query))
    if not result:
        return {"success": False, "error": "Ingredient not found", "ingredient_id": ingredient_id}
    
    row = result[0]
    
    ingredient = {
        "uri": ingredient_uri,
        "id": ingredient_uri.split("/")[-1],
        "name": str(row.name) if row.name else ingredient_uri.split("/")[-1].replace("_", " "),
        "external_links": {},
        "recipes": []
    }
    
    if row.dbpedia:
        ingredient["external_links"]["dbpedia"] = str(row.dbpedia)
    if row.wikidata:
        ingredient["external_links"]["wikidata"] = str(row.wikidata)
    if row.foodon:
        ingredient["external_links"]["foodon"] = str(row.foodon)
    
    # Get recipes using this ingredient
    recipe_query = f"""
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX schema: <https://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?recipe ?title
    WHERE {{
        ?recipe a food:Recipe ;
                food:ingredient <{ingredient_uri}> .
        OPTIONAL {{ ?recipe schema:name ?title }}
        OPTIONAL {{ ?recipe rdfs:label ?title }}
    }}
    LIMIT 20
    """
    
    for row in g.query(recipe_query):
        ingredient["recipes"].append({
            "uri": str(row.recipe),
            "id": str(row.recipe).split("/")[-1],
            "title": str(row.title) if row.title else "Untitled"
        })
    
    return {"success": True, "ingredient": ingredient}




def get_external_links() -> Dict[str, Any]:
    load_graph()
    
    links = {
        "dbpedia": [],
        "wikidata": [],
        "foodon": []
    }
    
    query = """
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?subject ?target ?label
    WHERE {
        ?subject owl:sameAs ?target .
        OPTIONAL { ?subject rdfs:label ?label }
    }
    """
    
    for row in g.query(query):
        target = str(row.target)
        link = {
            "local_uri": str(row.subject),
            "local_id": str(row.subject).split("/")[-1],
            "local_name": str(row.label) if row.label else str(row.subject).split("/")[-1].replace("_", " "),
            "external_uri": target
        }
        
        if "dbpedia.org" in target:
            links["dbpedia"].append(link)
        elif "wikidata.org" in target:
            links["wikidata"].append(link)
        elif "obolibrary.org" in target:
            links["foodon"].append(link)
    
    return {
        "success": True,
        "counts": {
            "dbpedia": len(links["dbpedia"]),
            "wikidata": len(links["wikidata"]),
            "foodon": len(links["foodon"]),
            "total": len(links["dbpedia"]) + len(links["wikidata"]) + len(links["foodon"])
        },
        "links": links
    }



def get_all_diets() -> Dict[str, Any]:
    load_graph()
    
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
    
    diets = []
    for row in g.query(query):
        diet_name = str(row.diet).split("/")[-1].replace("_", " ")
        diets.append({
            "uri": str(row.diet),
            "name": diet_name,
            "recipe_count": int(row[1])
        })
    
    return {
        "success": True,
        "count": len(diets),
        "diets": diets
    }


def get_all_cuisines() -> Dict[str, Any]:
    load_graph()
    
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
    
    cuisines = []
    for row in g.query(query):
        cuisine_name = str(row.cuisine).split("/")[-1].replace("_", " ")
        cuisines.append({
            "uri": str(row.cuisine),
            "name": cuisine_name,
            "recipe_count": int(row[1])
        })
    
    return {
        "success": True,
        "count": len(cuisines),
        "cuisines": cuisines
    }

def execute_sparql(query: str) -> Dict[str, Any]:
    load_graph()
    
    try:
        results = g.query(query)
        
        # Convert results to JSON
        rows = []
        for row in results:
            row_dict = {}
            for i, var in enumerate(results.vars):
                value = row[i]
                if value is not None:
                    row_dict[str(var)] = str(value)
                else:
                    row_dict[str(var)] = None
            rows.append(row_dict)
        
        return {
            "success": True,
            "variables": [str(v) for v in results.vars],
            "count": len(rows),
            "results": rows
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query
        }

if __name__ == "__main__":
    import json
    
    print("=" * 70)
    print("RECIPE KNOWLEDGE GRAPH")
    print("=" * 70)
    
    # Load graph
    load_graph()
    
    # Demo: Statistics
    print("\n STATISTICS:")
    print("-" * 50)
    stats = get_statistics()
    print(json.dumps(stats, indent=2))
    
    # Demo: Search recipes with chicken
    print("\n SEARCH: Recipes with 'chicken':")
    print("-" * 50)
    results = search_recipes(ingredient="chicken", limit=5)
    print(json.dumps(results, indent=2))
    
    # Demo: Recipes with videos
    print("\n RECIPES WITH VIDEOS:")
    print("-" * 50)
    videos = get_recipes_with_videos(limit=5)
    print(json.dumps(videos, indent=2))
    
    # Demo: Get single recipe
    print("\n RECIPE DETAILS (recipe/0):")
    print("-" * 50)
    recipe = get_recipe_by_id("0")
    print(json.dumps(recipe, indent=2))
    
    # Demo: External links
    print("\nEXTERNAL LINKS SUMMARY:")
    print("-" * 50)
    links = get_external_links()
    print(f"DBpedia: {links['counts']['dbpedia']}")
    print(f"Wikidata: {links['counts']['wikidata']}")
    print(f"FoodOn: {links['counts']['foodon']}")
    print(f"Total: {links['counts']['total']}")
    
    print("\n" + "=" * 70)
    print("API Module Ready!")
    print("=" * 70)