import streamlit as st
import time
from user_manager import (
    signup, login, get_user, update_tokens, User, purchase_tokens, 
    get_all_users, suspend_user, terminate_user, get_pending_complaints,
    resolve_complaint, get_user_complaints, respond_to_complaint, submit_complaint,
    get_complaint_details
)
from llm_utils import load_llm, correct_text, mask_blacklisted_words, highlight_corrections
from blacklist import get_blacklist, add_to_blacklist
from collaboration import invite_user_to_collaborate, list_invitations_for_user, accept_invitation, reject_invitation, list_collaborations_for_user, get_user_collaborations
from datetime import datetime

# Load LLM once
if 'llm' not in st.session_state:
    st.session_state['llm'] = load_llm()

# Session state for user and cooldown
if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'last_free_submit' not in st.session_state:
    st.session_state['last_free_submit'] = 0

st.sidebar.title("LLM Cooperative Editor")
page = st.sidebar.radio("Select Role", ["Free User", "Paid User", "Super User"])

# Top panel for stats
def show_stats():
    user = st.session_state['user']
    if user:
        st.markdown(f"Tokens: {user.tokens} | Role: {user.role}")
    else:
        st.markdown("Tokens: -- | Role: --")

st.markdown("---")
st.markdown("### User Statistics")
show_stats()
st.markdown("---")

# Free User Page
def free_user_page():
    st.header("Free User Portal")
    st.info("Free users can submit up to 20 words. Longer inputs are rejected. Re-login allowed after 3 mins")
    
    # Initialize error message in session state if not exists
    if 'free_user_error' not in st.session_state:
        st.session_state['free_user_error'] = None
    
    # Display error message if exists
    if st.session_state['free_user_error']:
        st.error(st.session_state['free_user_error'])
        if st.button("Logout"):
            st.session_state['user'] = None
            st.session_state['free_user_error'] = None
            st.rerun()
        return
    
    # Check cooldown
    cooldown = 180  # 3 minutes
    now = time.time()
    if 'last_free_submit' in st.session_state and now - st.session_state['last_free_submit'] < cooldown:
        remaining_time = int(cooldown - (now - st.session_state['last_free_submit']))
        minutes = remaining_time // 60
        seconds = remaining_time % 60
        st.warning(f"You must wait {minutes} minutes and {seconds} seconds before submitting again.")
        if st.button("Logout"):
            st.session_state['user'] = None
            st.rerun()
        return
    
    text = st.text_area("Enter your text (max 20 words):", key="free_text")
    if st.button("Submit"):
        if not text.strip():
            st.session_state['free_user_error'] = "Please enter some text first!"
            st.rerun()
            return
            
        word_count = len(text.strip().split())
        if word_count > 20:
            st.session_state['free_user_error'] = f"Too many words! You entered {word_count} words. Maximum 20 words allowed. You will be logged out."
            st.session_state['last_free_submit'] = time.time()  # Set cooldown when exceeding word limit
            st.session_state['user'] = None
            st.rerun()
            return
        
        st.session_state['last_free_submit'] = time.time()
        masked = mask_blacklisted_words(text)
        corrected = correct_text(st.session_state['llm'], masked)
        st.success("LLM Correction:")
        st.write(highlight_corrections(masked, corrected))
        
        # Add logout button after successful submission
        if st.button("Logout"):
            st.session_state['user'] = None
            st.rerun()

