import os
import kagglehub

import os

class Downloader:
    @staticmethod
    def download_spotify_data():
   
        bundled_path = "/app/data/dataset.csv"
        if os.path.exists(bundled_path):
            print(f"Using bundled data: {bundled_path}")
            return bundled_path
        
        # Fallback to local development data
        local_path = "./data/dataset.csv"
        if os.path.exists(local_path):
            print(f"Using local data: {local_path}")
            return local_path
 
        print("Downloading from Kaggle...")
        import kagglehub
        path = kagglehub.dataset_download("maharshipandya/-spotify-tracks-dataset")
        files = os.listdir(path)
        return os.path.join(path, files[0])