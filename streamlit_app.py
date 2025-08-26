from chat_agent import agent
import streamlit as st

def switch_session(session_id):
    with st.spinner("Switching session..."):
        agent.switch_session(session_id)

def new_session():
    with st.spinner("Creating new session..."):
        agent.new_session()

def delete_session(session_id):
    # with st.spinner("Deleting session..."):
    #     agent.delete_session(session_id)
    print(f"Delete session function called: {session_id}")  # Placeholder action
    pass

# Inject custom CSS to left-align button text
st.markdown("""
    <style>
    .stButton > button {
        text-align: left;
        display: block; /* Ensures the button takes up full width for text alignment */
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize the Streamlit app
# st.title("CHAT AV (web search)")

st.sidebar.title("CHAT AV")
new_chat = st.sidebar.button("New Chat")
if new_chat:
    new_session()

sessions = agent.get_sessions()
buttons = []
for s in sessions:
    buttons.append(
        st.sidebar.button(
            s['title'],
            type="tertiary",
            on_click=lambda s=s: switch_session(s['session_id'])
        )
    )
    # buttons.append(
    #     st.sidebar.button(
    #         "🗑️",
    #         key=f"delete_{s['session_id']}", 
    #         type="tertiary", 
    #     on_click=lambda s=s: delete_session(s['session_id'])
    #     )
    # )

# Get the user's input
user_input = st.chat_input("Ask a question:")

# Send the user's input to the agent and get the response, add both to the session state
if user_input:
    with st.spinner("Thinking..."):
        agent(user_input)

# Redraw the UI with all the messages in the session state
for message in agent.get_current_messages():
    role = message['role']
    content = message['content']
    if role == "user":
        st.chat_message("user").markdown(content)
    else:
        st.chat_message("assistant").markdown(content)