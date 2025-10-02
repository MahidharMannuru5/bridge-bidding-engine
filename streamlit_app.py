import streamlit as st
# Assuming bridge_coach_agent.py is in the same directory
from bridge_coach_agent import BridgeCoachAgent, format_hand_distribution 

# --- Streamlit Application Functions ---

def get_hand_input():
    st.sidebar.header("User (South) Hand Input")
    hcp = st.sidebar.slider("HCP", 0, 30, 14, key="hcp_slider")
    
    # Ensure distribution sums to 13
    col1, col2 = st.sidebar.columns(2)
    with col1:
        s = st.slider("Spades (S)", 0, 13, 4, key="s_slider")
        h = st.slider("Hearts (H)", 0, 13, 4, key="h_slider")
    with col2:
        d = st.slider("Diamonds (D)", 0, 13, 3, key="d_slider")
        c = st.slider("Clubs (C)", 0, 13, 2, key="c_slider")
    
    dist = [s, h, d, c]
    if sum(dist) != 13:
        st.sidebar.error(f"Total cards must be 13. Current total: {sum(dist)}")
        return None
    
    return {'hcp': hcp, 'dist': dist}

def reset_auction():
    """Clears session state for a new auction."""
    if 'agent' in st.session_state:
        del st.session_state.agent
    st.session_state.auction_running = False

def main():
    st.set_page_config(page_title="Bridge Bidding Coach (SAYC)", layout="wide")
    st.title("Bridge Bidding Coach (SAYC)")
    
    # --- Setup Phase ---
    if 'agent' not in st.session_state:
        st.subheader("1. Auction Setup")
        
        col_setup = st.columns(2)
        with col_setup[0]:
            vulnerability = st.selectbox("Select Vulnerability", ['None', 'NS', 'EW', 'All'], key="vulnerability_select")
        with col_setup[1]:
            dealer = st.selectbox("Select Dealer", ['N', 'E', 'S', 'W'], key="dealer_select")
            
        if st.button("Start New Auction"):
            st.session_state.agent = BridgeCoachAgent(dealer, vulnerability)
            st.session_state.auction_running = True
            st.experimental_rerun()
    
    # --- Auction Loop ---
    if 'agent' in st.session_state and st.session_state.auction_running:
        agent = st.session_state.agent
        current_bidder = agent._get_current_bidder()
        
        st.subheader(f"2. Auction Sequence (Dealer: {agent.dealer}, Vulnerability: {agent.vulnerability})")
        st.code(' - '.join(agent.current_sequence) if agent.current_sequence else "Auction hasn't started yet.", language='markdown')

        st.markdown(f"### Next to Bid: **{current_bidder}**")
        
        # --- User's Turn (SOUTH) ---
        if current_bidder == agent.user_pos:
            st.header("🎯 Your Turn (South) - Strategic Coaching")
            
            user_hand = get_hand_input()
            
            if user_hand:
                st.markdown(f"**Your Hand:** {user_hand['hcp']} HCP, {format_hand_distribution(user_hand['dist'])}")
                
                suggested_bid, reason = agent.suggest_bid(user_hand, agent.vulnerability)
                
                st.info(f"💡 **Suggested Optimal Bid:** **{suggested_bid}**")
                st.markdown(f"**Reasoning:** *{reason}*")
                
                # Action button to confirm and update
                if st.button(f"Confirm Bid: {suggested_bid}", key="confirm_bid"):
                    if agent._update_sequence(suggested_bid):
                        st.session_state.auction_running = False
                        st.success("Auction Ended!")
                    st.experimental_rerun() 

        # --- Partner/Opponent's Turn (N, E, W) ---
        else:
            st.header(f"🧑‍🏫 Educational Phase: {current_bidder}'s Bid")
            
            # Input for Partner/Opponent's bid
            bid = st.text_input(f"Enter Bid for {current_bidder} (e.g., 1S, 2NT, P)", 
                                key=f"bid_input_{len(agent.current_sequence)}").upper()
            
            if st.button("Analyze & Submit Bid", key="submit_bid"):
                if bid:
                    # Education: Explain the input bid
                    explanation = agent.explain_bid(bid, current_bidder)
                    
                    st.markdown("#### Educational Analysis:")
                    st.markdown(f"- **Meaning:** {explanation['meaning']}")
                    st.markdown(f"- **Convention:** {explanation['convention']}")
                    st.markdown(f"- **HCP Range:** {explanation['hcp_range']}")
                    st.markdown(f"- **Implied Shape:** {explanation['implied_shape']}")
                    
                    # Update sequence and check for termination
                    if agent._update_sequence(bid):
                        st.session_state.auction_running = False
                        st.success("Auction Ended!")
                    st.experimental_rerun()
                else:
                    st.error("Please enter a valid bid (e.g., 1S, 3NT, P).")

    # --- Termination ---
    if 'agent' in st.session_state and not st.session_state.auction_running:
        st.subheader("Auction Complete!")
        st.success(f"Final Contract: **{agent.current_sequence[-4]}**")
        st.button("Start New Auction", on_click=reset_auction)


if __name__ == '__main__':
    main()
