import base64
import io
import anthropic
from PIL import Image, ImageOps
import streamlit as st

# 1. Page Config
st.set_page_config(
    page_title="Flip or Skip | FuzzFlips",
    page_icon="💸",
    layout="wide"
)

# 2. Custom CSS for FuzzFlips Theme & Touch Controls
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
        border-radius: 12px !important;
        padding: 0.8rem 1rem !important;
        box-shadow: 0 4px 12px rgba(255, 102, 0, 0.4) !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #E05500 !important;
    }

    /* Secondary Buttons / Step Buttons */
    div.stButton > button[kind="secondary"] {
        border: 2px solid #008A3C !important;
        color: #008A3C !important;
        font-weight: 800 !important;
        font-size: 1.1rem !important;
        border-radius: 10px !important;
        padding: 0.5rem !important;
    }

    /* Target direct number input box for large font touch editing */
    div[data-testid="stNumberInput"] input {
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        text-align: center !important;
        color: #FFFFFF !important;
        background-color: #1E1E1E !important;
        border: 2px solid #FF6600 !important;
        border-radius: 12px !important;
        padding: 8px !important;
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

    /* Section Labels */
    .fuzz-label {
        font-size: 1.05rem;
        font-weight: 700;
        color: #FFFFFF;
        margin-bottom: 0.4rem;
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

# Initialize session states
if "captured_photos" not in st.session_state:
    st.session_state.captured_photos = []

if "item_cost" not in st.session_state:
    st.session_state.item_cost = 3.00

if "camera_key" not in st.session_state:
    st.session_state.camera_key = 0

# --- VERTICALLY STACKED COST CONTROLLER ---
st.markdown('<div class="fuzz-label">Purchase Cost ($):</div>', unsafe_allow_html=True)

# 1. Plus $1.00 Button on top
if st.button("➕ $1.00", use_container_width=True, key="cost_plus"):
    st.session_state.item_cost += 1.00
    st.rerun()

# 2. Clickable/Editable Number Field in center
new_cost = st.number_input(
    label="cost_input_field",
    label_visibility="collapsed",
    min_value=0.0,
    value=float(st.session_state.item_cost),
    step=1.00,
    format="%.2f"
)

# Update state if edited manually via keyboard input
if new_cost != st.session_state.item_cost:
    st.session_state.item_cost = new_cost

# 3. Minus $1.00 Button on bottom
if st.button("➖ $1.00", use_container_width=True, key="cost_minus"):
    st.session_state.item_cost = max(0.0, st.session_state.item_cost - 1.00)
    st.rerun()

cost = st.session_state.item_cost
st.write("")

# --- MULTI-PHOTO CAMERA FEED WITH AUTO-RESET KEY ---
st.markdown('<div class="fuzz-label">Snap photos of item, tags, or flaws:</div>', unsafe_allow_html=True)

st.markdown("""
    <style>
    [data-testid="stCameraInput"] {
        width: 100% !important;
    }
    [data-testid="stCameraInput"] > div {
        width: 100% !important;
    }
    [data-testid="stCameraInput"] iframe {
        width: 100% !important;
        border-radius: 12px !important;
        border: 2px solid #008A3C !important;
    }
    </style>
""", unsafe_allow_html=True)

# Dynamic camera input key allows instant resetting for multiple snaps
camera_photo = st.camera_input("", key=f"fuzz_cam_{st.session_state.camera_key}")

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
    return img, base64_str, bytes_data

# When a photo is taken, save it and immediately reset the camera key
if camera_photo:
    processed_img, base64_str, bytes_val = process_image(camera_photo)
    
    st.session_state.captured_photos.append({
        "img": processed_img,
        "base64": base64_str,
        "bytes": bytes_val
    })
    
    # Increment camera key to automatically re-open live camera stream
    st.session_state.camera_key += 1
    st.rerun()

# Display Gallery of Snapped Photos
if st.session_state.captured_photos:
    st.markdown(f"**Snapped Photos ({len(st.session_state.captured_photos)}):**")
    cols = st.columns(min(len(st.session_state.captured_photos), 4))
    
    for idx, photo_data in enumerate(st.session_state.captured_photos):
        with cols[idx % len(cols)]:
            st.image(photo_data["img"], caption=f"Photo {idx+1}", use_container_width=True)
            
    if st.button("🗑️ Clear All Photos", use_container_width=True):
        st.session_state.captured_photos = []
        st.session_state.camera_key += 1
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
