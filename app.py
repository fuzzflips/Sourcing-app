import streamlit as st
import base64
import anthropic
import json
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
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = None

def load_or_create_user_profile(user_id):
    try:
        res = supabase.table('profiles').select('*').eq('id', user_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        else:
            default_platforms = ["eBay"]
            new_profile = {"id": user_id, "platforms": default_platforms}
            supabase.table('profiles').insert(new_profile).execute()
            return new_profile
    except Exception as e:
        return {"platforms": ["eBay"]}


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
                res = supabase.auth.sign_up({"email": email, "password": password})
                st.success("Account created successfully! You can now log in.")
            except Exception as e:
                st.error(f"Signup failed: {str(e)}")
                
    elif auth_mode == "Login":
        if st.button("Log In", type="primary", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.session_state.user_profile = load_or_create_user_profile(res.user.id)
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {str(e)}")


# ==========================================
#             MAIN APPLICATION
# ==========================================
else:
    if st.session_state.user_profile is None:
        st.session_state.user_profile = load_or_create_user_profile(st.session_state.user.id)

    # Header & Logout 
    col_h1, col_h2 = st.columns([8, 2])
    with col_h1:
        st.markdown("<h2 style='color: #ff5722; font-style: italic; margin-top: -15px;'>FLIP <span style='color: #4CAF50;'>OR</span> SKIP</h2>", unsafe_allow_html=True)
    with col_h2:
        if st.button("Logout"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.session_state.user_profile = None
            st.rerun()

    # --- PROFILE / PLATFORM SETTINGS EXPANDER ---
    with st.expander("⚙️ Seller Profile & Platform Settings"):
        st.write("Select your primary selling platforms so the AI tailors its profit math and fee structures accordingly.")
        
        current_platforms = st.session_state.user_profile.get("platforms", ["eBay"])
        
        selected_platforms = st.multiselect(
            "Active Reselling Platforms",
            ["eBay", "Poshmark", "Mercari", "Whatnot", "Depop", "Local Marketplace"],
            default=current_platforms
        )
        
        if st.button("Save Platform Preferences"):
            try:
                supabase.table('profiles').update({"platforms": selected_platforms}).eq('id', st.session_state.user.id).execute()
                st.session_state.user_profile["platforms"] = selected_platforms
                st.success("Platform preferences saved to your profile!")
            except Exception as update_err:
                st.error(f"Failed to save preferences: {str(update_err)}")

    user_platforms_str = ", ".join(st.session_state.user_profile.get("platforms", ["eBay"]))
    st.write(f"*Active Sourcing Profile:* Tailored for **{user_platforms_str}**.")
    st.divider()

    # --- SCANNER INTERFACE ---
    if 'image_queue' not in st.session_state:
        st.session_state.image_queue = []

    camera_photo = st.camera_input("Camera")
    uploaded_files = st.file_uploader("Or upload from camera roll", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

    if camera_photo:
        is_duplicate = any(img.getvalue() == camera_photo.getvalue() for img in st.session_state.image_queue)
        if not is_duplicate:
            st.session_state.image_queue.append(camera_photo)

    if uploaded_files:
        for file in uploaded_files:
            is_duplicate = any(img.getvalue() == file.getvalue() for img in st.session_state.image_queue)
            if not is_duplicate:
                st.session_state.image_queue.append(file)

    if st.session_state.image_queue:
        st.markdown("### Current Batch")
        st.image(st.session_state.image_queue, width=150)
        
        # --- Purchase Price Input ---
        purchase_price = st.number_input("Purchase Price ($)", min_value=0.00, value=0.00, step=1.00, format="%.2f")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Clear Batch", use_container_width=True):
                st.session_state.image_queue = []
                st.rerun()
                
        with col2:
            if st.button("FLIP OR SKIP?", type="primary", use_container_width=True):
                with st.spinner("Analyzing market data & calculating fees..."):
                    try:
                        content_block = []
                        for img in st.session_state.image_queue:
                            encoded_image = base64.b64encode(img.getvalue()).decode("utf-8")
                            content_block.append({
                                "type": "image", 
                                "source": {"type": "base64", "media_type": "image/jpeg", "data": encoded_image}
                            })
                        
                        # --- STRICT JSON PROMPT WITH PLATFORM FEE BREAKDOWN FIELDS ---
                        prompt = f"""
                        You are an expert resale sourcing assistant. Look at the provided image(s) and analyze the item in deep detail.
                        The purchase price for this item is {purchase_price:.2f} dollars.
                        The user primarily sells on these platforms: {user_platforms_str}. Factor the specific seller fees, commission structures, and buyer behaviors of these platforms into your calculations.
                        
                        You must respond ONLY with a raw JSON object. Do not include markdown formatting outside the JSON, code blocks, or conversational text.
                        
                        Use this exact JSON structure:
                        {{
                          "item_name": "A precise and descriptive title for the item",
                          "category": "Choose exactly one: Clothing, Footwear, Collectibles, or Other",
                          "estimated_gross_sale": "Estimated market resale value as a dollar string (e.g., '$75.00')",
                          "estimated_fees": "Estimated platform commission and processing fees for {user_platforms_str} as a dollar string (e.g., '$10.50')",
                          "estimated_profit": "Realistic net profit after subtracting cost of goods ({purchase_price:.2f} dollars) and estimated fees, as a dollar string (e.g., '$64.50')",
                          "verdict": "FLIP or SKIP",
                          "analysis": "Provide a comprehensive breakdown of the item using clear Markdown formatting. Use '###' headings (e.g., ### Product Overview, ### Market Demand, ### Platform Strategy & Fee Breakdown, ### Final Verdict) and bullet points to organize the information. Discuss how this item performs specifically across {user_platforms_str}. IMPORTANT: You must use line breaks (\\\\n\\\\n) to space out your sections so it is highly readable. CRITICAL RULE: NEVER use the dollar sign symbol ($) anywhere in your analysis or strings. Streamlit will mistakenly render it as a LaTeX math equation and destroy the text formatting. Always type out the word 'dollars' instead or avoid the symbol entirely in your text values."
                        }}
                        """
                        content_block.append({"type": "text", "text": prompt})
                        
                        message = client.messages.create(
                            model="claude-sonnet-5",
                            max_tokens=1500,
                            messages=[
                                {
                                    "role": "user",
                                    "content": content_block
                                }
                            ]
                        )
                        
                        raw_response = message.content[0].text
                        cleaned_response = raw_response.replace("```json", "").replace("```", "").strip()
                        ai_data = json.loads(cleaned_response)
                        
                        # --- DISPLAY RESULTS WITH FEE BREAKDOWN UI ---
                        st.markdown(f"### Verdict: {ai_data['verdict']}")
                        st.write(f"**Item:** {ai_data['item_name']} | **Category:** {ai_data['category']}")
                        st.divider()
                        
                        # Metric Cards for Financial Breakdown
                        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                        with m_col1:
                            st.metric("Cost of Goods", f"${purchase_price:.2f}")
                        with m_col2:
                            st.metric("Est. Gross Sale", ai_data.get('estimated_gross_sale', 'N/A'))
                        with m_col3:
                            st.metric("Est. Platform Fees", ai_data.get('estimated_fees', 'N/A'))
                        with m_col4:
                            st.metric("Est. Net Profit", ai_data.get('estimated_profit', 'N/A'))
                            
                        st.caption(f"Calculations optimized for your active platforms: {user_platforms_str}")
                        st.divider()
                        
                        st.markdown(ai_data['analysis'])
                        
                        # Save structured data to Cloud Database
                        try:
                            supabase.table('scans').insert({
                                "user_id": st.session_state.user.id,
                                "item_name": ai_data['item_name'], 
                                "category": ai_data['category'],
                                "estimated_profit": ai_data['estimated_profit'],
                                "ai_analysis": ai_data['analysis']
                            }).execute()
                            st.success("✅ Scan securely saved to your cloud history!")
                            st.session_state.image_queue = [] 
                        except Exception as db_error:
                            st.error(f"Failed to save to database: {str(db_error)}")
                            
                    except json.JSONDecodeError:
                        st.error("The AI failed to format the data correctly. Please try scanning again.")
                    except Exception as ai_error:
                        st.error(f"Analysis failed: {str(ai_error)}")
    
    st.divider()
    
    # --- SCAN HISTORY VIEWER ---
    st.subheader("Field Scan History")
    if st.checkbox("Load Database"):
        try:
            response = supabase.table('scans').select('*').eq('user_id', st.session_state.user.id).order('created_at', desc=True).limit(10).execute()
            records = response.data
            
            if not records:
                st.write("No scans found in your history yet.")
            else:
                for record in records:
                    date_str = record['created_at'][:10]
                    with st.expander(f"{date_str}: {record['item_name']} ({record['category']})"):
                        st.write(f"**Estimated Profit:** {record.get('estimated_profit', 'N/A')}")
                        st.write(f"**Analysis:** {record['ai_analysis']}")
        except Exception as read_error:
            st.error(f"Could not load history: {str(read_error)}")
