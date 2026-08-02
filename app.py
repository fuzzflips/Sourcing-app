import base64
import io
import os
import tempfile
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

# Initialize session state gallery and cost
if "captured_photos" not in st.session_state:
    st.session_state.captured_photos = []

if "item_cost" not in st.session_state:
    st.session_state.item_cost = 3.00

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

# --- TRUE BIDIRECTIONAL HTML5 CAMERA COMPONENT SETUP ---
@st.cache_resource
def get_camera_component():
    """Builds a temporary real Streamlit component to guarantee 2-way image transfer."""
    temp_dir = os.path.join(tempfile.gettempdir(), "fuzzflips_cam")
    os.makedirs(temp_dir, exist_ok=True)
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <!-- Load Streamlit's official communication library -->
        <script src="https://unpkg.com/streamlit-component-lib@1.3.0/dist/streamlit-component-lib.js"></script>
        <style>
            * { box-sizing: border-box; }
            body { margin: 0; padding: 0; background-color: #0E1117; display: flex; flex-direction: column; align-items: center; font-family: sans-serif; }
            .cam-container { position: relative; width: 100%; height: 420px; background: #000; border-radius: 12px; overflow: hidden; border: 2px solid #008A3C; }
            video { width: 100%; height: 100%; object-fit: cover; }
            canvas { display: none; }
            .snap-btn { margin-top: 10px; width: 100%; background-color: #FF6600; color: white; border: none; padding: 16px; font-size: 1.2rem; font-weight: 800; border-radius: 12px; cursor: pointer; box-shadow: 0 4px 10px rgba(255, 102, 0, 0.3); touch-action: manipulation; }
            .snap-btn:active { background-color: #E05500; transform: scale(0.98); }
        </style>
    </head>
    <body>
        <div class="cam-container">
            <video id="video" autoplay playsinline muted></video>
        </div>
        <button class="snap-btn" id="snap" type="button">📸 TAKE PHOTO</button>
        <canvas id="canvas"></canvas>

        <script>
            // 1. Initialize Streamlit Connection
            function onRender(event) {
                Streamlit.setFrameHeight(500);
            }
            Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
            Streamlit.setComponentReady();

            // 2. Setup Camera
            const video = document.getElementById('video');
            const canvas = document.getElementById('canvas');
            const snapButton = document.getElementById('snap');

            navigator.mediaDevices.getUserMedia({
                video: { facingMode: { ideal: "environment" } },
                audio: false
            }).then(stream => {
                video.srcObject = stream;
            }).catch(err => {
                console.error("Camera access error:", err);
            });

            // 3. Snap and Send Data
            snapButton.addEventListener('click', (e) => {
                e.preventDefault();
                canvas.width = video.videoWidth || 1280;
                canvas.height = video.videoHeight || 1280;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                
                const dataURL = canvas.toDataURL('image/jpeg', 0.85);
                
                // This officially pushes the image back to Python
                Streamlit.setComponentValue(dataURL);
            });
        </script>
    </body>
    </html>
    """
    
    # Write the component out
    with open(os.path.join(temp_dir, "index.html"), "w") as f:
        f.write(html_content)
        
    return components.declare_component("fuzzflips_cam", path=temp_dir)

# Initialize the custom camera
fuzzflips_camera = get_camera_component()

st.markdown('<div class="fuzz-label">Snap photos of item, tags, or flaws:</div>', unsafe_allow_html=True)

# Render it and capture the returned image base64!
camera_data = fuzzflips_camera(key="main_cam")

# Process photo when snapped
if camera_data:
    try:
        header, encoded = camera_data.split(",", 1)
        binary_data = base64.b64decode(encoded)
        
        img = Image.open(io.BytesIO(binary_data))
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail((1200, 1200))
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        processed_bytes = buffer.getvalue()
        base64_str = base64.b64encode(processed_bytes).decode("utf-8")
        
        # Check against last photo to avoid duplicate rerender additions
        if not st.session_state.captured_photos or st.session_state.captured_photos[-1]["bytes"] != processed_bytes:
            st.session_state.captured_photos.append({
                "img": img,
                "base64": base64_str,
                "bytes": processed_bytes
            })
            st.rerun()
    except Exception as e:
        pass

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
