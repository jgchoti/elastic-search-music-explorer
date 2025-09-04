import os
import kagglehub

class Downloader:
    @staticmethod
    def download_spotify_data():
        path = kagglehub.dataset_download("maharshipandya/-spotify-tracks-dataset")
        files = os.listdir(path)
        print(os.path.join(path, files[0]))
        return os.path.join(path, files[0])