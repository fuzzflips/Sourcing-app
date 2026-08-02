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

# 2. Complete Custom Styling (FuzzFlips Brand Theme + Full Width Camera)
st.markdown("""
    <style>
    /* Safe top margin clearing Streamlit's top nav header */
    .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        padding-top: 4.8rem !important;
    }
    
    /* Branded Header Title */
    .fuzz-title {
        font-family: 'Impact', 'Arial Black', sans-serif;
        font-style: italic;
        font-size: 2.5rem;
        line-height: 1.1;
        margin-top: 0.2rem;
        margin-bottom: 2px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .fuzz-orange { color: #FF6600; }
    .fuzz-green { color: #008A3C; }
    
    .fuzz-subtitle {
        font-size: 0.9rem;
        color: #888888;
        margin-bottom: 1.2rem;
        font-weight: 500;
    }

    /* Target Camera Input Container to Stretch Edge to Edge */
    div[data-testid="stCameraInput"] {
        width: 100% !important;
        border-radius: 12px !important;
        border: 2px solid #008A3C !important;
        overflow: hidden !important;
        background-color: #0d1117 !important;
    }

    div[data-testid="stCameraInput"] > div {
        width: 100% !important;
    }

    /* Stretch the inner video frame using a CSS transform zoom trick */
    div[data-testid="stCameraInput"] iframe {
        width: 100% !important;
        height: 420px !important;
    }

    /* Primary CTA Button (FuzzFlips Orange) */
    div.stButton > button[kind="primary"] {
        background-color: #FF6600 !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 800 !important;
        font-size: 1.2rem !important;
        border-radius: 10px !important;
        padding: 0.75rem 1rem !important;
        box-shadow: 0 4px 10px rgba(255, 102, 0, 0.35) !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #E05500 !important;
    }

    /* Secondary Quick-Adjust & Action Buttons */
    div.stButton > button[kind="secondary"] {
        border: 1px solid #008A3C !important;
        color: #008A3C !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        background-color: rgba(0, 138, 60, 0.05) !important;
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

# Check API Key
if "ANTHROPIC_API_KEY" not in st.secrets:
    st.error("Please add your ANTHROPIC_API_KEY to Streamlit Secrets.")
    st.stop()

client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

# Session State Initializations
if "captured_photos" not in st.session_state:
    st.session_state.captured_photos = []

if "cost_val" not in st.session_state:
    st.session_state.cost_val = 3.0

# 1. Purchase Cost Section
st.markdown("**Purchase Cost ($):**")
st.session_state.cost_val = st.number_input(
    "Purchase Cost ($):", 
    min_value=0.0, 
    value=st.session_state.cost_val, 
    step=0.5, 
    label_visibility="collapsed"
)

btn_col1, btn_col2 = st.columns(2)
with btn_col1:
    if st.button("➕ $1.00", use_container_width=True):
        st.session_state.cost_val += 1.0
        st.rerun()
with btn_col2:
    if st.button("➖ $1.00", use_container_width=True):
        st.session_state.cost_val = max(0.0, st.session_state.cost_val - 1.0)
        st.rerun()

st.write("")

def process_image(img_file):
    """Auto-orient and compress photo directly."""
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

# 2. Camera Input Section (Native Streamlit Camera Input)
st.markdown("**Snap photos of item, tags, or flaws:**")
camera_photo = st.camera_input("", label_visibility="collapsed", key="live_cam")

# Add snapped photos to gallery
if camera_photo:
    processed_img, base64_str = process_image(camera_photo)
    
    # Check duplicate entry on rerun
    if not st.session_state.captured_photos or st.session_state.captured_photos[-1]["bytes"] != camera_photo.getvalue():
        st.session_state.captured_photos.append({
            "img": processed_img,
            "base64": base64_str,
            "bytes": camera_photo.getvalue()
        })

# 3. Photo Gallery Preview & Counter
if st.session_state.captured_photos:
    st.markdown(f"**📸 Captured Photos ({len(st.session_state.captured_photos)}):**")
    
    cols = st.columns(min(len(st.session_state.captured_photos), 4))
    for idx, photo_data in enumerate(st.session_state.captured_photos):
        with cols[idx % 4]:
            st.image(photo_data["img"], caption=f"Photo {idx+1}", use_container_width=True)
            
    if st.button("🗑️ Clear All Photos", use_container_width=True):
        st.session_state.captured_photos = []
        st.rerun()

st.write("")

# 4. Main Analysis CTA Button
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
                The item purchase cost is ${st.session_state.cost_val:.2f}.
                
                Please structure your response with formatting using these exact section headers:
                
                ### 🏷️ Item Identification
                Brand, model/style, category, era/vintage status, and notable tags/features.
                
                ### 💵 Estimated Resale Value
                Expected resale price range on eBay, Poshmark, Mercari, or Depop.
                
                ### 📈 Projected Net Profit
                Estimated net profit calculation after accounting for purchase cost (${st.session_state.cost_val:.2f}) and ~20% for platform fees & shipping costs.
                
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
                
                # Escape dollar signs to avoid Streamlit LaTeX italicization bug
                formatted_text = message.content[0].text.replace("$", r"\$")

                st.markdown("---")
                st.subheader("📊 FuzzFlips Analysis")
                st.markdown(formatted_text)
                
            except Exception as e:
                st.error(f"Error analyzing images: {e}")
