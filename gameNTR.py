# -*- coding: utf-8 -*-
import os
import sys
import time
import random
import threading
import math
import platform
import select

# Try to import termios and tty (Linux/Mac). If on Windows, will fail gracefully.
if platform.system() != "Windows":
    import termios
    import tty

########################################
# Conditional: enable ANSI codes on Windows
########################################
if platform.system() == "Windows":
    os.system("")  # Enable ANSI escape codes on Windows if possible

########################################
# Cross-platform char read:
# - Windows -> msvcrt
# - Linux/Mac -> select + termios
########################################
if platform.system() == "Windows":
    import msvcrt
    def get_char_nonblocking(timeout=0.05):
        """Return a single character if available on Windows, else None."""
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            if msvcrt.kbhit():
                return msvcrt.getwch()
            time.sleep(0.01)
        return None
else:
    def get_char_nonblocking(timeout=0.05):
        """Return a single character if available on Linux/Mac, else None."""
        # Save old terminal settings
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            # Switch to cbreak mode, non-blocking
            tty.setcbreak(sys.stdin.fileno())
            rlist, _, _ = select.select([sys.stdin], [], [], timeout)
            if rlist:
                return sys.stdin.read(1)
            return None
        finally:
            # Restore old settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

##########################################################
# 0) Define clamp, update_timer, and cross-platform input
##########################################################

def clamp(value, low, high):
    """Keeps 'value' in [low, high]."""
    return max(low, min(value, high))

def update_timer(total_time, start_time, penalty, stop_event):
    """
    Displays a timer at bottom line, factoring in penalty.
    If time runs out, sets stop_event so synergy ends.
    """
    try:
        lines = os.get_terminal_size().lines
    except:
        lines = 24
    while not stop_event.is_set():
        elapsed = (time.time() - start_time) + penalty[0]
        remain = total_time - elapsed
        if remain < 0:
            remain = 0
        sys.stdout.write(f"\033[{lines};1HTime remaining: {int(remain)}s   ")
        sys.stdout.flush()
        if remain <= 0:
            stop_event.set()
            break
        time.sleep(1)

def get_input_nonblocking(prompt, total_time, start_time, penalty):
    """
    Cross-platform non-blocking input with a time check. 
    If time runs out, returns None.
    'penalty' is a list with one float for time penalties.
    """
    sys.stdout.write(prompt)
    sys.stdout.flush()
    user_str = ""

    while True:
        # Check time
        if time.time() - start_time + penalty[0] >= total_time:
            return None

        # Read one char if available
        ch = get_char_nonblocking(0.05)
        if ch is not None:
            # Windows getwch() returns '\r' for Enter, 
            # Linux typically returns '\n'. Also handle backspace, etc.
            if ch in ("\r", "\n"):
                sys.stdout.write("\n")
                sys.stdout.flush()
                break
            # Handle backspace on Windows ('\b') or Linux ('\x7f' often for DEL)
            elif ch in ("\b", "\x7f"):
                if user_str:
                    user_str = user_str[:-1]
                    # Erase on screen
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            else:
                user_str += ch
                sys.stdout.write(ch)
                sys.stdout.flush()

        time.sleep(0.01)

    return user_str.strip()

##########################################################
# A) Print Stat Explanations
##########################################################