# Paid User Page
def paid_user_page():
    st.header("Paid User Portal")
    if st.session_state['user'] is None:
        st.subheader("Login or Sign Up")
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        with tab1:
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login"):
                user = login(username, password)
                if user:
                    st.session_state['user'] = user
                    st.success("Logged in!")
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
        with tab2:
            username = st.text_input("New Username", key="signup_user")
            password = st.text_input("New Password", type="password", key="signup_pass")
            if st.button("Sign Up"):
                if signup(username, password):
                    st.success("Account created! Please log in.")
                else:
                    st.error("Username already exists.")
        return

    # User is logged in
    st.info(f"Welcome, {st.session_state['user'].username}! Tokens: {st.session_state['user'].tokens}")
    
    # Check for pending complaints
    pending_complaints = get_user_complaints(st.session_state['user'].id)
    if pending_complaints:
        st.warning("You have pending complaints that require your response!")
        for complaint in pending_complaints:
            with st.expander(f"Complaint from {complaint['complainer_username']}"):
                st.write("Reason:", complaint['reason'])
                st.write("Created at:", datetime.fromtimestamp(complaint['created_at']).strftime('%Y-%m-%d %H:%M:%S'))
                
                if not complaint['response']:
                    response = st.text_area("Your response:", key=f"response_{complaint['id']}")
                    if st.button("Submit Response", key=f"submit_response_{complaint['id']}"):
                        if respond_to_complaint(complaint['id'], response):
                            st.success("Response submitted successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to submit response")
                else:
                    st.write("Your response:", complaint['response'])
                    st.write("Responded at:", datetime.fromtimestamp(complaint['responded_at']).strftime('%Y-%m-%d %H:%M:%S'))

    # Complaint submission section
    st.subheader("Submit Complaint")
    complained_username = st.text_input("Username of user to complain about:")
    complaint_reason = st.text_area("Reason for complaint:")
    if st.button("Submit Complaint"):
        if complained_username and complaint_reason:
            if submit_complaint(st.session_state['user'].id, complained_username, complaint_reason):
                st.success("Complaint submitted successfully!")
                st.rerun()
            else:
                st.error("Failed to submit complaint. Please check the username and try again.")
        else:
            st.error("Please provide both username and reason for complaint.")

    # Token Purchase Section
    st.subheader("Purchase Tokens")
    col1, col2 = st.columns(2)
    with col1:
        token_amount = st.number_input("Amount of tokens to purchase", min_value=10, step=10)
    with col2:
        if st.button("Purchase Tokens"):
            if purchase_tokens(st.session_state['user'].id, token_amount):
                st.session_state['user'] = get_user(st.session_state['user'].username)
                st.success(f"Successfully purchased {token_amount} tokens!")
                st.rerun()
            else:
                st.error("Failed to purchase tokens. Please try again.")

    # Text Input Section
    st.subheader("Text Input")
    input_method = st.radio("Choose input method:", ["Type Text", "Upload File"])
    
    if input_method == "Type Text":
        text = st.text_area("Enter your text:", key="paid_text")
    else:
        uploaded_file = st.file_uploader("Choose a text file", type=['txt'])
        if uploaded_file is not None:
            text = uploaded_file.getvalue().decode("utf-8")
            st.text_area("File contents:", text, key="paid_text")
        else:
            text = ""

    # Correction mode selection before submission
    st.subheader("Choose Correction Mode")
    correction_mode = st.radio("Correction Mode", ["Self-correction", "LLM-correction"])

    if st.button("Submit Text"):
        if not text.strip():
            st.error("Please enter some text or upload a file first!")
            return
            
        word_count = len(text.strip().split())
        user = get_user(st.session_state['user'].username)
        
        # Check if user has enough tokens
        if user.tokens < word_count:
            penalty = user.tokens // 2
            st.error(f"Not enough tokens! You need {word_count} tokens. {penalty} tokens will be deducted as penalty.")
            update_tokens(user.id, -penalty)
            st.session_state['user'] = get_user(user.username)
            st.rerun()
            return

        # Charge tokens for the word count
        update_tokens(user.id, -word_count)
        st.session_state['user'] = get_user(user.username)
        st.info(f"{word_count} tokens deducted for text submission. Remaining: {st.session_state['user'].tokens}")

        if correction_mode == "Self-correction":
            # Store original text for comparison
            if 'original_text' not in st.session_state:
                st.session_state['original_text'] = text
                st.session_state['show_correction'] = True
            
            if st.session_state['show_correction']:
                st.subheader("Self-correction Mode")
                st.write("Edit the text below to make your corrections:")
                corrected_text = st.text_area("Make your corrections:", value=text, key="self_correct_text")
                
                if st.button("Submit Corrections"):
                    # Count words that were actually corrected
                    original_words = st.session_state['original_text'].lower().split()
                    corrected_words = corrected_text.lower().split()
                    
                    # Count words that were changed (different from original)
                    corrected_word_count = 0
                    for orig, corr in zip(original_words, corrected_words):
                        if orig != corr:
                            corrected_word_count += 1
                    
                    # Charge half the number of corrected words
                    tokens_to_charge = corrected_word_count // 2
                    if st.session_state['user'].tokens < tokens_to_charge:
                        st.error(f"Not enough tokens for self-correction! You need {tokens_to_charge} tokens.")
                        return
                    
                    update_tokens(user.id, -tokens_to_charge)
                    st.session_state['user'] = get_user(user.username)
                    st.success("Self-corrected Text:")
                    st.write(corrected_text)
                    st.info(f"{tokens_to_charge} tokens deducted for self-correction ({corrected_word_count} words corrected). Remaining: {st.session_state['user'].tokens}")
                    
                    # Reset the correction interface
                    st.session_state['show_correction'] = False
                    st.session_state['original_text'] = None
                    st.rerun()
        else:
            # LLM correction
            masked = mask_blacklisted_words(text)
            # Charge tokens for blacklisted words
            blacklisted_words = [w for w in text.split() if w.lower() in get_blacklist()]
            if blacklisted_words:
                blacklist_charge = sum(len(w) for w in blacklisted_words)
                if st.session_state['user'].tokens < blacklist_charge:
                    st.error(f"Not enough tokens for blacklisted words! You need {blacklist_charge} tokens.")
                    return
                update_tokens(user.id, -blacklist_charge)
                st.session_state['user'] = get_user(user.username)
                st.info(f"{blacklist_charge} tokens deducted for blacklisted words. Remaining: {st.session_state['user'].tokens}")
            
            corrected = correct_text(st.session_state['llm'], masked)
            
            # Check if text has more than 10 words and no corrections were needed
            word_count = len(text.strip().split())
            if word_count > 10 and corrected.lower() == masked.lower():
                # Award bonus tokens for no corrections needed
                update_tokens(user.id, 3)
                st.session_state['user'] = get_user(user.username)
                st.success("No corrections needed! 3 bonus tokens awarded!")
            
            st.success("LLM Correction:")
            st.write(highlight_corrections(masked, corrected))
            
            if corrected != masked:
                st.subheader("Review Corrections")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Accept Corrections"):
                        if st.session_state['user'].tokens < 1:
                            st.error("Not enough tokens to accept corrections!")
                            return
                        update_tokens(user.id, -1)  # Charge 1 token for acceptance
                        st.session_state['user'] = get_user(user.username)
                        st.success("Corrections accepted! 1 token deducted.")
                        st.rerun()
                with col2:
                    if st.button("Mark as Correct"):
                        # Add word to whitelist
                        word_to_mark = st.text_input("Enter the word to mark as correct:")
                        if word_to_mark:
                            add_to_blacklist(word_to_mark.lower())
                            st.success(f"'{word_to_mark}' marked as correct. It won't be highlighted in future corrections.")

    # Save to file option
    if text and st.button("Save to File"):
        if st.session_state['user'].tokens >= 5:
            update_tokens(st.session_state['user'].id, -5)
            st.session_state['user'] = get_user(st.session_state['user'].username)
            st.download_button(
                label="Download corrected text",
                data=corrected if 'corrected' in locals() else text,
                file_name="corrected_text.txt",
                mime="text/plain"
            )
            st.success("5 tokens deducted for saving.")
        else:
            st.error("Not enough tokens to save file (requires 5 tokens)")

    # Collaboration: invite and view invitations
    st.subheader("Collaboration")
    invitee = st.text_input("Invite paid user to collaborate (username):")
    collab_text = st.text_area("Text to share for collaboration:", key="collab_text")
    if st.button("Invite to Collaborate"):
        if invitee and collab_text:
            invite_user_to_collaborate(st.session_state['user'].username, invitee, collab_text)
            st.success(f"Invitation sent to {invitee}!")
    st.subheader("Your Collaboration Invitations")
    invitations = list_invitations_for_user(st.session_state['user'].username)
    for inv in invitations:
        st.write(f"From: {inv['inviter']} | Text: {inv['text']} | Sent: {inv['created_at']}")
        col1, col2 = st.columns(2)
        if col1.button(f"Accept {inv['id']}"):
            if accept_invitation(inv['id']):
                st.success("Invitation accepted!")
                st.rerun()
            else:
                st.error("Failed to accept invitation")
        if col2.button(f"Reject {inv['id']}"):
            if reject_invitation(inv['id']):
                st.info("Invitation rejected.")
                st.rerun()
            else:
                st.error("Failed to reject invitation")
    st.subheader("Active Collaborations")
    collaborations = get_user_collaborations(st.session_state['user'].id)
    for c in collaborations:
        with st.expander(f"Collaboration with {c['inviter'] if c['inviter_id'] != st.session_state['user'].id else c['invitee']}"):
            st.write("Text:", c['text'])
    if st.button("Logout"):
        st.session_state['user'] = None
        st.rerun()

