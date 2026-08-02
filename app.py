import base64
import io
import json
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

def process_image_bytes(img_bytes):
    """Auto-orient and compress raw image bytes."""
    img = Image.open(io.BytesIO(img_bytes))
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail((1200, 1200))
    
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    bytes_data = buffer.getvalue()
    base64_str = base64.b64encode(bytes_data).decode("utf-8")
    return img, base64_str

# Camera Label
st.markdown("**Snap photos of item, tags, or flaws:**")

# HTML5 Full-Width Native Viewfinder Component
camera_html = """
<!DOCTYPE html>
<html>
<head>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: transparent; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
        
        .cam-wrapper {
            position: relative;
            width: 100%;
            height: 480px;
            background: #111;
            border-radius: 12px;
            border: 2px solid #008A3C;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        
        video {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .snap-btn {
            position: absolute;
            bottom: 16px;
            left: 50%;
            transform: translateX(-50%);
            width: 80%;
            padding: 12px 0;
            background: rgba(0, 0, 0, 0.75);
            border: 2px solid #FF6600;
            color: #FFFFFF;
            font-size: 1rem;
            font-weight: 700;
            border-radius: 8px;
            cursor: pointer;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            backdrop-filter: blur(4px);
        }
        
        .snap-btn:active {
            background: #FF6600;
        }
        
        .flip-cam {
            position: absolute;
            top: 12px;
            right: 12px;
            background: rgba(0,0,0,0.6);
            border: 1px solid #888;
            color: #fff;
            padding: 6px 10px;
            border-radius: 6px;
            font-size: 0.8rem;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="cam-wrapper">
        <video id="video" autoplay playsinline muted></video>
        <button class="flip-cam" onclick="toggleCamera()">🔄 Flip</button>
        <button class="snap-btn" onclick="takeSnapshot()">📷 TAKE PHOTO</button>
        <canvas id="canvas" style="display:none;"></canvas>
    </div>

    <script>
        let currentStream = null;
        let useFront = false;

        async function initCamera() {
            if (currentStream) {
                currentStream.getTracks().forEach(track => track.stop());
            }
            const constraints = {
                video: {
                    facingMode: useFront ? "user" : "environment",
                    width: { ideal: 1280 },
                    height: { ideal: 1600 }
                }
            };
            try {
                currentStream = await navigator.mediaDevices.getUserMedia(constraints);
                document.getElementById('video').srcObject = currentStream;
            } catch (err) {
                console.error("Camera access error:", err);
            }
        }

        function toggleCamera() {
            useFront = !useFront;
            initCamera();
        }

        function takeSnapshot() {
            const video = document.getElementById('video');
            const canvas = document.getElementById('canvas');
            if (!video.videoWidth) return;
            
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
            
            // Send back to Streamlit via input event trick
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: dataUrl
            }, '*');
        }

        initCamera();
    </script>
</body>
</html>
"""

# Native Streamlit Fallback + Custom Viewfinder component
captured_base64 = components.html(camera_html, height=500)

# Alternative standard fallback camera input if HTML5 media stream fails
with st.expander("Having trouble with camera preview? Click here for standard camera"):
    fallback_photo = st.camera_input("Standard Camera")
    if fallback_photo:
        processed_img, base64_str = process_image_bytes(fallback_photo.getvalue())
        if not st.session_state.captured_photos or st.session_state.captured_photos[-1]["bytes"] != fallback_photo.getvalue():
            st.session_state.captured_photos.append({
                "img": processed_img,
                "base64": base64_str,
                "bytes": fallback_photo.getvalue()
            })
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
