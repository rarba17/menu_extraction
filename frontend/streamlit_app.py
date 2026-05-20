# frontend/streamlit_app.py
import streamlit as st
import requests
import json
from PIL import Image
import os

# Configure page
st.set_page_config(
    page_title="Menu Extraction System",
    page_icon="🍽️",
    layout="wide"
)

# API endpoint: read from env var so it works both in Docker (http://backend:8000)
# and local dev (http://localhost:8000) without code changes
API_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

st.title("🍽️ AI-Powered Menu Extraction System")
st.markdown("Upload a restaurant menu (image or PDF) to extract structured data automatically")

# Sidebar for info
with st.sidebar:
    st.header("About")
    st.markdown("""
    This system uses **Google Gemini AI** to intelligently extract menu information.

    **Features:**
    - Extract dish names, prices, descriptions
    - Identify categories, allergens, dietary tags
    - Multi-language support with translation
    - Crop and save food images
    - Structured JSON output

    **Supported formats:**
    - JPG, JPEG, PNG
    - PDF files
    """)

# Main upload area
col1, col2 = st.columns([1, 1])

with col1:
    uploaded_file = st.file_uploader(
        "Choose a menu file",
        type=['jpg', 'jpeg', 'png', 'pdf'],
        help="Upload a restaurant menu image or PDF"
    )

    if uploaded_file is not None:
        # Display file info
        st.success(f"✅ File uploaded: {uploaded_file.name}")

        # Preview image if it's an image file
        if uploaded_file.type in ["image/jpeg", "image/png", "image/jpg"]:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Menu", use_column_width=True)

        # Extract button
        if st.button("🔍 Extract Menu Data", type="primary"):
            with st.spinner("Processing menu with AI..."):
                # Prepare file for API request
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}

                try:
                    # Call backend API
                    response = requests.post(f"{API_URL}/extract-menu", files=files)

                    if response.status_code == 200:
                        result = response.json()

                        if result["success"]:
                            st.success("✅ Extraction completed successfully!")

                            # Display results in tabs
                            tab1, tab2, tab3 = st.tabs(["📊 Structured Data", "📝 Raw JSON", "🖼️ Extracted Images"])

                            with tab1:
                                if result["data"]:
                                    data = result["data"]

                                    # Restaurant info
                                    st.subheader("Restaurant Information")
                                    col_a, col_b = st.columns(2)
                                    with col_a:
                                        st.write(f"**Name:** {data.get('restaurant_name', 'N/A')}")
                                    with col_b:
                                        st.write(f"**Language:** {data.get('menu_language', 'N/A')}")

                                    # Menu items
                                    st.subheader(f"Menu Items ({len(data.get('menu_items', []))})")

                                    for idx, item in enumerate(data.get('menu_items', []), 1):
                                        with st.expander(f"{idx}. {item.get('item_name', 'Unknown')}"):
                                            col_i1, col_i2 = st.columns(2)

                                            with col_i1:
                                                st.write(f"**Description:** {item.get('description', 'N/A')}")
                                                st.write(f"**Category:** {item.get('category', 'N/A')}")
                                                st.write(f"**Price:** {item.get('price', 'N/A')} {item.get('currency', '')}")
                                                st.write(f"**Calories:** {item.get('calories', 'N/A')}")

                                            with col_i2:
                                                if item.get('translated_item_name'):
                                                    st.write(f"**Translated Name:** {item['translated_item_name']}")
                                                if item.get('allergens'):
                                                    st.write(f"**Allergens:** {', '.join(item['allergens'])}")
                                                if item.get('dietary_tags'):
                                                    st.write(f"**Dietary Tags:** {', '.join(item['dietary_tags'])}")

                                            if item.get('image_path') and os.path.exists(item['image_path']):
                                                st.image(item['image_path'], caption="Dish Image", width=200)

                            with tab2:
                                st.json(result["data"])

                            with tab3:
                                # Display cropped images from output directory
                                if os.path.exists("outputs"):
                                    images = [f for f in os.listdir("outputs") if f.startswith("cropped_")]
                                    if images:
                                        for img_file in images:
                                            img_path = os.path.join("outputs", img_file)
                                            st.image(img_path, caption=img_file, width=200)
                                    else:
                                        st.info("No food images were detected/cropped from this menu")

                            # Show processing time
                            st.caption(f"⏱️ Processing time: {result.get('processing_time', 0):.2f} seconds")

                        else:
                            st.error(f"Extraction failed: {result.get('error', 'Unknown error')}")

                    else:
                        st.error(f"API Error: {response.status_code} - {response.text}")

                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to backend API. Please ensure the FastAPI server is running on port 8000")
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")

with col2:
    st.markdown("### 📋 Instructions")
    st.markdown("""
    1. **Upload** a menu image or PDF using the file uploader
    2. Click **'Extract Menu Data'** to start AI processing
    3. View results in three tabs:
       - Structured Data: Formatted view of extracted information
       - Raw JSON: Complete structured output
       - Extracted Images: Cropped food images (if detected)

    **Tips:**
    - Clear, well-lit images work best
    - PDFs with selectable text are ideal
    - The AI works with multiple languages
    - Processing takes 5-15 seconds depending on menu size
    """)

# Footer
st.markdown("---")
st.markdown("Built with FastAPI, Streamlit, and Google Gemini AI")