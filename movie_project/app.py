#------------------------------------------------------------------------
# Import
#------------------------------------------------------------------------
# Standard Library
import os
import re
import json
import pickle

# Data Science & Machine Learning
import pandas as pd
import numpy as np
import re
import faiss
import pickle
import json
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder
from tqdm import tqdm

# Web Framework
from flask import Flask, render_template, request, jsonify
from sentence_transformers import SentenceTransformer

# AI Clients
from openai import OpenAI
from rank_bm25 import BM25Okapi
from tqdm import tqdm
from sentence_transformers import CrossEncoder
from dotenv import load_dotenv

app = Flask(__name__)

#------------------------------------------------------------------------
# Load the data
#------------------------------------------------------------------------
movies = pd.read_csv('final_merged_movies.csv')
print(movies.shape)

# save genres
movies['genres'] = movies['search_text'].str.extract(r'Genres: (.*?);')
movies['genres'] = movies['genres'].fillna('')

#------------------------------------------------------------------------
# Configuration (OpenRouter)
#------------------------------------------------------------------------

# This loads the variables from the .env file
load_dotenv()

# Setup client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

#------------------------------------------------------------------------
# Embeddings & vector dataset
#------------------------------------------------------------------------
embedder = SentenceTransformer('all-mpnet-base-v2')
movie_vectors = np.load('movie_vectors.npy')

# FAISS and BM25
FAISS_PATH = "movie_faiss.index"
BM25_PATH = "bm25_model.pkl"

if os.path.exists(FAISS_PATH) and os.path.exists(BM25_PATH):
    print("--- Loading existing indexes from disk ---")
    index = faiss.read_index(FAISS_PATH)
    with open(BM25_PATH, 'rb') as f:
        bm25 = pickle.load(f)
else:
    print("--- Creating new indexes (this may take a moment) ---")
    
    # 1. Build FAISS
    dimension = movie_vectors.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(movie_vectors))
    faiss.write_index(index, FAISS_PATH)
    
    # 2. Build BM25
    tokenized_corpus = [doc.split(" ") for doc in movies['search_text']]
    bm25 = BM25Okapi(tokenized_corpus)
    with open(BM25_PATH, 'wb') as f:
        pickle.dump(bm25, f)

print("Setup Complete! Ready for retrieval.")

# Reranking
# Reranking model is trained to judge exactly how relevant a search result is
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')


#------------------------------------------------------------------------
# Search movies function
#------------------------------------------------------------------------
def search_movies(raw_json_query, k=5):
    """Performs a Hybrid Search: Vector (Semantic) + BM25 (Keyword) + Reranking"""
    try:
        # Parse the AI's JSON output
        try:
            query_data = json.loads(raw_json_query)
            clean_query = query_data.get("positive_query", "")
            exclusions = query_data.get("negative_constraints", [])
            print(f"🔍 Searching: '{clean_query}' | ⛔ Excluding: {exclusions}")
        except json.JSONDecodeError:
            # If JSON parsing fails, treat the whole string as the query
            clean_query = raw_json_query
            exclusions = []
        
        # --- A. VECTOR SEARCH ---
        # FAISS: Finds movies with similar meaning/vibe to the query
        query_vector = embedder.encode([clean_query])
        distances, indices = index.search(query_vector, k=50) # K for filtering
        vector_candidates_indices = [idx for idx in indices[0] if idx >= 0]

        # --- B. BM25 SEARCH ---
        # Finds movies containing specific keywords from the query
        tokenized_query = clean_query.split(" ")
        bm25_candidates_docs = bm25.get_top_n(tokenized_query, movies['search_text'].tolist(), n=50)
        
        bm25_indices = []
        for doc in bm25_candidates_docs:
            matches = movies.index[movies['search_text'] == doc].tolist()
            if matches: bm25_indices.extend(matches)

        # --- C. HARD FILTERING  ---
        # Combine candidates from both methods and apply strict safety/exclusion rules
        all_candidate_indices = list(set(vector_candidates_indices + bm25_indices))
        filtered_movies = []
        candidate_pairs = []
        
        for idx in all_candidate_indices:
            row = movies.loc[idx]
            # Ensure we check the FULL text for negative words
            # Combine title, overview, and genre for the check
            text_to_check = f"{row.get('title', '')} {row.get('search_text', '')} {row.get('genres', '')}".lower()
            
            # Rule 1: STRICT Exclusion
            # If ANY exclusion word appears in the text, skip this movie.
            if exclusions:
                is_excluded = False
                for neg in exclusions:
                    # check for the word with word boundaries to avoid partial matches
                    if re.search(rf"\b{re.escape(neg)}\b", text_to_check):
                        is_excluded = True
                        break
                if is_excluded:
                    continue

            # Rule 2: Family Safety (Your existing logic)
            is_family_query = any(word in clean_query.lower() for word in ['kids', 'family', 'children', 'animation'])
            if is_family_query:
                if any(bad in text_to_check for bad in ['horror', 'slasher', 'gore', 'r-rated']):
                    continue

            filtered_movies.append(row)
            candidate_pairs.append([clean_query, str(row['search_text'])])

        if not filtered_movies: 
            return []

        # --- D. RERANK ---
        # Use a Cross-Encoder to score exactly how relevant each candidate is to the query
        scores = reranker.predict(candidate_pairs)
        results_with_scores = list(zip(filtered_movies, scores))
        results_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        return [item[0] for item in results_with_scores[:k]]

    except Exception as e:
        print(f"❌ Search Error: {e}")
        import traceback
        traceback.print_exc()
        return []
    
