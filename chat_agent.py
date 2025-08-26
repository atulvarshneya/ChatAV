
from strands import Agent
from strands.session.file_session_manager import FileSessionManager
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.models.openai import OpenAIModel
from dotenv import load_dotenv
import os
import uuid

TITLE_AGENT_PROMPT = """
Generate a short title, in less than 5 words, for the conversation given below.
Just provide the title, do not put any additional context or explanation.
Do not put any quotation marks around the title text.

Conversation:
{all_messages}
"""

class ChatAgent:
    def __init__(self, model_id="gpt-4o"):
        load_dotenv()

        # Initialize model - get api_key, model_id, and create model instance
        self.OPENAI_API_KEY = os.getenv("SFN_OPENAI_API_KEY")
        self.model_id = model_id
        self.model = self.__get_model()

        # Initialize sessions list, select current_session, instantiate session_manager, reorder sessions list
        self.CONVERSATION_WINDOW_SIZE = 10
        self.SESSIONS_DIR = "./sessions"
        self.sessions = []  # just a reminder, we always maintain sessions list
        self.current_session = None  # just a reminder, we always maintain current session
        self.__read_sessions() # read existing sessions from SESSIONS_DIR, in time sorted
        if not self.sessions:
            # no existing sessions, create a new one
            self.new_session()
        else:
            # existing sessions, get latest session as current session
            session_id = self.__get_latest_session_id() # get latest session ID from session list
            self.__setup_session(session_id)

    def __call__(self, *args, **kwargs):
        return self.agent(*args, **kwargs)

    def __get_model(self):
        model = OpenAIModel(
            client_args={
                "api_key": self.OPENAI_API_KEY,
            },
            model_id=self.model_id,
            params={
                "max_tokens": 1000,
                "temperature": 0.7,
            }
        )
        return model

    def __get_agent(self, model, session_manager, conversation_manager):
        # Create an agent
        agent = Agent(
            model=model,
            session_manager=session_manager,
            conversation_manager=conversation_manager,
            callback_handler=None
        )

        return agent

    def __read_sessions(self):
        sessions = []
        # list folders under SESSIONS_DIR
        for folder in os.listdir(self.SESSIONS_DIR):
            if os.path.isdir(os.path.join(self.SESSIONS_DIR, folder)):
                if os.path.exists(os.path.join(self.SESSIONS_DIR, folder, "title.txt")):
                    with open(os.path.join(self.SESSIONS_DIR, folder, "title.txt"), "r") as f:
                        title = f.read().strip()
                else:
                    title = folder
                sessions.append({"session_id": folder.split("session_")[1], "title": title, "last_modified": os.path.getmtime(os.path.join(self.SESSIONS_DIR, folder))})
        self.sessions = sessions
        self.sessions.sort(key=lambda x: x["last_modified"], reverse=True)

    def __reorder_sessions(self):
        self.sessions.remove(self.current_session)
        self.sessions.insert(0, self.current_session)

    def __get_latest_session_id(self):
        sessions = self.get_sessions()
        if not sessions:
            return None
        latest_session = max(sessions, key=lambda x: x["last_modified"])
        return latest_session["session_id"]

    def __gen_unique_session_id(self):
        # Generate a Version 4 UUID (randomly generated)
        unique_id = uuid.uuid4()

        # Convert the UUID object to a string
        unique_id_str = str(unique_id)

        return f"{unique_id_str}"

    def __get_session_manager(self, session_id):
        # Create a session manager with the given session ID
        session_manager = FileSessionManager(
            session_id=session_id,
            storage_dir=self.SESSIONS_DIR
        )

        return session_manager

    def __setup_session(self, session_id):
        self.session_manager = self.__get_session_manager(session_id)
        self.__read_sessions()
        self.current_session = next((s for s in self.sessions if s["session_id"] == session_id))  # session obj of session_id
        self.__reorder_sessions() # bring current session to top
        # now create agent instance with this session_manager
        conversation_manager = SlidingWindowConversationManager(
            window_size=self.CONVERSATION_WINDOW_SIZE,  # Maximum number of messages to keep
            should_truncate_results=True,  # Truncate messages if they exceed the window size
            )
        self.agent = self.__get_agent(
            model=self.model,
            session_manager=self.session_manager,
            conversation_manager=conversation_manager
            )

    def __create_title_file(self, current_messages):
        title_path = os.path.join(self.SESSIONS_DIR, f"session_{self.session_manager.session_id}", "title.txt")
        if len(current_messages) > 2 and not os.path.exists(title_path):
            all_messages = ", ".join([msg['content'] for msg in current_messages])
            summarizing_agent = Agent(model=self.model, callback_handler=None)
            response = summarizing_agent(TITLE_AGENT_PROMPT.format(all_messages=all_messages))
            title = f"{response}"
            with open(title_path, "w") as f:
                f.write(title)

    def get_sessions(self):
        return self.sessions  # sessions list is maintained as time sorted and with current session moved to top

    def new_session(self):
        # Generate a unique session ID
        session_id = self.__gen_unique_session_id()

        self.__setup_session(session_id)

    def switch_session(self, session_id):
        # check for valid session_id
        if session_id not in [s["session_id"] for s in self.sessions]:
            raise ValueError(f"Invalid session_id: {session_id}")

        self.__setup_session(session_id)

    def get_current_messages(self):
        current_messages = [{'role': msg['role'], 'content': msg['content'][0]['text']} for msg in self.agent.messages]

        # Need to stop doing this over and over once it is done, check if title is proper?
        if self.current_session['title'] == f"session_{self.current_session['session_id']}":
            self.__create_title_file(current_messages)
            # Refresh sessions list
            session_id = self.current_session['session_id']
            self.__setup_session(session_id)

        return current_messages

agent = ChatAgent(model_id="gpt-4o")