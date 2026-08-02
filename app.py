import base64
import io
import re
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

# 2. Custom CSS & Styling
st.markdown("""
    <style>
    /* Safe top margin clearing Streamlit header */
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

    /* Secondary Buttons */
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

# Session State
if "captured_photos" not in st.session_state:
    st.session_state.captured_photos = []

if "cost_val" not in st.session_state:
    st.session_state.cost_val = 3.0

if "last_processed_ts" not in st.session_state:
    st.session_state.last_processed_ts = None

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

def process_base64_image(raw_input):
    """Safely sanitize, pad, and open incoming base64 camera image payload."""
    b64_str = ""
    ts = None
    
    if isinstance(raw_input, dict):
        val = raw_input.get("value", {})
        if isinstance(val, dict):
            b64_str = str(val.get("image", ""))
            ts = val.get("ts", None)
        elif isinstance(val, str):
            b64_str = val
    elif isinstance(raw_input, str):
        b64_str = raw_input

    # Strip data URL prefix if present
    if "base64," in b64_str:
        b64_str = b64_str.split("base64,")[-1]

    # Clean whitespace & fix base64 padding
    b64_str = re.sub(r'[^A-Za-z0-9+/=]', '', b64_str)
    missing_padding = len(b64_str) % 4
    if missing_padding:
        b64_str += "=" * (4 - missing_padding)

    img_bytes = base64.b64decode(b64_str)
    
    # Process image with PIL
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

# 2. Live Custom Viewfinder Component
st.markdown("**Snap photos of item, tags, or flaws:**")

custom_camera_html = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: transparent; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
        
        .cam-box {
            position: relative;
            width: 100%;
            height: 420px;
            background: #0d1117;
            border-radius: 12px;
            border: 2px solid #008A3C;
            overflow: hidden;
        }
        
        video {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }
        
        .controls {
            position: absolute;
            bottom: 12px;
            left: 0;
            width: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 10px;
            padding: 0 16px;
            z-index: 10;
        }
        
        .snap-btn {
            flex: 1;
            padding: 12px 0;
            background: #FF6600;
            color: #FFFFFF;
            border: none;
            font-size: 1.05rem;
            font-weight: 800;
            border-radius: 8px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .snap-btn:active {
            background: #E05500;
            transform: scale(0.98);
        }
        
        .flip-btn {
            background: rgba(0,0,0,0.65);
            border: 1px solid #008A3C;
            color: #FFF;
            padding: 12px 16px;
            border-radius: 8px;
            font-weight: 700;
            cursor: pointer;
            backdrop-filter: blur(4px);
        }
    </style>
</head>
<body>
    <div class="cam-box">
        <video id="webcam" autoplay playsinline muted></video>
        <div class="controls">
            <button class="snap-btn" onclick="snap()">📷 TAKE PHOTO</button>
            <button class="flip-btn" onclick="toggleCam()">🔄</button>
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
                video: {
                    facingMode: useFront ? "user" : "environment",
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                },
                audio: false
            };
            try {
                currentStream = await navigator.mediaDevices.getUserMedia(constraints);
                document.getElementById('webcam').srcObject = currentStream;
            } catch (err) {
                console.error("Camera access failed:", err);
            }
        }

        function toggleCam() {
            useFront = !useFront;
            startCamera();
        }

        function snap() {
            const video = document.getElementById('webcam');
            const canvas = document.getElementById('canvas');
            if (!video.videoWidth) return;
            
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
            
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: {
                    image: dataUrl,
                    ts: Date.now()
                }
            }, '*');
        }

        startCamera();
    </script>
</body>
</html>
"""

# Render custom component
camera_data = components.html(custom_camera_html, height=440)

# Process photo when snapped
if camera_data:
    try:
        processed_img, clean_b64, raw_bytes, ts = process_base64_image(camera_data)
        
        # Prevent double logging on rerenders
        if ts and ts != st.session_state.last_processed_ts:
            st.session_state.last_processed_ts = ts
            st.session_state.captured_photos.append({
                "img": processed_img,
                "base64": clean_b64,
                "bytes": raw_bytes
            })
            st.rerun()
    except Exception as e:
        # Prevent UI crash and ignore empty frames
        pass

# 3. Gallery Preview & Photo Counter
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
                
                # Format output: Escape dollar signs so Markdown doesn't trigger LaTeX math italics
                formatted_text = message.content[0].text.replace("$", r"\$")

                st.markdown("---")
                st.subheader("📊 FuzzFlips Analysis")
                st.markdown(formatted_text)
                
            except Exception as e:
                st.error(f"Error analyzing images: {e}")
