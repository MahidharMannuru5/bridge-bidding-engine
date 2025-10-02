import random

class BridgeCoachAgent:
    """
    Highly specialized Bridge Bidding Coach Agent implementing SAYC.
    Handles user guidance (suggest_bid) and educational explanations (explain_bid).
    """

    SAYC_RANGES = {
        '1NT_OPEN': (15, 17, "Balanced (4333, 4432, 5332 with 5c minor)"),
        '2NT_OPEN': (20, 22, "Balanced"),
        'OPEN_SUIT': (12, 21, "Unbalanced, 5+ card suit (4+ for Diamonds)"),
        'RESPONSE_1NT': (8, 12, "Forcing response to 1NT"),
        'SIMPLE_RAISE': (6, 9, "Support, 3+ cards"),
        'INVITE_RAISE': (10, 12, "Support, 3+ cards, Invitational"),
        'GAME_FORCE': (13, 21, "Game forcing values"),
        'OVERCALL': (8, 16, "Unbalanced, good 5+ card suit"),
        'TAKEOUT_DOUBLE': (12, 21, "Shortage in opponent's suit, support for others")
    }

    SUIT_MAP = {'S': 0, 'H': 1, 'D': 2, 'C': 3, 'N': 4} # S, H, D, C, NT

    def __init__(self, dealer='S', vulnerability='None'):
        self.dealer = dealer
        self.vulnerability = vulnerability
        self.bidders = ['N', 'E', 'S', 'W']
        self.bidder_index = self.bidders.index(dealer)
        self.current_sequence = []
        self.user_pos = 'S' # User is fixed as South
        self.trump_suit = None

    def _get_current_bidder(self):
        """Returns the position of the player whose turn it is."""
        return self.bidders[self.bidder_index % 4]

    def _get_last_bid_info(self):
        """Returns the last meaningful bid (not 'P'), its bidder, and their position."""
        meaningful_bids = [b for b in self.current_sequence if b != 'P']
        if not meaningful_bids:
            return None, None, None
        
        last_bid = meaningful_bids[-1]
        
        # Calculate who made the last meaningful bid
        temp_seq = self.current_sequence[:]
        bid_index_in_sequence = temp_seq.index(last_bid)
        
        # Start at dealer and advance until the bid is reached
        last_bidder_index = self.bidders.index(self.dealer)
        for i in range(bid_index_in_sequence):
             last_bidder_index = (last_bidder_index + 1) % 4
             
        last_bidder = self.bidders[last_bidder_index]
        
        return last_bid, last_bidder, last_bidder == self.user_pos or last_bidder == self._get_partner_pos(self.user_pos)
    
    def _get_partner_pos(self, pos):
        """Returns the position of the partner (N or S, E or W)."""
        return 'S' if pos == 'N' else 'N' if pos == 'S' else 'W' if pos == 'E' else 'E'

    def _update_sequence(self, bid):
        """Updates the auction sequence and checks for termination."""
        self.current_sequence.append(bid)
        
        if bid != 'P':
            self.consecutive_passes = 0
            # Simple check for establishing a trump suit (needs more complex logic in a full app)
            if bid in ['1S', '1H', '2S', '2H', '3S', '3H', '4S', '4H']:
                self.trump_suit = bid[-1]
            elif bid in ['1C', '1D', '2C', '2D', '3C', '3D', '4C', '4D']:
                self.trump_suit = bid[-1]

        else:
            self.consecutive_passes += 1
            
        self.bidder_index += 1

        # Auction ends when 3 consecutive passes occur *after* an initial bid
        if len(self.current_sequence) >= 4 and self.consecutive_passes >= 3:
            return True # Auction ends
        
        return False # Auction continues

    def explain_bid(self, bid_string, current_bidder):
        """
        Explains the meaning, range, and shape of a bid made by Partner or Opponent.
        """
        explanation = {
            "meaning": "Natural, non-forcing.",
            "hcp_range": "Variable.",
            "implied_shape": "Unspecified.",
            "convention": "None"
        }
        
        bid_string = bid_string.upper()
        last_bid, last_bidder, is_partner_last = self._get_last_bid_info()
        
        # If this is the very first bid (opening)
        if not last_bid:
            if bid_string == '1NT':
                hcp_low, hcp_high, shape = self.SAYC_RANGES['1NT_OPEN']
                explanation.update({"meaning": "Balanced Opening.", "hcp_range": f"{hcp_low}-{hcp_high} HCP", "implied_shape": shape})
            elif bid_string in ['1C', '1D', '1H', '1S']:
                explanation.update({"meaning": f"Natural Opening in {bid_string[-1]}.", "hcp_range": "12-21+ HCP", "implied_shape": "5+ cards in Major, 4+ in Minor (or 3+ in C)." })
            return explanation

        # --- CONVENTION LOGIC (Highest Priority) ---
        if is_partner_last and last_bid == '1NT':
            if bid_string == '2C':
                explanation.update({"convention": "Stayman", "meaning": "Artificial, asking for 4-card major suits.", "hcp_range": "8+ HCP", "implied_shape": "At least one 4-card Major."})
                return explanation
            if bid_string == '2D':
                explanation.update({"convention": "Jacoby Transfer to Hearts", "meaning": "Artificial, forces 2H. Promises 5+ Hearts.", "hcp_range": "8+ HCP", "implied_shape": "5+ Hearts."})
                return explanation
            if bid_string == '2H':
                explanation.update({"convention": "Jacoby Transfer to Spades", "meaning": "Artificial, forces 2S. Promises 5+ Spades.", "hcp_range": "8+ HCP", "implied_shape": "5+ Spades."})
        
        if bid_string == '4NT':
            if self.trump_suit:
                explanation.update({"convention": "Key Card Blackwood (RKCB 1430)", "meaning": f"Asking for Key Cards (4 Aces + {self.trump_suit} King).", "hcp_range": "Slam interest."})
                return explanation
            elif last_bid in ['1NT', '2NT', '3NT']:
                explanation.update({"convention": "Quantitative NT", "meaning": "Invitational to 6NT.", "hcp_range": "18-19 HCP (after 1NT)"})
                return explanation
        
        if bid_string == '4C' and last_bid in ['1NT', '2NT', '3NT']:
            explanation.update({"convention": "Gerber", "meaning": "Asking for Aces (after a NT agreement).", "hcp_range": "Slam interest."})
            return explanation

        # --- NATURAL RESPONSE / OVERCALL LOGIC ---
        
        if current_bidder != last_bidder and not is_partner_last: # Overcall / Double
            if bid_string == 'X':
                hcp_low, hcp_high, shape = self.SAYC_RANGES['TAKEOUT_DOUBLE']
                explanation.update({"meaning": "Takeout Double (not for penalty).", "hcp_range": f"{hcp_low}+ TP", "implied_shape": shape})
                return explanation
            elif bid_string in ['1S', '2H', '3D', '4C']:
                hcp_low, hcp_high, shape = self.SAYC_RANGES['OVERCALL']
                explanation.update({"meaning": f"Natural Overcall in {bid_string[-1]}.", "hcp_range": f"{hcp_low}-{hcp_high} TP", "implied_shape": "Good 5+ card suit."})
                return explanation

        if is_partner_last and last_bid in ['1C', '1D', '1H', '1S']: # Suit Response
            if len(bid_string) == 2 and bid_string[1] == last_bid[1] and bid_string[0] == '2': # Simple Raise 
                hcp_low, hcp_high, shape = self.SAYC_RANGES['SIMPLE_RAISE']
                explanation.update({"meaning": f"Simple Non-forcing Raise in {bid_string[-1]}.", "hcp_range": f"{hcp_low}-{hcp_high} TP", "implied_shape": shape})
                return explanation
            
        # Default for pass or other bids
        if bid_string == 'P':
            return {"meaning": "Pass.", "hcp_range": "Does not meet requirements for a bid.", "implied_shape": "N/A", "convention": "None"}
        
        return explanation


    def suggest_bid(self, user_hand, vulnerability):
        """
        Provides the optimal bid and justification for the User (South).
        user_hand: {'hcp': X, 'dist': [S, H, D, C]}
        """
        hcp = user_hand['hcp']
        dist = user_hand['dist']
        
        # Calculate Total Points (HCP + simple length points)
        tp = hcp + sum([max(0, d - 4) for d in dist])

        last_bid, last_bidder, is_partner_last = self._get_last_bid_info()
        
        # --- PHASE 1: OPENING BID (If User is the first to bid meaningfully) ---
        if not last_bid:
            if hcp >= 15 and hcp <= 17 and max(dist) <= 5: 
                return '1NT', f"Open 1NT. You have a balanced hand with 15-17 HCP."
            
            if hcp >= 12:
                # Prioritize 5-card Majors
                if dist[0] >= 5: return '1S', "Open 1 Spades (5+ cards, 12+ HCP)."
                if dist[1] >= 5: return '1H', "Open 1 Hearts (5+ cards, 12+ HCP)."
                # Prioritize 4-card Diamonds over 3-card Clubs
                if dist[2] >= 4: return '1D', "Open 1 Diamond (4+ cards, 12+ HCP)."
                if dist[3] >= 3: return '1C', "Open 1 Club (3+ cards, 12+ HCP)."
            
            return 'Pass', "You have less than 12 HCP, so the correct opening call is Pass."

        # --- PHASE 2: CONVENTIONAL RESPONSES (After Partner's Bid) ---
        if is_partner_last:
            if last_bid == '1NT':
                if hcp < 8:
                     return 'Pass', "Pass. You lack the 8 HCP minimum for a forcing response to 1NT."
                     
                # Stayman Check (4-card Major)
                if dist[0] >= 4 or dist[1] >= 4:
                    return '2C', "Bid 2 Clubs (Stayman) to ask for partner's 4-card Majors."
                # Jacoby Transfers
                if dist[1] >= 5: 
                    return '2D', "Bid 2 Diamonds (Jacoby Transfer) to show 5+ Hearts."
                if dist[0] >= 5: 
                    return '2H', "Bid 2 Hearts (Jacoby Transfer) to show 5+ Spades."
                
                # NT bids
                if hcp >= 13:
                    return '3NT', "Bid 3NT for game. You have 13+ HCP and a balanced hand without a Major fit."
                if hcp >= 10 and hcp <= 12:
                    return '2NT', "Bid 2NT (Invitational). You have 10-12 HCP for a possible 3NT."

            # Blackwood / Gerber Response (Simplified logic)
            if last_bid == '4NT' and self.trump_suit: 
                # Very simple Key Card count (HCP for demo)
                key_cards = hcp // 7 
                if key_cards in [0, 3]: return '5C', "Responding to RKCB: 0 or 3 Key Cards."
                if key_cards in [1, 4]: return '5D', "Responding to RKCB: 1 or 4 Key Cards."
                if key_cards == 2: return '5H', "Responding to RKCB: 2 Key Cards (simplified)."

        # --- PHASE 3: NATURAL RESPONSES / RAISES (After Partner's Opening Suit) ---
        if is_partner_last and last_bid in ['1C', '1D', '1H', '1S']:
            partner_suit = last_bid[-1]
            p_idx = self.SUIT_MAP[partner_suit]
            
            # Find a Fit (3+ cards needed for major, 4+ for minor raise)
            if dist[p_idx] >= 3:
                combined_tp = 12 + tp # Assume partner minimum 12
                
                if combined_tp >= 25:
                    return f'4{partner_suit}', f"Bid game: 4{partner_suit}. You have a fit and 25+ combined TP."
                if combined_tp >= 22:
                    return f'3{partner_suit}', f"Bid 3{partner_suit} (Invitational). You have a fit and 22-24 combined TP."
                if hcp >= 6:
                    return f'2{partner_suit}', f"Simple Non-forcing Raise to 2{partner_suit} (6-9 TP)."

            # New Suit (No Fit)
            if hcp >= 6:
                # Bid 1 Major over 1 Minor
                if last_bid in ['1C', '1D']:
                    if dist[0] >= 4: return '1S', "Bid your 4+ card Major, 1 Spades (forcing)."
                    if dist[1] >= 4: return '1H', "Bid your 4+ card Major, 1 Hearts (forcing)."

                # Bid 1NT if no fit and not enough for a new suit/higher level
                return '1NT', "No fit, 6-9 HCP, balanced. Non-forcing 1NT."

        # --- PHASE 4: COMPETITION (After Opponent's Bid) ---
        if last_bidder in ['E', 'W'] and last_bid != 'P':
            # Takeout Double
            if hcp >= 12 and random.choice([True, False]): # Simple demo of suitability
                return 'X', "Bid Takeout Double. You have 12+ HCP, shortage in opponent's suit implied."
            
            # Simple Overcall
            suits = sorted([(dist[i], s) for i, s in enumerate(['S', 'H', 'D', 'C'])], reverse=True)
            if suits[0][0] >= 5 and hcp >= 8:
                return f'1{suits[0][1]}', f"Overcall in your best 5+ card suit, 1{suits[0][1]} (8+ TP)."
            
            # Default to Pass if defense/competition is too risky
            return 'Pass', "Pass. Hand too weak or bid too high to compete safely."

        # Default Safety Net
        return 'Pass', "Pass. No clear action is suggested by the SAYC system at this point."


## Helper for Streamlit: Convert dist array to a string
def format_hand_distribution(dist):
    return f"S:{dist[0]} H:{dist[1]} D:{dist[2]} C:{dist[3]}"
