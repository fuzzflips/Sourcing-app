import base64
import io
import anthropic
from PIL import Image, ImageOps
import streamlit as st
import streamlit.components.v1 as components

# 1. Page Config
st.set_page_config(
    page_title="Flip or Skip | FuzzFlips",
    page_icon="💸",
    layout="wide"
)

# 2. Custom CSS for FuzzFlips Brand Theme
st.markdown("""
    <style>
    /* Generous top padding to clear Streamlit's header navigation */
    .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        padding-top: 4.2rem !important;
    }

    /* Main CTA Button - FuzzFlips Orange */
    div.stButton > button[kind="primary"] {
        background-color: #FF6600 !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 800 !important;
        font-size: 1.2rem !important;
        border-radius: 10px !important;
        padding: 0.7rem 1rem !important;
        box-shadow: 0 4px 10px rgba(255, 102, 0, 0.3) !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #E05500 !important;
    }

    /* Secondary Buttons */
    div.stButton > button[kind="secondary"] {
        border: 2px solid #008A3C !important;
        color: #008A3C !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
    }

    /* Branded Header Title */
    .fuzz-title {
        font-family: 'Impact', 'Arial Black', sans-serif;
        font-style: italic;
        font-size: 2.6rem;
        line-height: 1.1;
        margin-top: 0.2rem;
        margin-bottom: 0px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .fuzz-orange { color: #FF6600; }
    .fuzz-green { color: #008A3C; }
    
    .fuzz-subtitle {
        font-size: 0.95rem;
        color: #888888;
        margin-bottom: 1.0rem;
        font-weight: 500;
    }

    /* Mobile text spacing */
    .stMarkdown p, .stMarkdown li {
        font-size: 0.95rem !important;
        line-height: 1.5 !important;
    }
    </style>
""", unsafe_allow_html=True)

# App Header
st.markdown("""
    <div class="fuzz-title">
        <span class="fuzz-orange">FLIP</span> <span class="fuzz-green">OR SKIP$</span>
    </div>
    <div class="fuzz-subtitle">Powered by FuzzFlips AI Sourcing Companion</div>
""", unsafe_allow_html=True)

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
cost = st.number_input("Purchase Cost ($):", min_value=0.0, value=3.0, step=0.5)

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

# Native Camera Section
st.markdown("**Snap photos of item, tags, or flaws:**")

# Native camera widget via Streamlit camera component with overridden view container
camera_photo = st.camera_input("", key="main_camera")

# Apply target CSS directly to force stream container expand
st.markdown("""
    <style>
    /* Direct override on camera element iframe and video wrapper */
    [data-testid="stCameraInput"] {
        width: 100% !important;
    }
    [data-testid="stCameraInput"] > div {
        width: 100% !important;
    }
    [data-testid="stCameraInput"] iframe {
        width: 100% !important;
        height: 480px !important;
        min-height: 480px !important;
        border-radius: 12px !important;
        border: 2px solid #008A3C !important;
    }
    </style>
""", unsafe_allow_html=True)

# Add snapped photos to gallery
if camera_photo:
    processed_img, base64_str = process_image(camera_photo)
    
    # Avoid duplicate additions from Streamlit rerenders
    if not st.session_state.captured_photos or st.session_state.captured_photos[-1]["bytes"] != camera_photo.getvalue():
        st.session_state.captured_photos.append({
            "img": processed_img,
            "base64": base64_str,
            "bytes": camera_photo.getvalue()
        })

# Display Gallery of Snapped Photos
if st.session_state.captured_photos:
    st.markdown(f"**Snapped Photos ({len(st.session_state.captured_photos)}):**")
    cols = st.columns(min(len(st.session_state.captured_photos), 4))
    
    for idx, photo_data in enumerate(st.session_state.captured_photos):
        with cols[idx % len(cols)]:
            st.image(photo_data["img"], caption=f"Photo {idx+1}", use_container_width=True)
            
    if st.button("🗑️ Clear All Photos", use_container_width=True):
        st.session_state.captured_photos = []
        st.rerun()

st.write("")

# Analyze Button
if st.button("🔍 FLIP OR SKIP?", type="primary", use_container_width=True):
    if not st.session_state.captured_photos:
        st.warning("Please snap at least one photo first.")
    else:
        with st.spinner("Evaluating item potential with FuzzFlips AI..."):
            try:
                content_payload = []
                
                for item in st.session_state.captured_photos:
                    content_payload.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": item["base64"]
                        }
                    })
                
                prompt_text = f"""
                You are the master sourcing advisor for 'Flip or Skip' by FuzzFlips.
                Analyze the provided photo(s) of this resale item.
                The item purchase cost is ${cost:.2f}.
                
                Please structure your response with formatting using these exact section headers:
                
                ### 🏷️ Item Identification
                Brand, model/style, category, era/vintage status, and notable tags/features.
                
                ### 💵 Estimated Resale Value
                Expected resale price range on eBay, Poshmark, Mercari, or Depop.
                
                ### 📈 Projected Net Profit
                Estimated net profit calculation after accounting for purchase cost (${cost:.2f}) and ~20% for platform fees & shipping costs.
                
                ### 🚦 VERDICT: [FLIP, SKIP, or RISKY]
                Start with a bold line: "**VERDICT: [FLIP / SKIP / RISKY]**"
                Followed by a punchy 2-3 sentence explanation on why to buy or pass (considering sell-through speed, demand, and risk).
                """
                
                content_payload.append({
                    "type": "text",
                    "text": prompt_text
                })
                
                message = client.messages.create(
                    model="claude-sonnet-5",
                    max_tokens=1000,
                    messages=[{"role": "user", "content": content_payload}]
                )
                
                # Format output: Escape dollar signs so Markdown doesn't trigger LaTeX math italics
                formatted_text = message.content[0].text.replace("$", r"\$")

                st.markdown("---")
                st.subheader("📊 FuzzFlips Analysis")
                st.markdown(formatted_text)
                
            except Exception as e:
                st.error(f"Error analyzing images: {e}")
