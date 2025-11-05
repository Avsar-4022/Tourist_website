import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import os
from geopy.geocoders import Nominatim 

# Set page configuration
st.set_page_config(
    page_title="Explore India - TouristDestinations",
    page_icon="🌍",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stApp {
        background-color: #f5f5f5;
    }
    .destination-card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
    }
    .stTextInput>div>div>input {
        border-radius: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Load data
@st.cache_data
def load_data():
    """
    Robust CSV loader:
    - Accepts common header variations (Name, destination, Destination, lat, lng, etc.)
    - Strips BOM, trims whitespace, normalizes headers to lowercase with underscores
    - Attempts to map synonyms to the standard columns used in the app:
      name, state, description, popular_attractions, image_url, latitude, longitude
    - Shows an error with available columns if required columns are missing
    """
    try:
        # Try common encodings and strip BOM if present
        df = pd.read_csv('destinations.csv', encoding='utf-8-sig')

        # Normalize column names: strip, lower, replace spaces with _
        orig_cols = list(df.columns)
        norm_cols = [str(c).strip().lower().replace(' ', '_') for c in orig_cols]
        df.rename(columns=dict(zip(orig_cols, norm_cols)), inplace=True)

        # Synonyms for common alternate headers
        synonyms = {
            'name': ['name', 'destination', 'place', 'title', 'location'],
            'state': ['state', 'region', 'province'],
            'description': ['description', 'desc', 'details', 'about'],
            'popular_attractions': ['popular_attractions', 'attractions', 'popular_attraction', 'attraction'],
            'image_url': ['image_url', 'image', 'image_link', 'imageurl', 'photo', 'photo_url'],
            'latitude': ['latitude', 'lat'],
            'longitude': ['longitude', 'lon', 'long', 'lng']
        }

        # Find and rename columns to the canonical names used in the app
        found = {}
        for canonical, options in synonyms.items():
            for opt in options:
                if opt in df.columns:
                    found[canonical] = opt
                    break

        # Rename any found synonym column to the canonical name
        rename_map = {found[k]: k for k in found}
        if rename_map:
            df.rename(columns=rename_map, inplace=True)

        # Required columns for normal operation
        required_columns = ['name', 'state', 'description', 'popular_attractions', 'image_url']
        missing = [c for c in required_columns if c not in df.columns]

        if missing:
            # Give a helpful error message listing available columns so the user can fix CSV
            st.error(
                "Error: Required column(s) not found in CSV file: "
                f"{missing}. Available columns: {', '.join(df.columns)}. "
                "You can either rename your CSV headers to include these or use the app's expected names."
            )
            return None

        # Drop rows missing essential info
        df = df.dropna(subset=['name', 'state'])

        # Convert lat/lon to numeric if present
        for coord in ('latitude', 'longitude'):
            if coord in df.columns:
                df[coord] = pd.to_numeric(df[coord], errors='coerce')

        return df

    except FileNotFoundError:
        st.error("destinations.csv not found. Please place destinations.csv in the app directory.")
        return None
    except pd.errors.EmptyDataError:
        st.error("destinations.csv is empty or invalid. Please check the file.")
        return None
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def main():
    st.title("🌍 Explore India - TouristDestinations")
    st.write("Discover the most amazing places to visit in India")
    
    # Load data
    df = load_data()
    if df is None:
        st.warning("No data found. Please ensure destinations.csv exists with the required columns.")
        return
    
    # Sidebar for filters
    st.sidebar.header("🔍 Filters")
    
    # Universal search
    search_query = st.sidebar.text_input("Search destinations...")
    
    # State filter
    states = ['All'] + sorted(df['state'].unique().tolist())
    selected_state = st.sidebar.selectbox("Select State", states)
    
    # Apply filters
    filtered_df = df.copy()
    
    if search_query:
        mask = (df['name'].str.contains(search_query, case=False, na=False)) | 
               (df['description'].str.contains(search_query, case=False, na=False)) | 
               (df['popular_attractions'].str.contains(search_query, case=False, na=False))
        filtered_df = filtered_df[mask]
    
    if selected_state != 'All':
        filtered_df = filtered_df[filtered_df['state'] == selected_state]
    
    # Display results
    st.header(f"🗺️ {len(filtered_df)} Destinations Found")
    
    # Create two columns for layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Display map if coordinates are available
        if 'latitude' in df.columns and 'longitude' in df.columns:
            st.subheader("Map View")
            if not filtered_df.empty:
                # Create a map centered on India
                m = folium.Map(location=[20.5937, 78.9629], zoom_start=5)
                
                # Add markers for each destination
                for idx, row in filtered_df.iterrows():
                    if pd.notnull(row.get('latitude')) and pd.notnull(row.get('longitude')):
                        folium.Marker(
                            [row['latitude'], row['longitude']],
                            popup=row['name'],
                            tooltip=row['name']
                        ).add_to(m)
                
                folium_static(m, width=700, height=400)
    
    with col2:
        # Display filters summary
        st.subheader("🔍 Current Filters")
        st.write(f"State: **{selected_state if selected_state != 'All' else 'All States'}**")
        if search_query:
            st.write(f"Search: **{search_query}**")
    
    # Display destination cards
    st.subheader("🏞️ Destinations")
    
    if filtered_df.empty:
        st.warning("No destinations found matching your criteria. Try adjusting your filters.")
    else:
        for idx, row in filtered_df.iterrows():
            with st.expander(f"{row['name']}, {row['state']}", expanded=True):
                c1, c2 = st.columns([1, 2])
                
                with c1:
                    # Use a placeholder image if image_url is missing or invalid
                    img = row.get('image_url') if pd.notnull(row.get('image_url')) else None
                    if img:
                        st.image(img, use_column_width=True, caption=row['name'])
                    else:
                        st.text("No image available")
                
                with c2:
                    st.write(f"**State:** {row['state']}\n")
                    st.write(f"**Description:** {row['description']}\n")
                    if 'popular_attractions' in row and pd.notnull(row['popular_attractions']):
                        st.write("**Popular Attractions:**")
                        attractions = [a.strip() for a in str(row['popular_attractions']).split(',')]
                        for attraction in attractions:
                            st.write(f"- {attraction}")
                    
                    # Add a button to view on map (example)
                    if 'latitude' in row and 'longitude' in row and pd.notnull(row['latitude']) and pd.notnull(row['longitude']):
                        st.button(
                            f"View on Map", 
                            key=f"btn_{idx}",
                            on_click=None,
                            help=f"Show {row['name']} on the map"
                        )

if __name__ == "__main__":
    main()