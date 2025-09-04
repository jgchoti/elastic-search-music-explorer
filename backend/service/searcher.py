from elasticsearch import Elasticsearch
from typing import List, Union, Dict, Any
from service.model import SearchResult, ArtistAlbums, TopArtists, GenreComparison, Track

class SpotifySearcher:
    def __init__(self, index_name="spotify_tracks", es_host="http://localhost:9200"):
        self.client = Elasticsearch(es_host)
        self.index_name = index_name
    def search_artist_albums(self, artist_name: str, size: int = 50) -> Dict[str, Any]:
        query = {
        "size": 0,
        "query": {"match": {"artists": artist_name}},
        "aggs": {
            "albums": {
                "terms": {
                    "field": "album_name.keyword",
                    "size": size
                }
            }
        }
    }
        result = self.client.search(index=self.index_name, body=query)
        total_tracks = result.get('hits', {}).get('total', {}).get('value', 0)
        print(f"Total tracks by '{artist_name}': {total_tracks}")
        artist_albums = ArtistAlbums.from_elasticsearch_result(artist_name, result)
        return artist_albums.to_dict()


    def search_tracks_by_artist(self, artist_name: str, size: int = 100) -> Dict[str, Any]:
        query = {"match": {"artists": artist_name}}
        result = self.client.search(index=self.index_name, query=query, size=size)
        
        print(f"Found {result['hits']['total']['value']} tracks by '{artist_name}':")
        
        search_result = SearchResult.from_search_hits(
            result['hits']['hits'],
            result['hits']['total']['value'],
            filters={"artist": artist_name},
            artist=artist_name  
        )
        
        for track in search_result.results:
            print(f"- {track.track_name} from {track.album_name} (Popularity: {track.popularity})")
        
        return search_result.to_dict()
    
    def search_song_fuzzy(self, song_name: str, fuzziness: str = "AUTO", size: int = 10) -> Dict[str, Any]:
        """Search for songs with fuzzy matching"""
        query = {
            "fuzzy": {
                "track_name": {
                    "value": song_name,
                    "fuzziness": fuzziness
                }
            }
        }
        
        result = self.client.search(index=self.index_name, query=query, size=size)
        
        print(f"Found {result['hits']['total']['value']} tracks similar to '{song_name}' (fuzzy matching):")
        
        search_result = SearchResult.from_search_hits(
            result['hits']['hits'],
            result['hits']['total']['value'],
            filters={"search_type": "fuzzy", "query": song_name}
        )
        
        for track in search_result.results:
            print(f"- {track.track_name} by {track.artists}")
        
        return search_result.to_dict()
    
    def search_song_phrase(self, song_name: str, size: int = 10) -> Dict[str, Any]:
        """Search for exact phrase matches"""
        query = {"match_phrase": {"track_name": song_name}}
        result = self.client.search(index=self.index_name, query=query, size=size)
        
        print(f"Found {result['hits']['total']['value']} tracks with phrase '{song_name}':")
        
        search_result = SearchResult.from_search_hits(
            result['hits']['hits'],
            result['hits']['total']['value'],
            filters={"search_type": "phrase", "query": song_name}
        )
        
        for track in search_result.results:
            print(f"- {track.track_name} by {track.artists}")
        
        return search_result.to_dict()
    
    def search_song_partial(self, partial_title: str, size: int = 20) -> Dict[str, Any]:
        """Search for partial matches"""
        query = {
            "multi_match": {
                "query": partial_title,
                "fields": ["track_name"],
                "operator": "or"
            }
        }
        
        result = self.client.search(index=self.index_name, query=query, size=size)
        
        print(f"Found {result['hits']['total']['value']} tracks containing words from '{partial_title}':")
        
        search_result = SearchResult.from_search_hits(
            result['hits']['hits'][:10],  
            result['hits']['total']['value'],
            filters={"search_type": "partial", "query": partial_title}
        )
        
        for track in search_result.results:
            print(f"- {track.track_name} by {track.artists}")
        
        return search_result.to_dict()
    
    def song_searcher(self, song_title: str) -> Dict[str, Any]:
        """Smart song search with fallback strategies"""
        result_dict = self.search_song_phrase(song_title)
        if result_dict["total_tracks"] > 0:
            return result_dict
        
        stop_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 
                     'is', 'are', 'was', 'were', 'this', 'that']
        words = song_title.lower().split()
        key_words = [word for word in words if word not in stop_words]
        
        if key_words:
            key_phrase = ' '.join(key_words)
            result_dict = self.search_song_partial(key_phrase)
            if result_dict["total_tracks"] > 0:
                return result_dict
            
            for word in key_words:
                print(f"Trying fuzzy: '{word}'...")
                result_dict = self.search_song_fuzzy(word)
                if result_dict["total_tracks"] > 0:
                    return result_dict
        
        print("No matches found with any strategy.")
        
        empty_result = SearchResult(
            total_tracks=0,
            results=[],
            filters={"search_type": "smart", "query": song_title, "status": "no_matches"}
        )
        return empty_result.to_dict()
    
    def filter(self, genre: str = None, album: str = None, size: int = 20) -> Dict[str, Any]:
        """Filter tracks by genre and/or album with fuzzy fallback"""
        query = {
            "size": size,
            "query": {"bool": {"filter": []}}
        }
        
        filters = query["query"]["bool"]["filter"]
        applied_filters = {"track_genre": None, "album": None}
        
        if genre:
            filters.append({"term": {"track_genre": genre}})
            applied_filters["track_genre"] = genre
        
        if album:
            filters.append({"term": {"album_name.keyword": album}})
            applied_filters["album"] = album
        
        result = self.client.search(index=self.index_name, body=query)
        
        # If no results and album specified, try fuzzy search
        if result['hits']['total']['value'] == 0 and album:
            print(f"No exact matches for album '{album}', searching for similar matches...")
            return self.fuzzy_album_search(genre, album, size, applied_filters)

        search_result = SearchResult.from_search_hits(
            result['hits']['hits'][:10],  # Limit to 10
            result['hits']['total']['value'],
            filters=applied_filters
        )
        
        for track in search_result.results:
            print(f"- {track.track_name} by {track.artists}")
        
        return search_result.to_dict()
    
    def fuzzy_album_search(self, genre: str, album: str, size: int, 
                           applied_filters: Dict[str, Any]) -> Dict[str, Any]:
        
        fuzzy_query = {
            "size": size,
            "query": {
                "bool": {
                    "filter": [],
                    "must": [{
                        "match": {
                            "album_name": {
                                "query": album,
                                "fuzziness": "AUTO",
                                "operator": "and"
                            }
                        }
                    }]
                }
            }
        }
        
        if genre:
            fuzzy_query["query"]["bool"]["filter"].append({"term": {"track_genre": genre}})
        
        result = self.client.search(index=self.index_name, body=fuzzy_query)
        
        applied_filters["search_type"] = "fuzzy_fallback"
        
        search_result = SearchResult.from_search_hits(
            result['hits']['hits'][:10],
            result['hits']['total']['value'],
            filters=applied_filters
        )
        
        for track in search_result.results:
            print(f"- {track.track_name} by {track.artists}")
        
        return search_result.to_dict()
    
    def find_similar_by_vector(self, track_id: str, size: int = 10) -> Union[Dict[str, Any], None]:
        try:
            source_result = self.client.get(index=self.index_name, id=track_id)
            source_vector = source_result['_source']['audio_vector']
            source_track = source_result['_source']
            
            print(f"\nFinding songs similar to:")
            print(f"'{source_track['track_name']}' by {source_track['artists']}")
            print(f"Genre: {source_track['track_genre']}, Popularity: {source_track['popularity']}")
            
            search_query = {
                "knn": {
                    "field": "audio_vector",
                    "query_vector": source_vector,
                    "k": size + 1,
                    "num_candidates": 1000
                }
            }
            
            result = self.client.search(index=self.index_name, body=search_query)
 
            search_result = SearchResult.from_similarity_search(
                result['hits']['hits'],
                track_id,
                size
            )
            

            for track in search_result.results:
                print(f"   Similarity: {track.similarity:.3f} | Genre: {track.track_genre}")
            
            return search_result.to_dict()
            
        except Exception as e:
            print(f"Error finding similar tracks: {e}")
            return None
    
    def compare_genres(self, genre_list: List[str]) -> Dict[str, Any]:
        """Compare multiple genres"""
        query = {
            "size": 0,
            "aggs": {}
        }
        
        for genre in genre_list:
            query["aggs"][f"genre_{genre.replace('-', '_')}"] = {
                "filter": {"term": {"track_genre": genre}},
                "aggs": {
                    "avg_danceability": {"avg": {"field": "danceability"}},
                    "avg_energy": {"avg": {"field": "energy"}},
                    "avg_valence": {"avg": {"field": "valence"}},
                    "avg_popularity": {"avg": {"field": "popularity"}},
                    "avg_tempo": {"avg": {"field": "tempo"}},
                    "track_count": {"value_count": {"field": "track_id"}}
                }
            }
        
        result = self.client.search(index=self.index_name, body=query)

        comparison = GenreComparison.from_elasticsearch_result(genre_list, result)
        return comparison.to_dict()
    
    def top_artists_per_genre(self, genre: str, size: int = 10) -> Dict[str, Any]:

        query = {
            "size": 0,
            "query": {"term": {"track_genre": genre}},
            "aggs": {
                "all_artists": {
                    "terms": {
                        "field": "artists.keyword",
                        "size": 500,
                        "order": {"avg_popularity": "desc"}
                    },
                    "aggs": {
                        "avg_popularity": {"avg": {"field": "popularity"}},
                        "popularity_filter": {
                            "bucket_selector": {
                                "buckets_path": {
                                    "avg_pop": "avg_popularity",
                                    "track_count": "_count"
                                },
                                "script": "params.track_count >= 2"
                            }
                        }
                    }
                }
            }
        }
        
        result = self.client.search(index=self.index_name, body=query)
        
        top_artists = TopArtists.from_elasticsearch_result(genre, result, size)
        return top_artists.to_dict()
    
    # def debug_genres(self):
    #     query = {
    #     "size": 0,
    #     "aggs": {
    #         "genres": {
    #             "terms": {
    #                 "field": "track_genre",
    #                 "size": 100
    #             }
    #         }
    #     }
    # }
    #     result = self.client.search(index=self.index_name, body=query)
    #     print("Available genres:")
    #     for bucket in result['aggregations']['genres']['buckets']:
    #         print(f"- '{bucket['key']}' ({bucket['doc_count']} tracks)")
            
    