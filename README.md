# INFOMKDE_Project_Group7


## API Documentation

### Initialize FastAPI Backend & Fuseki Graph Database

1. After you have installed Docker on your machine, in the project's root directory run:
```bash
docker compose up -d 
```

2. On your browser open `http://localhost:3030` which is where the Fuseki service is hosted.

3. Go to manage tab → new dataset → add `recipes` as dataset name → select `Persistent (TDB2) – dataset will persist across Fuseki restarts` as dataset type → click create dataset

4. Go to datasets tab → click `add data` for the `recipes` → click select files → upload the `recipe_recommendation_with_axioms_v4.ttl` file → click `upload now`

5. On a HTTP request client or your browser try `localhost:8001/docs` to see endpoint information

### API Routes

- `localhost:8001/recipes` returns the first 50 recipes (due to memory constraints) in the graph along with their URIs, ingredients and instructions. Response format:

```json
[
    {
        "recipeURI": "http://example.org/food/recipe/0",
        "name": "No-Bake Nut Cookies",
        "ingredients": [
            "vanilla",
            "bite_size_shredded_rice_biscuits",
            "firmly_packed_brown_sugar",
            "butter_or_margarine",
            "evaporated_milk",
            "broken_nuts_(pecans)"
        ],
        "instructions": [
            "1. In a heavy 2-quart saucepan, mix brown sugar, nuts, evaporated milk and butter or margarine.",
            "2. Stir over medium heat until mixture bubbles all over top.",
            "3. Boil and stir 5 minutes more. Take off heat.",
            "4. Stir in vanilla and cereal; mix well.",
            "5. Using 2 teaspoons, drop and shape into 30 clusters on wax paper.",
            "6. Let stand until firm, about 30 minutes."
        ]
    }
]
``` 

---

## HTML Web Interface

**URL:** http://localhost:8000

**Run with:** `python scripts/web_interface.py`

After starting Docker services with `docker compose up -d`, navigate to the scripts folder and run the web interface. On Windows, open PowerShell, activate the virtual environment using `.\.venv\Scripts\Activate.ps1`, then change to the scripts directory with `cd scripts` and start the application with `python web_interface.py`. On Linux or Mac, use `source .venv/bin/activate` instead to activate the virtual environment. Once the server starts, you should see a message indicating that Uvicorn is running on http://127.0.0.1:8000. Open your browser and visit http://localhost:8000 to access the application.
