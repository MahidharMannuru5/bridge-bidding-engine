import random

class BridgeCoachAgent:
    """
    Highly specialized Bridge Bidding Coach Agent implementing SAYC.
    Handles user guidance (suggest_bid) and educational explanations (explain_bid).
    """

    SAYC_RANGES = {
        '1NT_OPEN': (15, 17, "Balanced"),
        '2NT_OPEN': (20, 22, "Balanced"),
        'OPEN_SUIT': (12, 21, "Unbalanced, 5+ suit"),
        'RESPONSE_1NT': (8, 12, "Response to 1NT"),
        'SIMPLE_RAISE': (6, 9, "Support, 3+ cards"),
        'INVITE_RAISE': (10, 12, "Support, 3+ cards"),
        'GAME_FORCE': (13, 21, "Game forcing values"),
    }

    def __init__(self, dealer='S', vulnerability='None'):
        self.dealer = dealer
        self.vulnerability = vulnerability
        self.bidders = ['N', 'E', 'S', 'W']
        self.bidder_index = self.bidders.index(dealer)
        self.current_sequence = []
        self.consecutive_passes = 0
        self.user_pos = 'S' # Fixed as South for this implementation
        self.trump_suit = None

    def _get_current_bidder(self):
        return self.bidders[self.bidder_index % 4]

    def _update_sequence(self, bid):
        """Updates the auction sequence and checks for termination."""
        self.current_sequence.append(bid)
        
        if bid != 'P':
            self.consecutive_passes = 0
            # Check for establishing a trump suit
            if bid in ['1C', '1D', '1H', '1S', '2C', '2D', '2H', '2S', '3C', '3D', '3H', '3S']:
                suit = bid[-1]
                # A new suit establishes trump potential if a fit is later found
                if len(self.current_sequence) > 1 and self.current_sequence[-2][-1] == suit:
                    self.trump_suit = suit
        else:
            self.consecutive_passes += 1
            
        self.bidder_index += 1

        # Auction ends when 3 consecutive passes occur *after* an initial bid
        if len(self.current_sequence) >= 4 and self.consecutive_passes >= 3:
            return True # Auction ends
        
        return False # Auction continues

    def _get_last_bid_info(self):
        """Returns the last meaningful bid and its bidder's position."""
        meaningful_bids = [b for b in self.current_sequence if b != 'P']
        if not meaningful_bids:
            return None, None, None
        
        last_bid = meaningful_bids[-1]
        last_bid_index = self.current_sequence.index(last_bid)
        last_bidder = self.bidders[self.bidder_index - (len(self.current_sequence) - last_bid_index)]

        return last_bid, last_bidder, last_bid_index

    def explain_bid(self, bid_string, current_bidder):
        """
        Explains the meaning, range, and shape of a bid made by Partner or Opponent.
        """
        last_bid, last_bidder, _ = self._get_last_bid_info()
        explanation = {
            "meaning": "Natural, non-forcing.",
            "hcp_range": "Variable.",
            "implied_shape": "Unspecified.",
            "convention": "None"
        }

        # --- CONTEXT DETERMINATION ---
        is_opening = len([b for b in self.current_sequence if b != 'P']) == 0
        is_overcall = (current_bidder == 'E' or current_bidder == 'W') and last_bidder == ('N' if current_bidder == 'E' else 'S')
        is_response = (current_bidder == 'N' or current_bidder == 'S') and last_bidder in ['N', 'S']

        # --- CONVENTION LOGIC (Highest Priority) ---

        # 1. Stayman / Transfers (After 1NT opening by Partner)
        if last_bid == '1NT' and is_response:
            if bid_string == '2C':
                explanation["convention"] = "Stayman"
                explanation["meaning"] = "Artificial, asking for 4-card major suits."
                explanation["hcp_range"] = "8+ HCP"
                explanation["implied_shape"] = "At least one 4-card Major."
                return explanation
            elif bid_string == '2D':
                explanation["convention"] = "Jacoby Transfer to Hearts"
                explanation["meaning"] = "Artificial, forcing 2H. Promises 5+ Hearts."
                explanation["hcp_range"] = "8+ HCP"
                explanation["implied_shape"] = "5+ Hearts."
                return explanation
            elif bid_string == '2H':
                explanation["convention"] = "Jacoby Transfer to Spades"
                explanation["meaning"] = "Artificial, forcing 2S. Promises 5+ Spades."
                explanation["hcp_range"] = "8+ HCP"
                explanation["implied_shape"] = "5+ Spades."
                return explanation
        
        # 2. Blackwood / Gerber
        if bid_string == '4NT':
            if self.trump_suit:
                explanation["convention"] = "Key Card Blackwood (RKCB 1430)"
                explanation["meaning"] = f"Asking for Key Cards (4 Aces + {self.trump_suit} King)."
                explanation["hcp_range"] = "Slam interest."
                return explanation
            elif last_bid in ['1NT', '2NT', '3NT']:
                explanation["convention"] = "Quantitative NT"
                explanation["meaning"] = "Invitational to 6NT."
                explanation["hcp_range"] = "18-19 HCP (after 1NT)"
                return explanation
        
        if bid_string == '4C' and last_bid in ['1NT', '2NT', '3NT']:
            explanation["convention"] = "Gerber"
            explanation["meaning"] = "Asking for Aces (after a NT agreement)."
            explanation["hcp_range"] = "Slam interest."
            return explanation

        # --- NATURAL LOGIC ---
        if is_opening:
            if bid_string == '1NT':
                hcp_low, hcp_high, shape = self.SAYC_RANGES['1NT_OPEN']
                explanation["meaning"] = "Natural, Balanced Opening."
                explanation["hcp_range"] = f"{hcp_low}-{hcp_high} HCP"
                explanation["implied_shape"] = shape
            elif bid_string in ['1C', '1D', '1H', '1S']:
                explanation["meaning"] = f"Natural, showing {bid_string[-1]}."
                explanation["hcp_range"] = "12+ HCP"
                explanation["implied_shape"] = "5+ cards in Major, 4+ in Minor (or 3+ in C)."
            # ... (Add logic for 2-level, 3-level openings)
        
        elif is_overcall:
            if 'X' in bid_string:
                explanation["meaning"] = "Takeout Double"
                explanation["hcp_range"] = "12+ TP"
                explanation["implied_shape"] = "Shortage in opponent's suit, support for unbid suits."
            else:
                explanation["meaning"] = f"Natural Overcall in {bid_string[-1]}."
                explanation["hcp_range"] = "8-16 TP"
                explanation["implied_shape"] = "Good 5+ card suit."

        return explanation

    def suggest_bid(self, user_hand, vulnerability):
        """
        Provides the optimal bid and justification for the User (South).
        user_hand: {'hcp': X, 'dist': [S, H, D, C]}
        """
        hcp = user_hand['hcp']
        dist = user_hand['dist']
        tp = hcp + sum([max(0, d - 4) for d in dist]) # Simple TP calc

        last_bid, last_bidder, _ = self._get_last_bid_info()
        
        # --- PHASE 1: OPENING BID (If User is the first to bid meaningfully) ---
        if not last_bid or last_bid == 'P':
            if hcp >= 15 and hcp <= 17 and max(dist) <= 5: # Check for 1NT
                return '1NT', f"You have a balanced hand with 15-17 HCP. Opening bid is 1NT."
            
            if hcp >= 12:
                # Prioritize 5-card Majors
                if dist[0] >= 5: return '1S', "Open with your 5-card major, 1 Spades. (12+ HCP)."
                if dist[1] >= 5: return '1H', "Open with your 5-card major, 1 Hearts. (12+ HCP)."
                # Prioritize best minor (usually Diamonds)
                if dist[2] >= 4: return '1D', "Open with your 4+ card minor, 1 Diamond. (12+ HCP)."
                if dist[3] >= 3: return '1C', "Open with your best minor, 1 Club. (12+ HCP)."
            
            return 'Pass', "You have less than 12 HCP, so the correct opening call is Pass."

        # --- PHASE 2: CONVENTIONAL RESPONSES (After Partner's Bid) ---
        if last_bidder == 'N': # Partner's last bid
            if last_bid == '1NT':
                if hcp >= 8:
                    # Stayman Check
                    if dist[0] >= 4 or dist[1] >= 4:
                        return '2C', f"You have 4-card Majors and 8+ HCP. Bid 2 Clubs (Stayman) to ask for partner's Majors."
                    # Jacoby Transfers
                    if dist[1] >= 5: # Hearts
                        return '2D', f"You have 5+ Hearts and 8+ HCP. Bid 2 Diamonds (Jacoby Transfer) to force 2H."
                    if dist[0] >= 5: # Spades
                        return '2H', f"You have 5+ Spades and 8+ HCP. Bid 2 Hearts (Jacoby Transfer) to force 2S."
                    # NT bids
                    if hcp >= 10 and hcp <= 12:
                        return '3NT', f"You have 10-12 HCP, guaranteeing game values without a major fit. Bid 3NT."
                
                return 'Pass', "You lack the 8 HCP minimum to respond to 1NT with a forcing bid."

            # Blackwood/Gerber Response (if last_bid was 4NT or 4C and we are the responder)
            if last_bid == '4NT' and self.trump_suit: # Blackwood
                aces = sum(1 for d in dist if d == 0) # Mock: assume void=A for simplicity
                key_cards = aces # Simplified Key Card count
                if key_cards == 0 or key_cards == 3: return '5C', "Responding to RKCB: 0 or 3 Key Cards."
                if key_cards == 1 or key_cards == 4: return '5D', "Responding to RKCB: 1 or 4 Key Cards."
                if key_cards == 2: return '5H', "Responding to RKCB: 2 Key Cards (simplified)."


        # --- PHASE 3: NATURAL RESPONSES / RAISES (After Partner's Opening Suit) ---
        if last_bidder == 'N' and last_bid in ['1C', '1D', '1H', '1S']:
            partner_suit = last_bid[-1]
            p_idx = {'S':0, 'H':1, 'D':2, 'C':3}[partner_suit]
            
            # Find a Fit (3+ cards needed for raise)
            if dist[p_idx] >= 3:
                # Total TP: Partner (12) + User (TP)
                combined_tp = 12 + tp
                
                if combined_tp >= 25:
                    return f'4{partner_suit}', f"You have a major-suit fit and 25+ TP. Bid game: 4{partner_suit}."
                elif combined_tp >= 22:
                    return f'3{partner_suit}', f"You have a major-suit fit and 22+ TP (Invitational). Bid 3{partner_suit}."
                elif hcp >= 6:
                    return f'2{partner_suit}', f"You have support (3+ cards) and 6-9 HCP. Simple non-forcing raise to 2{partner_suit}."

            # New Suit (No Fit)
            if hcp >= 6:
                if dist[0] >= 4 and last_bid != '1S': return '1S', "Bid your 4+ card Major suit (forcing)."
                if dist[1] >= 4 and last_bid != '1H': return '1H', "Bid your 4+ card Major suit (forcing)."
                
                if hcp >= 10 and max(dist) <= 5:
                    return '2NT', "No fit, balanced, 10-12 HCP. Invitational 2NT."
                
                return '1NT', "No fit, 6-9 HCP, balanced. Non-forcing 1NT."

        # --- PHASE 4: COMPETITION (After Opponent's Bid) ---
        if last_bidder in ['E', 'W']:
            if hcp >= 12 and 'X' not in last_bid and len(self.current_sequence) > 1 and last_bidder != self.bidders[self.bidder_index - 2]: # Opponent Overcalled
                return 'X', "Bid a Takeout Double. You have 12+ HCP and should ask partner to bid."
            
            if hcp >= 8:
                suits = sorted([(dist[i], s) for i, s in enumerate(['S', 'H', 'D', 'C'])], reverse=True)
                best_suit = suits[0][1]
                
                # Simple Overcall if available at 1-level
                if suits[0][0] >= 5 and best_suit not in last_bid:
                    return f'1{best_suit}', f"With 8+ HCP, overcall in your best 5-card suit: 1{best_suit}."
            
            return 'Pass', "The opponent's bid is too high/risky to compete, or your hand is too weak (less than 8 TP/HCP)."

        # Default Safety Net
        return 'Pass', "No strong action available. Pass."