# Super User Page
def super_user_page():
    st.header("Super User Portal")
    if st.session_state['user'] is None or st.session_state['user'].role != 'super':
        st.subheader("Super User Login")
        username = st.text_input("Super Username", key="super_login_user")
        password = st.text_input("Super Password", type="password", key="super_login_pass")
        if st.button("Login as Super User"):
            user = login(username, password)
            if user and user.role == 'super':
                st.session_state['user'] = user
                st.success("Super user logged in!")
                st.rerun()
            else:
                st.error("Invalid super user credentials.")
        return

    st.info(f"Welcome, Super User {st.session_state['user'].username}!")
    
    # Create tabs for different super user functions
    tab1, tab2, tab3 = st.tabs(["Blacklist Management", "User Management", "Complaints"])
    
    with tab1:
        st.subheader("Blacklist Management")
        st.write("Current Blacklist:")
        st.write(get_blacklist())
        new_word = st.text_input("Add word to blacklist:")
        if st.button("Add to Blacklist"):
            if new_word:
                add_to_blacklist(new_word.lower())
                st.success(f"Added '{new_word}' to blacklist.")
    
    with tab2:
        st.subheader("User Management")
        users = get_all_users()
        for user in users:
            with st.expander(f"User: {user['username']} (Role: {user['role']})"):
                st.write(f"Current tokens: {user['tokens']}")
                st.write(f"Total corrections: {user['total_corrections']}")
                st.write(f"Total tokens used: {user['total_tokens_used']}")
                
                if user['role'] != 'terminated' and user['role'] != 'super':
                    if st.button(f"Terminate {user['username']}", key=f"terminate_{user['id']}"):
                        terminate_user(user['id'])
                        st.success(f"User {user['username']} has been terminated and can no longer log in.")
                        st.rerun()
    
    with tab3:
        st.subheader("Complaints Management")
        complaints = get_pending_complaints()
        for complaint in complaints:
            with st.expander(f"Complaint from {complaint['complainer_username']} against {complaint['complained_username']}"):
                st.write("Reason:", complaint['reason'])
                st.write("Created at:", datetime.fromtimestamp(complaint['created_at']).strftime('%Y-%m-%d %H:%M:%S'))
                
                # Get the full complaint details including response
                complaint_details = get_complaint_details(complaint['id'])
                if complaint_details and complaint_details.get('response'):
                    st.write("Response:", complaint_details['response'])
                    st.write("Responded at:", datetime.fromtimestamp(complaint_details['responded_at']).strftime('%Y-%m-%d %H:%M:%S'))
                    
                    if st.button("Resolve", key=f"resolve_{complaint['id']}"):
                        action = st.selectbox("Action", ["Warning", "Token Penalty"], key=f"action_{complaint['id']}")
                        
                        if action == "Token Penalty":
                            penalty = st.number_input("Penalty tokens", min_value=1, value=10, key=f"penalty_{complaint['id']}")
                            penalty_user = st.selectbox("Apply penalty to", 
                                                      [complaint['complainer_username'], complaint['complained_username']],
                                                      key=f"penalty_user_{complaint['id']}")
                            penalty_user_id = complaint['complainer_id'] if penalty_user == complaint['complainer_username'] else complaint['complained_id']
                        else:
                            penalty = 0
                            penalty_user_id = None
                        
                        if st.button("Confirm", key=f"confirm_{complaint['id']}"):
                            if resolve_complaint(complaint['id'], action, penalty, penalty_user_id):
                                st.success("Complaint resolved successfully")
                                st.rerun()
                            else:
                                st.error("Failed to resolve complaint")
                else:
                    st.warning("Waiting for response from the complained user")

    if st.button("Logout (Super User)"):
        st.session_state['user'] = None
        st.rerun()

# Page routing
if page == "Free User":
    free_user_page()
elif page == "Paid User":
    paid_user_page()
elif page == "Super User":
    super_user_page() 