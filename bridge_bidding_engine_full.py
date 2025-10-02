
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bridge Bidding Engine — Full (Colab-ready: points + slams up to 7NT)
===================================================================
- Run this cell in Google Colab (or any Python 3 environment).
- Interactive loop: you input your hand once, then type other players' bids.
- On your turn, engine suggests bids with POINT RANGES + reasons.
- Covers openings, responses, overcalls, doubles/redoubles.
- NT conventions: Stayman, Jacoby transfers, quantitative 4NT.
- Slam tools: Blackwood/RKCB (auto-replies), Gerber over NT (auto-replies).
- Drives to game/small slam/grand slam when point thresholds justify it.
- Ends when three consecutive passes occur.

Disclaimer: simplified SAYC-style rules. Seat/vulnerability/style nuances not modeled.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional

RANKS = "23456789TJQKA"
SUITS = ["S","H","D","C"]
HCP_MAP = dict(zip(RANKS, [0,0,0,0,0,0,0,0,0,1,2,3,4]))

# ---- Basic hand math ----
def parse_hand_string(s: str) -> List[str]:
    s = s.strip().upper().replace("-", "")
    if "." in s and " " not in s:
        parts = s.split(".")
        if len(parts)!=4: raise ValueError("Use S.H.D.C groups like 'J643.AJ54.A7.T97'")
        out=[]
        for ranks, suit in zip(parts, SUITS):
            for r in ranks:
                if r not in RANKS: raise ValueError("Bad rank "+r)
                out.append(r+suit)
        return out
    toks = [t for t in s.replace("\n"," ").split(" ") if t]
    if len(toks)!=13: raise ValueError(f"Expected 13 cards, got {len(toks)}")
    out=[]
    for t in toks:
        if len(t)!=2: raise ValueError(f"Card '{t}' must be 2 chars like AS, TD")
        r,su=t[0],t[1]
        if r not in RANKS or su not in "SHDC": raise ValueError(f"Bad card '{t}'")
        out.append(r+su)
    return out

def hcp(cards: List[str]) -> int:
    return sum(HCP_MAP[c[0]] for c in cards)

def suit_len(cards: List[str], suit: str) -> int:
    return sum(1 for c in cards if c[1]==suit)

def shape(cards: List[str]) -> Tuple[int,int,int,int]:
    return (suit_len(cards,"S"), suit_len(cards,"H"), suit_len(cards,"D"), suit_len(cards,"C"))

def is_balanced(sh):
    return sorted(sh) in [[3,3,3,4],[2,3,4,4],[2,3,3,5]]

def count_aces(cards: List[str]) -> int:
    return sum(1 for c in cards if c[0]=="A")

@dataclass
class Hand:
    cards: List[str]
    hcp: int = field(init=False)
    shape: Tuple[int,int,int,int] = field(init=False)
    def __post_init__(self):
        self.hcp = hcp(self.cards)
        self.shape = shape(self.cards)

@dataclass
class Suggestion:
    bid: str
    reason: str

# ---- Partner range heuristics ----
def partner_range_guess(auction: List[str]) -> Tuple[int,int]:
    if not auction: return (0,0)
    last = auction[-1]
    if last=="1NT": return (15,17)
    if last=="2NT": return (20,21)
    if last in ["1S","1H","1D","1C"]: return (12,21)
    if last=="2C": return (22,40)
    if last in ["2NT"]: return (18,19)
    if last in ["3NT"]: return (25,27)
    return (0,20)

