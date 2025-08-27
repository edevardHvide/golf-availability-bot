    # Enhanced Header with hero image
    col_header_text, col_header_image = st.columns([2, 1])
    
    with col_header_text:
        st.markdown("""
        <div class="main-header">
            <h1>🏌️ Golf Availability Monitor</h1>
            <p>Smart tee time notifications with instant availability checking</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_header_image:
        try:
            st.markdown('<div class="hero-image">', unsafe_allow_html=True)
            st.image("streamlit_app/assets/907d8ed5-d913-4739-8b1e-c66e7231793b.jpg", 
                    caption="Perfect your swing!", 
                    use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        except:
            # Fallback if image not found
            st.markdown("""
            <div style="background: #f0f0f0; padding: 2rem; border-radius: 10px; text-align: center;">
                <h3>🏌️</h3>
                <p>Golf Image</p>
            </div>
            """, unsafe_allow_html=True)
