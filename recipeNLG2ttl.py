import pandas as pd
import re
import json
from rdflib import Graph, URIRef, Literal, Namespace, RDF, RDFS, XSD, OWL
from rdflib.namespace import FOAF, DCTERMS
from tqdm import tqdm
from datetime import datetime


# ==================== CONFIGURATION ====================

RECIPES_NLG_PATH = 'recipesNLG/all_recipes.csv'
OUTPUT_TTL_PATH = 'recipesNLG/recipesNLG_knowledge_graph.ttl'
CHUNK_SIZE = 10000

MEASUREMENT_UNITS = [
    'cups', 'cup', 'c.', 'c', 
    'tsp', 'teaspoon', 'teaspoons',
    'tbsp', 'tablespoon', 'tablespoons',
    'oz.', 'oz', 'ounce', 'ounces',
    'lb.', 'lb', 'pound', 'pounds',
    'g', 'gr.', 'gram', 'grams',
    'kg', 'kilogram', 'kilograms',
    'ml', 'milliliter', 'milliliters',
    'l', 'liter', 'liters',
    'can', 'cans',
    'pkg', 'package', 'packages',
    'slice', 'slices',
    'pinch', 'dash'
]


# ==================== NAMESPACE DEFINITIONS ====================

# Standard W3C namespaces
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")
OWL = Namespace("http://www.w3.org/2002/07/owl#")

# Schema.org
SCHEMA = Namespace("https://schema.org/")

# Food Ontology - LIRMM
FOOD = Namespace("http://data.lirmm.fr/ontologies/food#")

# Use example.org as base namespace (aligned with MealDB)
BASE = Namespace("http://example.org/")
RECIPE = Namespace("http://example.org/food/recipe/")
INGREDIENT = Namespace("http://example.org/food/ingredient/")

# Additional useful namespaces
FOODON = Namespace("http://purl.obolibrary.org/obo/FOODON_")
UNIT = Namespace("http://qudt.org/vocab/unit/")
DCTERMS = Namespace("http://purl.org/dc/terms/")


# ==================== UTILITY FUNCTIONS ====================

def normalize_ingredient_name(ingredient_text):
    """
    Extract and normalize ingredient name from full ingredient line.
    This helps with linking to MealDB ingredients later.

    Example: "2 cups all-purpose flour" -> "all_purpose_flour"
    """
    # Convert to lowercase
    text = ingredient_text.lower()

    # Remove quantities (numbers, fractions)
    text = re.sub(r'\d+\s*\d*/\d+|\d+\.?\d*', '', text)

    # Remove measurement units
    for unit in MEASUREMENT_UNITS:
        text = re.sub(r'\b' + re.escape(unit) + r's?\b', '', text)

    # Remove common preparation terms
    prep_terms = ['chopped', 'diced', 'minced', 'sliced', 'grated', 'fresh', 
                  'dried', 'frozen', 'canned', 'cooked', 'raw', 'optional',
                  'to taste', 'finely', 'thinly', 'roughly', 'large', 'small',
                  'medium', 'boneless', 'skinless']
    for term in prep_terms:
        text = re.sub(r'\b' + re.escape(term) + r'\b', '', text)

    # Replace spaces with '_' for readable uris
    text = re.sub(r'\s+', ' ', text).strip()  
    text = text.replace(' ', '_')

    # Return empty string if nothing left
    if not text:
        return None

    return text


