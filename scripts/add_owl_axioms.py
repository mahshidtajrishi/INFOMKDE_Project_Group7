
from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD, OWL
import os

# Namespaces
RECIPE = Namespace("http://example.org/recipe/")
INGREDIENT = Namespace("http://example.org/ingredient/")
CUISINE = Namespace("http://example.org/cuisine/")
SCHEMA = Namespace("http://schema.org/")
DBPEDIA = Namespace("http://dbpedia.org/resource/")
WIKIDATA = Namespace("http://www.wikidata.org/entity/")


def add_ontology_axioms(g):
    """
    Add RDFS and OWL axioms to the graph.
    This creates a proper ontology with reasoning capabilities.
    """
    
    print("Adding RDFS/OWL axioms...")
    print("-" * 50)
    
    
    # 1. ONTOLOGY 
   
    ontology_uri = URIRef("http://example.org/recipe/ontology")
    g.add((ontology_uri, RDF.type, OWL.Ontology))
    g.add((ontology_uri, RDFS.label, Literal("Smart Recipe Knowledge Graph Ontology", lang="en")))
    g.add((ontology_uri, RDFS.comment, Literal(
        "An ontology for representing recipes, ingredients, cuisines, and nutritional information. "
        "Created for INFOMKDE course at Utrecht University.", lang="en")))
    g.add((ontology_uri, OWL.versionInfo, Literal("1.0")))
    
    print("  ✓ Added ontology metadata")
    
    
    # 2. CLASS HIERARCHY (rdfs:subClassOf)
    
    # Recipe subclasses based on diet
    g.add((RECIPE.VeganRecipe, RDF.type, OWL.Class))
    g.add((RECIPE.VeganRecipe, RDFS.subClassOf, RECIPE.Recipe))
    g.add((RECIPE.VeganRecipe, RDFS.label, Literal("Vegan Recipe", lang="en")))
    g.add((RECIPE.VeganRecipe, RDFS.comment, Literal("A recipe that contains no animal products", lang="en")))
    
    g.add((RECIPE.VegetarianRecipe, RDF.type, OWL.Class))
    g.add((RECIPE.VegetarianRecipe, RDFS.subClassOf, RECIPE.Recipe))
    g.add((RECIPE.VegetarianRecipe, RDFS.label, Literal("Vegetarian Recipe", lang="en")))
    
    g.add((RECIPE.GlutenFreeRecipe, RDF.type, OWL.Class))
    g.add((RECIPE.GlutenFreeRecipe, RDFS.subClassOf, RECIPE.Recipe))
    g.add((RECIPE.GlutenFreeRecipe, RDFS.label, Literal("Gluten-Free Recipe", lang="en")))
    
    g.add((RECIPE.DairyFreeRecipe, RDF.type, OWL.Class))
    g.add((RECIPE.DairyFreeRecipe, RDFS.subClassOf, RECIPE.Recipe))
    g.add((RECIPE.DairyFreeRecipe, RDFS.label, Literal("Dairy-Free Recipe", lang="en")))
    
    # Recipe subclasses based on preparation time
    g.add((RECIPE.QuickRecipe, RDF.type, OWL.Class))
    g.add((RECIPE.QuickRecipe, RDFS.subClassOf, RECIPE.Recipe))
    g.add((RECIPE.QuickRecipe, RDFS.label, Literal("Quick Recipe", lang="en")))
    g.add((RECIPE.QuickRecipe, RDFS.comment, Literal("A recipe that can be prepared in under 30 minutes", lang="en")))
    
    g.add((RECIPE.SlowCookerRecipe, RDF.type, OWL.Class))
    g.add((RECIPE.SlowCookerRecipe, RDFS.subClassOf, RECIPE.Recipe))
    g.add((RECIPE.SlowCookerRecipe, RDFS.label, Literal("Slow Cooker Recipe", lang="en")))
    
    # Recipe subclasses based on nutrition
    g.add((RECIPE.LowCalorieRecipe, RDF.type, OWL.Class))
    g.add((RECIPE.LowCalorieRecipe, RDFS.subClassOf, RECIPE.Recipe))
    g.add((RECIPE.LowCalorieRecipe, RDFS.label, Literal("Low-Calorie Recipe", lang="en")))
    g.add((RECIPE.LowCalorieRecipe, RDFS.comment, Literal("A recipe with less than 300 calories per serving", lang="en")))
    
    g.add((RECIPE.HighProteinRecipe, RDF.type, OWL.Class))
    g.add((RECIPE.HighProteinRecipe, RDFS.subClassOf, RECIPE.Recipe))
    g.add((RECIPE.HighProteinRecipe, RDFS.label, Literal("High-Protein Recipe", lang="en")))
    g.add((RECIPE.HighProteinRecipe, RDFS.comment, Literal("A recipe with more than 20g protein per serving", lang="en")))
    
    # Ingredient subclasses
    g.add((RECIPE.Vegetable, RDF.type, OWL.Class))
    g.add((RECIPE.Vegetable, RDFS.subClassOf, RECIPE.Ingredient))
    g.add((RECIPE.Vegetable, RDFS.label, Literal("Vegetable", lang="en")))
    
    g.add((RECIPE.Protein, RDF.type, OWL.Class))
    g.add((RECIPE.Protein, RDFS.subClassOf, RECIPE.Ingredient))
    g.add((RECIPE.Protein, RDFS.label, Literal("Protein Source", lang="en")))
    
    g.add((RECIPE.Grain, RDF.type, OWL.Class))
    g.add((RECIPE.Grain, RDFS.subClassOf, RECIPE.Ingredient))
    g.add((RECIPE.Grain, RDFS.label, Literal("Grain", lang="en")))
    
    g.add((RECIPE.Dairy, RDF.type, OWL.Class))
    g.add((RECIPE.Dairy, RDFS.subClassOf, RECIPE.Ingredient))
    g.add((RECIPE.Dairy, RDFS.label, Literal("Dairy Product", lang="en")))
    
    g.add((RECIPE.Spice, RDF.type, OWL.Class))
    g.add((RECIPE.Spice, RDFS.subClassOf, RECIPE.Ingredient))
    g.add((RECIPE.Spice, RDFS.label, Literal("Spice", lang="en")))
    
    g.add((RECIPE.AnimalProduct, RDF.type, OWL.Class))
    g.add((RECIPE.AnimalProduct, RDFS.subClassOf, RECIPE.Ingredient))
    g.add((RECIPE.AnimalProduct, RDFS.label, Literal("Animal Product", lang="en")))
    
    # Cuisine hierarchy
    g.add((RECIPE.AsianCuisine, RDF.type, OWL.Class))
    g.add((RECIPE.AsianCuisine, RDFS.subClassOf, RECIPE.Cuisine))
    
    g.add((RECIPE.EuropeanCuisine, RDF.type, OWL.Class))
    g.add((RECIPE.EuropeanCuisine, RDFS.subClassOf, RECIPE.Cuisine))
    
    g.add((RECIPE.AmericanCuisine, RDF.type, OWL.Class))
    g.add((RECIPE.AmericanCuisine, RDFS.subClassOf, RECIPE.Cuisine))
    
    print("  ✓ Added class hierarchy (subClassOf)")
    
    
    # 3. DISJOINT CLASSES (owl:disjointWith)
   
    
    # Vegan recipes cannot be non-vegan
    g.add((RECIPE.VeganRecipe, OWL.disjointWith, RECIPE.MeatRecipe))
    
    # Define MeatRecipe for disjointness
    g.add((RECIPE.MeatRecipe, RDF.type, OWL.Class))
    g.add((RECIPE.MeatRecipe, RDFS.subClassOf, RECIPE.Recipe))
    g.add((RECIPE.MeatRecipe, RDFS.label, Literal("Meat Recipe", lang="en")))
    
    # Ingredient categories are disjoint
    g.add((RECIPE.Vegetable, OWL.disjointWith, RECIPE.AnimalProduct))
    g.add((RECIPE.Grain, OWL.disjointWith, RECIPE.AnimalProduct))
    
    print("  ✓ Added disjoint classes")
    
   
    # 4. PROPERTY CHARACTERISTICS
   
    
    # hasIngredient is NOT functional (recipes have multiple ingredients)
    # But usesIngredient in IngredientUsage IS functional
    g.add((RECIPE.usesIngredient, RDF.type, OWL.FunctionalProperty))
    
    # Define inverse property: isIngredientOf
    g.add((RECIPE.isIngredientOf, RDF.type, OWL.ObjectProperty))
    g.add((RECIPE.isIngredientOf, OWL.inverseOf, RECIPE.hasIngredient))
    g.add((RECIPE.isIngredientOf, RDFS.domain, RECIPE.Ingredient))
    g.add((RECIPE.isIngredientOf, RDFS.range, RECIPE.Recipe))
    g.add((RECIPE.isIngredientOf, RDFS.label, Literal("is ingredient of", lang="en")))
    
    # Define inverse: isCuisineOf
    g.add((RECIPE.isCuisineOf, RDF.type, OWL.ObjectProperty))
    g.add((RECIPE.isCuisineOf, OWL.inverseOf, RECIPE.hasCuisine))
    
    # hasNutrition is functional (one nutrition info per recipe)
    g.add((RECIPE.hasNutrition, RDF.type, OWL.FunctionalProperty))
    
    # Symmetric property: similarTo (for recipe similarity)
    g.add((RECIPE.similarTo, RDF.type, OWL.ObjectProperty))
    g.add((RECIPE.similarTo, RDF.type, OWL.SymmetricProperty))
    g.add((RECIPE.similarTo, RDFS.domain, RECIPE.Recipe))
    g.add((RECIPE.similarTo, RDFS.range, RECIPE.Recipe))
    g.add((RECIPE.similarTo, RDFS.label, Literal("similar to", lang="en")))
    
    # Transitive property: broaderCuisine
    g.add((RECIPE.broaderCuisine, RDF.type, OWL.ObjectProperty))
    g.add((RECIPE.broaderCuisine, RDF.type, OWL.TransitiveProperty))
    g.add((RECIPE.broaderCuisine, RDFS.domain, RECIPE.Cuisine))
    g.add((RECIPE.broaderCuisine, RDFS.range, RECIPE.Cuisine))
    g.add((RECIPE.broaderCuisine, RDFS.label, Literal("broader cuisine", lang="en")))
    
    print("  ✓ Added property characteristics (functional, inverse, symmetric, transitive)")
    
    
    # 5. OWL RESTRICTIONS (equivalentClass)
    
    # VeganRecipe = Recipe AND hasDiet some {diet_vegan}
    vegan_restriction = BNode()
    g.add((RECIPE.VeganRecipe, OWL.equivalentClass, vegan_restriction))
    g.add((vegan_restriction, RDF.type, OWL.Restriction))
    g.add((vegan_restriction, OWL.onProperty, RECIPE.hasDiet))
    g.add((vegan_restriction, OWL.hasValue, RECIPE.diet_vegan))
    
    # GlutenFreeRecipe = Recipe AND hasDiet some {diet_gluten_free}
    gf_restriction = BNode()
    g.add((RECIPE.GlutenFreeRecipe, OWL.equivalentClass, gf_restriction))
    g.add((gf_restriction, RDF.type, OWL.Restriction))
    g.add((gf_restriction, OWL.onProperty, RECIPE.hasDiet))
    g.add((gf_restriction, OWL.hasValue, RECIPE.diet_gluten_free))
    
    print("  ✓ Added OWL class restrictions (equivalentClass)")
    
    
    # 6. CARDINALITY CONSTRAINTS
   
    
    # Every recipe must have at least 1 ingredient
    min_ing_restriction = BNode()
    g.add((RECIPE.Recipe, RDFS.subClassOf, min_ing_restriction))
    g.add((min_ing_restriction, RDF.type, OWL.Restriction))
    g.add((min_ing_restriction, OWL.onProperty, RECIPE.hasIngredient))
    g.add((min_ing_restriction, OWL.minCardinality, Literal(1, datatype=XSD.nonNegativeInteger)))
    
    # Every recipe must have exactly 1 title
    title_restriction = BNode()
    g.add((RECIPE.Recipe, RDFS.subClassOf, title_restriction))
    g.add((title_restriction, RDF.type, OWL.Restriction))
    g.add((title_restriction, OWL.onProperty, RECIPE.title))
    g.add((title_restriction, OWL.cardinality, Literal(1, datatype=XSD.nonNegativeInteger)))
    
    print("  ✓ Added cardinality constraints")
    
    
    # 7. LINK TO EXTERNAL VOCABULARIES
    
    
    # Link our classes to schema.org
    g.add((RECIPE.Recipe, OWL.equivalentClass, SCHEMA.Recipe))
    g.add((RECIPE.Ingredient, RDFS.subClassOf, SCHEMA.Thing))
    g.add((RECIPE.title, OWL.equivalentProperty, SCHEMA.name))
    g.add((RECIPE.readyInMinutes, OWL.equivalentProperty, SCHEMA.totalTime))
    
    print("  ✓ Added links to schema.org")
    
    print("-" * 50)
    
    return g


