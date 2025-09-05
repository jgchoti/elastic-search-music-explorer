from elasticsearch import Elasticsearch
from elasticsearch import helpers
import pandas as pd
import os
class Indexer():
    def __init__(self, index_name="spotify_tracks", es_host=None):
        self.index_name = index_name
        if es_host is None:
            es_host = os.getenv('ELASTICSEARCH_HOST', 'http://localhost:9200')
        self.client = Elasticsearch(es_host)
        self.df = None
    
    def check_index(self):
        if not self.client.indices.exists(index=self.index_name):
            print(f"Index '{self.index_name}' doesn't exist. Creating with mapping...")
            self.create_index_with_mapping()
            return False 
        else:
            print(f"Index '{self.index_name}' already exists. Skipping indexing.")
            return True  

    def delete_index(self):
        if self.client.indices.exists(index=self.index_name):
            self.client.indices.delete(index=self.index_name)
            print(f"Deleted index '{self.index_name}'")

    def create_mapping(self):
        """Create mapping for Spotify tracks data based on actual columns"""
        mapping = {
            "properties": {
                "track_id": {"type": "keyword"},
                "artists": {
                    "type": "text",
                    "analyzer": "standard",
                    "fields": {"keyword": {"type": "keyword"}}
                },
                "album_name": {
                    "type": "text", 
                    "analyzer": "standard",
                    "fields": {"keyword": {"type": "keyword"}}
                },
                "track_name": {
                    "type": "text",
                    "analyzer": "standard", 
                    "fields": {"keyword": {"type": "keyword"}}
                },
                "popularity": {"type": "integer"},
                "duration_ms": {"type": "long"},
                "explicit": {"type": "boolean"},
                "danceability": {"type": "float"},
                "energy": {"type": "float"},
                "key": {"type": "integer"},
                "loudness": {"type": "float"},
                "mode": {"type": "integer"},
                "speechiness": {"type": "float"},
                "acousticness": {"type": "float"},
                "instrumentalness": {"type": "float"},
                "liveness": {"type": "float"},
                "valence": {"type": "float"},
                "tempo": {"type": "float"},
                "time_signature": {"type": "integer"},
                "track_genre": {"type": "keyword"},
                "audio_vector": {
                "type": "dense_vector",
                "dims": 10, 
                "index": True,
                "similarity": "cosine"
            }
            }
        }
        return mapping
    
    def create_index_with_mapping(self):
        """Create index with proper mapping"""
        mapping = self.create_mapping()
        self.client.indices.create(
            index=self.index_name,
            body={"mappings": mapping}
        )
        print(f"Created index '{self.index_name}' with mapping")
    
    def load_data(self, input_file):
        print(f"Loading data from: {input_file}")
        self.df = pd.read_csv(input_file)
        
        if 'Unnamed: 0' in self.df.columns:
            self.df = self.df.drop('Unnamed: 0', axis=1)
            print("Dropped 'Unnamed: 0' column")
        
        print(f"Loaded {len(self.df)} records")
        print(f"Columns: {list(self.df.columns)}")
        
    def create_audio_vector(self, track_data):
        ranges = {
        'danceability': (0.00, 0.99),
        'energy': (0.00, 1.00),
        'valence': (0.00, 1.00),
        'acousticness': (0.00, 1.00),
        'instrumentalness': (0.00, 1.00),
        'speechiness': (0.00, 0.96),
        'liveness': (0.00, 1.00),
        'tempo': (0.00, 243.37),
        'loudness': (-49.53, 4.53),
        'popularity': (0.00, 100.00)
    }
        feature_names = [
        'danceability', 'energy', 'valence', 'acousticness',
        'instrumentalness', 'speechiness', 'liveness', 
        'tempo', 'loudness', 'popularity'
    ]
        features = []
        for feature_name in feature_names:
            value = track_data[feature_name]
            min_val, max_val = ranges[feature_name]
            if max_val != min_val:
                normalized = (value - min_val) / (max_val - min_val)
                normalized = max(0.0, min(1.0, normalized))
            else:
                normalized = 0.0
            features.append(normalized)
        return features
        
    
    def index_data(self, batch_size=1000):
        """Bulk index data in batches for better memory management"""
        
        bulk_data = []
        total_docs = len(self.df)
        for index, row in self.df.iterrows():
            doc = row.to_dict()
            doc = {k: (None if pd.isna(v) else v) for k, v in doc.items()}
            try:
                audio_vector = self.create_audio_vector(doc)
                doc['audio_vector'] = audio_vector
            except Exception as e:
                print(f"Vector creation error for doc {index}: {e}")
                continue
            
            bulk_data.append({
                "_index": self.index_name,
                "_id": doc.get("track_id"),  
                "_source": doc
            })
            if len(bulk_data) >= batch_size:
                try:
                    helpers.bulk(self.client, bulk_data)
                    print(f"Indexed batch: {index + 1}/{total_docs} documents")
                    bulk_data = [] 
                except Exception as e:
                    print(f"Error indexing batch at document {index}: {e}")
                    bulk_data = []
    
        if bulk_data:   
            helpers.bulk(self.client, bulk_data)
 
            
        print("Indexing completed!")

    
    def verify_indexing(self):
        """Verify the indexing was successful"""
        if self.client.indices.exists(index=self.index_name):
            count = self.client.count(index=self.index_name)['count']
            print(f"Verification: Index '{self.index_name}' contains {count} documents")
            
            sample = self.client.search(index=self.index_name, size=1)
            if sample['hits']['hits']:
                print("\nSample document:")
                doc = sample['hits']['hits'][0]['_source']
                print(f"Track: {doc.get('track_name')} by {doc.get('artists')}")
        else:
            print(f"Index '{self.index_name}' does not exist!")
            
    def analyze_feature_ranges(self):
        """Find the actual min/max ranges for all numeric features"""
        numeric_features = [
        'danceability', 'energy', 'valence', 'acousticness', 
        'instrumentalness', 'speechiness', 'tempo', 'loudness',
        'liveness', 'popularity'
    ]
        aggs = {}
        for feature in numeric_features:
            aggs[f"{feature}_stats"] = {
            "stats": {
                "field": feature
            }
        }
        query = {
        "size": 0,  
        "aggs": aggs
    }
        result = self.client.search(index=self.index_name, body=query)
        print("Feature Ranges in Your Dataset:")
        print("=" * 50)
        ranges = {}
        for feature in numeric_features:
            stats = result['aggregations'][f"{feature}_stats"]
            min_val = stats['min']
            max_val = stats['max']
            avg_val = stats['avg']
            ranges[feature] = {'min': min_val, 'max': max_val}
            print(f"{feature:15s}: {min_val:8.2f} to {max_val:8.2f} (avg: {avg_val:.2f})")
        return ranges
    