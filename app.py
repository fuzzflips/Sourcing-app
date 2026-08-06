import base64
import io
import re
import datetime
import anthropic
from PIL import Image, ImageOps
import streamlit as st
from supabase import create_client, Client

# 1. Page Config
st.set_page_config(
    page_title="Flip or Skip | FuzzFlips",
    page_icon="💸",
    layout="wide"
)

# 2. Initialize Supabase
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Database Connection Error: {str(e)}")
    st.stop()

# 3. Aggressive Mobile-Optimized CSS
st.markdown("""
    <style>
    .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        padding-top: 4.8rem !important;
    }
    
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

    .cost-label {
        font-size: 1.3rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }
    
    div[data-testid="stNumberInput"] input {
        font-size: 2.2rem !important;
        font-weight: 900 !important;
        color: #FF6600 !important;
        height: 4.5rem !important;
        text-align: center !important;
        border-radius: 10px !important;
        border: 2px solid #008A3C !important;
    }

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

    [data-testid="stCameraInput"] {
        width: 100% !important;
        background-color: #0d1117 !important;
        border-radius: 12px !important;
        border: 2px solid #008A3C !important;
        overflow: hidden !important;
        padding: 0 !important;
    }
    
    [data-testid="stCameraInput"] video {
        width: 100vw !important;
        min-height: 450px !important;
        object-fit: cover !important; 
    }
    
    [data-testid="stCameraInput"] button {
        background-color: #FF6600 !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 800 !important;
        font-size: 1.2rem !important;
        border-radius: 0px 0px 10px 10px !important;
        padding: 1rem !important;
        width: 100% !important;
        text-transform: uppercase !important;
    }
    [data-testid="stCameraInput"] button:hover {
        background-color: #E05500 !important;
    }

    div.stButton > button[kind="primary"] {
        background-color: #FF6600 !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 800 !important;
        font-size: 1.4rem !important;
        border-radius: 10px !important;
        padding: 1rem !important;
        box-shadow: 0 4px 10px rgba(255, 102, 0, 0.35) !important;
        margin-top: 10px !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #E05500 !important;
    }
    </style>
""", unsafe_allow_html=True)

# 4. Session State Management
if 'user' not in st.session_state:
    st.session_state.user = None
if "captured_photos" not in st.session_state:
    st.session_state.captured_photos = []
if "cost_val" not in st.session_state:
    st.session_state.cost_val = 3.0
if "scan_history" not in st.session_state:
    st.session_state.scan_history = []


# ==========================================
# AUTHENTICATION UI ROUTING
# ==========================================
if st.session_state.user is None:
    st.markdown("""
        <div class="fuzz-title" style="text-align: center; margin-top: 2rem;">
            <span class="fuzz-orange">FLIP</span> <span class="fuzz-green">OR</span> <span class="fuzz-orange">SKIP</span>
        </div>
        <div class="fuzz-subtitle" style="text-align: center;">Powered by FuzzFlips AI</div>
    """, unsafe_allow_html=True)
    
    st.write("---")
    
    auth_mode = st.radio("Choose Action", ["Login", "Sign Up"], horizontal=True, label_visibility="collapsed")
    
    email = st.text_input("Email Address")
    password = st.text_input("Password", type="password")
    
    if auth_mode == "Login":
        if st.button("Log In", type="primary", use_container_width=True):
            try:
                response = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = response.user
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {str(e)}")
                
    else:
        if st.button("Create Account", type="primary", use_container_width=True):
            try:
                response = supabase.auth.sign_up({"email": email, "password": password})
                st.success("Account created! You can now log in.")
            except Exception as e:
                st.error(f"Signup failed: {str(e)}")

# ==========================================
# MAIN APP UI (ONLY SHOWS IF LOGGED IN)
# ==========================================
else:
    # App Header
    st.markdown("""
        <div class="fuzz-title">
            <span class="fuzz-orange">FLIP</span> <span class="fuzz-green">OR</span> <span class="fuzz-orange">SKIP</span>
        </div>
        <div class="fuzz-subtitle">Powered by FuzzFlips AI Sourcing Companion</div>
    """, unsafe_allow_html=True)

    # Logout Button
    if st.button("Logout", size="small"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.captured_photos = []
        st.session_state.scan_history = []
        st.rerun()

    # Check API Key
    if "ANTHROPIC_API_KEY" not in st.secrets:
        st.error("Please add your ANTHROPIC_API_KEY to Streamlit Secrets.")
        st.stop()

    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

    # SESSION HISTORY DROPDOWN
    if st.session_state.scan_history:
        with st.expander(f"📚 Session History ({len(st.session_state.scan_history)} items)"):
            history_options = [scan["label"] for scan in reversed(st.session_state.scan_history)]
            selected_history = st.selectbox("Previous Scans:", history_options, label_visibility="collapsed")
            
            if selected_history:
                for scan in st.session_state.scan_history:
                    if scan["label"] == selected_history:
                        st.markdown(scan["analysis"])
                        break
        st.write("") 

    # JUMBO PURCHASE COST SECTION
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

    def process_native_photo(img_file):
        img = Image.open(img_file)
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail((1200, 1200))
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        bytes_data = buffer.getvalue()
        clean_b64 = base64.b64encode(bytes_data).decode("utf-8")
        return img, clean_b64, bytes_data

    # NATIVE CAMERA 
    st.markdown('<div class="cost-label">Snap photos of item, tags, or flaws:</div>', unsafe_allow_html=True)
    camera_photo = st.camera_input("Take Photo", label_visibility="collapsed", key="live_cam")

    if camera_photo:
        proc_img, clean_b64, raw_bytes = process_native_photo(camera_photo)
        if not st.session_state.captured_photos or st.session_state.captured_photos[-1]["bytes"] != raw_bytes:
            st.session_state.captured_photos.append({
                "img": proc_img,
                "base64": clean_b64,
                "bytes": raw_bytes
            })

    # GALLERY PREVIEW 
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

    # MAIN ANALYSIS BUTTON 
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

                    verdict_match = re.search(r'\*\*VERDICT:\s*(FLIP|SKIP|RISKY)\*\*', formatted_text, re.IGNORECASE)
                    verdict_result = verdict_match.group(1).upper() if verdict_match else "ANALYZED"
                    
                    scan_count = len(st.session_state.scan_history) + 1
                    time_now = datetime.datetime.now().strftime("%I:%M %p")
                    
                    history_label = f"#{scan_count} - {time_now} | {verdict_result} | Cost: ${st.session_state.cost_val:.2f}"
                    
                    st.session_state.scan_history.append({
                        "label": history_label,
                        "analysis": formatted_text
                    })

                    st.markdown("---")
                    st.subheader("📊 FuzzFlips Analysis")
                    st.markdown(formatted_text)
                    
                except Exception as e:
                    st.error(f"Error analyzing images: {e}")
