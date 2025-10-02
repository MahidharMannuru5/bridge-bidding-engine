import streamlit as st

# Try to import your engine (must be in the same folder)
try:
    from bridge_bidding_engine_full import (
        Hand,
        parse_hand_string,
        advise_your_bid,
        is_balanced,
    )
except Exception as e:
    st.error(
        "Couldn't import `bridge_bidding_engine_full.py`.\n"
        "Make sure that file is in the same directory as this app.\n\n"
        f"Import error: {e}"
    )
    st.stop()

# Minimal page config (no big title)
st.set_page_config(page_title="Bridge Coach", page_icon="")

# Constants
SEATS = ["N", "E", "S", "W"]
NEXT = {"N": "E", "E": "S", "S": "W", "W": "N"}

# --- Init session state ---
if "started" not in st.session_state:
    st.session_state.started = False
    st.session_state.seat = None
    st.session_state.dealer = None
    st.session_state.auction = []
    st.session_state.turn = None
    st.session_state.your_hand = None

# ======== SETUP PANEL ========
if not st.session_state.started:
    st.subheader("Setup")
    with st.form("setup"):
        seat = st.selectbox("Your seat", SEATS, index=0)
        dealer = st.selectbox("Dealer", SEATS, index=0)
        hand_input = st.text_input(
            "Enter your 13 cards",
            value="J643.AJ54.A7.T97",
            help=(
                "Examples: 'J643.AJ54.A7.T97' (S.H.D.C) or 'AS KH QH 7H TC 2C 9D 8D 7S 6S 5C 4C 3C'"
            ),
        )
        submitted = st.form_submit_button("Start auction")

    if submitted:
        try:
            your_hand = Hand(parse_hand_string(hand_input))
        except Exception as e:
            st.error(f"Hand parse error: {e}")
        else:
            st.session_state.seat = seat
            st.session_state.dealer = dealer
            st.session_state.your_hand = your_hand
            st.session_state.auction = []
            st.session_state.turn = dealer
            st.session_state.started = True
            st.rerun()

# ======== AUCTION PANEL ========
else:
    # Top bar (compact, no title)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**Seat:** {st.session_state.seat}")
    with col2:
        st.write(f"**Dealer:** {st.session_state.dealer}")
    with col3:
        h = st.session_state.your_hand
        st.write(
            f"**HCP:** {h.hcp} | **Shape (S,H,D,C):** {h.shape} | **Balanced?** {'Yes' if is_balanced(h.shape) else 'No'}"
        )

    st.divider()

    st.caption("Auction so far")
    st.code(" ".join(st.session_state.auction) if st.session_state.auction else "(none)")

    # End condition
    if (
        len(st.session_state.auction) >= 4
        and st.session_state.auction[-3:] == ["PASS", "PASS", "PASS"]
    ):
        st.success("Auction finished.")
        st.write("**Final Auction:**", " ".join(st.session_state.auction))
        colA, colB = st.columns(2)
        if colA.button("Reset auction"):
            st.session_state.auction = []
            st.session_state.turn = st.session_state.dealer
            st.rerun()
        if colB.button("Start over (change setup)"):
            st.session_state.started = False
            st.rerun()
        st.stop()

    st.subheader(f"Turn: {st.session_state.turn}")

    # --- Your turn ---
    if st.session_state.turn == st.session_state.seat:
        sugs = advise_your_bid(st.session_state.your_hand, st.session_state.auction)
        if not sugs:
            st.info("No suggestions available (will Pass by default).")
            if st.button("PASS"):
                st.session_state.auction.append("PASS")
                st.session_state.turn = NEXT[st.session_state.turn]
                st.rerun()
        else:
            st.write("**Your suggestions (point ranges & reasons):**")
            for i, s in enumerate(sugs, start=1):
                if st.button(f"{s.bid} — {s.reason}", key=f"mysug{i}"):
                    st.session_state.auction.append(s.bid.upper())
                    st.session_state.turn = NEXT[st.session_state.turn]
                    st.rerun()

            # Optional manual override
            with st.expander("Or type a custom call"):
                manual = st.text_input("Your call (e.g., PASS, 1S, X, 4NT, 4C)", key="manual_me")
                if st.button("Play my custom call") and manual:
                    st.session_state.auction.append(manual.upper())
                    st.session_state.turn = NEXT[st.session_state.turn]
                    st.rerun()

    # --- Partner/Opp turn ---
    else:
        st.write("**Enter partner/opponent call:**")
        # Quick picks row
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        if c1.button("PASS"): chosen = "PASS"
        elif c2.button("X"): chosen = "X"
        elif c3.button("XX"): chosen = "XX"
        elif c4.button("1NT"): chosen = "1NT"
        elif c5.button("2NT"): chosen = "2NT"
        elif c6.button("3NT"): chosen = "3NT"
        else: chosen = None

        opp_input = st.text_input(
            f"Custom call for {st.session_state.turn}", value="", key="opp_custom"
        )
        if st.button("Submit call") or chosen:
            call = chosen or opp_input.strip().upper() or "PASS"
            st.session_state.auction.append(call)
            st.session_state.turn = NEXT[st.session_state.turn]
            st.rerun()

    st.divider()
    cols = st.columns(3)
    if cols[0].button("Reset auction"):
        st.session_state.auction = []
        st.session_state.turn = st.session_state.dealer
        st.rerun()
    if cols[1].button("Start over (change setup)"):
        st.session_state.started = False
        st.rerun()
    if cols[2].button("Undo last call") and st.session_state.auction:
        st.session_state.auction.pop()
        # Move turn back one seat
        prev = {v: k for k, v in NEXT.items()}[st.session_state.turn]
        st.session_state.turn = prev
        st.rerun()
        
