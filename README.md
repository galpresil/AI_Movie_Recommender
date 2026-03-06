# AI Movie Recommender

This project is an AI-powered movie recommendation platform designed to decode natural language user requests and provide highly relevant, personalized film suggestions. By combining semantic search with lexical precision, the system ensures that users find the exact movie they are looking for.

## Project Overview
- Goal: To develop a recommendation system based on advanced AI techniques that understands user intent.
- Core Question: Can AI effectively decode user requests to locate and recommend the most suitable movie? 

## Technical Architecture
The system utilizes a Retrieval-Augmented Generation (RAG) workflow to provide conversational and accurate answers.
- Backend: Python and Flask.
- Frontend: HTML5, CSS3, and JavaScript.
- Hybrid Search Engine:
    - FAISS (Vector Search) for semantic meaning.
    - BM25 (Keyword Filtering) for exact term matching.
- AI Models:
    - Trinity Large Preview (Arcee AI): Used for query optimization (rewriting) and generating the final conversational response.
    - MoonDream2 (Hugging Face): A Vision-Language Model used to describe movie posters for better text enrichment.

## Key Functions
- Rewriting Function: Acts as a "smart translator" that splits a user's natural language request into positive terms (what they want) and negative terms (what to avoid).
- Semantic Pipeline: Converts movie data into numerical vectors using Sentence Transformers to find "nearest neighbor" matches.
- Reranking: Scores and re-orders results to ensure the most relevant movies are presented at the top.

## Installation
Install the required libraries via pip: <br>
pip install flask pandas numpy faiss-cpu sentence-transformers openai rank_bm25 tqdm

## Folder Tree Structure
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
└── movie_project/
    │
    ├── app.py
    ├── bm25_model.pkl
    ├── final_merged_movies.csv
    ├── movie_faiss.index
    ├── movie_vectors.npy
    │
    ├── .vscode/
    │   └── settings.json
    │     
    ├── static/
    │   ├── cinema.png
    │   ├── main.js
    │   └── style.css
    │    
    └── templates/
        ├── explore.html
        └── index.html