def print_stat_explanations():
    print("\n=== Explanation of Stats ===")
    print("PLAYER (MC) STATS:")
    print("1. Presence (PRS) – The ability to command attention and shape first impressions.")
    print("2. Adaptability (ADP) – Flexibility in social/personal encounters.")
    print("3. Instinct (INS) – Gut feeling, noticing subtext, hidden cues.")
    print("4. Will (WIL) – Determination, resisting doubts or manipulation.")
    print("5. Projection (PJT) – How you present yourself to others.")
    print("6. Conviction (CVT) – Certainty in your actions, confidence under pressure.")
    print("7. Resonance (RSN) – Emotional impact you leave on others.")
    print("8. Spirit (SPT) – A hidden ‘luck’ or ‘fate’ stat shaping synergy. Higher => more synergy; lower => less.\n")
    
    print("NTR VICTIM (RIVAL) STATS:")
    print("1. Social Command (SCM) – Their control in social/relationship spheres.")
    print("2. Embedded Trust (EMT) – How much the Target sees them as reliable.")
    print("3. Instinctive Awareness (IAW) – Quickly sensing suspicious behavior.")
    print("4. Relational Grip (RLG) – Their deep emotional/financial hold on the Target.")
    print("5. Emotional Leverage (ELG) – Ability to guilt or bond with the Target.")
    print("6. Narrative Control (NCT) – Spinning events in their favor.")
    print("7. Relational Pull (RLP) – The raw magnetism that keeps the Target drawn to them.\n")
    
    print("NTR TARGET STATS:")
    print("1. Emotional Anchoring (EAC) – Their emotional bond to the Rival.")
    print("2. Thrill Inclination (THI) – How much they crave risk/taboo.")
    print("3. Autonomy Drive (ATD) – Valuing independence vs. being led.")
    print("4. Internal Justification (IJT) – How they rationalize potential cheating.")
    print("5. Romantic Worldview (RMW) – Traditional vs. alternative relationship ideals.")
    print("6. Social Masking (SOM) – Hiding true feelings from others (including you).")
    print("7. Response Momentum (RPM) – Speed at which they escalate emotionally.\n")
    print("=== End of Stats Explanation ===\n")
    input("Press Enter to continue...")

##########################################################
# B) Bell-Curve Rolls
##########################################################

def roll_stat_bell(mu=32, sigma=10):
    """
    Bell-curve around mu=32, stdev=10, clamp in [1..64].
    """
    val = int(random.gauss(mu, sigma))
    return max(1, min(64, val))

def roll_stat_bell_chosen(mu=40, sigma=10):
    """
    For chosen MC stats => bell around 40, clamp [20..64].
    """
    v = int(random.gauss(mu, sigma))
    if v < 20:
        v = 20
    elif v > 64:
        v = 64
    return v

##########################################################
# C) Fuzzy Matching for MC Stats
##########################################################

STAT_NAME_MAP = {
    "presence (prs)": "Presence (PRS)",
    "presence":        "Presence (PRS)",
    "prs":             "Presence (PRS)",

    "adaptability (adp)": "Adaptability (ADP)",
    "adaptability":       "Adaptability (ADP)",
    "adp":                "Adaptability (ADP)",

    "instinct (ins)": "Instinct (INS)",
    "instinct":       "Instinct (INS)",
    "ins":            "Instinct (INS)",

    "will (wil)": "Will (WIL)",
    "will":       "Will (WIL)",
    "wil":        "Will (WIL)",

    "projection (pjt)": "Projection (PJT)",
    "projection":       "Projection (PJT)",
    "pjt":              "Projection (PJT)",

    "conviction (cvt)": "Conviction (CVT)",
    "conviction":       "Conviction (CVT)",
    "cvt":              "Conviction (CVT)",

    "resonance (rsn)": "Resonance (RSN)",
    "resonance":       "Resonance (RSN)",
    "rsn":             "Resonance (RSN)",

    "spirit (spt)": "Spirit (SPT)",
    "spirit":       "Spirit (SPT)",
    "spt":          "Spirit (SPT)"
}

def levenshtein_distance(s1, s2):
    if not s1: 
        return len(s2)
    if not s2: 
        return len(s1)
    if s1[0] == s2[0]:
        return levenshtein_distance(s1[1:], s2[1:])
    return 1 + min(
        levenshtein_distance(s1[1:], s2),
        levenshtein_distance(s1, s2[1:]),
        levenshtein_distance(s1[1:], s2[1:])
    )

