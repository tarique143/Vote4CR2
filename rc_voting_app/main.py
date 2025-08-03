# Yeh aapka poora aur final main.py code hai

import streamlit as st
import requests
import pandas as pd
from PIL import Image

# --- Configuration ---
COLLEGE_NAME = "Bunts Sangha's S. M. Shetty High School & Jr. College"

st.set_page_config(page_title=f"{COLLEGE_NAME} | CR Election", page_icon="🗳️", layout="wide")

API_URL = "https://vote4cr2-production.up.railway.app" # Aapka Railway backend URL
LOGO_PATH = "rc_voting_app/assets/SMSHETTYLOGO.png"

# --- API Communication Functions ---
# (Inme koi badlav nahi hai)
def get_settings():
    try: res = requests.get(f"{API_URL}/settings"); res.raise_for_status(); return res.json()
    except: return {"election_status": "Closed", "roll_number_rule": "Optional", "show_vote_counts_to_students": False}
def update_settings(settings):
    try: res = requests.post(f"{API_URL}/settings", json=settings); res.raise_for_status(); return True
    except: st.error("Failed to update settings. Is the API server running?"); return False
def get_candidates():
    try: res = requests.get(f"{API_URL}/candidates"); res.raise_for_status(); return res.json()
    except: return []
def add_candidate(name, stream, division, gender):
    payload = {"name": name, "stream": stream, "division": division, "gender": gender};
    try: res = requests.post(f"{API_URL}/candidates", json=payload); res.raise_for_status(); return True
    except Exception as e: st.error(f"Failed to add: {e}"); return False
def delete_candidate(candidate_id):
    try: res = requests.delete(f"{API_URL}/candidates/{candidate_id}"); res.raise_for_status(); return True
    except: return False
def vote_for_candidate(candidate_id, roll_no=None):
    payload = {"candidate_id": candidate_id, "student_roll_no": roll_no}
    try:
        res = requests.post(f"{API_URL}/vote", json=payload); res.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        error_detail = res.json().get('detail', 'An unknown error occurred.'); st.error(f"Vote Failed: {error_detail}"); return False
def get_vote_status(roll_no):
    try: res = requests.get(f"{API_URL}/votestatus/{roll_no}"); res.raise_for_status(); return res.json()
    except: return {"Boy": False, "Girl": False}
def get_voter_stats():
    try: res = requests.get(f"{API_URL}/voter-stats"); res.raise_for_status(); return res.json()
    except: return {"unique_voter_count": "N/A", "total_vote_count": "N/A"}

def reset_voter_session():
    keys_to_delete = ['voted_for_boy_anon', 'voted_for_girl_anon', 'roll_no_input']
    for key in keys_to_delete:
        if key in st.session_state:
            del st.session_state[key]

# --- UI Rendering Functions ---