def parse_ingredient(ingredient_text, recipe_id, position):
    """
    Parse a single ingredient string and return dictionary with extracted info.
    """
    ingredient_text_lower = ingredient_text.lower()

    parsed = {
        'recipe_id': recipe_id,
        'ingredient_text': ingredient_text,
        'position': position,
        'normalized_name': None, # normalize_ingredient_name(ingredient_text),
        'primary_qty': None,
        'secondary_qty': None,
        'primary_unit': None,
        'secondary_unit': None
    }

    # Extract quantities (handles: "2", "1/2", "2 1/2")
    quantity_pattern = r'\d+\s+\d+/\d+|\d+/\d+|\d+\.?\d*'
    quantities = re.findall(quantity_pattern, ingredient_text_lower)

    # Extract units
    found_units = []
    for unit in MEASUREMENT_UNITS:
        if re.search(r'\b' + re.escape(unit) + r's?\b', ingredient_text_lower):
            found_units.append(unit)

    # Assign quantities
    if len(quantities) > 0:
        parsed['primary_qty'] = quantities[0]
        if len(quantities) > 1:
            parsed['secondary_qty'] = ", ".join(quantities[1:])
        # also remove quantities from ingredient text
        for q in quantities:
            ingredient_text_lower.replace(q, '')

    # Assign units
    if len(found_units) > 0:
        parsed['primary_unit'] = found_units[0]
        if len(found_units) > 1:
            parsed['secondary_unit'] = ", ".join(found_units[1:])
        # also remove quantities from ingredient text
        for u in found_units:
            ingredient_text_lower.replace(u, '')

    ingredient_text_lower = ingredient_text_lower.replace('.','').replace('/','').replace('"','').replace('\\','')
    
    parsed['normalized_name'] = normalize_ingredient_name(ingredient_text_lower)

    return parsed


def create_recipe_uri(recipe_id):
    """Generate URI for a recipe."""
    return RECIPE[str(recipe_id)]


def create_ingredient_line_uri(recipe_id, position):
    """Generate URI for an ingredient line (food:IngredientLine)."""
    return URIRef(f"http://example.org/food/ingredientline/{recipe_id}_{position}")


def create_ingredient_uri(normalized_name):
    """
    Generate URI for normalized ingredient (food:Ingredient).
    Uses same pattern as MealDB for consistency.
    """
    if not normalized_name:
        return None
    return INGREDIENT[normalized_name]


# ==================== MAIN PROCESSING ====================

def add_recipe_to_graph(graph, recipe_row):
    """
    Add a recipe and its ingredients to the RDF graph using FOOD ontology.

    Args:
        graph: rdflib.Graph instance
        recipe_row: pandas Series containing recipe data
    """
    recipe_id = recipe_row['recipe_id']
    recipe_uri = create_recipe_uri(recipe_id)

    # Add recipe types - use both FOOD ontology and Schema.org for interoperability
    graph.add((recipe_uri, RDF.type, FOOD.Recipe))
    graph.add((recipe_uri, RDF.type, SCHEMA.Recipe))

    # Add recipe title (FOOD ontology uses schema:name)
    if pd.notna(recipe_row['title']):
        graph.add((recipe_uri, SCHEMA.name, Literal(recipe_row['title'], datatype=XSD.string)))
        graph.add((recipe_uri, RDFS.label, Literal(recipe_row['title'], datatype=XSD.string)))

    # Add recipe source/link
    if pd.notna(recipe_row['link']):
        graph.add((recipe_uri, SCHEMA.url, URIRef(recipe_row['link'])))

    # Add source website
    if pd.notna(recipe_row['source']):
        graph.add((recipe_uri, DCTERMS.source, Literal(recipe_row['source'], datatype=XSD.string)))

    # Parse and add directions
    try:
        directions = json.loads(recipe_row['directions'])
        if directions and isinstance(directions, list):
            # Add as concatenated text (schema:recipeInstructions)
            directions_text = "\n".join([f"{i+1}. {step}" for i, step in enumerate(directions)])
            graph.add((recipe_uri, SCHEMA.recipeInstructions, Literal(directions_text, datatype=XSD.string)))

            # Add structured steps using HowToStep
            for step_num, step_text in enumerate(directions, start=1):
                step_uri = URIRef(f"{recipe_uri}/step/{step_num}")
                graph.add((recipe_uri, SCHEMA.step, step_uri))
                graph.add((step_uri, RDF.type, SCHEMA.HowToStep))
                graph.add((step_uri, SCHEMA.position, Literal(step_num, datatype=XSD.integer)))
                graph.add((step_uri, SCHEMA.text, Literal(step_text, datatype=XSD.string)))
    except (json.JSONDecodeError, TypeError):
        pass  # Skip if directions can't be parsed

    # Parse and add ingredients
    try:
        ingredients = json.loads(recipe_row['ingredients'])
        if ingredients and isinstance(ingredients, list):
            for position, ingredient_text in enumerate(ingredients):
                parsed = parse_ingredient(ingredient_text, recipe_id, position)
                add_ingredient_to_graph(graph, recipe_uri, parsed)
    except (json.JSONDecodeError, TypeError):
        pass  # Skip if ingredients can't be parsed


