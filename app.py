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
                with st.spinner("Analyzing market data..."):
                    try:
                        content_block = []
                        for img in st.session_state.image_queue:
                            encoded_image = base64.b64encode(img.getvalue()).decode("utf-8")
                            content_block.append({
                                "type": "image", 
                                "source": {"type": "base64", "media_type": "image/jpeg", "data": encoded_image}
                            })
                        
                        # --- STRICT JSON PROMPT WITH PURCHASE PRICE ---
                        prompt = f"""
                        You are an expert resale sourcing assistant. Look at the provided image(s) and analyze the item in deep detail.
                        The purchase price for this item is {purchase_price:.2f} dollars.
                        
                        You must respond ONLY with a raw JSON object. Do not include markdown formatting outside the JSON, code blocks, or conversational text.
                        
                        Use this exact JSON structure:
                        {{
                          "item_name": "A precise and descriptive title for the item",
                          "category": "Choose exactly one: Clothing, Footwear, Collectibles, or Other",
                          "estimated_profit": "A realistic dollar range for NET profit (after subtracting the {purchase_price:.2f} cost of goods and standard platform fees)",
                          "verdict": "FLIP or SKIP",
                          "analysis": "Provide a comprehensive, highly detailed breakdown of the item using clear Markdown formatting. Use '###' headings (e.g., ### Product Overview, ### Market Demand, ### Profit Breakdown, ### Final Verdict) and bullet points to organize the information. IMPORTANT: You must use line breaks (\\\\n\\\\n) to space out your sections so it is highly readable. CRITICAL RULE: NEVER use the dollar sign symbol ($) anywhere in your analysis. Streamlit will mistakenly render it as a LaTeX math equation and destroy the text formatting. Always type out the word 'dollars' instead."
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
                        
                        # Clean the text just in case Claude adds markdown backticks
                        raw_response = message.content[0].text
                        cleaned_response = raw_response.replace("```json", "").replace("```", "").strip()
                        
                        # Parse the JSON
                        ai_data = json.loads(cleaned_response)
                        
                        # Display Results nicely in the UI without compressing them in an info box
                        st.markdown(f"### Verdict: {ai_data['verdict']}")
                        st.write(f"**Item:** {ai_data['item_name']} | **Category:** {ai_data['category']}")
                        st.write(f"**Estimated Profit:** {ai_data['estimated_profit']}")
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
                            st.session_state.image_queue = [] # Auto-clear queue after successful scan
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
