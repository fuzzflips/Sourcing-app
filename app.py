import streamlit as st
import anthropic
import base64

st.set_page_config(page_title="Sourcing Companion", page_icon="🏷️", layout="centered")

st.title("🏷️ Sourcing Companion")
st.caption("AI-Powered Thrift Valuation & Buy/Pass Advisor")

# Get API Key securely from Streamlit secrets or user input
api_key = st.secrets.get("ANTHROPIC_API_KEY") if "ANTHROPIC_API_KEY" in st.secrets else None

if not api_key:
    api_key = st.text_input("Enter Anthropic API Key:", type="password")

if api_key:
    client = anthropic.Anthropic(api_key=api_key)

    # Inputs for the item
    cost = st.number_input("Purchase Cost ($):", min_value=0.0, value=3.0, step=0.50)
    
    # Mobile Camera Input
    uploaded_file = st.camera_input("Take a photo of the item or tag")
    
    if not uploaded_file:
        uploaded_file = st.file_uploader("Or upload from gallery", type=["jpg", "png", "jpeg"])

    if uploaded_file and st.button("🔍 Analyze Item", type="primary"):
        with st.spinner("Analyzing item & estimating market value..."):
            # Read and encode image
            bytes_data = uploaded_file.getvalue()
            base64_image = base64.b64encode(bytes_data).decode('utf-8')
            media_type = uploaded_file.type if uploaded_file.type in ["image/jpeg", "image/png"] else "image/jpeg"

            prompt = f"""
            Act as an expert secondhand reseller. Analyze this image of an item I am considering buying for sourcing.
            Purchase Price / Cost of Goods (COGS): ${cost:.2f}

            Provide a concise, highly structured mobile-friendly response with these sections:

            1. **Item Identification:** Brand, exact item/model name, era/vintage status, and category.
            2. **Condition Assessment:** Visible flaws, wear areas to inspect carefully, or signs of authenticity/counterfeiting.
            3. **Resale Valuation & Price Range:**
               - Estimated eBay Pre-Owned Fair Condition Price
               - Estimated eBay Pre-Owned Good/Excellent Condition Price
            4. **Recommendation:**
               - **BUY / PASS Decision:** (Clear bold recommendation based on COGS of ${cost:.2f} vs estimated net profit after fees/shipping)
               - **Estimated Net Profit:** ($ range)
            5. **Top eBay Search Keywords:** 5-8 high-converting keywords to verify sold comps manually.
            """

            try:
                response = client.messages.create(
                    model="claude-3-5-sonnet-20240620",
                    max_tokens=800,
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64_image,
                                },
                            },
                            {"type": "text", "text": prompt}
                        ],
                    }]
                )
                
                st.markdown("---")
                st.markdown(response.content[0].text)

            except Exception as e:
                st.error(f"Error analyzing image: {e}")
