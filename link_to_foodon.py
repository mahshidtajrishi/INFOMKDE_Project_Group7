from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD
import os

# Namespaces
RECIPE = Namespace("http://example.org/recipe/")
INGREDIENT = Namespace("http://example.org/ingredient/")
FOODON = Namespace("http://purl.obolibrary.org/obo/")
OBO = Namespace("http://purl.obolibrary.org/obo/")

# FoodOn mappings for common ingredients

FOODON_MAPPINGS = {
    # Proteins
    "chicken": "FOODON_00001040",      # chicken (food)
    "chicken breast": "FOODON_00002703", # chicken breast
    "beef": "FOODON_00001041",          # beef (food)
    "pork": "FOODON_00001042",          # pork (food)
    "salmon": "FOODON_03411222",        # salmon
    "tuna": "FOODON_03411397",          # tuna
    "shrimp": "FOODON_03411279",        # shrimp
    "egg": "FOODON_00001274",           # egg (food)
    "eggs": "FOODON_00001274",
    "bacon": "FOODON_00002618",         # bacon
    "turkey": "FOODON_00002738",        # turkey meat
    "lamb": "FOODON_00002912",          # lamb meat
    "fish": "FOODON_00001248",          # fish food product
    "tofu": "FOODON_00003296",          # tofu
    
    # Vegetables
    "tomato": "FOODON_00002505",        # tomato (whole)
    "tomatoes": "FOODON_00002505",
    "onion": "FOODON_00002501",         # onion (whole)
    "onions": "FOODON_00002501",
    "garlic": "FOODON_00001252",        # garlic (whole)
    "carrot": "FOODON_00002418",        # carrot
    "carrots": "FOODON_00002418",
    "potato": "FOODON_00002477",        # potato
    "potatoes": "FOODON_00002477",
    "broccoli": "FOODON_00002416",      # broccoli
    "spinach": "FOODON_00002499",       # spinach
    "lettuce": "FOODON_00002463",       # lettuce
    "cucumber": "FOODON_00002437",      # cucumber
    "bell pepper": "FOODON_00002468",   # bell pepper
    "pepper": "FOODON_00002468",
    "mushroom": "FOODON_00002285",      # mushroom
    "mushrooms": "FOODON_00002285",
    "celery": "FOODON_00002423",        # celery
    "corn": "FOODON_00001296",          # corn
    "peas": "FOODON_00002260",          # pea
    "zucchini": "FOODON_00002521",      # zucchini
    "eggplant": "FOODON_00002444",      # eggplant
    "cabbage": "FOODON_00002417",       # cabbage
    "asparagus": "FOODON_00002413",     # asparagus
    "green beans": "FOODON_00002251",   # green bean
    
    # Fruits
    "apple": "FOODON_00002473",         # apple (whole)
    "banana": "FOODON_00002482",        # banana
    "lemon": "FOODON_00002461",         # lemon
    "lime": "FOODON_00002464",          # lime
    "orange": "FOODON_00002490",        # orange
    "strawberry": "FOODON_00002510",    # strawberry
    "blueberry": "FOODON_00002520",     # blueberry
    "avocado": "FOODON_00002409",       # avocado
    "mango": "FOODON_00002465",         # mango
    "pineapple": "FOODON_00002492",     # pineapple
    "grape": "FOODON_00002454",         # grape
    "peach": "FOODON_00002491",         # peach
    "pear": "FOODON_00002493",          # pear
    
    # Dairy
    "milk": "FOODON_00001282",          # milk (food product)
    "cheese": "FOODON_00001013",        # cheese (food product)
    "butter": "FOODON_00001145",        # butter
    "cream": "FOODON_00001053",         # cream
    "yogurt": "FOODON_00002443",        # yogurt
    "parmesan": "FOODON_03306882",      # parmesan cheese
    "mozzarella": "FOODON_03306867",    # mozzarella
    "cheddar": "FOODON_03306833",       # cheddar cheese
    
    # Grains & Carbs
    "rice": "FOODON_00001314",          # rice (food)
    "pasta": "FOODON_00002141",         # pasta
    "bread": "FOODON_00001183",         # bread
    "flour": "FOODON_03301441",         # flour
    "noodles": "FOODON_00002138",       # noodle
    "oats": "FOODON_00001305",          # oat (food)
    "quinoa": "FOODON_00003332",        # quinoa
    
    # Herbs & Spices
    "basil": "FOODON_00002660",         # basil
    "parsley": "FOODON_00002689",       # parsley
    "cilantro": "FOODON_00002668",      # cilantro/coriander
    "oregano": "FOODON_00002686",       # oregano
    "thyme": "FOODON_00002709",         # thyme
    "rosemary": "FOODON_00002697",      # rosemary
    "ginger": "FOODON_00002677",        # ginger
    "cinnamon": "FOODON_00002665",      # cinnamon
    "cumin": "FOODON_00002671",         # cumin
    "paprika": "FOODON_00002687",       # paprika
    "turmeric": "FOODON_00002710",      # turmeric
    "black pepper": "FOODON_00002962",  # black pepper
    "salt": "FOODON_00003605",          # salt
    "sugar": "FOODON_00001244",         # sugar
    "honey": "FOODON_00001263",         # honey
    
    # Oils & Fats
    "olive oil": "FOODON_00001184",     # olive oil
    "vegetable oil": "FOODON_00001179", # vegetable oil
    "coconut oil": "FOODON_00002773",   # coconut oil
    "sesame oil": "FOODON_00002779",    # sesame oil
    
    # Legumes & Nuts
    "beans": "FOODON_00001015",         # bean (food)
    "lentils": "FOODON_00002099",       # lentil
    "chickpeas": "FOODON_00002023",     # chickpea
    "almonds": "FOODON_00002014",       # almond
    "peanuts": "FOODON_00002124",       # peanut
    "walnuts": "FOODON_00002182",       # walnut
    "cashews": "FOODON_00002022",       # cashew
    
    # Sauces & Condiments
    "soy sauce": "FOODON_00002295",     # soy sauce
    "vinegar": "FOODON_00002329",       # vinegar
    "ketchup": "FOODON_00002253",       # ketchup
    "mayonnaise": "FOODON_00002266",    # mayonnaise
    "mustard": "FOODON_00002269",       # mustard
}

