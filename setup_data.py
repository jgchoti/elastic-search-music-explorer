import os
import sys
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.service.indexer import Indexer
from backend.service.downloader import Downloader

def wait_for_elasticsearch(max_retries=10, delay=5):
    """Wait for Elasticsearch to be ready"""
    print("Waiting for Elasticsearch to be ready...")
    
    for attempt in range(max_retries):
        try:
            indexer = Indexer()
            info = indexer.client.info()
            print(f"✓ Elasticsearch is ready: {info['cluster_name']} v{info['version']['number']}")
            return True
        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_retries}: Elasticsearch not ready ({e})")
            if attempt < max_retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
    
    print("✗ Failed to connect to Elasticsearch after all retries")
    return False

def setup_data():
    """Download and index Spotify data"""
    try:
        # Wait for Elasticsearch
        if not wait_for_elasticsearch():
            print("ERROR: Cannot proceed without Elasticsearch")
            return False
        
        # Initialize services
        indexer = Indexer()
        downloader = Downloader()
        
        # Check if index already exists
        if indexer.check_index():
            print("✓ Index already exists")
            
            # Ask user if they want to recreate
            response = input("Do you want to recreate the index? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("Skipping data setup")
                return True
            
            print("Deleting existing index...")
            indexer.delete_index()
        
        print("Starting data download and indexing...")
        
        # Download data
        print("1. Downloading Spotify data...")
        input_file = downloader.download_spotify_data()
        print(f"✓ Data downloaded to: {input_file}")
        
        # Load and index data
        print("2. Loading data...")
        indexer.load_data(input_file)
        print("✓ Data loaded")
        
        print("3. Indexing data (this may take a while)...")
        indexer.index_data()
        print("✓ Data indexed successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Setup failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🎵 Spotify Music Explorer - Data Setup")
    print("=" * 50)
    
    # Check if docker-compose is running
    print("Make sure your docker-compose is running with Elasticsearch:")
    print("  docker-compose up elasticsearch")
    print()
    
    response = input("Is Elasticsearch running? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Please start Elasticsearch first:")
        print("  docker-compose up elasticsearch")
        return
    
    print("\nStarting data setup...")
    
    if setup_data():
        print("\n🎉 Setup completed successfully!")
        print("\nYou can now start your application:")
        print("  docker-compose up spotify-app")
        print("\nOr start the full stack:")
        print("  docker-compose up")
    else:
        print("\n❌ Setup failed. Check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()