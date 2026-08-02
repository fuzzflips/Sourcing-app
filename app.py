import base64
import io
import anthropic
from PIL import Image, ImageOps
import streamlit as st

# 1. Expand layout to wide mode
st.set_page_config(
    page_title="Sourcing Companion", page_icon="🏷️", layout="wide"
)

# 2. Mobile styling CSS
st.markdown(
    """
    <style>
    .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        padding-top: 1rem !important;
    }
    div[data-testid="stCameraInput"] video {
        min-height: 380px !important;
        object-fit: cover !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("🏷️ Sourcing Companion")

# Check for API key in secrets
if "ANTHROPIC_API_KEY" not in st.secrets:
    st.error("Please add your ANTHROPIC_API_KEY to Streamlit Secrets.")
    st.stop()

# Initialize Anthropic Client
client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

# Initialize session state gallery for photos
if "captured_photos" not in st.session_state:
    st.session_state.captured_photos = []

# Input for Purchase Cost
cost = st.number_input(
    "Purchase Cost ($):", min_value=0.0, value=3.0, step=0.5
)


def process_image(img_file):
    """Auto-orient and compress photos."""
    img = Image.open(img_file)
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail((1200, 1200))

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    bytes_data = buffer.getvalue()
    base64_str = base64.b64encode(bytes_data).decode("utf-8")
    return img, base64_str


# In-app live camera feed
camera_photo = st.camera_input("Take a photo of item or tag")

# Automatically add snapped photos to session state gallery
if camera_photo:
    processed_img, base64_str = process_image(camera_photo)

    # Avoid duplicate additions from Streamlit rerenders
    if (
        not st.session_state.captured_photos
        or st.session_state.captured_photos[-1]["bytes"]
        != camera_photo.getvalue()
    ):
        st.session_state.captured_photos.append(
            {
                "img": processed_img,
                "base64": base64_str,
                "bytes": camera_photo.getvalue(),
            }
        )

# Display Gallery of Snapped Photos
if st.session_state.captured_photos:
    st.write(f"**Photos Snapped ({len(st.session_state.captured_photos)}):**")
    cols = st.columns(min(len(st.session_state.captured_photos), 4))

    for idx, photo_data in enumerate(st.session_state.captured_photos):
        with cols[idx % len(cols)]:
            st.image(
                photo_data["img"],
                caption=f"Photo {idx + 1}",
                use_container_width=True,
            )

    if st.button("🗑️ Clear All Photos", use_container_width=True):
        st.session_state.captured_photos = []
        st.rerun()

# Analyze Button
if st.button(
    "🔍 Analyze All Photos", type="primary", use_container_width=True
):
    if not st.session_state.captured_photos:
        st.warning("Please snap at least one photo first.")
    else:
        with st.spinner("Analyzing photos with Claude Vision..."):
            try:
                content_payload = []

                for item in st.session_state.captured_photos:
                    content_payload.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": item["base64"],
                            },
                        }
                    )

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

                message = client.messages.create(
                    model="claude-sonnet-5",
                    max_tokens=1000,
                    messages=[{"role": "user", "content": content_payload}],
                )

                st.markdown("---")
                st.subheader("📊 Resale Analysis")
                st.markdown(message.content[0].text)

            except Exception as e:
                st.error(f"Error analyzing images: {e}")