def clean_ingredient_name(name):
   
    return name.lower().strip()

def link_ingredients_to_foodon(input_file, output_file):
    print("=" * 60)
    print("FOODON ONTOLOGY LINKING")
    print("=" * 60)
    
    # Load existing graph
    g = Graph()
    print(f"\nLoading: {input_file}")
    g.parse(input_file, format="turtle")
    print(f"Loaded {len(g)} triples")
    
    # Add FoodOn namespace
    g.bind("foodon", FOODON)
    g.bind("obo", OBO)
    
    # Find all ingredients
    ingredient_query = """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT DISTINCT ?ing ?label
    WHERE {
        ?ing a recipe:Ingredient .
        ?ing rdfs:label ?label .
    }
    """
    
    ingredients = list(g.query(ingredient_query))
    print(f"\nFound {len(ingredients)} ingredients")
    
    # Track statistics
    linked = 0
    not_found = []
    
    # Link each ingredient to FoodOn
    for row in ingredients:
        ing_uri = row.ing
        label = str(row.label).lower().strip()
        
        # Try to find exact match
        foodon_id = None
        
        # Check direct match
        if label in FOODON_MAPPINGS:
            foodon_id = FOODON_MAPPINGS[label]
        else:
            # Try partial matching
            for key, value in FOODON_MAPPINGS.items():
                if key in label or label in key:
                    foodon_id = value
                    break
        
        if foodon_id:
            foodon_uri = URIRef(f"http://purl.obolibrary.org/obo/{foodon_id}")
            
            # Add rdfs:subClassOf link to FoodOn class
            g.add((ing_uri, RDFS.subClassOf, foodon_uri))
            
            # Also add owl:sameAs for interoperability
            g.add((ing_uri, OWL.sameAs, foodon_uri))
            
            linked += 1
        else:
            not_found.append(label)
    
    # Save updated graph
    print(f"\nLinked {linked} ingredients to FoodOn")
    print(f"Not found: {len(not_found)} ingredients")
    
    # Show some examples of not found
    if not_found and len(not_found) <= 20:
        print(f"\nIngredients without FoodOn match:")
        for ing in not_found[:20]:
            print(f"  - {ing}")
    elif not_found:
        print(f"\nFirst 20 ingredients without FoodOn match:")
        for ing in not_found[:20]:
            print(f"  - {ing}")
    
    # Save
    g.serialize(output_file, format="turtle")
    print(f"\nSaved to: {output_file}")
    print(f"Total triples: {len(g)}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Ingredients processed: {len(ingredients)}")
    print(f"FoodOn links added: {linked * 2}")  # subClassOf + sameAs
    print(f"Link types: rdfs:subClassOf, owl:sameAs")
    print(f"FoodOn namespace: http://purl.obolibrary.org/obo/FOODON_*")
    print("=" * 60)
    
    return linked

if __name__ == "__main__":
    # File paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    
    input_file = os.path.join(project_dir, "output", "recipes_with_usda.ttl")
    output_file = os.path.join(project_dir, "output", "recipes_with_foodon.ttl")
    
    # Check if input exists
    if not os.path.exists(input_file):
        # Try alternative input
        input_file = os.path.join(project_dir, "output", "recipes_integrated.ttl")
    
    if not os.path.exists(input_file):
        print(f"ERROR: Input file not found: {input_file}")
        exit(1)
    
    # Run linking
    link_ingredients_to_foodon(input_file, output_file)