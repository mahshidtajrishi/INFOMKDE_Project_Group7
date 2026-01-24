import requests
import time
import re
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD
import os
import urllib.parse

# Namespaces
RECIPE = Namespace("http://example.org/recipe/")
INGREDIENT = Namespace("http://example.org/ingredient/")
DBPEDIA = Namespace("http://dbpedia.org/resource/")
WIKIDATA = Namespace("http://www.wikidata.org/entity/")
DBO = Namespace("http://dbpedia.org/ontology/")


def clean_ingredient_name(name):
    """Clean ingredient name for better matching."""
    # Remove common prefixes/suffixes that hurt matching
    name = name.lower().strip()
    
    # Remove measurements and quantities
    patterns_to_remove = [
        r'^\d+[\d./]*\s*',  # Numbers at start
        r'\s*\(.*?\)',       # Parentheses content
        r'\s*,.*$',          # Everything after comma
        r'^(fresh|dried|ground|chopped|minced|diced|sliced|whole|raw|cooked)\s+',
        r'\s+(fresh|dried|ground|chopped|minced|diced|sliced|whole|raw|cooked)$',
        r'^(a|an|the)\s+',
        r'\s+\*\d+$',        # *1, *2 suffixes
        r'^optional:\s*',
        r'^additional\s+',
        r'\s+to\s+taste$',
        r'\s+or\s+.*$',
    ]
    
    for pattern in patterns_to_remove:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)
    
    return name.strip()


