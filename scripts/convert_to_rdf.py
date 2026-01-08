import json
import os
from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD, OWL



# custom namespace for recipes
RECIPE = Namespace("http://example.org/recipe/")

# custom namespace for ingredients
INGREDIENT = Namespace("http://example.org/ingredient/")

#  custom namespace for cuisines
CUISINE = Namespace("http://example.org/cuisine/")

# Schema.org
SCHEMA = Namespace("http://schema.org/")

# Food Ontology (if we want to link to existing food ontologies)
FOOD = Namespace("http://purl.org/foodontology#")


def clean_string_for_uri(text):
    """
    Convert a string into a valid URI component.
    Example: "Red Kidney Bean" -> "red_kidney_bean"
    """
    if not text:
        return "unknown"
   
    clean = text.lower().strip()
    clean = clean.replace(" ", "_")
    clean = clean.replace("&", "and")
   
    clean = ''.join(c for c in clean if c.isalnum() or c == '_')
    return clean


def create_recipe_graph(recipes_data):
    """
    Create an RDF graph from recipe JSON data.
    
    This function:
    1. Creates a new RDF graph
    2. Defines the ontology classes (Recipe, Ingredient, Cuisine)
    3. Creates instances (actual recipes) with their properties
    """
    
    
    g = Graph()
    
    
    g.bind("recipe", RECIPE)
    g.bind("ingredient", INGREDIENT)
    g.bind("cuisine", CUISINE)
    g.bind("schema", SCHEMA)
    g.bind("food", FOOD)
    
    print("Creating RDF triples...")
    print("-" * 40)
    
   
    # These define WHAT TYPES of things exist in our knowledge graph
    
    # Define Recipe as a class
    g.add((RECIPE.Recipe, RDF.type, OWL.Class))
    g.add((RECIPE.Recipe, RDFS.label, Literal("Recipe", lang="en")))
    g.add((RECIPE.Recipe, RDFS.comment, Literal("A food recipe with ingredients and instructions", lang="en")))
    
    # Define Ingredient as a class
    g.add((RECIPE.Ingredient, RDF.type, OWL.Class))
    g.add((RECIPE.Ingredient, RDFS.label, Literal("Ingredient", lang="en")))
    
    # Define Cuisine as a class
    g.add((RECIPE.Cuisine, RDF.type, OWL.Class))
    g.add((RECIPE.Cuisine, RDFS.label, Literal("Cuisine", lang="en")))
    
    # Define Diet as a class (vegetarian, vegan, etc.)
    g.add((RECIPE.Diet, RDF.type, OWL.Class))
    g.add((RECIPE.Diet, RDFS.label, Literal("Diet", lang="en")))
    
    # Define NutritionInfo as a class
    g.add((RECIPE.NutritionInfo, RDF.type, OWL.Class))
    g.add((RECIPE.NutritionInfo, RDFS.label, Literal("Nutrition Information", lang="en")))
    g.add((RECIPE.IngredientUsage, RDF.type, OWL.Class))
    g.add((RECIPE.IngredientUsage, RDFS.label, Literal("Ingredient Usage", lang="en")))
    
    
   
    # STEP 2: Define properties (relationships)
   
    # hasIngredient: Recipe -> Ingredient
    g.add((RECIPE.hasIngredient, RDF.type, OWL.ObjectProperty))
    g.add((RECIPE.hasIngredient, RDFS.domain, RECIPE.Recipe))
    g.add((RECIPE.hasIngredient, RDFS.range, RECIPE.Ingredient))
    
    # ingredientUsage: Recipe -> Usage (blank node)
    g.add((RECIPE.ingredientUsage, RDF.type, OWL.ObjectProperty))
    g.add((RECIPE.ingredientUsage, RDFS.domain, RECIPE.Recipe))
    g.add((RECIPE.ingredientUsage, RDFS.range, RECIPE.IngredientUsage))
    
    # usesIngredient: Usage -> Ingredient
    g.add((RECIPE.usesIngredient, RDF.type, OWL.ObjectProperty))
    g.add((RECIPE.usesIngredient, RDFS.domain, RECIPE.IngredientUsage))
    g.add((RECIPE.usesIngredient, RDFS.range, RECIPE.Ingredient))

    
    
    # hasCuisine: Recipe -> Cuisine
    g.add((RECIPE.hasCuisine, RDF.type, OWL.ObjectProperty))
    g.add((RECIPE.hasCuisine, RDFS.domain, RECIPE.Recipe))
    g.add((RECIPE.hasCuisine, RDFS.range, RECIPE.Cuisine))
    
    # hasDiet: Recipe -> Diet
    g.add((RECIPE.hasDiet, RDF.type, OWL.ObjectProperty))
    g.add((RECIPE.hasDiet, RDFS.domain, RECIPE.Recipe))
    g.add((RECIPE.hasDiet, RDFS.range, RECIPE.Diet))
    
    # hasNutrition: Recipe -> NutritionInfo
    g.add((RECIPE.hasNutrition, RDF.type, OWL.ObjectProperty))
    g.add((RECIPE.hasNutrition, RDFS.domain, RECIPE.Recipe))
    g.add((RECIPE.hasNutrition, RDFS.range, RECIPE.NutritionInfo))
    
    # Data properties (literal values)
    g.add((RECIPE.title, RDF.type, OWL.DatatypeProperty))
    g.add((RECIPE.readyInMinutes, RDF.type, OWL.DatatypeProperty))
    g.add((RECIPE.servings, RDF.type, OWL.DatatypeProperty))
    g.add((RECIPE.ingredientAmount, RDF.type, OWL.DatatypeProperty))
    g.add((RECIPE.ingredientUnit, RDF.type, OWL.DatatypeProperty))
    g.add((RECIPE.calories, RDF.type, OWL.DatatypeProperty))
    g.add((RECIPE.protein, RDF.type, OWL.DatatypeProperty))
    g.add((RECIPE.fat, RDF.type, OWL.DatatypeProperty))
    g.add((RECIPE.carbohydrates, RDF.type, OWL.DatatypeProperty))
    
    
    # STEP 3: Create instances (ABox) - actual recipe data
   
    recipes = recipes_data.get('results', [])
    
    for recipe in recipes:
        recipe_id = recipe.get('id')
        title = recipe.get('title', 'Unknown Recipe')
        
        print(f"  Processing: {title}")
        
        # Create URI for this recipe
        recipe_uri = RECIPE[f"recipe_{recipe_id}"]
        
        # Add type triple: this resource IS A Recipe
        g.add((recipe_uri, RDF.type, RECIPE.Recipe))
        
        # Add basic properties
        g.add((recipe_uri, RECIPE.title, Literal(title, datatype=XSD.string)))
        g.add((recipe_uri, RDFS.label, Literal(title, lang="en")))
        
        if recipe.get('readyInMinutes'):
            g.add((recipe_uri, RECIPE.readyInMinutes, 
                   Literal(recipe['readyInMinutes'], datatype=XSD.integer)))
        
        if recipe.get('servings'):
            g.add((recipe_uri, RECIPE.servings, 
                   Literal(recipe['servings'], datatype=XSD.integer)))
        
        if recipe.get('image'):
            g.add((recipe_uri, SCHEMA.image, URIRef(recipe['image'])))
        
        # ------------------------------------------------
        # Add cuisines
        # ------------------------------------------------
        for cuisine_name in recipe.get('cuisines', []):
            cuisine_uri = CUISINE[clean_string_for_uri(cuisine_name)]
            # Define the cuisine instance
            g.add((cuisine_uri, RDF.type, RECIPE.Cuisine))
            g.add((cuisine_uri, RDFS.label, Literal(cuisine_name, lang="en")))
            # Link recipe to cuisine
            g.add((recipe_uri, RECIPE.hasCuisine, cuisine_uri))
        
        # ------------------------------------------------
        # Add diets (vegetarian, vegan, gluten-free, etc.)
        # ------------------------------------------------
        for diet_name in recipe.get('diets', []):
            diet_uri = RECIPE[f"diet_{clean_string_for_uri(diet_name)}"]
            g.add((diet_uri, RDF.type, RECIPE.Diet))
            g.add((diet_uri, RDFS.label, Literal(diet_name, lang="en")))
            g.add((recipe_uri, RECIPE.hasDiet, diet_uri))
        
        # ------------------------------------------------
        # Add ingredients
        # ------------------------------------------------
        for ing in recipe.get('extendedIngredients', []):
            ing_id = ing.get('id', hash(ing.get('name', '')))
            ing_name = ing.get('name', 'unknown')
            
            # Create ingredient URI
            ingredient_uri = INGREDIENT[f"ing_{ing_id}"]
            
            # Define the ingredient
            g.add((ingredient_uri, RDF.type, RECIPE.Ingredient))
            g.add((ingredient_uri, RDFS.label, Literal(ing_name, lang="en")))
            
            # Link recipe to ingredient
            g.add((recipe_uri, RECIPE.hasIngredient, ingredient_uri))
            
            # Create a blank node for the specific usage of this ingredient in this recipe
            # (because the same ingredient can have different amounts in different recipes)
            usage = BNode()
            g.add((usage, RDF.type, RECIPE.IngredientUsage))
            g.add((recipe_uri, RECIPE.ingredientUsage, usage))
            g.add((usage, RECIPE.usesIngredient, ingredient_uri))
            
            if ing.get('amount'):
                g.add((usage, RECIPE.ingredientAmount, 
                       Literal(ing['amount'], datatype=XSD.float)))
            if ing.get('unit'):
                g.add((usage, RECIPE.ingredientUnit, 
                       Literal(ing['unit'], datatype=XSD.string)))
        
        # ------------------------------------------------
        # Add nutrition information
        # ------------------------------------------------
        nutrition = recipe.get('nutrition', {})
        nutrients = nutrition.get('nutrients', [])
        
        if nutrients:
            nutrition_uri = RECIPE[f"nutrition_{recipe_id}"]
            g.add((nutrition_uri, RDF.type, RECIPE.NutritionInfo))
            g.add((recipe_uri, RECIPE.hasNutrition, nutrition_uri))
            
            for nutrient in nutrients:
                name = nutrient.get('name', '').lower()
                amount = nutrient.get('amount')
                
                if amount is not None:
                    if 'calorie' in name:
                        g.add((nutrition_uri, RECIPE.calories, 
                               Literal(amount, datatype=XSD.float)))
                    elif 'protein' in name:
                        g.add((nutrition_uri, RECIPE.protein, 
                               Literal(amount, datatype=XSD.float)))
                    elif 'fat' in name and 'saturated' not in name:
                        g.add((nutrition_uri, RECIPE.fat, 
                               Literal(amount, datatype=XSD.float)))
                    elif 'carbohydrate' in name:
                        g.add((nutrition_uri, RECIPE.carbohydrates, 
                               Literal(amount, datatype=XSD.float)))
    
    print("-" * 40)
    print(f"✓ Created {len(g)} triples from {len(recipes)} recipes")
    
    return g


