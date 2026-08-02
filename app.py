import base64
import io
import anthropic
from PIL import Image, ImageOps
import streamlit as st

# 1. Expand layout to wide mode
st.set_page_config(
    page_title="Sourcing Companion", page_icon="🏷️", layout="wide"
)

# 2. Add custom CSS for phone formatting and mobile view
st.markdown(
    """
    <style>
    .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        padding-top: 1rem !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("🏷️ Sourcing Companion")
st.write(
    "Snap item & tag photos to check resale value and get instant recommendations."
)

# Check for API key in secrets
if "ANTHROPIC_API_KEY" not in st.secrets:
    st.error("Please add your ANTHROPIC_API_KEY to Streamlit Secrets.")
    st.stop()

# Initialize Anthropic Client
client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

# Input for Purchase Cost
cost = st.number_input(
    "Purchase Cost ($):", min_value=0.0, value=3.0, step=0.5
)

# Multi-photo upload input
uploaded_files = st.file_uploader(
    "Take/upload photos of item & tags",
    type=["jpg", "png", "jpeg", "webp"],
    accept_multiple_files=True,
    help="On mobile, tap to select or take multiple photos.",
)


def process_image(uploaded_file):
    """Fix EXIF orientation and compress image for API speed."""
    img = Image.open(uploaded_file)

    # Automatically rotate photo right-side up based on phone EXIF metadata
    img = ImageOps.exif_transpose(img)

    # Convert to RGB if in RGBA mode
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Resize long edge to max 1200px to save bandwidth and speed up API response
    img.thumbnail((1200, 1200))

    # Save to buffer
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    bytes_data = buffer.getvalue()

    base64_str = base64.b64encode(bytes_data).decode("utf-8")
    return img, base64_str


# Display upright preview thumbnails
if uploaded_files:
    cols = st.columns(min(len(uploaded_files), 4))
    processed_images = []

    for idx, uploaded_file in enumerate(uploaded_files):
        processed_img, base64_str = process_image(uploaded_file)
        processed_images.append((processed_img, base64_str))

        with cols[idx % len(cols)]:
            st.image(
                processed_img,
                caption=f"Photo {idx + 1}",
                use_container_width=True,
            )

# Analyze Button
if st.button("🔍 Analyze Item", type="primary", use_container_width=True):
    if not uploaded_files:
        st.warning("Please capture or upload at least one photo first.")
    else:
        with st.spinner("Analyzing photos with Claude Vision..."):
            try:
                # Build content array with all processed images
                content_payload = []

                for _, base64_str in processed_images:
                    content_payload.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": base64_str,
                            },
                        }
                    )

                # Append prompt instructions
                prompt_text = f"""
                Analyze the provided photo(s) of this resale item.
                The item purchase cost is ${cost:.2f}.
                
                Please provide:
                1. **Item Identification**: Name, brand, approximate age/era, vintage markers (if any), and notable features/tags.
                2. **Estimated Resale Value**: Expected price range on platforms like eBay, Poshmark, or Mercari.
                3. **Estimated Profit**: Net profit estimate after purchase cost (${cost:.2f}) and typical platform/shipping fees (~20%).
                4. **Buy / Pass Recommendation**: A clear BUY, PASS, or RISKY decision with 2-3 sentence justification.
                """

                content_payload.append({"type": "text", "text": prompt_text})

                # Call Anthropic API
                message = client.messages.create(
                    model="claude-sonnet-5",
                    max_tokens=1000,
                    messages=[{"role": "user", "content": content_payload}],
                )

                # Display Results
                st.markdown("---")
                st.subheader("📊 Resale Analysis")
                st.markdown(message.content[0].text)

            except Exception as e:
                st.error(f"Error analyzing image: {e}")