# ---- Core suggestion logic ----
def opening_suggestions(hand: Hand)->List[Suggestion]:
    H = hand.hcp; S,Ht,D,C = hand.shape
    out=[]

    if H>=22:
        return [Suggestion("2C","22+ HCP — strong, artificial, forcing opening.")]

    if is_balanced(hand.shape):
        if 20<=H<=21: out.append(Suggestion("2NT","20–21 HCP, balanced."))
        if 15<=H<=17: out.append(Suggestion("1NT","15–17 HCP, balanced; no 5-card major."))

    # Preempts (majors)
    if 6<=H<=10 and Ht>=6: out.append(Suggestion("2H","Weak two: 6+♥, 6–10 HCP."))
    if 6<=H<=10 and S>=6: out.append(Suggestion("2S","Weak two: 6+♠, 6–10 HCP."))
    if 5<=H<=10 and Ht>=7: out.append(Suggestion("3H","Preempt: 7+♥, 5–10 HCP."))
    if 5<=H<=10 and S>=7: out.append(Suggestion("3S","Preempt: 7+♠, 5–10 HCP."))

    # 1-level suit openings
    if 12<=H<=21:
        if S>=5 or Ht>=5:
            if S>=5 and S>=Ht: out.append(Suggestion("1S", f"{H} HCP and 5+♠."))
            if Ht>=5 and Ht>S: out.append(Suggestion("1H", f"{H} HCP and 5+♥."))
        else:
            if D>=C: out.append(Suggestion("1D", f"{H} HCP, no 5-card major; longer/equal ♦."))
            else: out.append(Suggestion("1C", f"{H} HCP, no 5-card major; longer ♣."))

    if H<12 and not out:
        out=[Suggestion("Pass", f"{H} HCP — no suitable preempt.")]

    order = {"2C":0,"2NT":1,"1NT":2,"1S":3,"1H":3,"1D":4,"1C":5,"3S":6,"3H":6,"2S":7,"2H":7,"Pass":9}
    uniq = {s.bid:s for s in out}
    return [uniq[k] for k in sorted(uniq, key=lambda b:order.get(b,8))]

def overcall_suggestions(rhs_open:str, hand:Hand)->List[Suggestion]:
    H=hand.hcp; S,Ht,D,C=hand.shape; out=[]
    if rhs_open in ["1NT","2NT"]:
        if rhs_open=="1NT" and H>=15: return [Suggestion("X","Penalty double vs 1NT (≈15+ HCP).")]
        return [Suggestion("Pass","No NT penalty double available by rule.")]
    opener_suit = rhs_open[-1]
    if is_balanced(hand.shape) and H>=19:
        out.append(Suggestion("2NT","19–21 balanced overcall with stopper(s)."))
    if is_balanced(hand.shape) and 15<=H<=18:
        out.append(Suggestion("1NT","15–18 balanced overcall with stopper(s)."))
    # suit overcall
    for suit, ln in zip(SUITS, (S,Ht,D,C)):
        if ln>=5:
            level = "1" if rhs_open[0]=="1" and suit!=opener_suit else "2"
            if 8<=H<=16: out.append(Suggestion(level+suit, f"{level}-level overcall: {ln}-card {suit}, {H} HCP."))
            if 6<=H<=10 and ln>=6 and level in ["2","3"]:
                out.append(Suggestion("JUMP "+level+suit, f"Weak jump overcall: {ln}-card {suit}, {H} HCP."))
    # takeout double
    ln_open = {"S":S,"H":Ht,"D":D,"C":C}[opener_suit]
    if H>=12 and ln_open<=2:
        out.append(Suggestion("X","Takeout double: 12+ HCP, short in opener’s suit; support for unbid."))
    if not out: out=[Suggestion("Pass","No safe overcall/double by these rules.")]
    return out

