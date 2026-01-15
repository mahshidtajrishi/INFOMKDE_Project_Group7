@"
# Recipe Knowledge Graph
## Project Overview

This project creates a unified knowledge graph combining recipe data from multiple sources:
- **10,211 recipes** from MealDB, RecipesNLG, and Spoonacular
- **16,196 ingredients** with semantic relationships
- **55 YouTube video tutorials**
- **10,057 recipes with cooking instructions**

### External Knowledge Base Links
- **DBpedia**: 268 links
- **Wikidata**: 154 links  
- **FoodOn**: 291 links
- **USDA Nutrition**: 124 ingredients

## Technology Stack

- **RDF/OWL** - Knowledge representation
- **SPARQL** - Query language
- **Python/rdflib** - Data processing
- **FastAPI** - REST API
- **Protégé** - Ontology editing

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| GET /api/stats | Knowledge graph statistics |
| GET /api/recipes | All recipes (paginated) |
| GET /api/recipes/{id} | Recipe details |
| GET /api/search | Search with filters |
| GET /api/videos | Recipes with YouTube videos |
| GET /api/ingredients | All ingredients |
| GET /api/external-links | External KB links |

## Running the Project
```bash
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Run API server
cd scripts
python api_server.py
# Open http://localhost:8001/docs

# Run web interface  
python web_interface.py
# Open http://localhost:8000
```

## Vocabularies Used

- `food:` - http://data.lirmm.fr/ontologies/food#
- `schema:` - https://schema.org/



