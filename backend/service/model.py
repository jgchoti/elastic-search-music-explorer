from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

@dataclass
class Track:
    track_id: str
    track_name: str
    album_name: str
    popularity: int
    track_genre: str
    artists: Optional[str] = None
    similarity: Optional[float] = None
    
    @classmethod
    def from_elasticsearch_hit(cls, hit: Dict[str, Any], similarity: float = None) -> 'Track':
        """Create Track from Elasticsearch hit result"""
        source = hit['_source']
        return cls(
            track_id=source.get('track_id', hit.get('_id', '')),
            track_name=source.get('track_name', ''),
            album_name=source.get('album_name', ''),
            popularity=source.get('popularity', 0),
            track_genre=source.get('track_genre', ''),
            artists=source.get('artists', ''),
            similarity=similarity
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        result = asdict(self)
        return {k: v for k, v in result.items() if v is not None}

@dataclass
class Album:
    artist:str
    name: str
    nb_tracks: int
    
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ArtistAlbums:
    artist: str
    total_albums: int
    albums: List[Album]
    
    @classmethod
    def from_elasticsearch_result(cls, artist_name: str, result: Dict[str, Any]) -> 'ArtistAlbums':
        buckets = result.get('aggregations', {}).get('albums', {}).get('buckets', [])
        albums = [
        Album(
            artist=artist_name,
            name=bucket.get('key', 'Unknown'),
            nb_tracks=bucket.get('doc_count', 0)
        )
        for bucket in buckets
    ]
        return cls(
        artist=artist_name,
        total_albums=len(albums),
        albums=albums
    )

    
    def to_dict(self) -> Dict[str, Any]:
        try:
            return {
            "artist": getattr(self, "artist", "Unknown"),
            "total_albums": getattr(self, "total_albums", 0),
            "albums": [album.to_dict() for album in getattr(self, "albums", [])]
        }
        except Exception as e:
            print(f"Error converting ArtistAlbums to dict: {e}")
            return {
            "artist": getattr(self, "artist", "Unknown"),
            "total_albums": 0,
            "albums": []
        }

@dataclass
class SearchResult:
    total_tracks: int
    results: List[Track]
    filters: Optional[Dict[str, Any]] = None
    artist: Optional[str] = None  
    
    @classmethod
    def from_search_hits(cls, hits: List[Dict[str, Any]], total: int, 
                        filters: Dict[str, Any] = None, artist: str = None) -> 'SearchResult':
        """Create SearchResult from Elasticsearch hits"""
        tracks = []
        for hit in hits:
            tracks.append(Track.from_elasticsearch_hit(hit))
        
        return cls(
            total_tracks=total,
            results=tracks,
            filters=filters,
            artist=artist
        )
    
    @classmethod 
    def from_similarity_search(cls, hits: List[Dict[str, Any]], 
                              source_track_id: str, size: int) -> 'SearchResult':
        """Create SearchResult from similarity search results"""
        tracks = []
        count = 0
        
        for hit in hits:
            if hit['_id'] == source_track_id: 
                continue
            
            if count >= size:
                break
                
            similarity = hit['_score'] - 1.0
            track = Track.from_elasticsearch_hit(hit, similarity)
            tracks.append(track)
            count += 1
        
        return cls(
            total_tracks=count,
            results=tracks,
            filters={"similarity_search": True}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "total_tracks": self.total_tracks,
            "results": [track.to_dict() for track in self.results]
        }
        
        if self.filters:
            result["filters"] = self.filters
        
        if self.artist:
            result["artist"] = self.artist
            # For artist searches, use "tracks" instead of "results"
            result["tracks"] = result.pop("results")
        
        return result

@dataclass
class GenreStats:
    genre: str
    track_count: int
    avg_danceability: float
    avg_energy: float
    avg_valence: float
    avg_popularity: float
    avg_tempo: float
    
    @classmethod
    def from_aggregation(cls, genre: str, agg: Dict[str, Any]) -> 'GenreStats':
        """Create GenreStats from Elasticsearch aggregation bucket"""
        return cls(
            genre=genre,
            track_count=int(agg["track_count"]["value"]),
            avg_danceability=agg["avg_danceability"]["value"] or 0,
            avg_energy=agg["avg_energy"]["value"] or 0,
            avg_valence=agg["avg_valence"]["value"] or 0,
            avg_popularity=agg["avg_popularity"]["value"] or 0,
            avg_tempo=agg["avg_tempo"]["value"] or 0
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class GenreComparison:
    genres: List[GenreStats]
    
    @classmethod
    def from_elasticsearch_result(cls, genre_list: List[str], 
                                 result: Dict[str, Any]) -> 'GenreComparison':
        """Create GenreComparison from Elasticsearch aggregation result"""
        genre_stats = []
        
        for genre in genre_list:
            agg_key = f"genre_{genre.replace('-', '_')}"
            if agg_key in result["aggregations"]:
                agg = result["aggregations"][agg_key]
                stats = GenreStats.from_aggregation(genre, agg)
                genre_stats.append(stats)
        
        return cls(genres=genre_stats)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "genres": [stats.to_dict() for stats in self.genres]
        }

@dataclass
class Artist:
    rank: int
    artist: str
    track_count: int
    avg_popularity: float
    weighted_score: Optional[float] = None
    
    @classmethod
    def from_aggregation_bucket(cls, rank: int, bucket: Dict[str, Any], 
                               include_weighted: bool = False) -> 'Artist':
        """Create Artist from Elasticsearch aggregation bucket"""
        artist = cls(
            rank=rank,
            artist=bucket["key"],
            track_count=bucket["doc_count"],
            avg_popularity=round(bucket["avg_popularity"]["value"] or 0, 1)
        )
        
        if include_weighted and "weighted_score" in bucket:
            artist.weighted_score = round(bucket["weighted_score"]["value"], 1)
        
        return artist
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        return {k: v for k, v in result.items() if v is not None}

@dataclass
class TopArtists:
    genre: str
    top_artists: List[Artist]
    
    @classmethod
    def from_elasticsearch_result(cls, genre: str, result: Dict[str, Any], 
                                 size: int, include_weighted: bool = False) -> 'TopArtists':
        """Create TopArtists from Elasticsearch aggregation result"""
        artists = []
        
        for i, bucket in enumerate(result["aggregations"]["all_artists"]["buckets"][:size], 1):
            artist = Artist.from_aggregation_bucket(i, bucket, include_weighted)
            artists.append(artist)
        
        return cls(genre=genre, top_artists=artists)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "genre": self.genre,
            "top_artists": [artist.to_dict() for artist in self.top_artists]
        }