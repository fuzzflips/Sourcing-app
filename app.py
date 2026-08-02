st.markdown("""
    <style>
    /* Expand the camera container to force full width */
    div[data-testid="stCameraInput"] {
        width: 100% !important;
        display: flex !important;
        justify-content: center !important;
    }

    div[data-testid="stCameraInput"] > div {
        width: 100% !important;
    }

    /* Force the camera iframe to stretch vertically */
    div[data-testid="stCameraInput"] iframe {
        width: 100% !important;
        height: 550px !important;
        min-height: 550px !important;
        border-radius: 12px !important;
        border: 2px solid #008A3C !important;
    }
    </style>
""", unsafe_allow_html=True)