def main():
    """
    Main function to load JSON and convert to RDF.
    """
    print("=" * 60)
    print("JSON TO RDF CONVERTER")
    print("=" * 60)
    
    # Get paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.join(script_dir, "..")
    data_dir = os.path.join(project_dir, "data")
    output_dir = os.path.join(project_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    
    # Try to load data files in order of preference
    all_recipes_path = os.path.join(data_dir, "all_recipes.json")
    real_data_path = os.path.join(data_dir, "spoonacular_recipes_raw.json")
    sample_data_path = os.path.join(data_dir, "sample_recipes.json")
    
    if os.path.exists(all_recipes_path):
        data_path = all_recipes_path
        print(f"Using all recipes data: {data_path}")
    elif os.path.exists(real_data_path):
        data_path = real_data_path
        print(f"Using real Spoonacular data: {data_path}")
    elif os.path.exists(sample_data_path):
        data_path = sample_data_path
        print(f"Using sample data: {data_path}")
    else:
        print("✗ No data found! Run fetch_more_recipes.py first.")
        return
    
    # Load JSON data
    print(f"\nLoading data from: {data_path}")
    with open(data_path, 'r', encoding='utf-8') as f:
        recipes_data = json.load(f)
    
    # Handle both formats (list or dict with 'results')
    if isinstance(recipes_data, list):
        recipes_data = {"results": recipes_data}
    print(f"Found {len(recipes_data.get('results', []))} recipes\n")
    
    # Create RDF graph
    graph = create_recipe_graph(recipes_data)
    
    # Save as Turtle format (human-readable)
    turtle_path = os.path.join(output_dir, "recipes.ttl")
    graph.serialize(destination=turtle_path, format='turtle')
    print(f"\n✓ Saved Turtle format: {turtle_path}")
    
    # Save as RDF/XML format (for tools)
    rdf_xml_path = os.path.join(output_dir, "recipes.rdf")
    graph.serialize(destination=rdf_xml_path, format='xml')
    print(f"✓ Saved RDF/XML format: {rdf_xml_path}")
    
    # Print some example triples
    print("\n" + "=" * 60)
    print("SAMPLE TRIPLES (first 10)")
    print("=" * 60)
    
    for i, (s, p, o) in enumerate(graph):
        if i >= 10:
            break
        print(f"  {s.n3()} {p.n3()} {o.n3()}")
    
    print("\n" + "=" * 60)
  
    print("=" * 60)
   


if __name__ == "__main__":
    main()
