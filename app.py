import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from typing import List, Dict, Any
import numpy as np
import os

st.set_page_config(
    page_title="Spotify Music Analytics",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_BASE = os.getenv('API_BASE', "http://localhost:8000")


st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .stSelectbox > div > div {
        background-color: #f0f2f6;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def call_api(endpoint: str, params: dict = None) -> dict:
    """Make API calls with caching"""
    try:
        url = f"{API_BASE}{endpoint}"
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return {}

def main():

    st.title("🎵 Spotify Music Analytics Dashboard")
    st.markdown("---")
    
    st.sidebar.title("🎛️ Controls")
    
    page = st.sidebar.selectbox(
        "Choose Analysis",
        ["🏠 Overview", "🔍 Search & Filter", "📊 Genre Analytics", "👥 Artist Rankings", "🎯 Similarity Analysis"]
    )
    
    if page == "🏠 Overview":
        show_overview()
    elif page == "🔍 Search & Filter":
        show_search_filter()
    elif page == "📊 Genre Analytics":
        show_genre_analytics()
    elif page == "👥 Artist Rankings":
        show_artist_rankings()
    elif page == "🎯 Similarity Analysis":
        show_similarity_analysis()

def show_overview():
    st.header("📈 Music Collection Overview")
    
    col1, col2, col3 = st.columns(3)
    
    try:
        health_data = call_api("/health")
        
        with col1:
            st.metric("🔗 API Status", "Connected", "✅")
        
        with col2:
            if health_data.get('elasticsearch'):
                es_version = health_data['elasticsearch'].get('version', 'Unknown')
                st.metric("🔍 Elasticsearch", es_version, "✅")
        
        with col3:
            index_name = health_data.get('index', 'Unknown')
            st.metric("📚 Index", index_name, "✅")
    
    except Exception as e:
        st.error("Cannot connect to API. Make sure your backend is running.")
        return
    
    st.subheader("🎭 Genre Distribution")
    
    popular_genres = ["rock", "pop", "electronic", "jazz", "hip-hop", "country"]
    
    try:
        params = "&".join([f"genres={genre}" for genre in popular_genres])
        genre_data = call_api(f"/analytics/compare?{params}")
        
        if genre_data.get('genres'):
            df_genres = pd.DataFrame(genre_data['genres'])
            
            fig_bar = px.bar(
                df_genres, 
                x='genre', 
                y='track_count',
                title="Track Count by Genre",
                color='avg_popularity',
                color_continuous_scale='viridis'
            )
            fig_bar.update_layout(height=400)
            st.plotly_chart(fig_bar, use_container_width=True)
            
            audio_features = ['avg_danceability', 'avg_energy', 'avg_valence', 'avg_tempo']
            
            fig_radar = go.Figure()
            
            for _, genre_row in df_genres.iterrows():
                tempo_normalized = genre_row['avg_tempo'] / 243.37 
                fig_radar.add_trace(go.Scatterpolar(
                    r=[genre_row['avg_danceability'], genre_row['avg_energy'], genre_row['avg_valence'], tempo_normalized],
                    theta=['Danceability', 'Energy', 'Valence', 'Tempo'],
                    fill='toself',
                    name=genre_row['genre'].title(),
                    opacity=0.6
                ))
            
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 1]
                    )),
                showlegend=True,
                title="Audio Features by Genre"
            )
            
            st.plotly_chart(fig_radar, use_container_width=True)
    
    except Exception as e:
        st.error(f"Error loading genre data: {str(e)}")