#------------------------------------------------------------------------
# Rewrite function
#------------------------------------------------------------------------
def rewrite_query(user_message, history):
    """Uses AI to extract core search terms and negative constraints (exclusions) from user input."""
    try:
        chat_context = ""
        # Build context from history
        for turn in history:
            role = turn[0] if isinstance(turn, tuple) else turn.get('role')
            content = turn[1] if isinstance(turn, tuple) else turn.get('content', '')
            chat_context += f"{role}: {content}\n"

        # --- IMPROVED PROMPT ---
        prompt = f"""
        You are a Search Query Optimizer. Your goal is to separate what the user WANTS from what they want to AVOID.

        Instructions:
        1. Analyze the User Message and Context.
        2. Create a "positive_query": The core search terms (genre, plot, actors, mood).
        3. Create "negative_constraints": A list of specific keywords the user explicitly excludes (e.g., using "no", "without", "not", "except", "hate").
        4. OUTPUT FORMAT: You must return ONLY a valid JSON object. Do not add markdown formatting or explanations.
        
        Examples:
        - Input: "I want a funny movie but no animation"
          Output: {{ "positive_query": "funny comedy movie", "negative_constraints": ["animation", "cartoon", "animated"] }}
        
        - Input: "Action movies without guns or violence"
          Output: {{ "positive_query": "action movies", "negative_constraints": ["guns", "shooting", "violence", "blood"] }}
        
        - Input: "Show me movies like The Matrix"
          Output: {{ "positive_query": "Sci-fi action movies like The Matrix", "negative_constraints": [] }}

        Context: {chat_context}
        User Message: "{user_message}"
        """

        response = client.chat.completions.create(
            model="arcee-ai/trinity-large-preview:free", # Or your preferred model
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0, 
            response_format={ "type": "json_object" } # valid for some models, otherwise prompt instruction handles it
        )

        raw_content = response.choices[0].message.content.strip()
        
        # Cleanup: Remove markdown code blocks if the model adds them (e.g. ```json ... ```)
        if "```" in raw_content:
            raw_content = re.sub(r"```json|```", "", raw_content).strip()

        return raw_content

    except Exception as e:
        print(f"⚠️ AI Rewrite failed: {e}")
        # Fallback: return a simple JSON structure with just the message
        return json.dumps({"positive_query": user_message, "negative_constraints": []})