def search_dbpedia(ingredient_name):
    clean_name = clean_ingredient_name(ingredient_name)
    if not clean_name or len(clean_name) < 2:
        return None
    
    # DBpedia Lookup API
    url = "http://lookup.dbpedia.org/api/search"
    params = {
        "query": clean_name,
        "maxResults": 5,
        "format": "json"
    }
    headers = {
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            # Look for food-related results
            if "docs" in data:
                for doc in data["docs"]:
                    resource = doc.get("resource", [""])[0]
                    categories = doc.get("category", [])
                    type_name = doc.get("typeName", [""])[0] if doc.get("typeName") else ""
                    
                    # Check if it's food-related
                    is_food = any(
                        "food" in str(cat).lower() or 
                        "vegetable" in str(cat).lower() or
                        "fruit" in str(cat).lower() or
                        "spice" in str(cat).lower() or
                        "ingredient" in str(cat).lower() or
                        "cuisine" in str(cat).lower()
                        for cat in categories
                    )
                    
                    # Also check type
                    if "food" in type_name.lower() or is_food:
                        return resource
                    
                # If no food-specific match, return first result if name matches well
                if data["docs"]:
                    first_label = data["docs"][0].get("label", [""])[0].lower()
                    if clean_name in first_label or first_label in clean_name:
                        return data["docs"][0].get("resource", [""])[0]
                        
    except Exception as e:
        pass  # Silently handle errors
    
    return None


def search_dbpedia_sparql(ingredient_name):
    clean_name = clean_ingredient_name(ingredient_name)
    if not clean_name or len(clean_name) < 2:
        return None
    
    # Capitalize first letter for DBpedia resource naming convention
    dbpedia_name = clean_name.title().replace(" ", "_")
    
    # Try direct resource lookup first
    direct_uri = f"http://dbpedia.org/resource/{urllib.parse.quote(dbpedia_name)}"
    
    # Verify it exists using SPARQL
    sparql_endpoint = "http://dbpedia.org/sparql"
    query = f"""
    ASK {{
        <{direct_uri}> ?p ?o .
    }}
    """
    
    try:
        response = requests.get(
            sparql_endpoint,
            params={"query": query, "format": "json"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("boolean", False):
                return direct_uri
    except:
        pass
    
    return None


def search_wikidata(ingredient_name):
    clean_name = clean_ingredient_name(ingredient_name)
    if not clean_name or len(clean_name) < 2:
        return None
    
    # Wikidata API
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "search": clean_name,
        "language": "en",
        "limit": 5,
        "format": "json"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            if "search" in data and data["search"]:
                # Look for food-related items
                for item in data["search"]:
                    description = item.get("description", "").lower()
                    label = item.get("label", "").lower()
                    
                    # Check if description suggests it's food
                    food_keywords = ["food", "vegetable", "fruit", "spice", "herb", 
                                   "ingredient", "dish", "plant", "edible", "cuisine",
                                   "legume", "grain", "nut", "meat", "fish", "dairy"]
                    
                    is_food = any(kw in description for kw in food_keywords)
                    
                    if is_food or clean_name == label:
                        entity_id = item.get("id")
                        return f"http://www.wikidata.org/entity/{entity_id}"
                
                # If no food-specific match, return first if label matches
                first_item = data["search"][0]
                if clean_name == first_item.get("label", "").lower():
                    entity_id = first_item.get("id")
                    return f"http://www.wikidata.org/entity/{entity_id}"
                    
    except Exception as e:
        pass
    
    return None


def get_dbpedia_info(dbpedia_uri):
    
    sparql_endpoint = "http://dbpedia.org/sparql"
    
    query = f"""
    PREFIX dbo: <http://dbpedia.org/ontology/>
    PREFIX dbp: <http://dbpedia.org/property/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?abstract ?thumbnail ?origin
    WHERE {{
        <{dbpedia_uri}> rdfs:comment ?abstract .
        FILTER (lang(?abstract) = 'en')
        OPTIONAL {{ <{dbpedia_uri}> dbo:thumbnail ?thumbnail }}
        OPTIONAL {{ <{dbpedia_uri}> dbo:origin ?origin }}
    }}
    LIMIT 1
    """
    
    try:
        response = requests.get(
            sparql_endpoint,
            params={"query": query, "format": "json"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data["results"]["bindings"]:
                result = data["results"]["bindings"][0]
                return {
                    "abstract": result.get("abstract", {}).get("value"),
                    "thumbnail": result.get("thumbnail", {}).get("value"),
                    "origin": result.get("origin", {}).get("value")
                }
    except:
        pass
    
    return None


def main():
    print("=" * 70)
    print("DATA INTEGRATION: Linking to DBpedia and Wikidata")
    print("=" * 70)
    
    # Load the graph
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, "..", "output", "recipes_with_ontology.ttl")
    output_path = os.path.join(script_dir, "..", "output", "recipes_integrated.ttl")
    
    print(f"\nLoading RDF from: {input_path}")
    g = Graph()
    g.parse(input_path, format="turtle")
    original_count = len(g)
    print(f"Loaded {original_count} triples")
    
    # Find all ingredients
    print("\nFinding ingredients...")
    ingredients = {}
    
    for ing in g.subjects(RDF.type, RECIPE.Ingredient):
        labels = list(g.objects(ing, RDFS.label))
        if labels:
            # Get the first label (usually the cleanest one)
            label = str(labels[0])
            ingredients[ing] = label
    
    print(f"Found {len(ingredients)} unique ingredients")
    
    # Link to external knowledge bases
    print("\n" + "-" * 70)
    print("Linking to DBpedia and Wikidata...")
    print("-" * 70)
    
    dbpedia_links = 0
    wikidata_links = 0
    
    # Define some manual mappings for common ingredients
    manual_dbpedia = {
        "olive oil": "http://dbpedia.org/resource/Olive_oil",
        "garlic": "http://dbpedia.org/resource/Garlic",
        "onion": "http://dbpedia.org/resource/Onion",
        "salt": "http://dbpedia.org/resource/Salt",
        "pepper": "http://dbpedia.org/resource/Black_pepper",
        "tomato": "http://dbpedia.org/resource/Tomato",
        "carrot": "http://dbpedia.org/resource/Carrot",
        "chicken": "http://dbpedia.org/resource/Chicken_as_food",
        "beef": "http://dbpedia.org/resource/Beef",
        "rice": "http://dbpedia.org/resource/Rice",
        "quinoa": "http://dbpedia.org/resource/Quinoa",
        "kale": "http://dbpedia.org/resource/Kale",
        "lentil": "http://dbpedia.org/resource/Lentil",
        "chickpea": "http://dbpedia.org/resource/Chickpea",
        "avocado": "http://dbpedia.org/resource/Avocado",
        "cilantro": "http://dbpedia.org/resource/Coriander",
        "cumin": "http://dbpedia.org/resource/Cumin",
        "turmeric": "http://dbpedia.org/resource/Turmeric",
        "ginger": "http://dbpedia.org/resource/Ginger",
        "basil": "http://dbpedia.org/resource/Basil",
        "parsley": "http://dbpedia.org/resource/Parsley",
        "thyme": "http://dbpedia.org/resource/Thyme",
        "rosemary": "http://dbpedia.org/resource/Rosemary",
        "oregano": "http://dbpedia.org/resource/Oregano",
        "cinnamon": "http://dbpedia.org/resource/Cinnamon",
        "honey": "http://dbpedia.org/resource/Honey",
        "lemon": "http://dbpedia.org/resource/Lemon",
        "lime": "http://dbpedia.org/resource/Lime_(fruit)",
        "orange": "http://dbpedia.org/resource/Orange_(fruit)",
        "apple": "http://dbpedia.org/resource/Apple",
        "banana": "http://dbpedia.org/resource/Banana",
        "spinach": "http://dbpedia.org/resource/Spinach",
        "broccoli": "http://dbpedia.org/resource/Broccoli",
        "cauliflower": "http://dbpedia.org/resource/Cauliflower",
        "potato": "http://dbpedia.org/resource/Potato",
        "celery": "http://dbpedia.org/resource/Celery",
        "mushroom": "http://dbpedia.org/resource/Mushroom",
        "egg": "http://dbpedia.org/resource/Egg_as_food",
        "butter": "http://dbpedia.org/resource/Butter",
        "cheese": "http://dbpedia.org/resource/Cheese",
        "milk": "http://dbpedia.org/resource/Milk",
        "yogurt": "http://dbpedia.org/resource/Yogurt",
        "salmon": "http://dbpedia.org/resource/Salmon_as_food",
        "shrimp": "http://dbpedia.org/resource/Shrimp",
        "tofu": "http://dbpedia.org/resource/Tofu",
        "soy sauce": "http://dbpedia.org/resource/Soy_sauce",
        "vinegar": "http://dbpedia.org/resource/Vinegar",
        "mustard": "http://dbpedia.org/resource/Mustard_(condiment)",
        "mayonnaise": "http://dbpedia.org/resource/Mayonnaise",
        "pasta": "http://dbpedia.org/resource/Pasta",
        "bread": "http://dbpedia.org/resource/Bread",
        "flour": "http://dbpedia.org/resource/Flour",
        "sugar": "http://dbpedia.org/resource/Sugar",
        "corn": "http://dbpedia.org/resource/Corn",
        "bean": "http://dbpedia.org/resource/Bean",
        "pea": "http://dbpedia.org/resource/Pea",
        "asparagus": "http://dbpedia.org/resource/Asparagus",
        "zucchini": "http://dbpedia.org/resource/Zucchini",
        "eggplant": "http://dbpedia.org/resource/Eggplant",
        "cabbage": "http://dbpedia.org/resource/Cabbage",
        "lettuce": "http://dbpedia.org/resource/Lettuce",
        "cucumber": "http://dbpedia.org/resource/Cucumber",
        "bell pepper": "http://dbpedia.org/resource/Bell_pepper",
        "jalapeño": "http://dbpedia.org/resource/Jalapeño",
        "chili": "http://dbpedia.org/resource/Chili_pepper",
        "coconut": "http://dbpedia.org/resource/Coconut",
        "almond": "http://dbpedia.org/resource/Almond",
        "walnut": "http://dbpedia.org/resource/Walnut",
        "peanut": "http://dbpedia.org/resource/Peanut",
        "cashew": "http://dbpedia.org/resource/Cashew",
        "sesame": "http://dbpedia.org/resource/Sesame",
        "olive": "http://dbpedia.org/resource/Olive",
        "mango": "http://dbpedia.org/resource/Mango",
        "strawberry": "http://dbpedia.org/resource/Strawberry",
        "cherry": "http://dbpedia.org/resource/Cherry",
        "pork": "http://dbpedia.org/resource/Pork",
        "bacon": "http://dbpedia.org/resource/Bacon",
        "ham": "http://dbpedia.org/resource/Ham",
        "sausage": "http://dbpedia.org/resource/Sausage",
    }
    
    manual_wikidata = {
        "olive oil": "http://www.wikidata.org/entity/Q179049",
        "garlic": "http://www.wikidata.org/entity/Q23400",
        "onion": "http://www.wikidata.org/entity/Q23485",
        "salt": "http://www.wikidata.org/entity/Q11254",
        "pepper": "http://www.wikidata.org/entity/Q43304",
        "tomato": "http://www.wikidata.org/entity/Q235",
        "carrot": "http://www.wikidata.org/entity/Q81",
        "rice": "http://www.wikidata.org/entity/Q5090",
        "quinoa": "http://www.wikidata.org/entity/Q192072",
        "kale": "http://www.wikidata.org/entity/Q37453",
        "lentil": "http://www.wikidata.org/entity/Q217283",
        "chickpea": "http://www.wikidata.org/entity/Q42589",
        "avocado": "http://www.wikidata.org/entity/Q961769",
        "cumin": "http://www.wikidata.org/entity/Q26037",
        "honey": "http://www.wikidata.org/entity/Q10987",
        "lemon": "http://www.wikidata.org/entity/Q1093742",
        "spinach": "http://www.wikidata.org/entity/Q47305",
        "broccoli": "http://www.wikidata.org/entity/Q47722",
        "potato": "http://www.wikidata.org/entity/Q10998",
        "egg": "http://www.wikidata.org/entity/Q17147",
        "butter": "http://www.wikidata.org/entity/Q34172",
        "cheese": "http://www.wikidata.org/entity/Q10943",
        "milk": "http://www.wikidata.org/entity/Q8495",
        "salmon": "http://www.wikidata.org/entity/Q2066715",
        "tofu": "http://www.wikidata.org/entity/Q177378",
        "pasta": "http://www.wikidata.org/entity/Q178",
        "corn": "http://www.wikidata.org/entity/Q11575",
        "bean": "http://www.wikidata.org/entity/Q379813",
        "asparagus": "http://www.wikidata.org/entity/Q28298",
        "eggplant": "http://www.wikidata.org/entity/Q7540",
        "mushroom": "http://www.wikidata.org/entity/Q83093",
        "ginger": "http://www.wikidata.org/entity/Q35625",
        "turmeric": "http://www.wikidata.org/entity/Q42562",
        "cinnamon": "http://www.wikidata.org/entity/Q28165",
        "basil": "http://www.wikidata.org/entity/Q8269",
        "mango": "http://www.wikidata.org/entity/Q169",
    }
    
    processed = 0
    for ing_uri, label in ingredients.items():
        processed += 1
        clean_label = clean_ingredient_name(label)
        
        # Skip very short or generic labels
        if len(clean_label) < 2:
            continue
        
        found_dbpedia = False
        found_wikidata = False
        
        # Check manual mappings first
        for key, dbpedia_uri in manual_dbpedia.items():
            if key in clean_label or clean_label in key:
                g.add((ing_uri, OWL.sameAs, URIRef(dbpedia_uri)))
                dbpedia_links += 1
                found_dbpedia = True
                break
        
        for key, wikidata_uri in manual_wikidata.items():
            if key in clean_label or clean_label in key:
                g.add((ing_uri, OWL.sameAs, URIRef(wikidata_uri)))
                wikidata_links += 1
                found_wikidata = True
                break
        
        # If not found manually, try searching
        if not found_dbpedia and processed <= 20:  # Limit API calls
            dbpedia_uri = search_dbpedia_sparql(clean_label)
            if dbpedia_uri:
                g.add((ing_uri, OWL.sameAs, URIRef(dbpedia_uri)))
                dbpedia_links += 1
                found_dbpedia = True
                time.sleep(0.3)  # Rate limiting
        
        if not found_wikidata and processed <= 20:
            wikidata_uri = search_wikidata(clean_label)
            if wikidata_uri:
                g.add((ing_uri, OWL.sameAs, URIRef(wikidata_uri)))
                wikidata_links += 1
                found_wikidata = True
                time.sleep(0.3)  # Rate limiting
        
        # Progress indicator
        if processed % 20 == 0:
            print(f"  Processed {processed}/{len(ingredients)} ingredients...")
    
    # Add namespace declarations for external KBs
    g.bind("dbpedia", DBPEDIA)
    g.bind("wikidata", WIKIDATA)
    g.bind("dbo", DBO)
    g.bind("owl", OWL)
    
    # Save the enhanced graph
    print(f"\nSaving integrated RDF to: {output_path}")
    g.serialize(destination=output_path, format="turtle")
    
    new_count = len(g)
    added = new_count - original_count
    
    # Print summary
    print("\n" + "=" * 70)
    print("INTEGRATION SUMMARY")
    print("=" * 70)
    print(f"Original triples:      {original_count}")
    print(f"New triples:           {new_count}")
    print(f"Triples added:         {added}")
    print(f"")
    print(f"DBpedia links added:   {dbpedia_links}")
    print(f"Wikidata links added:  {wikidata_links}")
    print(f"Total owl:sameAs:      {dbpedia_links + wikidata_links}")
    print(f"")
    
    
    # Show some examples
    print("\n" + "=" * 70)
    print("EXAMPLE LINKS CREATED")
    print("=" * 70)
    
    example_count = 0
    for s, p, o in g.triples((None, OWL.sameAs, None)):
        if example_count < 10:
            # Get the label
            labels = list(g.objects(s, RDFS.label))
            if labels:
                label = str(labels[0])
                print(f"  {label}")
                print(f"    → {o}")
                example_count += 1
    
    print("\n" + "=" * 70)
   
    print("=" * 70)
    


if __name__ == "__main__":
    main()
