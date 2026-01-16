# query_db.py - FIXED SUBSTITUTIONS
from pyoxigraph import Store
from pathlib import Path

DB_PATH = Path("oxigraph_db")

def run_query(sparql):
    store = Store(path=str(DB_PATH))
    return list(store.query(sparql))

def recommend_recipes(avoid: list = None, must_have: list = None, dietary: list = None, 
                      max_calories: int = None, min_protein: int = None, pantry: list = None, limit: int = None):
    avoid = avoid or []
    must_have = must_have or []
    dietary = dietary or []
    pantry = pantry or []

    # Build FILTER conditions
    avoid_conditions = ""
    for ing in avoid:
        avoid_conditions += f'FILTER NOT EXISTS {{ ?recipe schema:recipeIngredient ?ing_avoid . FILTER(CONTAINS(LCASE(?ing_avoid), "{ing.lower()}")) }} \n'

    must_have_conditions = ""
    for idx, ing in enumerate(must_have):
        var_name = f"ing_must_{idx}"
        must_have_conditions += f'?recipe schema:recipeIngredient ?{var_name} . FILTER(CONTAINS(LCASE(?{var_name}), "{ing.lower()}")) \n'

    dietary_conditions = ""
    for diet in dietary:
        dietary_conditions += f'?recipe schema:recipeCategory "{diet}" . \n'

    calorie_filter = f'FILTER (?calories <= {max_calories}) \n' if max_calories else ''
    protein_filter = f'FILTER (?protein >= {min_protein}) \n' if min_protein else ''

    pantry_condition = ""
    pantry_select = ""
    pantry_group = ""
    pantry_order = ""
    if pantry:
        pantry_filters = " || ".join([f'CONTAINS(LCASE(?ing_all), "{p.lower()}")' for p in pantry])
        pantry_condition = f"""
        OPTIONAL {{
            SELECT ?recipe (COUNT(DISTINCT ?ing_all) AS ?pantry_matches) WHERE {{ 
                ?recipe schema:recipeIngredient ?ing_all . 
                FILTER({pantry_filters})
            }} GROUP BY ?recipe 
        }}
        """
        pantry_select = "?pantry_matches "
        pantry_group = "?pantry_matches "
        pantry_order = "DESC(?pantry_matches) "

    base_where = f"""
        ?recipe a schema:Recipe ;
                schema:name ?name ;
                schema:recipeInstructions ?instructions ;
                schema:nutrition ?nutrition .
        ?nutrition schema:calories ?calories ;
                   schema:proteinContent ?protein ;
                   schema:fatContent ?fat ;
                   schema:carbohydrateContent ?carbs ;
                   schema:fiberContent ?fiber ;
                   schema:sugarContent ?sugar .
        OPTIONAL {{ ?recipe schema:recipeCategory ?category . }}
        OPTIONAL {{ ?recipe schema:recipeCuisine ?cuisine . }}
        OPTIONAL {{ ?recipe schema:recipeYield ?servings . }}
        {dietary_conditions}
        {must_have_conditions}
        {avoid_conditions}
        {calorie_filter}
        {protein_filter}
        {pantry_condition}
    """

    if limit is None:
        count_sparql = f"""
        PREFIX schema: <https://schema.org/>
        SELECT (COUNT(DISTINCT ?recipe) AS ?count) WHERE {{
            {base_where}
        }}
        """
        print("\n--- Executing Count SPARQL Query ---")
        print(count_sparql)
        print("--- End Count Query ---\n")

        try:
            count_results = run_query(count_sparql)
            total_count = int(count_results[0]['count'].value) if count_results else 0
            limit = total_count
        except Exception as e:
            print(f"Error executing count query: {e}")
            return

        print(f"Found {limit} unique recipe(s) matching criteria.\n")

    sparql = f"""
    PREFIX schema: <https://schema.org/>
    SELECT DISTINCT ?recipe ?name ?instructions ?calories ?protein ?fat ?carbs ?fiber ?sugar ?servings
           (GROUP_CONCAT(DISTINCT ?category; SEPARATOR=", ") AS ?categories) 
           (GROUP_CONCAT(DISTINCT ?cuisine; SEPARATOR=", ") AS ?cuisines) {pantry_select}WHERE {{
        {base_where}
    }} GROUP BY ?recipe ?name ?instructions ?calories ?protein ?fat ?carbs ?fiber ?sugar ?servings {pantry_group} 
      ORDER BY {pantry_order} DESC(?protein) ASC(?calories) LIMIT {limit}
    """

    print("\n--- Executing SPARQL Query ---")
    print(sparql)
    print("--- End Query ---\n")

    try:
        results = run_query(sparql)
    except Exception as e:
        print(f"Error executing query: {e}")
        return

    if not results:
        print("No recipes found matching your criteria.")
        print("\nTips:")
        print("  - Try removing some filters")
        print("  - Check if dietary tags exist (try without 'Gluten-Free' or 'Vegan')")
        print("  - Avoid filters might be too strict")
        return

    print(f"Found {len(results)} recipe(s):\n")
    
    for idx, row in enumerate(results, 1):
        name = row['name'].value
        calories = int(float(row['calories'].value)) if row['calories'] else 0
        protein = float(row['protein'].value) if row['protein'] else 0
        fat = float(row['fat'].value) if row['fat'] else 0
        carbs = float(row['carbs'].value) if row['carbs'] else 0
        fiber = float(row['fiber'].value) if row['fiber'] else 0
        sugar = float(row['sugar'].value) if row['sugar'] else 0
        categories = row['categories'].value if 'categories' in row else "N/A"
        cuisines = row['cuisines'].value if 'cuisines' in row else "N/A"
        servings = int(row['servings'].value) if 'servings' in row and row['servings'] and row['servings'].value else 2
        instructions = row['instructions'].value[:200] + "..." if len(row['instructions'].value) > 200 else row['instructions'].value
        
        print(f"{idx}. {name}")
        print(f"   Servings: {servings}")
        print(f"   Categories: {categories} | Cuisines: {cuisines}")
        print(f"   Nutrition (per serving): {calories} kcal | Protein {protein:.1f}g | Fat {fat:.1f}g | Carbs {carbs:.1f}g | Fiber {fiber:.1f}g | Sugar {sugar:.1f}g")
        print(f"   Instructions: {instructions}")
        print()

    # FIXED: Simpler substitution query that actually works
    if avoid:
        print("\n Suggested substitutions for avoided ingredients:")
        
        # For each avoided ingredient, suggest common protein alternatives
        substitution_map = {
            'egg': ['chicken', 'tofu', 'cheese', 'yogurt', 'beans'],
            'chicken': ['turkey', 'tofu', 'pork', 'beef'],
            'beef': ['pork', 'turkey', 'chicken', 'tofu'],
            'pork': ['chicken', 'turkey', 'beef', 'tofu'],
            'fish': ['chicken', 'tofu', 'shrimp', 'beans'],
            'salmon': ['tuna', 'cod', 'chicken', 'tofu'],
            'milk': ['almond milk', 'soy milk', 'coconut milk', 'oat milk'],
            'cheese': ['nutritional yeast', 'tofu', 'cashew cheese'],
            'butter': ['olive oil', 'coconut oil', 'margarine'],
            'nuts': ['seeds', 'oats', 'coconut'],
        }
        
        for ing in avoid:
            ing_lower = ing.lower()
            
            # Check if we have predefined substitutions
            if ing_lower in substitution_map:
                print(f"   {ing.capitalize()}: {', '.join(substitution_map[ing_lower])}")
            else:
                # Try to find actual usage in the database
                sub_sparql = f"""
                PREFIX schema: <https://schema.org/>
                SELECT (COUNT(?recipe) as ?count) WHERE {{
                    ?recipe schema:recipeIngredient ?ingredient .
                    FILTER(
                        CONTAINS(LCASE(?ingredient), "chicken") ||
                        CONTAINS(LCASE(?ingredient), "tofu") ||
                        CONTAINS(LCASE(?ingredient), "turkey")
                    )
                }}
                """
                
                try:
                    results = run_query(sub_sparql)
                    if results and int(results[0]['count'].value) > 0:
                        print(f"   {ing.capitalize()}: chicken, tofu, turkey (found in {results[0]['count'].value} recipes)")
                    else:
                        print(f"   {ing.capitalize()}: Try similar proteins or omit")
                except:
                    print(f"   {ing.capitalize()}: Try similar proteins (chicken, tofu, beans) or omit")
        print()