#------------------------------------------------------------------------
# The chat answer function
#------------------------------------------------------------------------
def chat_logic(user_message, history=[]):
    """Orchestrates the conversation: Clean History -> Rewrite Query -> Search -> Generate Answer"""
    try:
        
        # 1. Clean history of HTML tags before rewriting
        clean_history = []
        for h in history:
            # h[0] is user, h[1] is AI
            clean_ai_msg = re.sub('<[^<]+?>', '', h[1]) 
            clean_history.append((h[0], clean_ai_msg))

        # 2. Use the cleaned history for the rewriter
        recent_history = clean_history[-5:] 
        optimized_query = rewrite_query(user_message, recent_history)

        # 3. RETRIEVE: Search using the AI-optimized string
        # Model Tip: Ensure your 'search_movies' uses a hybrid search (semantic + keyword)
        retrieved_movies = search_movies(optimized_query, k=5)

        context_str = ""
        if retrieved_movies:
            context_str = "\n".join([f"- {m.get('search_text', 'N/A')}" for m in retrieved_movies])
        else:
            context_str = "No specific matches found."

        # 4. GENERATE: Conversational Response
        # Using a slightly higher temperature (0.5) for a "friendlier" feel
        response = client.chat.completions.create(
            model="arcee-ai/trinity-large-preview:free", 
            messages=[
                {"role": "system", "content": "You are a friendly Movie Assistant. Use the provided data to recommend films. Be brief (2-3 sentences)."},
                {"role": "user", "content": f"Context:\n{context_str}\n\nQuestion: {user_message}"}
            ],
            temperature=0.5,
            max_tokens=150
        )
        
        answer = response.choices[0].message.content.strip()

        print(f"--- DEBUG: Context sent to AI: {retrieved_movies}")
        print(f"--- DEBUG: AI Response: {answer}")


        return answer,retrieved_movies

    except Exception as e:
        return f"I ran into a snag: {str(e)}"

#------------------------------------------------------------------------
# The App
#------------------------------------------------------------------------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    try:
        user_query = request.json.get('query')
        if not user_query:
            return jsonify({"error": "No query provided"}), 400

        # 1. Use chat_logic to handle everything (Rewrite -> Search -> Final Answer)
        # This function already returns the summary and the movie list
        answer, results = chat_logic(user_query, history=[])

        # 2. Convert results safely to a list of dicts to avoid JSON 'NaN' errors
        movie_list = []
        for m in results:
            movie_list.append({
                "title": str(m.get('original_title', 'Unknown')),
                "rating": float(m.get('vote_average', 0)),
                "overview": str(m.get('overview', '')),
                "poster": str(m.get('Poster', 'nan')),
                "genres": str(m.get('genres', '')),
            })

        # 3. Return a combined object
        return jsonify({
            "ai_summary": answer,
            "movies": movie_list
        })

    except Exception as e:
        print(f"❌ Server Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/explore')
def explore():
    # This list matches your request
    genres = ['Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 'Documentary', 'Drama', 'Family', 'Fantasy', 'Foreign', 'History', 'Horror', 'Music', 'Mystery', 'Romance', 'Science Fiction', 'TV Movie', 'Thriller', 'War', 'Western']
    return render_template('explore.html', genres=genres)

@app.route('/get_movies_by_genre')
def get_movies_by_genre():
    """Filters movies based on a comma-separated list of genres (AND logic)."""
    genres_arg = request.args.get('genres', '')
    
    if not genres_arg:
        # If no genre is selected, show top 50 overall
        filtered = movies.sort_values(by='vote_average', ascending=False).head(50)
    else:
        genre_list = [g.strip() for g in genres_arg.split(',') if g.strip()]
        
        # We start with a mask of all True
        mask = pd.Series([True] * len(movies))
        
        for g in genre_list:
            mask &= movies['genres'].str.contains(rf"\b{re.escape(g)}\b", case=False, na=False)
            
        filtered = movies[mask].sort_values(by='vote_average', ascending=False).head(50)
    
    movie_list = []
    for _, m in filtered.iterrows():
        # Clean up the genre string for the UI
        clean_genres = str(m.get('genres', '')).replace('[', '').replace(']', '').replace("'", "").strip()
        
        movie_list.append({
            "title": str(m.get('original_title', 'Unknown')),
            "rating": round(float(m.get('vote_average', 0)), 1),
            "genres": clean_genres,
            "year": str(m.get('release_date', ''))[:4],
            "poster": str(m.get('Poster', 'nan')),
            "overview": str(m.get('overview', 'No description available.'))
        })
    return jsonify(movie_list)

if __name__ == '__main__':
    app.run(debug=True)