def render_admin_panel():
    st.header("👑 Admin Dashboard")
    # ... (Admin panel ka poora code waisa hi rahega) ...
    st.subheader("Election Control Panel")
    settings = get_settings()
    with st.form("settings_form"):
        col1, col2, col3 = st.columns(3)
        with col1: election_status = st.selectbox("Election Status", ["Open", "Closed"], index=["Open", "Closed"].index(settings['election_status']))
        with col2: roll_number_rule = st.selectbox("Roll Number Rule", ["Mandatory", "Optional", "Disabled"], index=["Mandatory", "Optional", "Disabled"].index(settings['roll_number_rule']))
        with col3: show_counts = st.checkbox("Show vote counts to students?", value=settings['show_vote_counts_to_students'])
        if st.form_submit_button("Save Settings", type="primary"):
            new_settings = {"election_status": election_status, "roll_number_rule": roll_number_rule, "show_vote_counts_to_students": show_counts}
            if update_settings(new_settings): st.success("Settings updated successfully!"); st.rerun()

    st.markdown("---")
    stats = get_voter_stats()
    col1, col2 = st.columns(2)
    col1.metric("Total Votes Casted", stats.get('total_vote_count', 'N/A'))
    col2.metric("Unique Identified Voters (by Roll No.)", stats.get('unique_voter_count', 'N/A'))
    
    st.markdown("---")
    st.header("Candidate Management & Results")
    with st.expander("Add or Delete Candidates"):
        st.subheader("Add New Candidate")
        with st.form("add_candidate_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1: name = st.text_input("Candidate Name"); stream = st.selectbox("Stream", ["Science", "Commerce", "Arts"])
            with c2: division = st.text_input("Division (e.g., A, B)"); gender = st.radio("Gender", ["Boy", "Girl"])
            if st.form_submit_button("Add Candidate"):
                if name and stream and division: add_candidate(name, stream, division, gender); st.rerun()
                else: st.warning("Please fill all details.")
        st.subheader("Delete a Candidate")
        candidates_list = get_candidates()
        candidate_map = {f"{c['name']} ({c['stream']})": c['id'] for c in candidates_list}
        if candidate_map:
            selected_name = st.selectbox("Select candidate to delete", options=candidate_map.keys())
            if st.button("Delete Selected Candidate", type="primary"): delete_candidate(candidate_map[selected_name]); st.rerun()

    candidates = get_candidates()
    if not candidates: st.info("No candidates added yet.")
    else:
        df = pd.DataFrame(candidates); st.dataframe(df[['name', 'stream', 'division', 'gender', 'votes']])
        st.subheader("🏆 Winners")
        boys = [c for c in candidates if c['gender'] == 'Boy']; girls = [c for c in candidates if c['gender'] == 'Girl']
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Boy CR Winner(s)")
            if boys:
                max_votes = max(c['votes'] for c in boys) if boys else 0
                winners = [c for c in boys if c['votes'] == max_votes and max_votes > 0]
                if winners:
                    for w in winners: st.success(f"**{w['name']}** with {w['votes']} votes.")
                    if len(winners) > 1: st.warning("It's a tie!")
                else: st.info("No votes casted yet.")
        with col2:
            st.subheader("Girl CR Winner(s)")
            if girls:
                max_votes = max(c['votes'] for c in girls) if girls else 0
                winners = [c for c in girls if c['votes'] == max_votes and max_votes > 0]
                if winners:
                    for w in winners: st.success(f"**{w['name']}** with {w['votes']} votes.")
                    if len(winners) > 1: st.warning("It's a tie!")
                else: st.info("No votes casted yet.")

def render_student_view():
    st.sidebar.button("Reset / New Voter", on_click=reset_voter_session, use_container_width=True, help="Click here to clear the form for the next student.")

    settings = get_settings()
    if not settings or settings.get('election_status') == "Closed":
        st.info("🗳️ Voting is currently closed by the admin. Please check back later."); return

    st.header("Vote for Your Class Representative (CR)")
    roll_no = None
    if settings.get('roll_number_rule') != "Disabled":
        placeholder = "Enter Your Roll Number" + (" (Required)" if settings.get('roll_number_rule') == "Mandatory" else " (Optional)")
        roll_no = st.text_input(placeholder, key="roll_no_input")

    voted_for_boy, voted_for_girl = (get_vote_status(roll_no).get("Boy", False), get_vote_status(roll_no).get("Girl", False)) if roll_no else (st.session_state.get('voted_for_boy_anon', False), st.session_state.get('voted_for_girl_anon', False))
    
    if voted_for_boy and voted_for_girl:
        st.success("🎉 Thank you for casting your vote!"); st.balloons()
        st.button("Start Vote for Next Student", on_click=reset_voter_session, type="primary", use_container_width=True)
        st.stop()

    candidates = get_candidates()
    boys = [c for c in candidates if c['gender'] == 'Boy']; girls = [c for c in candidates if c['gender'] == 'Girl']
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Candidates for Boy CR")
        if not boys: st.info("No boy candidates.")
        for cand in boys:
            with st.container(border=True):
                st.markdown(f"#### {cand['name']}")
                st.caption(f"Stream: {cand['stream']} | Division: {cand['division']}")
                label = "Vote" + (f" ({cand['votes']} votes)" if settings.get('show_vote_counts_to_students') else "")
                if st.button(label, key=f"boy_{cand['id']}", disabled=voted_for_boy, use_container_width=True):
                    if vote_for_candidate(cand['id'], roll_no):
                        if not roll_no: st.session_state.voted_for_boy_anon = True
                        st.rerun()
    with col2:
        st.subheader("Candidates for Girl CR")
        if not girls: st.info("No girl candidates.")
        for cand in girls:
            with st.container(border=True):
                st.markdown(f"#### {cand['name']}")
                st.caption(f"Stream: {cand['stream']} | Division: {cand['division']}")
                label = "Vote" + (f" ({cand['votes']} votes)" if settings.get('show_vote_counts_to_students') else "")
                if st.button(label, key=f"girl_{cand['id']}", disabled=voted_for_girl, use_container_width=True):
                    if vote_for_candidate(cand['id'], roll_no):
                        if not roll_no: st.session_state.voted_for_girl_anon = True
                        st.rerun()

# --- Main App Logic ---
# <<< BEHTAR UI KE LIYE LAYOUT UPDATE KIYA GAYA HAI >>>
st.markdown(f"""
<div style="text-align: center;">
    <img src="https://raw.githubusercontent.com/tarique143/Vote4CR2/main/rc_voting_app/assets/logo.png" width="150">
    <h1 style='color: #2E4053;'>{COLLEGE_NAME}</h1>
    <h3 style='color: #566573;'>CR Election Portal</h3>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

st.sidebar.title("Navigation")
view = st.sidebar.radio("Go to", ["Student Voting", "Admin Panel"])

if view == "Student Voting":
    render_student_view()
else:
    with st.sidebar.form("admin_login_form"):
        password = st.text_input("Enter Admin Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if password == "admin123":
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("Incorrect Password!")

    if st.session_state.get("admin_logged_in", False):
        render_admin_panel()
        if st.sidebar.button("Logout", use_container_width=True):
             del st.session_state.admin_logged_in
             st.rerun()

