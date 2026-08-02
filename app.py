import base64
import anthropic
import streamlit as st

# 1. Expand layout to wide mode
st.set_page_config(
    page_title="Sourcing Companion", page_icon="🏷️", layout="wide"
)

# 2. Add custom CSS for phone formatting and padded mobile view
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
st.write("Snap item & tag photos to check resale value and get instant recommendations.")

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
    help="On mobile, tap to take multiple photos using your camera or gallery.",
)

# Display preview thumbnails of captured photos
if uploaded_files:
    cols = st.columns(min(len(uploaded_files), 4))
    for idx, uploaded_file in enumerate(uploaded_files):
        with cols[idx % len(cols)]:
            st.image(
                uploaded_file,
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
                # Build content array with all uploaded images
                content_payload = []

                for uploaded_file in uploaded_files:
                    bytes_data = uploaded_file.getvalue()
                    base64_image = base64.b64encode(bytes_data).decode("utf-8")

                    # Map media type for API
                    mime_type = uploaded_file.type
                    if mime_type not in [
                        "image/jpeg",
                        "image/png",
                        "image/webp",
                        "image/gif",
                    ]:
                        mime_type = "image/jpeg"

                    content_payload.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": base64_image,
                            },
                        }
                    )

                # Append system prompt instructions as the text portion
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
