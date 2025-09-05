from fastapi import FastAPI, Query, HTTPException
from typing import List, Optional
from backend.service.indexer import Indexer
from backend.service.downloader import Downloader
from backend.service.searcher import SpotifySearcher
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


app = FastAPI(
    title="Spotify Elasticsearch API",
    description="API for searching and analyzing Spotify tracks",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

indexer = Indexer()
searcher = SpotifySearcher()

# @app.on_event("startup")
# async def startup_event():
#     """Initialize index on startup"""
#     try:
#         import asyncio
#         max_retries = 3  # Reduced retries
#         retry_delay = 2  # Reduced delay
        
#         for attempt in range(max_retries):
#             try:
#                 print(f"Attempt {attempt + 1}/{max_retries}: Checking Elasticsearch connection...")
                
#                 # Test basic connection with timeout
#                 loop = asyncio.get_event_loop()
#                 await loop.run_in_executor(None, indexer.client.info)
#                 print("Elasticsearch connection successful")
                
#                 # Quick index check only - NO data loading on startup
#                 index_exists = await loop.run_in_executor(None, indexer.check_index)
#                 if not index_exists:
#                     print("Index not found - will be created on first data request")
#                 else:
#                     print("Index exists and ready")
                
#                 break  
                
#             except Exception as e:
#                 print(f"Attempt {attempt + 1} failed: {e}")
#                 if attempt < max_retries - 1:
#                     print(f"Retrying in {retry_delay} seconds...")
#                     await asyncio.sleep(retry_delay)  # Use async sleep
#                 else:
#                     print("Elasticsearch not ready - API will start anyway")
        
#     except Exception as e:
#         print(f"Startup check failed: {e}")
#         print("API starting without Elasticsearch verification")


@app.get("/albums/{artist_name}", summary="Get artist albums")
async def get_albums(artist_name: str, size: int = Query(50, ge=1, le=100)):
    try:
        result = searcher.search_artist_albums(artist_name, size)
        return result  
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tracks/{artist}", summary="Get artist tracks") 
async def get_tracks(artist: str, size: int = Query(20, ge=1, le=100)):
    try:
        result = searcher.search_tracks_by_artist(artist, size)
        return result  
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Song search endpoints
@app.get("/search/song/{song}", summary="Smart song search")
async def search_song(song: str):
    try:
        result = searcher.song_searcher(song)
        return result  
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/fuzzy/{song}", summary="Fuzzy song search")
async def search_song_fuzzy(
    song: str, 
    fuzziness: str = Query("AUTO", description="Fuzziness level"),
    size: int = Query(10, ge=1, le=50)
):
    try:
        result = searcher.search_song_fuzzy(song, fuzziness, size)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/phrase/{song}", summary="Exact phrase search")
async def search_song_phrase(song: str, size: int = Query(10, ge=1, le=50)):
    try:
        result = searcher.search_song_phrase(song, size)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Filter endpoints
@app.get("/filter", summary="Filter tracks")
async def filter_tracks(
    genre: Optional[str] = Query(None, description="Music genre"),
    album: Optional[str] = Query(None, description="Album name"), 
    size: int = Query(20, ge=1, le=100, description="Number of results")
):
    """Filter tracks by genre and/or album"""
    try:
        result = searcher.filter(genre, album, size)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Similarity endpoint
@app.get("/similar/{track_id}", summary="Find similar tracks")
async def find_similar(
    track_id: str, 
    size: int = Query(10, ge=1, le=50, description="Number of similar tracks")
):
    """Find tracks similar to the given track using audio features"""
    try:
        result = searcher.find_similar_by_vector(track_id, size)
        if result is None:
            raise HTTPException(status_code=404, detail="Track not found or similarity search failed")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Analytics endpoints
@app.get("/analytics/compare", summary="Compare genres")
async def compare_genres(genres: List[str] = Query(..., description="List of genres to compare")):
    """Compare audio features across multiple genres"""
    try:
        if len(genres) < 2:
            raise HTTPException(status_code=400, detail="At least 2 genres required for comparison")
        if len(genres) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 genres allowed")
        
        result = searcher.compare_genres(genres)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/top-artists/{genre}", summary="Top artists in genre")
async def get_top_artists(
    genre: str,
    size: int = Query(10, ge=1, le=50, description="Number of top artists"),
    min_tracks: int = Query(2, ge=1, le=10, description="Minimum tracks required")):
    try:
        result = searcher.top_artists_per_genre(genre, size)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health", summary="Health check")
async def health_check():
    """Check if the API and Elasticsearch are working"""
    try:
        info = searcher.client.info()
        return {
            "status": "healthy",
            "elasticsearch": {
                "cluster_name": info["cluster_name"],
                "version": info["version"]["number"]
            },
            "index": searcher.index_name
        }
    except Exception as e:
        return {
            "status": "degraded",
            "api": "healthy",
            "elasticsearch": "unavailable",
            "error": str(e),
            "message": "API is running but Elasticsearch is not accessible"
        }


@app.get("/", summary="API info")
async def root():
    """API information and available endpoints"""
    return {
        "message": "Spotify Elasticsearch API",
        "version": "1.0.0",
        "endpoints": {
            "albums": "/albums/{artist}",
            "tracks": "/tracks/{artist}", 
            "search": "/search/song/{song}",
            "filter": "/filter?genre=rock&album=album_name",
            "similar": "/similar/{track_id}",
            "compare": "/analytics/compare?genres=rock&genres=pop",
            "top_artists": "/analytics/top-artists/{genre}",
            "health": "/health"
        }
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Resource not found", "detail": str(exc)},
    )

@app.exception_handler(500)  
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )