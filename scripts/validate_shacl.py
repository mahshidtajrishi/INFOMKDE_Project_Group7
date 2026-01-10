import os
from rdflib import Graph
from pyshacl import validate

# File paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

# Input files
SHAPES_FILE = os.path.join(SCRIPT_DIR, "recipe_shapes.ttl")
DATA_FILE = os.path.join(PROJECT_DIR, "output", "recipes_with_foodon.ttl")

# Alternative data files (in order of preference)
ALTERNATIVE_DATA_FILES = [
    os.path.join(PROJECT_DIR, "output", "recipes_with_foodon.ttl"),
    os.path.join(PROJECT_DIR, "output", "recipes_with_usda.ttl"),
    os.path.join(PROJECT_DIR, "output", "recipes_integrated.ttl"),
    os.path.join(PROJECT_DIR, "output", "recipes_with_ontology.ttl"),
    os.path.join(PROJECT_DIR, "output", "recipes.ttl"),
]


def find_data_file():
    """Find the first available data file."""
    for file_path in ALTERNATIVE_DATA_FILES:
        if os.path.exists(file_path):
            return file_path
    return None


def run_validation():
    """Run SHACL validation on the knowledge graph."""
    
    print("=" * 70)
    print("SHACL VALIDATION FOR RECIPE KNOWLEDGE GRAPH")
    print("=" * 70)
    
    # Find data file
    data_file = find_data_file()
    if not data_file:
        print("✗ Error: No RDF data file found!")
        print("  Please run the pipeline scripts first to generate data.")
        return False
    
    print(f"\nData file: {data_file}")
    print(f"Shapes file: {SHAPES_FILE}")
    
    # Check shapes file exists
    if not os.path.exists(SHAPES_FILE):
        print(f"✗ Error: Shapes file not found: {SHAPES_FILE}")
        return False
    
    # Load the data graph
    print("\n" + "-" * 70)
    print("Loading RDF data...")
    data_graph = Graph()
    data_graph.parse(data_file, format="turtle")
    print(f"✓ Loaded {len(data_graph)} triples")
    
    # Load the shapes graph
    print("\nLoading SHACL shapes...")
    shapes_graph = Graph()
    shapes_graph.parse(SHAPES_FILE, format="turtle")
    print(f"✓ Loaded SHACL shapes")
    
    # Run validation
    print("\n" + "-" * 70)
    print("Running SHACL validation...")
    print("This may take a moment...")
    
    conforms, results_graph, results_text = validate(
        data_graph,
        shacl_graph=shapes_graph,
        inference='rdfs',           # Use RDFS inference
        abort_on_first=False,       # Check all violations
        meta_shacl=False,
        advanced=True,
        js=False,
        debug=False
    )
    
    # Print results
    print("\n" + "=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)
    
    if conforms:
        print("\n✅ SUCCESS! Data conforms to all SHACL shapes.")
        print("\nYour knowledge graph passes all validation rules:")
        print("  • All recipes have titles and ingredients")
        print("  • All nutrition values are valid numbers")
        print("  • All ingredients have labels")
        print("  • All data types are correct")
    else:
        print("\n⚠️  VALIDATION FOUND ISSUES")
        print("\nDetails:")
        print(results_text)
    
    # Count violations by severity
    violation_query = """
    PREFIX sh: <http://www.w3.org/ns/shacl#>
    
    SELECT ?severity (COUNT(?result) as ?num)
    WHERE {
        ?result a sh:ValidationResult .
        ?result sh:resultSeverity ?severity .
    }
    GROUP BY ?severity
    """
    
    print("\n" + "-" * 70)
    print("SUMMARY BY SEVERITY")
    print("-" * 70)
    
    severity_counts = {}
    for row in results_graph.query(violation_query):
        severity = str(row.severity).split("#")[-1]
        count = int(row.num)
        severity_counts[severity] = count
        
        if severity == "Violation":
            icon = "❌"
        elif severity == "Warning":
            icon = "⚠️ "
        else:
            icon = "ℹ️ "
        
        print(f"  {icon} {severity}: {count}")
    
    if not severity_counts:
        print("  ✅ No violations found!")
    
    # Show sample violations (if any)
    if not conforms:
        sample_query = """
        PREFIX sh: <http://www.w3.org/ns/shacl#>
        
        SELECT ?focus ?path ?message ?severity
        WHERE {
            ?result a sh:ValidationResult .
            ?result sh:focusNode ?focus .
            ?result sh:resultPath ?path .
            ?result sh:resultMessage ?message .
            ?result sh:resultSeverity ?severity .
        }
        LIMIT 10
        """
        
        print("\n" + "-" * 70)
        print("SAMPLE ISSUES (first 10)")
        print("-" * 70)
        
        for i, row in enumerate(results_graph.query(sample_query), 1):
            focus = str(row.focus).split("/")[-1]
            path = str(row.path).split("/")[-1] if row.path else "N/A"
            severity = str(row.severity).split("#")[-1]
            print(f"\n{i}. [{severity}] {focus}")
            print(f"   Path: {path}")
            print(f"   Message: {row.message}")
    
    # Statistics about what was validated
    print("\n" + "-" * 70)
    print("VALIDATION COVERAGE")
    print("-" * 70)
    
    stats_queries = {
        "Recipes": "SELECT (COUNT(?r) as ?c) WHERE { ?r a <http://example.org/recipe/Recipe> }",
        "Ingredients": "SELECT (COUNT(?i) as ?c) WHERE { ?i a <http://example.org/recipe/Ingredient> }",
        "Nutrition records": "SELECT (COUNT(?n) as ?c) WHERE { ?n a <http://example.org/recipe/Nutrition> }",
        "Diets": "SELECT (COUNT(?d) as ?c) WHERE { ?d a <http://example.org/recipe/Diet> }",
        "Cuisines": "SELECT (COUNT(?c) as ?c) WHERE { ?c a <http://example.org/recipe/Cuisine> }",
    }
    
    for name, query in stats_queries.items():
        for row in data_graph.query(query):
            print(f"  {name}: {int(row.c)} validated")
    
    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)
    
    
    print("-" * 70)
    if conforms:
        print("Data conforms to SHACL shapes: YES")
    else:
        violations = severity_counts.get("Violation", 0)
        warnings = severity_counts.get("Warning", 0)
    
    return conforms


if __name__ == "__main__":
   
    try:
        import pyshacl
    except ImportError:
        print("Installing pyshacl...")
        import subprocess
        subprocess.run(["pip", "install", "pyshacl", "--break-system-packages"])
        import pyshacl
    
    run_validation()