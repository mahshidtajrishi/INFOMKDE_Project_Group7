# INFOMKDE_Project_Group7


## API Documentation
### Initialize Fast API backend & Fuseki Graph Database
1. After you have installed docker on your machine in the project's root directory run:
```bash
$ docker compose up -d 
```
2. On your browser open `http://localhost:3030` which is where the Fuseki service is hosted.
3. Go to manage tab > new dataset > add `recipe-graph` as dataset name > select `Persistent (TDB2) – dataset will persist across Fuseki restarts` as dataset type > click create dataset
4. Go to datasets tab > click `add data` for the `recipe-graph` > click select files > upload the recipes ttl file > click `upload now`
5. On a HTTP request client or your browser try `localhost:8000/docs` to see endpoint information

### API Routes
- `localhost:8000/recipes` returns the first 50 recipes (due to memory constraints) in the graph along with their URIs, ingredients and instructions. Response format :
```json
[
    {
        "recipeURI": "http://example.org/food/recipe/0",
        "name": "No-Bake Nut Cookies",
        "ingredients": [
            " vanilla",
            "bite_size_shredded_rice_biscuits",
            " firmly_packed_brown_sugar",
            " butter_or_margarine",
            " evaporated_milk",
            " broken_nuts_(pecans)"
        ],
        "instructions": [
            "1. In a heavy 2-quart saucepan, mix brown sugar, nuts, evaporated milk and butter or margarine.",
            "2. Stir over medium heat until mixture bubbles all over top.",
            "3. Boil and stir 5 minutes more. Take off heat.",
            "4. Stir in vanilla and cereal; mix well.",
            "5. Using 2 teaspoons, drop and shape into 30 clusters on wax paper.",
            "6. Let stand until firm, about 30 minutes."
        ]
    },
    ...
]
``` 