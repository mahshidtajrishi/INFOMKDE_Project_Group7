# app.py
import sys

from fetch_data import fetch_useful_dataset
from convert_to_rdf import convert
from load_to_db import load_graph_to_oxigraph, test_query
from query_db import recommend_recipes
from visualize_graph import visualize_rdf_graph

def print_usage():
    print("Recipe Knowledge Graph System\n")
    print("Commands:")
    print("  python app.py fetch         # Download data (cached)")
    print("  python app.py convert       # Create RDF file")
    print("  python app.py load          # Load into Oxigraph DB")
    print("  python app.py all           # Full pipeline + test")
    print("  python app.py test          # Test DB")
    print("  python app.py recommend     # Interactive: avoid or must-have ingredients")
    print("  python app.py visualize     # Show graph visualization")
    print("  python app.py help          # Show this help")

def main():
    if len(sys.argv) < 2:
        print_usage()
        return

    cmd = sys.argv[1].lower()

    if cmd in ("fetch", "all"):
        print("\n=== Fetching data ===")
        fetch_useful_dataset()

    if cmd in ("convert", "all"):
        print("\n=== Converting to RDF ===")
        convert()

    if cmd in ("load", "all"):
        print("\n=== Loading into database ===")
        if load_graph_to_oxigraph():
            print("\nRunning test query...")
            test_query()

    if cmd == "test":
        print("\n=== Testing database ===")
        test_query()

# app.py (snippet for recommend command)
    if cmd == "recommend":
        print("\n🍴 Advanced Recipe Recommender 🍴\n")

        avoid_input = input("Ingredients to AVOID (comma-separated, e.g., nuts, egg): ").strip()
        avoid = [i.strip() for i in avoid_input.split(',') if i.strip()]

        must_input = input("Ingredients you MUST HAVE (comma-separated, e.g., salmon): ").strip()
        must_have = [i.strip() for i in must_input.split(',') if i.strip()]

        dietary_input = input("Dietary preferences (e.g., Vegan, Gluten-Free): ").strip()
        dietary = [i.strip() for i in dietary_input.split(',') if i.strip()]

        max_cal_input = input("Maximum calories (or press Enter to skip): ").strip()
        max_cal = int(max_cal_input) if max_cal_input.isdigit() else None

        min_prot_input = input("Minimum protein in grams (or press Enter to skip): ").strip()
        min_prot = int(min_prot_input) if min_prot_input.isdigit() else None

        pantry_input = input("Your pantry ingredients (comma-separated, optional): ").strip()
        pantry = [i.strip() for i in pantry_input.split(',') if i.strip()]

        print("\nSearching for recipes...\n")
        recommend_recipes(
            avoid=avoid,
            must_have=must_have,
            dietary=dietary,
            max_calories=max_cal,
            min_protein=min_prot,
            pantry=pantry,
            limit=None  # Changed to None for dynamic limit
        )

    if cmd == "visualize":
        print("\n=== Visualizing knowledge graph ===")
        visualize_rdf_graph(limit_nodes=80)

    if cmd in ("help", "-h", "--help"):
        print_usage()

if __name__ == "__main__":
    main()