def classify_recipes(g):
    """
    Classify existing recipes into subclasses based on their properties.
    This simulates what a reasoner would infer.
    """
    print("\nClassifying recipes into subclasses...")
    
    # Find all recipes
    recipes = list(g.subjects(RDF.type, RECIPE.Recipe))
    
    vegan_count = 0
    gluten_free_count = 0
    quick_count = 0
    low_cal_count = 0
    high_protein_count = 0
    
    for recipe in recipes:
        # Check if vegan
        if (recipe, RECIPE.hasDiet, RECIPE.diet_vegan) in g:
            g.add((recipe, RDF.type, RECIPE.VeganRecipe))
            vegan_count += 1
        
        # Check if gluten-free
        if (recipe, RECIPE.hasDiet, RECIPE.diet_gluten_free) in g:
            g.add((recipe, RDF.type, RECIPE.GlutenFreeRecipe))
            gluten_free_count += 1
        
        # Check if dairy-free
        if (recipe, RECIPE.hasDiet, RECIPE.diet_dairy_free) in g:
            g.add((recipe, RDF.type, RECIPE.DairyFreeRecipe))
        
        # Check if quick (< 30 minutes)
        for time in g.objects(recipe, RECIPE.readyInMinutes):
            if int(time) < 30:
                g.add((recipe, RDF.type, RECIPE.QuickRecipe))
                quick_count += 1
            elif int(time) > 120:
                g.add((recipe, RDF.type, RECIPE.SlowCookerRecipe))
        
        # Check nutrition
        for nutrition in g.objects(recipe, RECIPE.hasNutrition):
            # Low calorie check
            for cal in g.objects(nutrition, RECIPE.calories):
                if float(cal) < 300:
                    g.add((recipe, RDF.type, RECIPE.LowCalorieRecipe))
                    low_cal_count += 1
            
            # High protein check
            for protein in g.objects(nutrition, RECIPE.protein):
                if float(protein) > 20:
                    g.add((recipe, RDF.type, RECIPE.HighProteinRecipe))
                    high_protein_count += 1
    
    print(f"  ✓ Classified {vegan_count} vegan recipes")
    print(f"  ✓ Classified {gluten_free_count} gluten-free recipes")
    print(f"  ✓ Classified {quick_count} quick recipes (<30 min)")
    print(f"  ✓ Classified {low_cal_count} low-calorie recipes (<300 kcal)")
    print(f"  ✓ Classified {high_protein_count} high-protein recipes (>20g)")
    
    return g


