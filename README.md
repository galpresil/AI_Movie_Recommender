# AI_Movie_Recommender

## Folder Tree Structure:

```text
AI_Movie_Recommender/
|
├── .env
├── AI MOVIE RECOMMENDER.pptx
├── LICENSE
├── README.md
|
├── Code - From Pre-proccesing to Evaluation/
│   ├── 1. project-ai (merge, clean, and EDA).ipynb
│   ├── 2. project-ai (generate movie poster desc).ipynb
│   ├── 3. project-ai (embeddings & vector dataset).ipynb
│   └── 4. project-ai (with rag evaluation).ipynb
|
├── CSV - Generate Movie Poster Descriptions/
│   ├── cleaned_merged_movies (output).csv
│   └── my_data (input).csv
|
├── movie_project/
    ├── app.py
    ├── bm25_model.pkl
    ├── final_merged_movies.csv
    ├── movie_faiss.index
    ├── movie_vectors.npy
    ├── .vscode/
    │      └── settings.json
    │     
    ├── static/
    │      ├── cinema.png
    │      ├── main.js
    │      └── style.css
    │    
    └── templates/
        ├── explore.html
        └── index.html
