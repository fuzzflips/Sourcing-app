import base64
import io
import re
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

# 2. FuzzFlips Mobile-Optimized CSS
st.markdown("""
    <style>
    /* Safe margin clearing Streamlit top header */
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
        margin-bottom: 1.5rem;
        font-weight: 500;
    }

    /* MASSIVE Purchase Cost UI */
    .cost-label {
        font-size: 1.3rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }
    
    /* Enlarge the number input box */
    div[data-testid="stNumberInput"] input {
        font-size: 2.2rem !important;
        font-weight: 900 !important;
        color: #FF6600 !important;
        height: 4.5rem !important;
        text-align: center !important;
        border-radius: 10px !important;
        border: 2px solid #008A3C !important;
    }

    /* Enlarge the Quick-Adjust Secondary Buttons */
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
        height: 4.5rem !important;
        font-size: 1.4rem !important;
        font-weight: 900 !important;
        border-radius: 10px !important;
        border: 2px solid #008A3C !important;
        background-color: rgba(0, 138, 60, 0.1) !important;
        color: #FFFFFF !important;
        width: 100% !important;
    }
    div[data-testid="stHorizontalBlock"] button[kind="secondary"]:active {
        background-color: #008A3C !important;
    }

    /* Primary CTA Button (FuzzFlips Orange) */
    div.stButton > button[kind="primary"] {
        background-color: #FF6600 !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 800 !important;
        font-size: 1.4rem !important;
        border-radius: 10px !important;
        padding: 1rem !important;
        box-shadow: 0 4px 10px rgba(255, 102, 0, 0.35) !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #E05500 !important;
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

# Initialize Session State
if "captured_photos" not in st.session_state:
    st.session_state.captured_photos = []

if "cost_val" not in st.session_state:
    st.session_state.cost_val = 3.0

if "last_processed_ts" not in st.session_state:
    st.session_state.last_processed_ts = None

# --- 1. JUMBO PURCHASE COST SECTION ---
st.markdown('<div class="cost-label">Purchase Cost ($):</div>', unsafe_allow_html=True)
st.session_state.cost_val = st.number_input(
    "Cost", 
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

# --- 2. THE ULTIMATE FULL-WIDTH CAMERA COMPONENT ---
# We dynamically create a true Streamlit custom component so the button natively talks to Python.
if "cam_component_path" not in st.session_state:
    temp_dir = tempfile.mkdtemp()
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.jsdelivr.net/npm/streamlit-component-lib@1.3.0/dist/streamlit-component-lib.js"></script>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { background: transparent; font-family: -apple-system, sans-serif; overflow: hidden; }
            
            .cam-box {
                position: relative;
                width: 100%;
                height: 420px;
                background: #0d1117;
                border-radius: 12px;
                border: 2px solid #008A3C;
                overflow: hidden;
            }
            
            video { width: 100%; height: 100%; object-fit: cover; display: block; }
            
            .controls {
                position: absolute; bottom: 12px; left: 0; width: 100%;
                display: flex; justify-content: center; align-items: center; gap: 10px; padding: 0 16px; z-index: 10;
            }
            
            .snap-btn {
                flex: 1; padding: 14px 0; background: #FF6600; color: #FFF; border: none; 
                font-size: 1.15rem; font-weight: 800; border-radius: 8px; cursor: pointer; 
                box-shadow: 0 4px 12px rgba(0,0,0,0.5); text-transform: uppercase;
            }
            .snap-btn:active { background: #E05500; transform: scale(0.98); }
            
            .flip-btn {
                background: rgba(0,0,0,0.65); border: 1px solid #008A3C; color: #FFF; 
                padding: 14px 18px; font-size: 1.2rem; border-radius: 8px; font-weight: 700; cursor: pointer;
            }
        </style>
    </head>
    <body>
        <div class="cam-box">
            <video id="webcam" autoplay playsinline muted></video>
            <div class="controls">
                <button class="snap-btn" id="snapBtn">📷 TAKE PHOTO</button>
                <button class="flip-btn" id="flipBtn">🔄</button>
            </div>
            <canvas id="canvas" style="display:none;"></canvas>
        </div>

        <script>
            let currentStream = null;
            let useFront = false;

            async function startCamera() {
                if (currentStream) {
                    currentStream.getTracks().forEach(track => track.stop());
                }
                const constraints = {
                    video: { facingMode: useFront ? "user" : "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
                    audio: false
                };
                try {
                    currentStream = await navigator.mediaDevices.getUserMedia(constraints);
                    document.getElementById('webcam').srcObject = currentStream;
                } catch (err) {
                    console.error("Camera access failed:", err);
                }
            }

            document.getElementById('flipBtn').addEventListener('click', () => {
                useFront = !useFront;
                startCamera();
            });

            document.getElementById('snapBtn').addEventListener('click', () => {
                const video = document.getElementById('webcam');
                const canvas = document.getElementById('canvas');
                if (!video || !video.videoWidth) return;
                
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                
                const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
                
                // Officially tell Streamlit the value changed
                Streamlit.setComponentValue({
                    image: dataUrl,
                    ts: Date.now()
                });
            });

            function onRender(event) {
                Streamlit.setFrameHeight(430);
            }

            Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
            Streamlit.setComponentReady();
            startCamera();
        </script>
    </body>
    </html>
    """
    with open(os.path.join(temp_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_content)
    st.session_state.cam_component_path = temp_dir

# Register and display the true custom component
st.markdown("**Snap photos of item, tags, or flaws:**")
fuzzflips_cam = components.declare_component("fuzzflips_cam", path=st.session_state.cam_component_path)
camera_data = fuzzflips_cam(key="live_cam")

def process_base64_payload(raw_input):
    """Safely decode base64 strings."""
    if not raw_input or not isinstance(raw_input, dict):
        return None, None, None, None
        
    b64_str = raw_input.get("image", "")
    ts = raw_input.get("ts", None)
    
    if "base64," in b64_str:
        b64_str = b64_str.split("base64,")[-1]

    b64_str = re.sub(r'[^A-Za-z0-9+/=]', '', b64_str)
    missing_padding = len(b64_str) % 4
    if missing_padding:
        b64_str += "=" * (4 - missing_padding)

    img_bytes = base64.b64decode(b64_str)
    img = Image.open(io.BytesIO(img_bytes))
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail((1200, 1200))
    
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    bytes_data = buffer.getvalue()
    clean_b64 = base64.b64encode(bytes_data).decode("utf-8")
    return img, clean_b64, bytes_data, ts

# Handle Incoming Photos natively
if camera_data:
    try:
        proc_img, clean_b64, raw_bytes, ts = process_base64_payload(camera_data)
        if proc_img and ts and ts != st.session_state.last_processed_ts:
            st.session_state.last_processed_ts = ts
            st.session_state.captured_photos.append({
                "img": proc_img,
                "base64": clean_b64,
                "bytes": raw_bytes
            })
            st.rerun()
    except Exception as e:
        pass

# --- 3. GALLERY PREVIEW & COUNTER ---
if st.session_state.captured_photos:
    st.markdown(f"**📸 Captured Photos ({len(st.session_state.captured_photos)}):**")
    
    cols = st.columns(min(len(st.session_state.captured_photos), 4))
    for idx, photo_data in enumerate(st.session_state.captured_photos):
        with cols[idx % 4]:
            st.image(photo_data["img"], caption=f"Photo {idx+1}", use_container_width=True)
            
    if st.button("🗑️ Clear All Photos", use_container_width=True):
        st.session_state.captured_photos = []
        st.session_state.last_processed_ts = None
        st.rerun()

st.write("")

# --- 4. MAIN ANALYSIS CTA BUTTON ---
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
                
                formatted_text = message.content[0].text.replace("$", r"\$")

                st.markdown("---")
                st.subheader("📊 FuzzFlips Analysis")
                st.markdown(formatted_text)
                
            except Exception as e:
                st.error(f"Error analyzing images: {e}")