def main():
    print("=" * 60)
    print("ADDING RDFS/OWL SCHEMA AXIOMS")
    print("=" * 60)
    
    # Load existing graph
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, "..", "output", "recipes.ttl")
    output_path = os.path.join(script_dir, "..", "output", "recipes_with_ontology.ttl")
    
    print(f"\nLoading existing RDF from: {input_path}")
    g = Graph()
    g.parse(input_path, format="turtle")
    
    original_count = len(g)
    print(f"Original triples: {original_count}")
    
    # Add ontology axioms
    g = add_ontology_axioms(g)
    
    # Classify recipes
    g = classify_recipes(g)
    
    # Bind namespaces for nice output
    g.bind("recipe", RECIPE)
    g.bind("ingredient", INGREDIENT)
    g.bind("cuisine", CUISINE)
    g.bind("schema", SCHEMA)
    g.bind("owl", OWL)
    g.bind("dbpedia", DBPEDIA)
    g.bind("wikidata", WIKIDATA)
    
    # Save enhanced graph
    g.serialize(destination=output_path, format="turtle")
    
    new_count = len(g)
    added = new_count - original_count
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Original triples:  {original_count}")
    print(f"New triples:       {new_count}")
    print(f"Axioms added:      {added}")
    print(f"\n✓ Enhanced ontology saved to: {output_path}")
    
    # Print some statistics
    print("\n" + "=" * 60)
    print("ONTOLOGY STATISTICS")
    print("=" * 60)
    
    classes = set(g.subjects(RDF.type, OWL.Class))
    obj_props = set(g.subjects(RDF.type, OWL.ObjectProperty))
    data_props = set(g.subjects(RDF.type, OWL.DatatypeProperty))
    
    print(f"Classes defined:           {len(classes)}")
    print(f"Object properties:         {len(obj_props)}")
    print(f"Datatype properties:       {len(data_props)}")


if __name__ == "__main__":
    main()