def guess_stat_name(user_input):
    lower_in = user_input.strip().lower()
    if lower_in in STAT_NAME_MAP:
        return STAT_NAME_MAP[lower_in]
    best_dist = 9999
    best_val = None
    for possible_key, val in STAT_NAME_MAP.items():
        dist = levenshtein_distance(lower_in, possible_key)
        if dist < best_dist:
            best_dist = dist
            best_val = val
    if best_dist > len(user_input)*2:
        return None
    return best_val

##########################################################
# D) Choose Stats
##########################################################

def choose_stats():
    stats_list = [
        "Presence (PRS)",
        "Adaptability (ADP)",
        "Instinct (INS)",
        "Will (WIL)",
        "Projection (PJT)",
        "Conviction (CVT)",
        "Resonance (RSN)",
        "Spirit (SPT)"
    ]

    while True:
        chosen_stats = []
        max_spirit = False

        print("\n=== Character Creation: Choose Your Core Stats ===")
        print("Pick 4 total, or only 2 if Spirit (SPT) is included.")
        print("Spirit can be first or second if you have <2 picks so far.\n")
        print("Type abbreviation or full name. E.g. 'prs','presence'...\n")
        print("Available Stats:")
        for s in stats_list:
            print(" -", s)

        while True:
            needed = 2 if max_spirit else 4
            if len(chosen_stats) >= needed:
                break
            user_in = input("\nPick a stat: ").strip()
            if not user_in:
                print("Empty input, try again.")
                continue
            final_s = guess_stat_name(user_in)
            if not final_s:
                print(f"Could not guess from '{user_in}'. Try again.")
                continue

            if final_s == "Spirit (SPT)":
                # If we already have 2 picks => can't pick spirit
                if len(chosen_stats) >= 2:
                    print("Cannot pick Spirit now (2+ picks).")
                    continue
                if not max_spirit:
                    max_spirit = True
                    chosen_stats.append("Spirit (SPT)")
                    print("Spirit chosen. 1 more stat total now.")
                else:
                    print("Spirit is already chosen.")
            else:
                if final_s in chosen_stats:
                    print("Already chosen.")
                else:
                    chosen_stats.append(final_s)
                    print(f"{final_s} chosen.")

        print("\nYou picked:")
        for cst in chosen_stats:
            print(" -", cst)
        confirm = input("\nAre you sure? (Y/N): ").strip().lower()
        if confirm == 'y':
            break
        else:
            print("Resetting picks. Press Enter to pick again.")
            input()

    final_stats = {}
    for s in stats_list:
        if s in chosen_stats:
            v = roll_stat_bell_chosen(mu=40, sigma=10)  # ~[20..64]
        else:
            v = roll_stat_bell(mu=32, sigma=10)         # ~[1..64]
        final_stats[s] = v

    print("\n=== Final MC Stats (1..64) ===")
    print("(Chosen => ~[20..64], unchosen => [1..64], both bell-curve).")
    for s in stats_list:
        print(f" {s}: {final_stats[s]}")
    input("\nPress Enter to proceed...")

    return final_stats

##########################################################
# E) Rival (Victim) & Target Stats
##########################################################

def generate_ntr_victim_stats():
    return {
        "Social Command (SCM)": roll_stat_bell(),
        "Embedded Trust (EMT)": roll_stat_bell(),
        "Instinctive Awareness (IAW)": roll_stat_bell(),
        "Relational Grip (RLG)": roll_stat_bell(),
        "Emotional Leverage (ELG)": roll_stat_bell(),
        "Narrative Control (NCT)": roll_stat_bell(),
        "Relational Pull (RLP)": roll_stat_bell()
    }

def generate_ntr_target_stats():
    return {
        "Emotional Anchoring (EAC)": roll_stat_bell(),
        "Thrill Inclination (THI)": roll_stat_bell(),
        "Autonomy Drive (ATD)": roll_stat_bell(),
        "Internal Justification (IJT)": roll_stat_bell(),
        "Romantic Worldview (RMW)": roll_stat_bell(),
        "Social Masking (SOM)": roll_stat_bell(),
        "Response Momentum (RPM)": roll_stat_bell()
    }

