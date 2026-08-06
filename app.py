import streamlit as st
import base64
import anthropic
from supabase import create_client, Client

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Flip or Skip", page_icon="📦", layout="centered")

# --- INITIALIZE DATABASE CONNECTION ---
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

# --- INITIALIZE AI CLIENT ---
client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

# --- SESSION STATE MANAGEMENT ---
if 'user' not in st.session_state:
    st.session_state.user = None


# ==========================================
#         AUTHENTICATION GATEWAY
# ==========================================
if st.session_state.user is None:
    st.markdown("<h1 style='text-align: center; color: #ff5722; font-style: italic;'>FLIP <span style='color: #4CAF50;'>OR</span> SKIP</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Powered by FuzzFlips AI</p>", unsafe_allow_html=True)
    st.divider()

    auth_mode = st.radio("Welcome", ["Login", "Sign Up"], horizontal=True, label_visibility="hidden")
    email = st.text_input("Email Address")
    password = st.text_input("Password", type="password")
    
    if auth_mode == "Sign Up":
        if st.button("Create Account", type="primary", use_container_width=True):
            try:
                # We do not use email verification for testing, so this auto-confirms
                res = supabase.auth.sign_up({"email": email, "password": password})
                st.success("Account created successfully! You can now log in.")
            except Exception as e:
                st.error(f"Signup failed: {str(e)}")
                
    elif auth_mode == "Login":
        if st.button("Log In", type="primary", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {str(e)}")


# ==========================================
#             MAIN APPLICATION
# ==========================================
else:
    # Header & Logout 
    col1, col2 = st.columns([8, 2])
    with col1:
        st.markdown("<h2 style='color: #ff5722; font-style: italic; margin-top: -15px;'>FLIP <span style='color: #4CAF50;'>OR</span> SKIP</h2>", unsafe_allow_html=True)
    with col2:
        if st.button("Logout"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

    st.write("Scan clothing, footwear, or collectibles to analyze market value and estimated profit.")

   # --- SCANNER INTERFACE ---
    camera_photo = st.camera_input("Camera")
    uploaded_files = st.file_uploader("Or upload from camera roll", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

    # Combine any inputs into a single list
    images_to_process = []
    if camera_photo:
        images_to_process.append(camera_photo)
    if uploaded_files:
        images_to_process.extend(uploaded_files)

    if images_to_process:
        # Display thumbnails of all selected images side-by-side
        st.image(images_to_process, width=150)
        
        if st.button("FLIP OR SKIP?", type="primary", use_container_width=True):
            with st.spinner("Analyzing market data..."):
                try:
                    # 1. Prepare ALL images for Anthropic Claude
                    content_block = []
                    for img in images_to_process:
                        encoded_image = base64.b64encode(img.getvalue()).decode("utf-8")
                        content_block.append({
                            "type": "image", 
                            "source": {"type": "base64", "media_type": "image/jpeg", "data": encoded_image}
                        })
                    
                    # Add the text prompt at the end
                    prompt = """
                    You are an expert resale sourcing assistant. Look at the provided image(s) and tell me:
                    1. A short description of the item.
                    2. Estimated resale value range.
                    3. Final verdict: FLIP or SKIP.
                    Keep it brief and punchy.
                    """
                    content_block.append({"type": "text", "text": prompt})
                    
                    # 2. Call the AI
                    message = client.messages.create(
                        model="claude-3-5-sonnet-20240620",
                        max_tokens=300,
                        messages=[
                            {
                                "role": "user",
                                "content": content_block
                            }
                        ]
                    )
                    
                    ai_response = message.content[0].text
                    
                    # 3. Display Results
                    st.markdown("### AI Verdict")
                    st.info(ai_response)
                    
                    # 4. Save to Cloud Database
                    try:
                        supabase.table('scans').insert({
                            "user_id": st.session_state.user.id,
                            "item_name": "Field Scan", 
                            "category": "Uncategorized",
                            "ai_analysis": ai_response
                        }).execute()
                        st.success("✅ Scan securely saved to your cloud history!")
                    except Exception as db_error:
                        st.error(f"Failed to save to database: {str(db_error)}")
                        
                except Exception as ai_error:
                    st.error(f"AI Analysis failed: {str(ai_error)}")
    
    st.divider()
    
    # --- SCAN HISTORY VIEWER ---
    st.subheader("Field Scan History")
    if st.checkbox("Load Database"):
        try:
            # Retrieve only the scans that belong to the currently logged-in user
            response = supabase.table('scans').select('*').eq('user_id', st.session_state.user.id).order('created_at', desc=True).limit(10).execute()
            records = response.data
            
            if not records:
                st.write("No scans found in your history yet.")
            else:
                for record in records:
                    date_str = record['created_at'][:10]
                    with st.expander(f"Scan from {date_str}"):
                        st.write(record['ai_analysis'])
        except Exception as read_error:
            st.error(f"Could not load history: {str(read_error)}")