def add_ingredient_to_graph(graph, recipe_uri, parsed_ingredient):
    """
    Add an ingredient specification to the RDF graph using FOOD ontology.

    Creates TWO entities:
    1. food:IngredientLine - the recipe-specific line with quantity/unit
    2. food:Ingredient - the normalized ingredient entity (for linking)

    Args:
        graph: rdflib.Graph instance
        recipe_uri: URI of the parent recipe
        parsed_ingredient: dict with parsed ingredient data
    """
    ingredient_line_uri = create_ingredient_line_uri(
        parsed_ingredient['recipe_id'],
        parsed_ingredient['position']
    )

    # ===== INGREDIENT LINE (recipe-specific) =====

    # Link recipe to ingredient line
    graph.add((recipe_uri, FOOD.hasIngredient, ingredient_line_uri))
    graph.add((recipe_uri, SCHEMA.recipeIngredient, ingredient_line_uri))

    # Type: This is an ingredient line
    graph.add((ingredient_line_uri, RDF.type, FOOD.IngredientLine))

    # Original ingredient text (full line)
    graph.add((ingredient_line_uri, RDFS.label, Literal(
        parsed_ingredient['ingredient_text'], 
        datatype=XSD.string
    )))

    # FOOD ontology property for original text
    graph.add((ingredient_line_uri, FOOD.text, Literal(
        parsed_ingredient['ingredient_text'], 
        datatype=XSD.string
    )))

    # Position/order in recipe
    graph.add((ingredient_line_uri, FOOD.order, Literal(
        parsed_ingredient['position'], 
        datatype=XSD.integer
    )))

    # Quantity and unit (FOOD ontology properties)
    if parsed_ingredient['primary_qty']:
        graph.add((ingredient_line_uri, FOOD.quantity, Literal(
            parsed_ingredient['primary_qty'], 
            datatype=XSD.string
        )))

    if parsed_ingredient['primary_unit']:
        graph.add((ingredient_line_uri, FOOD.unit, Literal(
            parsed_ingredient['primary_unit'], 
            datatype=XSD.string
        )))

    # For multi-unit ingredients
    if parsed_ingredient['secondary_qty']:
        graph.add((ingredient_line_uri, FOOD.alternativeQuantity, Literal(
            parsed_ingredient['secondary_qty'], 
            datatype=XSD.string
        )))

    if parsed_ingredient['secondary_unit']:
        graph.add((ingredient_line_uri, FOOD.alternativeUnit, Literal(
            parsed_ingredient['secondary_unit'], 
            datatype=XSD.string
        )))

    # ===== NORMALIZED INGREDIENT (for linking to MealDB) =====

    if parsed_ingredient['normalized_name']:
        ingredient_uri = create_ingredient_uri(parsed_ingredient['normalized_name'])

        if ingredient_uri:
            # Link IngredientLine to normalized Ingredient
            # This is the key link for connecting to MealDB later
            graph.add((ingredient_line_uri, FOOD.ingredient, ingredient_uri))

            # Type: food:Ingredient (same as MealDB)
            graph.add((ingredient_uri, RDF.type, FOOD.Ingredient))

            # Add normalized label
            graph.add((ingredient_uri, RDFS.label, Literal(
                parsed_ingredient['normalized_name'], 
                datatype=XSD.string
            )))