##########################################################
# F) Sibling Setup
##########################################################

def describe_attire(gender):
    if gender == "male":
        return "loose sleep shorts and a comfortable t-shirt"
    elif gender == "female":
        return "light, somewhat revealing sleepwear"
    else:
        return "casual lounge attire that doesn't cover much"

def sibling_label(age_status):
    if age_status == "older":
        return "older sibling"
    elif age_status == "younger":
        return "younger sibling"
    else:
        return "twin sibling"

##########################################################
# G) Synergy with Detailed Breakdown
##########################################################

def synergy_convo(mc_stats, target_stats, victim_stats):
    """
    Hard synergy approach:
      baseline=2
      Gains => ratio * 1.2
      Rival penalty => ratio * 2.0
      Then multiply final synergy by (1 + luck_factor) from Spirit (SPT).
    We store a synergy breakdown for each line in the conversation log.
    """
    total_time = 90
    start_time = time.time()
    penalty = [0]
    stop_event = threading.Event()

    synergy_score = 0.0
    conversation_log = []

    # We'll compute a Spirit-based luck factor:
    # if SPT=32 => factor=0 => no effect
    # if SPT=64 => factor=+0.05 => +5%
    # if SPT=1 => factor ~ -5%
    SPT_val = mc_stats["Spirit (SPT)"]
    luck_factor = (SPT_val - 32) / 32 * 0.05  # ~ -0.05..+0.05

    interactions = [
        {
            "prompt": "[Target sees your outburst...]",
            "options":{
                "1":{
                  "text":"What? You don’t get hyped when you win?",
                  "synergy":{
                     "MC_needed":["Presence","Conviction"],
                     "Target_needed":["ThrillIncl"],
                     "Victim_risk":["IAW"]
                  }
                },
                "2":{
                  "text":"I thought I was alone saying that.",
                  "synergy":{
                    "MC_needed":["Adaptability"],
                    "Target_needed":["Autonomy"],
                    "Victim_risk":[]
                  }
                },
                "3":{
                  "text":"Should I apologize?",
                  "synergy":{
                    "MC_needed":["Will"],
                    "Target_needed":["Anchoring"],
                    "Victim_risk":["SCM"]
                  }
                }
            }
        },
        {
            "prompt":"(They draw closer) 'So, do you always say whatever comes to mind?'",
            "options":{
                "1":{
                  "text":"If it’s worth saying, yeah.",
                  "synergy":{
                    "MC_needed":["Presence","Projection"],
                    "Target_needed":["ThrillIncl","RPM"],
                    "Victim_risk":["SCM","IAW"]
                  }
                },
                "2":{
                  "text":"Only when I’m feeling lucky.",
                  "synergy":{
                    "MC_needed":["Adaptability","Spirit"],
                    "Target_needed":["Autonomy"],
                    "Victim_risk":["RLP"]
                  }
                },
                "3":{
                  "text":"I usually think before I speak… usually.",
                  "synergy":{
                    "MC_needed":["Instinct"],
                    "Target_needed":["Masking"],
                    "Victim_risk":[]
                  }
                }
            }
        },
        {
            "prompt":"(They glance away) 'So... you’re the bold type, or...?'",
            "options":{
                "1":{
                  "text":"You bet. I don’t hold back.",
                  "synergy":{
                    "MC_needed":["Presence","Will"],
                    "Target_needed":["ThrillIncl"],
                    "Victim_risk":["SCM","IAW","RLP"]
                  }
                },
                "2":{
                  "text":"I adapt to whoever I’m around.",
                  "synergy":{
                    "MC_needed":["Adaptability","Instinct"],
                    "Target_needed":["Masking","Autonomy"],
                    "Victim_risk":[]
                  }
                },
                "3":{
                  "text":"Is that too forward? I can slow down.",
                  "synergy":{
                    "MC_needed":["Conviction","Resonance"],
                    "Target_needed":["Anchoring","RPM"],
                    "Victim_risk":["ELG"]
                  }
                }
            }
        }
    ]

    tthread = threading.Thread(target=update_timer, args=(total_time, start_time, penalty, stop_event))
    tthread.daemon = True
    tthread.start()

    for inter in interactions:
        conversation_log.append("\n" + inter["prompt"])
        print("\n" + inter["prompt"])
        for k, optdata in inter["options"].items():
            line_str = f" {k}. {optdata['text']}"
            print(line_str)
            conversation_log.append(line_str)

        resp = get_input_nonblocking("\nChoose (1,2,3): ", total_time, start_time, penalty)
        if resp is None:
            print("\nTime's up mid-conversation!")
            conversation_log.append("\n[Time ended mid-conversation!]")
            stop_event.set()
            tthread.join()
            return synergy_score, conversation_log
        while resp not in ["1","2","3"]:
            print("Invalid choice. +10s penalty.")
            penalty[0] += 10
            conversation_log.append(f"[Invalid => +10s penalty (User typed {resp})]")
            resp = get_input_nonblocking("Choose (1,2,3): ", total_time, start_time, penalty)
            if resp is None:
                print("\nTime's up after invalid input.")
                conversation_log.append("\n[Time ended after invalid attempt!]")
                stop_event.set()
                tthread.join()
                return synergy_score, conversation_log

        synergy_tags = inter["options"][resp]["synergy"]
        # Now compute synergy + a breakdown
        synergy_val, detail_str = compute_choice_synergy_breakdown(mc_stats, target_stats, victim_stats, synergy_tags, luck_factor)
        synergy_score += synergy_val
        synergy_msg = f"[Chose {resp}, synergy +{synergy_val:.2f}]"
        conversation_log.append(synergy_msg)
        conversation_log.append(detail_str)
        print(synergy_msg + "\n")

    stop_event.set()
    tthread.join()
    return synergy_score, conversation_log

