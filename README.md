# 🎵 Spotify Music Explorer

A powerful music analytics platform using Elasticsearch, FastAPI, and Streamlit for exploring Spotify track data with advanced search and AI-powered recommendations.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.x-yellow.svg)](https://elastic.co)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-Latest-red.svg)](https://streamlit.io)

## ✨ Features

- 🔍 **Smart Search** - Find tracks by title, artist, or album
- 📊 **Genre Analytics** - Compare audio features across genres
- 🎯 **AI Recommendations** - Vector-based similarity search
- 👥 **Artist Rankings** - Top performers by genre and popularity
- 📈 **Interactive Dashboards** - Real-time visualizations with Plotly

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/jgchoti/elastic-search-music-explorer.git
cd elastic-search-music-explorer

# Start Elasticsearch
docker run -d -p 9200:9200 -e "discovery.type=single-node" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0

# Install dependencies
pip install -r requirements.txt

python backend/main.py

# Start services
uvicorn backend.main:app --reload &
streamlit run app.py
```

## 🎯 Demo

**Dashboard**: http://localhost:8501  
**API Docs**: http://localhost:8000/docs

![Dashboard Preview](demo-screenshot.png)

## 🏗️ Architecture

```
Backend (FastAPI) ↔ Elasticsearch ↔ Frontend (Streamlit)
     ↓                    ↓              ↓
API Endpoints         Search Index    Visualizations
Vector Search         Audio Features  Interactive Charts
```

## 📊 Dataset

Uses [Spotify Tracks Dataset](https://www.kaggle.com/datasets/maharshipandya/-spotify-tracks-dataset) with:

- 114,000+ tracks
- Audio features (danceability, energy, valence, tempo)
- Metadata (artist, album, genre, popularity)

## 🔧 Key Technologies

- **Search**: Elasticsearch with vector similarity
- **Backend**: FastAPI with async support
- **Frontend**: Streamlit + Plotly visualizations

## 📱 Main Features

| Feature             | Description                                    |
| ------------------- | ---------------------------------------------- |
| **Search & Filter** | Advanced text search with genre/year filtering |
| **Genre Analytics** | Compare audio features across music genres     |
| **Artist Rankings** | Top artists by popularity and track count      |
| **Real-time Stats** | Live dashboard with collection insights        |

---

⭐ **Star this repo** if you found it helpful!