def show_search_filter():
    st.header("🔍 Search & Filter Music")
  
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_query = st.text_input("🎵 Search for songs, artists, or albums:", placeholder="Enter your search...")
    
    with col2:
        search_type = st.selectbox("Search Type:", ["Songs", "Artists", "Albums"])
    
    if search_query and st.button("🔍 Search", type="primary"):
        
        endpoint_map = {
            "Songs": f"/search/song/{search_query}",
            "Artists": f"/tracks/{search_query}",
            "Albums": f"/albums/{search_query}"
        }
        
        try:
            results = call_api(endpoint_map[search_type])
            
            if search_type == "Albums" and results.get('albums'):
                st.subheader(f"📀 Albums by {results.get('artist', search_query)}")
                albums_df = pd.DataFrame(results['albums'])
                
                fig = px.bar(
                    albums_df, 
                    x='name', 
                    y='nb_tracks',
                    title=f"Track Count by Album"
                )
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(albums_df, use_container_width=True)
            
            elif search_type == "Artists" and results.get('tracks'):
                st.subheader(f"🎤 Tracks by {results.get('artist', search_query)}")
                tracks_df = pd.DataFrame(results['tracks'])
                
                if not tracks_df.empty:
                    fig_hist = px.histogram(
                        tracks_df, 
                        x='popularity',
                        title="Track Popularity Distribution",
                        nbins=20
                    )
                    st.plotly_chart(fig_hist, use_container_width=True)
                    
                    st.dataframe(
                        tracks_df[['track_name', 'album_name', 'popularity', 'track_genre']],
                        use_container_width=True
                    )
            
            elif search_type == "Songs" and results.get('results'):
                st.subheader(f"🎵 Songs matching '{search_query}'")
                songs_df = pd.DataFrame(results['results'])
                st.dataframe(songs_df, use_container_width=True)
        
        except Exception as e:
            st.error(f"Search error: {str(e)}")
    

    st.markdown("---")
    st.subheader("🎛️ Advanced Filtering")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filter_genre = st.text_input("Genre:", placeholder="e.g., rock, pop, jazz")
    
    with col2:
        filter_album = st.text_input("Album:", placeholder="Album name")
    
    with col3:
        filter_size = st.slider("Max Results:", 5, 50, 20)
    
    if st.button("🔽 Apply Filters", type="primary"):
        if filter_genre or filter_album:
            try:
                params = {"size": filter_size}
                if filter_genre:
                    params["genre"] = filter_genre
                if filter_album:
                    params["album"] = filter_album
                
                filtered_results = call_api("/filter", params)
                
                if filtered_results.get('results'):
                    st.subheader("🎯 Filtered Results")
                    filtered_df = pd.DataFrame(filtered_results['results'])
                    st.dataframe(filtered_df, use_container_width=True)
                else:
                    st.info("No results found with those filters.")
            
            except Exception as e:
                st.error(f"Filter error: {str(e)}")
        else:
            st.warning("Please enter at least one filter criteria.")