def compute_choice_synergy_breakdown(mc_stats, target_stats, victim_stats, synergy_tags, luck_factor):
    """
    Returns synergy_line + a detail string explaining the synergy breakdown:
      - baseline=2
      - MC/Target Gains => ratio*1.2 each
      - Rival penalty => ratio*2.0
      - Then multiply final synergy by (1+luck_factor)
    We'll record each step in detail_str.
    """
    baseline = 2.0
    synergy_line = baseline
    detail_list = []
    detail_list.append(f"Baseline={baseline:.2f}")

    # We'll accumulate numeric values for MC, Target, Rival penalty
    mc_total = 0.0
    tgt_total = 0.0
    rv_penalty = 0.0

    # For easier referencing
    mc_map = {
        "Presence":"Presence (PRS)",
        "Adaptability":"Adaptability (ADP)",
        "Instinct":"Instinct (INS)",
        "Will":"Will (WIL)",
        "Projection":"Projection (PJT)",
        "Conviction":"Conviction (CVT)",
        "Resonance":"Resonance (RSN)",
        "Spirit":"Spirit (SPT)"
    }
    tgt_map = {
        "Anchoring":"Emotional Anchoring (EAC)",
        "ThrillIncl":"Thrill Inclination (THI)",
        "Autonomy":"Autonomy Drive (ATD)",
        "Masking":"Social Masking (SOM)",
        "RPM":"Response Momentum (RPM)"
    }
    rv_map = {
        "SCM":"Social Command (SCM)",
        "IAW":"Instinctive Awareness (IAW)",
        "RLP":"Relational Pull (RLP)",
        "ELG":"Emotional Leverage (ELG)"
    }

    # Gains from MC
    for shortn in synergy_tags.get("MC_needed", []):
        fk = mc_map.get(shortn)
        if fk and fk in mc_stats:
            ratio = mc_stats[fk]/64.0
            gain = ratio*1.2
            mc_total += gain

    # Gains from Target
    for shortn in synergy_tags.get("Target_needed", []):
        fk = tgt_map.get(shortn)
        if fk and fk in target_stats:
            ratio = target_stats[fk]/64.0
            gain = ratio*1.2
            tgt_total += gain

    # Rival penalty
    for shortn in synergy_tags.get("Victim_risk", []):
        fk = rv_map.get(shortn)
        if fk and fk in victim_stats:
            ratio = victim_stats[fk]/64.0
            penalty = ratio*2.0
            rv_penalty += penalty

    synergy_line += mc_total
    synergy_line += tgt_total
    synergy_line -= rv_penalty

    detail_list.append(f"+MC={mc_total:.2f}")
    detail_list.append(f"+Target={tgt_total:.2f}")
    detail_list.append(f"-Rival={rv_penalty:.2f}")

    pre_luck = synergy_line
    detail_list.append(f"=> pre-luck= {pre_luck:.2f}")

    # luck factor
    synergy_line *= (1 + luck_factor)
    synergy_line = clamp(synergy_line, 0, 10)
    luck_pct = luck_factor * 100
    detail_list.append(f"luck= {luck_pct:+.2f}% => final= {synergy_line:.2f}")

    detail_str = "[Detail] " + " ".join(detail_list)
    return synergy_line, detail_str