def process_chunk_to_rdf(chunk, graph):
    """
    Process a chunk of recipes and add to RDF graph.

    Args:
        chunk: pandas DataFrame with recipe data
        graph: rdflib.Graph instance to add triples to

    Returns:
        int: number of recipes processed
    """
    recipes_processed = 0

    for idx, row in chunk.iterrows():
        try:
            add_recipe_to_graph(graph, row)
            recipes_processed += 1
        except Exception as e:
            print(f"Error processing recipe {row.get('recipe_id', idx)}: {e}")
            continue

    return recipes_processed


def initialize_graph():
    """
    Initialize RDF graph with namespace bindings and ontology imports.

    Returns:
        rdflib.Graph: initialized graph with namespaces
    """
    g = Graph()

    # Bind standard W3C namespaces
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    g.bind("owl", OWL)

    # Bind Schema.org
    g.bind("schema", SCHEMA)

    # Bind FOOD ontology (LIRMM)
    g.bind("food", FOOD)

    # Bind example.org namespaces (aligned with MealDB)
    g.bind("", BASE)  # Default namespace

    # Bind additional ontologies for future entity resolution
    g.bind("foodon", FOODON)
    g.bind("unit", UNIT)
    g.bind("dcterms", DCTERMS)

    # Add ontology metadata
    ontology_uri = BASE["ontology"]
    g.add((ontology_uri, RDF.type, OWL.Ontology))
    g.add((ontology_uri, RDFS.label, Literal("RecipeNLG Knowledge Graph", lang="en")))
    g.add((ontology_uri, RDFS.comment, Literal(
        "Knowledge graph of recipes from RecipeNLG dataset, "
        "modeled using FOOD ontology and Schema.org vocabulary. "
        "Uses example.org namespace for compatibility with MealDB.",
        lang="en"
    )))
    g.add((ontology_uri, OWL.imports, URIRef("http://data.lirmm.fr/ontologies/food")))
    g.add((ontology_uri, OWL.imports, URIRef("https://schema.org/")))
    g.add((ontology_uri, DCTERMS.created, Literal(datetime.now().isoformat(), datatype=XSD.dateTime)))

    return g