def show_genre_analytics():
    st.header("📊 Genre Analytics & Comparison")
    
    available_genres = [
        "rock", "pop", "jazz", "electronic", "hip-hop", "country", 
        "classical", "metal", "indie", "folk", "r-n-b", "dance"
    ]
    
    selected_genres = st.multiselect(
        "Select genres to compare:",
        available_genres,
        default=["rock", "pop", "jazz"]
    )
    
    if len(selected_genres) < 2:
        st.warning("Please select at least 2 genres to compare.")
        return
    
    if st.button("📈 Analyze Genres", type="primary"):
        try:
            params = "&".join([f"genres={genre}" for genre in selected_genres])
            comparison_data = call_api(f"/analytics/compare?{params}")
            
            if comparison_data.get('genres'):
                df = pd.DataFrame(comparison_data['genres'])
            
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_tracks = px.bar(
                        df, 
                        x='genre', 
                        y='track_count',
                        title="📀 Track Count by Genre",
                        color='track_count',
                        color_continuous_scale='blues'
                    )
                    st.plotly_chart(fig_tracks, use_container_width=True)
                
                with col2:
                    fig_pop = px.bar(
                        df, 
                        x='genre', 
                        y='avg_popularity',
                        title="⭐ Average Popularity by Genre",
                        color='avg_popularity',
                        color_continuous_scale='reds'
                    )
                    st.plotly_chart(fig_pop, use_container_width=True)
                
                audio_cols = ['avg_danceability', 'avg_energy', 'avg_valence', 'avg_tempo']
                
                df_norm = df.copy()
                df_norm['avg_tempo_norm'] = df_norm['avg_tempo'] / 243.37  
                heatmap_data = df_norm[['genre'] + ['avg_danceability', 'avg_energy', 'avg_valence', 'avg_tempo_norm']].set_index('genre')
                
                fig_heatmap = px.imshow(
                    heatmap_data.T,
                    title="🎵 Audio Features Heatmap",
                    labels=dict(x="Genre", y="Audio Features", color="Value"),
                    aspect="auto",
                    color_continuous_scale='viridis'
                )
                st.plotly_chart(fig_heatmap, use_container_width=True)
                
                # Scatter plot: Energy vs Danceability
                fig_scatter = px.scatter(
                    df, 
                    x='avg_energy', 
                    y='avg_danceability',
                    size='track_count',
                    color='avg_popularity',
                    hover_name='genre',
                    title="⚡ Energy vs Danceability",
                    labels={'avg_energy': 'Energy', 'avg_danceability': 'Danceability'}
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
                
                # Summary stats table
                st.subheader("📋 Detailed Comparison")
                display_df = df.round(3)
                st.dataframe(display_df, use_container_width=True)
        
        except Exception as e:
            st.error(f"Error analyzing genres: {str(e)}")

def show_artist_rankings():
    st.header("👥 Artist Rankings & Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        genre = st.selectbox(
            "Select Genre:",
            ["rock", "pop", "jazz", "electronic", "hip-hop", "country", "classical", "metal"]
        )
    
    with col2:
        ranking_method = st.selectbox(
            "Ranking Method:",
            ["popularity", "track_count"],
            help="popularity: by average popularity, track_count: by number of tracks"
        )
    
    with col3:
        top_n = st.slider("Top N Artists:", 5, 20, 10)
    
    if st.button("🏆 Get Top Artists", type="primary"):
        try:
            params = {
                "size": top_n,
                "ranking_method": ranking_method,
                "min_tracks": 2
            }
            
            artist_data = call_api(f"/analytics/top-artists/{genre}", params)
            
            if artist_data.get('top_artists'):
                artists_df = pd.DataFrame(artist_data['top_artists'])
                
                st.subheader(f"🎤 Top {genre.title()} Artists")
                
                if ranking_method == "popularity":
                    fig = px.bar(
                        artists_df,
                        x='avg_popularity',
                        y='artist',
                        orientation='h',
                        title=f"Top {genre.title()} Artists by Average Popularity",
                        color='track_count',
                        color_continuous_scale='plasma'
                    )
                else:
                    fig = px.bar(
                        artists_df,
                        x='track_count',
                        y='artist',
                        orientation='h',
                        title=f"Top {genre.title()} Artists by Track Count",
                        color='avg_popularity',
                        color_continuous_scale='plasma'
                    )
                
                fig.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
                
                # Scatter plot: Track Count vs Popularity
                fig_scatter = px.scatter(
                    artists_df,
                    x='track_count',
                    y='avg_popularity',
                    hover_name='artist',
                    size='rank',
                    title="📈 Track Count vs Average Popularity",
                    labels={'track_count': 'Number of Tracks', 'avg_popularity': 'Average Popularity'}
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
                
                # Artists table
                st.dataframe(
                    artists_df[['rank', 'artist', 'track_count', 'avg_popularity']],
                    use_container_width=True,
                    hide_index=True
                )
        
        except Exception as e:
            st.error(f"Error getting artist rankings: {str(e)}")

def show_similarity_analysis():
    st.header("🎯 Music Similarity Analysis")
    
    st.markdown("Enter a track ID to find similar songs based on audio features.")
    
    track_id = st.text_input("🆔 Track ID:", placeholder="Enter track ID...")
    
    col1, col2 = st.columns(2)
    
    with col1:
        similarity_count = st.slider("Number of Similar Tracks:", 5, 20, 10)
    
    if track_id and st.button("🔍 Find Similar Tracks", type="primary"):
        try:
            params = {"size": similarity_count}
            similar_data = call_api(f"/similar/{track_id}", params)
            
            if similar_data.get('results'):
                similar_df = pd.DataFrame(similar_data['results'])
                
                st.subheader("🎵 Similar Tracks Found")
                
                # Similarity scores bar chart
                if 'similarity' in similar_df.columns:
                    fig_sim = px.bar(
                        similar_df.head(10),
                        x='similarity',
                        y='track_name',
                        orientation='h',
                        title="🎯 Similarity Scores",
                        color='similarity',
                        color_continuous_scale='greens'
                    )
                    fig_sim.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig_sim, use_container_width=True)
                
                # Audio features comparison if available
                audio_features = ['energy', 'danceability', 'valence']
                available_features = [f for f in audio_features if f in similar_df.columns]
                
                if available_features:
                    st.subheader("🎼 Audio Features Distribution")
                    
                    fig_features = make_subplots(
                        rows=2, cols=2,
                        subplot_titles=available_features,
                        specs=[[{"type": "histogram"}, {"type": "histogram"}],
                               [{"type": "histogram"}, {"type": "histogram"}]]
                    )
                    
                    for i, feature in enumerate(available_features):
                        row = (i // 2) + 1
                        col = (i % 2) + 1
                        
                        fig_features.add_trace(
                            go.Histogram(x=similar_df[feature], name=feature.title()),
                            row=row, col=col
                        )
                    
                    fig_features.update_layout(height=600, showlegend=False)
                    st.plotly_chart(fig_features, use_container_width=True)
                
                # Similar tracks table
                display_cols = ['track_name', 'artist', 'track_genre', 'popularity']
                if 'similarity' in similar_df.columns:
                    display_cols.append('similarity')
                
                available_cols = [col for col in display_cols if col in similar_df.columns]
                st.dataframe(similar_df[available_cols], use_container_width=True)
            
            else:
                st.info("No similar tracks found.")
        
        except Exception as e:
            st.error(f"Error finding similar tracks: {str(e)}")
    
    with st.expander("ℹ️ How to find Track IDs"):
        st.markdown("""
        **To get track IDs:**
        1. Use the Search & Filter page to find tracks
        2. Look for the `track_id` column in the results
        3. Copy the track ID and paste it here
        
        **Example track IDs to try:**
        - Search for a popular artist first
        - Copy one of their track IDs
        - Use it in this similarity analysis
        """)

if __name__ == "__main__":
    main()