import os
import sys
import subprocess
import time


def run_script(script_name, description):
    """Run a Python script and handle errors."""
    print("\n" + "=" * 70)
    print(f"STEP: {description}")
    print("=" * 70)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, script_name)
    
    if not os.path.exists(script_path):
        print(f"⚠️  Script not found: {script_path}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=script_dir,
            check=True
        )
        print(f"✓ {description} - COMPLETE")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running {script_name}: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def main():
   
    
    print("\n" + "-" * 70)
    input("Press ENTER to start the pipeline...")
    
    start_time = time.time()
    
    # Step 1: Fetch more recipes
    success = run_script("convert_to_rdf.py", "Converting recipes to RDF")
    if not success:
        print("\n RDF conversion failed. Check if recipes.json exists in data/")
    
    
    time.sleep(1)
    success = run_script("add_owl_axioms.py", "Adding OWL axioms and class hierarchy")
    
    time.sleep(1)
    success = run_script("link_to_dbpedia.py", "Linking to DBpedia and Wikidata")
    
    #  Integrate USDA
    time.sleep(1)
    print("\n" + "=" * 70)
    print("STEP: Integrating USDA nutrition data")
    print("=" * 70)
    print("⚠️  This step requires USDA API key in .env file")
    print("   If you don't have it, this step will be skipped.")
    run_script("integrate_usda.py", "USDA Integration")
    
    # Train embeddings
    time.sleep(1)
    print("\n" + "=" * 70)
    print("STEP: Training graph embeddings")
    print("=" * 70)
    print("⚠️  This requires PyKEEN and PyTorch installed")
    try:
        run_script("graph_embeddings.py", "Graph Embeddings")
    except:
        print("   Skipping embeddings (packages not installed)")
    
    # Calculate elapsed time
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE!")
    print("=" * 70)
    print(f"\nTotal time: {minutes}m {seconds}s")
    
    # Show output files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "..", "output")
    
    print("\nOutput files created:")
    if os.path.exists(output_dir):
        for f in sorted(os.listdir(output_dir)):
            filepath = os.path.join(output_dir, f)
            size = os.path.getsize(filepath)
            print(f"  ✓ {f} ({size:,} bytes)")
    
    # Ask about web interface
    print("\n" + "=" * 70)
    print("READY TO LAUNCH WEB INTERFACE?")
    print("=" * 70)
    
    response = input("\nStart the web interface now? (y/n): ").strip().lower()
    
    if response == 'y':
        print("\n🚀 Starting web server...")
       
        script_path = os.path.join(script_dir, "web_interface.py")
        subprocess.run([sys.executable, script_path], cwd=script_dir)
    else:
        print("\nTo start the web interface later, run:")
        print("  python scripts/web_interface.py")


if __name__ == "__main__":
    main()