##########################################################
# H) MAIN
##########################################################

def main():
    print_stat_explanations()
    print("\n=== Final Extended NTR Example (Harder) with Spirit as Luck + Detailed Breakdown ===")
    print("We'll gather name, age, pick stats, synergy with a detailed breakdown in the final log.\n")
    input("Press Enter to begin...")

    # 1) Basic user info
    user_name = input("What is your name? ").strip()
    user_age_str = input("How old are you? (Must be >21): ").strip()
    try:
        user_age = int(user_age_str)
    except:
        print("Invalid age. Exiting.")
        return
    if user_age <= 21:
        print("Sorry, you're too young for this game.")
        return

    user_gender = input("What is your gender? (male/female/other): ").strip().lower()
    while user_gender not in ["male","female","other"]:
        user_gender = input("Please type 'male','female','other': ").strip().lower()

    target_gender = input("NTR Target's gender? (male/female/other): ").strip().lower()
    while target_gender not in ["male","female","other"]:
        target_gender = input("Please type 'male','female','other': ").strip().lower()

    print(f"\nHello {user_name}, age {user_age}, you are {user_gender}, aiming for a {target_gender} target.\n")
    input("Press Enter to pick your MC stats...")

    # 2) MC Stats
    mc_stats = choose_stats()

    # 3) Rival & Target
    victim_stats = generate_ntr_victim_stats()
    target_stats = generate_ntr_target_stats()

    # Sibling
    sibling_age_status = random.choice(["older","younger","twins"])
    sibling_gender = target_gender
    attire = describe_attire(sibling_gender)
    sibling_role = sibling_label(sibling_age_status)

    # Noticing => modifies shower time
    raw_player_notice = random.randint(1,100)
    inst_val = mc_stats.get("Instinct (INS)",0)
    eff_player_notice = raw_player_notice + max(inst_val - 10, 0)
    raw_friend_notice = random.randint(1,100)
    player_notices = (eff_player_notice >= 50)
    friend_notices = (raw_friend_notice >= 50)

    print("\n=== NTR Victim (Rival) Stats (Bell Dist) ===")
    for k, v in victim_stats.items():
        print(f" {k}: {v}")

    print("\n=== NTR Target Stats (Bell Dist) ===")
    for k, v in target_stats.items():
        print(f" {k}: {v}")

    input("\nPress Enter for scenario...")

    print(f"\n--- SCENARIO ---")
    print(f"You ({user_gender}, age {user_age}) and your best friend are in the living room.")
    print(f"The {sibling_role} (gender: {sibling_gender}) arrives wearing {attire}.\n")

    if player_notices and friend_notices:
        print("Both you and your friend notice them lurking.\n")
    elif player_notices:
        print("You notice them, your friend doesn't.\n")
    elif friend_notices:
        print("Your friend notices them, though you do not.\n")
    else:
        print("Neither of you notices them.\n")

    print("You jump up exclaiming, 'Suck this fat dick!' as 'Winner' flashes on screen.\n[Time passes...]\n")

    # Shower time logic
    if friend_notices:
        if raw_friend_notice < 10:
            reduction = 0.0
        elif raw_friend_notice <= 35:
            reduction = 0.10 + ((raw_friend_notice - 10) / 25)*0.15
        else:
            reduction = 0.25
    else:
        reduction = 0.0

    if sibling_age_status == "older":
        reduction = max(reduction - 0.05, 0)
    elif sibling_age_status == "younger":
        reduction = min(reduction + 0.05, 1)

    original_time = 120
    new_shower = int(original_time * (1 - reduction))
    print(f"Shower time is now {new_shower}/{original_time} seconds.\n")

    print("Your friend is showering. Do you talk to the sibling?")
    print("1. Small Talk\n2. Address the Incident\n3. Stay Silent")
    cchoice = input("Enter choice (1-3): ").strip()
    while cchoice not in ["1","2","3"]:
        cchoice = input("Enter choice (1-3): ").strip()

    synergy_score = 0.0
    conversation_log = []
    if cchoice in ["1","2"]:
        print("\n[You decide to talk with synergy-based approach (Hard + Spirit luck).]\n")
        synergy_score, conversation_log = synergy_convo(mc_stats, target_stats, victim_stats)
    else:
        print("\n[You remain silent, no synergy conversation.]\n")

    # Evaluate synergy
    outcome_str = "No conversation"
    max_synergy = 3*10
    if synergy_score > 0:
        if synergy_score >= 25:
            outcome_str = "NTR Option Unlocked!"
        elif synergy_score >= 15:
            outcome_str = "Partially intrigued"
        else:
            outcome_str = "Unimpressed"

    # 4) Write final results
    file_name = "results_synergy.txt"
    with open(file_name,"w",encoding="utf-8") as f:
        f.write("=== Final Extended NTR Results (Harder) + Spirit as Luck + Detailed Breakdown ===\n\n")
        f.write(f"Player Name: {user_name}\n")
        f.write(f"Player Age: {user_age}\n")
        f.write(f"Player Gender: {user_gender}\n")
        f.write(f"Target Gender: {target_gender}\n")

        f.write("\nMC Stats:\n")
        for st,val in mc_stats.items():
            f.write(f"  {st}: {val}\n")

        f.write("\nNTR Victim (Rival) Stats:\n")
        for st,val in victim_stats.items():
            f.write(f"  {st}: {val}\n")

        f.write("\nNTR Target Stats:\n")
        for st,val in target_stats.items():
            f.write(f"  {st}: {val}\n")

        f.write(f"\nSibling: {sibling_role}, Gender: {sibling_gender}, Attire: {attire}\n")
        f.write(f"Player Notice Roll: {raw_player_notice} => Effective {eff_player_notice}, Noticed? {player_notices}\n")
        f.write(f"Friend Notice Roll: {raw_friend_notice}, Noticed? {friend_notices}\n")
        f.write(f"Shower Time => {new_shower}/{original_time}\n")

        if synergy_score > 0:
            f.write(f"\nUser conversed => synergy= {synergy_score:.2f}/{max_synergy}\nOutcome= {outcome_str}\n")
            f.write("\n--- Conversation Log + Detailed Synergy ---\n")
            for line in conversation_log:
                f.write(line + "\n")
        else:
            f.write("\nUser stayed silent => no synergy conversation.\n")

    if synergy_score > 0:
        print(f"\nConversation synergy= {synergy_score:.2f}/{max_synergy}")
        print("Outcome:", outcome_str)
    else:
        print("\nNo synergy conversation happened.")

    print(f"\nDetailed synergy breakdown saved to '{file_name}'. Press Enter to exit.")
    input()

if __name__ == "__main__":
    main()