### 2. Conceptual Streamlit App (`streamlit_app.py`)

This demonstrates how the agent would be used in a Streamlit loop.

```python
import streamlit as st
# from bridge_coach_agent import BridgeCoachAgent # Assume the class above is imported

# --- Streamlit Application Structure ---

def get_hand_input():
    st.sidebar.header("User (South) Hand Input")
    hcp = st.sidebar.slider("HCP", 0, 30, 14)
    s = st.sidebar.slider("Spades (S)", 0, 8, 4)
    h = st.sidebar.slider("Hearts (H)", 0, 8, 4)
    d = st.sidebar.slider("Diamonds (D)", 0, 8, 3)
    c = st.sidebar.slider("Clubs (C)", 0, 8, 2)
    
    if sum([s, h, d, c]) != 13:
        st.sidebar.warning(f"Total cards must be 13. Current total: {sum([s, h, d, c])}")
        return None
    
    return {'hcp': hcp, 'dist': [s, h, d, c]}

def main():
    st.title("Bridge Bidding Coach (SAYC)")
    
    # --- Setup Phase ---
    if 'agent' not in st.session_state:
        st.session_state.vulnerability = st.selectbox("Select Vulnerability", ['None', 'NS', 'EW', 'All'])
        st.session_state.dealer = st.selectbox("Select Dealer", ['N', 'E', 'S', 'W'])
        if st.button("Start Auction"):
            st.session_state.agent = BridgeCoachAgent(st.session_state.dealer, st.session_state.vulnerability)
            st.session_state.auction_running = True
    
    if 'agent' in st.session_state and st.session_state.auction_running:
        agent = st.session_state.agent
        st.header(f"Current Bidder: {agent._get_current_bidder()}")
        st.write(f"Sequence: **{' - '.join(agent.current_sequence)}**")

        current_bidder = agent._get_current_bidder()
        
        # --- User's Turn (SOUTH) ---
        if current_bidder == agent.user_pos:
            user_hand = get_hand_input()
            
            if user_hand:
                st.subheader("Your Turn (South) - Coaching Advice")
                suggested_bid, reason = agent.suggest_bid(user_hand, agent.vulnerability)
                
                st.info(f"**Suggested Bid:** {suggested_bid}")
                st.markdown(f"**Reasoning:** {reason}")
                
                # Action button to confirm and update
                if st.button(f"Confirm Bid: {suggested_bid}"):
                    if agent._update_sequence(suggested_bid):
                        st.session_state.auction_running = False
                        st.success("Auction Ended!")
                    st.experimental_rerun() # Rerun to update state and next bidder

        # --- Partner/Opponent's Turn ---
        else:
            st.subheader(f"{current_bidder}'s Turn - Enter Bid")
            bid = st.text_input(f"Enter Bid for {current_bidder} (e.g., 1S, 2NT, P)", key=f"bid_{len(agent.current_sequence)}")
            
            if st.button("Submit Bid"):
                if bid:
                    # Education: Explain the input bid
                    explanation = agent.explain_bid(bid.upper(), current_bidder)
                    st.markdown("### Educational Analysis of the Bid:")
                    st.json(explanation) # Display the detailed explanation
                    
                    if agent._update_sequence(bid.upper()):
                        st.session_state.auction_running = False
                        st.success("Auction Ended!")
                    st.experimental_rerun()
    
    if 'agent' in st.session_state and not st.session_state.auction_running:
        st.success(f"Final Contract: {agent.current_sequence[-4]}")
        st.button("Reset Auction", on_click=lambda: st.session_state.clear())


# if __name__ == '__main__':
#     main()
        