def responder_suggestions(opener_bid:str, hand:Hand, auction:List[str])->List[Suggestion]:
    h=hand.hcp; S,Ht,D,C=hand.shape; out=[]
    if opener_bid=="1NT":
        if Ht>=5: out.append(Suggestion("2D","Transfer to ♥ (5+ hearts)."))
        if S>=5: out.append(Suggestion("2H","Transfer to ♠ (5+ spades)."))
        if (S>=4 or Ht>=4) and h>=8: out.append(Suggestion("2C","Stayman — asks for 4-card major (8+ HCP)."))
        if S<5 and Ht<5:
            min_tot = h+15; max_tot = h+17
            if h<=7: out.append(Suggestion("Pass","0–7 HCP, no 5-card major."))
            if 8<=h<=9: out.append(Suggestion("2NT","Invite: 8–9 HCP (combined ≈%d–%d)"%(min_tot,max_tot)))
            if h>=10:
                out.append(Suggestion("3NT","Game: 10+ HCP opposite 1NT (combined ≈%d–%d)"%(min_tot,max_tot)))
                if h>=16: out.append(Suggestion("4NT","Quantitative: invite 6NT with 16+ opposite 15–17."))
                if h>=20: out.append(Suggestion("6NT","Small slam tendency (combined ≈%d–%d)"%(h+15,h+17)))
                if h>=21: out.append(Suggestion("7NT","Grand slam tendency (combined ≈%d–%d)"%(h+15,h+17)))
        if h>=13: out.append(Suggestion("4C","Gerber: ask for aces over NT (slam interest)."))
        return out

    if opener_bid in ["1S","1H"]:
        trump = "S" if opener_bid=="1S" else "H"; ln = S if trump=="S" else Ht
        if ln>=3:
            if 6<=h<=9: out.append(Suggestion(f"2{trump}", f"Single raise: {ln} trumps, 6–9 HCP."))
            if 10<=h<=12: out.append(Suggestion(f"3{trump}", f"Limit raise: {ln}+ trumps, 10–12 HCP."))
            if h>=13:
                out.append(Suggestion(f"4{trump}", f"Game raise: {ln}+ trumps, 13+ HCP (≈25+ combined)."))
                out.append(Suggestion("2NT","Jacoby 2NT: GF raise with 4+ support, 13+ HCP (slam interest)."))
        if 6<=h<=10: out.append(Suggestion("1NT","6–10, no fit (semi-forcing)."))
        for suit,ln2 in [("H",Ht),("S",S),("D",D),("C",C)]:
            if suit!=trump and ln2>=4 and h>=10:
                out.append(Suggestion(f"2{suit}", f"New suit: 10+ HCP, 4+ {suit}."))
        if not out: out=[Suggestion("Pass","Too weak.")]
        return out

    if opener_bid in ["1D","1C"]:
        if S>=4 and h>=6: out.append(Suggestion("1S","4+ spades, 6+ HCP."))
        if Ht>=4 and h>=6: out.append(Suggestion("1H","4+ hearts, 6+ HCP."))
        if S<4 and Ht<4 and 6<=h<=10: out.append(Suggestion("1NT","6–10 balanced, no 4-card major."))
        if opener_bid=="1D" and D>=4 and 6<=h<=9: out.append(Suggestion("2D","Raise ♦, 6–9."))
        if opener_bid=="1C" and C>=4 and 6<=h<=9: out.append(Suggestion("2C","Raise ♣, 6–9."))
        if not out: out=[Suggestion("Pass","Too weak.")]
        return out

    if opener_bid=="2NT":
        min_tot = h+20; max_tot = h+21
        if h<=3: return [Suggestion("Pass","Very weak opposite 20–21.")]
        out=[Suggestion("3NT","Game opposite 20–21 (combined ≈%d–%d)"%(min_tot,max_tot))]
        if h>=5: out.append(Suggestion("4C","Gerber: ask for aces (slam interest)."))
        if h>=11: out.append(Suggestion("4NT","Quantitative: invite 6NT (combined ≈%d–%d)"%(min_tot,max_tot)))
        if h>=13: out.append(Suggestion("6NT","Small slam tendency (combined ≈%d–%d)"%(min_tot,max_tot)))
        if h>=16: out.append(Suggestion("7NT","Grand slam tendency (combined ≈%d–%d)"%(min_tot,max_tot)))
        return out

    if opener_bid=="2C":
        return [Suggestion("2D","Waiting (artificial), game forcing.")]

    return [Suggestion("Pass","No rule matched.")]

# ---- Slam auto-replies ----
def auto_reply_rkcb(our_cards: List[str]) -> str:
    aces = count_aces(our_cards)
    mapping = {0:"5C",1:"5D",2:"5H",3:"5S",4:"5C"}
    return mapping.get(aces, "5C")

def auto_reply_gerber(our_cards: List[str]) -> str:
    aces = count_aces(our_cards)
    mapping = {0:"4D",1:"4H",2:"4S",3:"4NT",4:"4D"}
    return mapping.get(aces, "4D")

def nt_context_exists(auction: List[str]) -> bool:
    return any(b in ["1NT","2NT","3NT"] for b in auction)

def major_fit_agreed(auction: List[str]) -> Optional[str]:
    majors = ["H","S"]
    bids = [b for b in auction if b not in ["Pass","X","XX"]]
    for M in majors:
        if any(b in [f"2{M}",f"3{M}",f"4{M}"] for b in bids):
            return M
    return None

