import streamlit as st
from bridge_bidding_engine_full import Hand, parse_hand_string, advise_your_bid, is_balanced

st.set_page_config(page_title="Bridge Bidding Engine", page_icon="♠️")

st.title("♠️ Bridge Bidding Engine — Streamlit Version")

# --- Sidebar: setup ---
st.sidebar.header("Setup")
seat = st.sidebar.selectbox("Your seat", ["N", "E", "S", "W"])
dealer = st.sidebar.selectbox("Dealer", ["N", "E", "S", "W"])
hand_input = st.sidebar.text_area("Enter your 13 cards",
    "J643.AJ54.A7.T97", height=80)

if "auction" not in st.session_state:
    st.session_state.auction = []
if "turn" not in st.session_state:
    st.session_state.turn = dealer

# --- Parse your hand ---
try:
    your_hand = Hand(parse_hand_string(hand_input))
    st.sidebar.markdown(
        f"**HCP**: {your_hand.hcp}  \n"
        f"**Shape (S,H,D,C)**: {your_hand.shape}  \n"
        f"**Balanced?** {'Yes' if is_balanced(your_hand.shape) else 'No'}"
    )
except Exception as e:
    st.sidebar.error(f"Error parsing hand: {e}")
    your_hand = None

st.subheader("Auction so far")
st.write(" ".join(st.session_state.auction) if st.session_state.auction else "(none)")

# --- Bidding Turn ---
if your_hand:
    st.subheader(f"Turn: {st.session_state.turn}")

    if st.session_state.turn == seat:
        suggestions = advise_your_bid(your_hand, st.session_state.auction)
        for i, sug in enumerate(suggestions, 1):
            if st.button(f"{sug.bid} — {sug.reason}", key=f"sug{i}"):
                st.session_state.auction.append(sug.bid)
                st.session_state.turn = {"N":"E","E":"S","S":"W","W":"N"}[st.session_state.turn]
                st.experimental_rerun()
    else:
        opp_bid = st.text_input(f"Enter {st.session_state.turn}'s call", value="PASS", key="oppbid")
        if st.button("Submit Opponent/Partner Call"):
            st.session_state.auction.append(opp_bid.upper())
            st.session_state.turn = {"N":"E","E":"S","S":"W","W":"N"}[st.session_state.turn]
            st.experimental_rerun()

# --- End Auction Check ---
if len(st.session_state.auction) >= 4 and st.session_state.auction[-3:] == ["PASS","PASS","PASS"]:
    st.success("Auction finished!")
    st.write("**Final Auction:**", " ".join(st.session_state.auction))
    if st.button("Reset Auction"):
        st.session_state.auction = []
        st.session_state.turn = dealer
        st.experimental_rerun()
      