def main():
    """
    Main processing function: Read RecipeNLG CSV and convert to RDF Knowledge Graph.
    """
    print("=" * 70)
    print("RecipeNLG to RDF Knowledge Graph Converter")
    print("Using FOOD Ontology (LIRMM) + Schema.org")
    print("Aligned with MealDB using example.org namespace")
    print("=" * 70)
    print(f"Input:  {RECIPES_NLG_PATH}")
    print(f"Output: {OUTPUT_TTL_PATH}")
    print(f"Chunk size: {CHUNK_SIZE:,} recipes")
    print()

    # Initialize RDF graph with ontology imports
    print("Initializing RDF graph with ontologies...")
    print("  - RDFS (http://www.w3.org/2000/01/rdf-schema#)")
    print("  - XSD (http://www.w3.org/2001/XMLSchema#)")
    print("  - Schema.org (https://schema.org/)")
    print("  - FOOD Ontology (http://data.lirmm.fr/ontologies/food#)")
    print("  - Base: http://example.org/ (aligned with MealDB)")
    print()

    g = initialize_graph()

    # Count total rows for progress tracking
    try:
        total_recipes = sum(1 for _ in open(RECIPES_NLG_PATH)) - 1
        print(f"Total recipes to process: {total_recipes:,}\n")
    except:
        total_recipes = None
        print("Could not count total recipes (file might be large)\n")

    # Process CSV in chunks
    total_processed = 0
    chunk_num = 0
    start_time = datetime.now()

    chunk_iterator = pd.read_csv(
        RECIPES_NLG_PATH,
        chunksize=CHUNK_SIZE,
        dtype={'ingredients': str, 'directions': str}
    )

    print("Processing recipes and building knowledge graph...")
    with tqdm(total=total_recipes, desc="Recipes processed", unit="recipes") as pbar:
        for chunk in chunk_iterator:
            chunk_num += 1

            # Rename index column if needed
            if 'Unnamed: 0' in chunk.columns:
                chunk.rename(columns={'Unnamed: 0': 'recipe_id'}, inplace=True)

            # Ensure recipe_id exists
            if 'recipe_id' not in chunk.columns:
                chunk['recipe_id'] = chunk.index

            # Process this chunk and add to graph
            processed = process_chunk_to_rdf(chunk, g)
            total_processed += processed
            pbar.update(processed)

            # Log progress every 10 chunks
            if chunk_num % 10 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = total_processed / elapsed if elapsed > 0 else 0
                triples = len(g)
                print(f"\n  Chunk {chunk_num}: {total_processed:,} recipes → {triples:,} triples "
                      f"({rate:.1f} recipes/sec)")
            break

    # Final statistics
    elapsed = (datetime.now() - start_time).total_seconds()
    triples_count = len(g)

    print(f"\n{'=' * 70}")
    print(f"Processing complete!")
    print(f"  Recipes processed: {total_processed:,}")
    print(f"  Total RDF triples: {triples_count:,}")
    print(f"  Processing time: {elapsed:.1f} seconds ({total_processed/elapsed:.1f} recipes/sec)")
    print(f"{'=' * 70}\n")

    # Serialize to Turtle format
    print(f"Serializing knowledge graph to Turtle format...")
    print(f"Output file: {OUTPUT_TTL_PATH}")

    try:
        g.serialize(destination=OUTPUT_TTL_PATH, format='turtle')
        print(f"✓ Successfully exported {triples_count:,} triples to {OUTPUT_TTL_PATH}")

        # Show file size
        import os
        file_size = os.path.getsize(OUTPUT_TTL_PATH) / (1024 * 1024)  # MB
        print(f"✓ File size: {file_size:.2f} MB")

    except Exception as e:
        print(f"✗ Error during serialization: {e}")
        return

    print(f"\n{'=' * 70}")
    print("Knowledge graph creation complete!")
    print(f"{'=' * 70}")

    # Print ontology summary
    print("\nOntology Structure:")
    print("  Classes Used:")
    print("    - food:Recipe (recipe entities)")
    print("    - food:IngredientLine (recipe-specific ingredient lines)")
    print("    - food:Ingredient (normalized ingredients - for linking)")
    print("    - schema:Recipe (Schema.org compatibility)")
    print("    - schema:HowToStep (cooking instructions)")
    print()

    print("  Key Properties:")
    print("    - food:hasIngredient (recipe → ingredient line)")
    print("    - food:ingredient (ingredient line → normalized ingredient)")
    print("    - food:text (ingredient original text)")
    print("    - food:quantity, food:unit (measurements)")
    print("    - food:order (ingredient position)")
    print("    - schema:name (recipe title)")
    print("    - schema:recipeInstructions (cooking steps)")
    print()

    print("  Namespace Alignment:")
    print("    - Recipes: http://example.org/food/recipe/{id}")
    print("    - Ingredients: http://example.org/food/ingredient/{normalized_name}")
    print("    - IngredientLines: http://example.org/food/ingredientline/{recipe_id}_{position}")
    print("    ✓ Compatible with MealDB namespace structure")
    print()

    # Print sample triples for verification
    print("Sample triples from the graph:")
    print("-" * 70)
    for i, (s, p, o) in enumerate(g):
        if i >= 15:  # Show first 15 triples
            break
        # Format output nicely
        s_str = str(s).replace('http://example.org/', '...')
        p_str = str(p).split('#')[-1].split('/')[-1]
        o_str = str(o)[:50] + '...' if len(str(o)) > 50 else str(o)
        print(f"  {s_str}")
        print(f"    {p_str}: {o_str}")
    print("-" * 70)

    print("\n✓ Ready for linking with MealDB knowledge graph!")


if __name__ == "__main__":
    main()