# ---- Advise your bid (your turn only) ----
def advise_your_bid(your_hand:Hand, auction:List[str]) -> List[Suggestion]:
    # Redouble opportunity
    if auction and auction[-1]=="X":
        if your_hand.hcp>=10:
            return [Suggestion("XX","Redouble with 10+ HCP after partner's double.")]
        else:
            return [Suggestion("Bid best suit","Runout after partner's double (not fully modeled).")]

    # Auto replies to ace-asking conventions
    if auction and auction[-1]=="4NT" and major_fit_agreed(auction):
        reply = auto_reply_rkcb(your_hand.cards)
        return [Suggestion(reply, f"Auto-reply to RKCB (4NT): showing aces ({reply}).")]
    if auction and auction[-1]=="4C" and nt_context_exists(auction):
        reply = auto_reply_gerber(your_hand.cards)
        return [Suggestion(reply, f"Auto-reply to Gerber (4♣ over NT): showing aces ({reply}).")]

    # Identify last real call
    real_calls = [b for b in auction if b not in ["Pass","X","XX"]]
    if real_calls:
        last = real_calls[-1]
        # If odd number of total calls, assume RHO acted last => overcall space
        if (len(auction) % 2)==1:
            return overcall_suggestions(last, your_hand)
        else:
            # Partner acted last => responder logic
            sugs = responder_suggestions(last, your_hand, auction)
            pmin,pmax = partner_range_guess(auction)
            min_tot, max_tot = pmin+your_hand.hcp, pmax+your_hand.hcp
            fit = major_fit_agreed(auction)
            if fit and min_tot>=33:
                sugs.append(Suggestion("4NT", f"RKCB (slam try in {'♥' if fit=='H' else '♠'}); combined ≈%d–%d"%(min_tot,max_tot)))
            if nt_context_exists(auction) and min_tot>=32:
                sugs.append(Suggestion("4NT","Quantitative: invite 6NT (combined high totals)."))
            if nt_context_exists(auction) and min_tot>=33:
                sugs.append(Suggestion("6NT", "Small slam tendency (combined ≈%d–%d)"%(min_tot,max_tot)))
            if nt_context_exists(auction) and min_tot>=37:
                sugs.append(Suggestion("7NT", "Grand slam tendency (combined ≈%d–%d)"%(min_tot,max_tot)))
            return sugs
    else:
        # No one opened yet -> it's your opening
        return opening_suggestions(your_hand)

# ---- Interactive loop ----
SEATS = ["N","E","S","W"]
NEXT = {"N":"E","E":"S","S":"W","W":"N"}

def run_loop():
    print("== Bridge Bidding Engine — Full (Colab-ready) ==")
    while True:
        you = input("Your seat (N/E/S/W): ").strip().upper()
        if you in SEATS: break
    while True:
        dealer = input("Dealer/Who starts (N/E/S/W): ").strip().upper()
        if dealer in SEATS: break
    hstr = input("Enter YOUR 13 cards (e.g., 'J643.AJ54.A7.T97' or 'AS KH QH JD ...'): ").strip()
    your = Hand(parse_hand_string(hstr))
    print(f"Your HCP: {your.hcp}, Shape (S,H,D,C): {your.shape} — Balanced? {'Yes' if is_balanced(your.shape) else 'No'}")

    turn = dealer
    auction: List[str] = []
    passes = 0

    while True:
        print("\nAuction so far:", " ".join(auction) if auction else "(none)")
        print(f"Turn: {turn}")
        if turn==you:
            sugs = advise_your_bid(your, auction)
            print("Your suggestions (with points):")
            for i,s in enumerate(sugs,1):
                print(f"  {i}) {s.bid} — {s.reason}")
            call = input("Your call (Enter = choose 1): ").strip().upper()
            if call=="":
                call = sugs[0].bid.upper()
            print(f"You bid: {call}")
            auction.append(call)
        else:
            call = input(f"Enter {turn}'s call (e.g., PASS, 1S, X, 2NT, 4NT, 4C) [default PASS]: ").strip().upper() or "PASS"
            auction.append(call)

        if auction[-1]=="PASS":
            passes += 1
        else:
            passes = 0

        if passes>=3 and len(auction)>=4:
            print("\n=== Auction finished ===")
            print("Final auction:", " ".join(auction))
            break

        turn = NEXT[turn]

# If running in Colab/Jupyter, call run_loop() directly or import and call later.
if __name__=="__main__":
    run_loop()
