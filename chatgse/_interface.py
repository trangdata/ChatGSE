# user interface class for ChatGSE
from loguru import logger
import os
import pandas as pd
import streamlit as st
from chatgse._llm_connect import GptConversation, BloomConversation


PLEASE_ENTER_QUESTIONS = (
    "The model will be with you shortly. "
    "Please enter your questions below. "
    "These can be general, such as 'explain these results', or specific. "
    "General questions will yield more general answers, while specific "
    "questions go into more detail. You can follow up on the answers with "
    "more questions."
)
KNOWN_TOOLS = ["decoupler", "progeny", "dorothea", "gsea"]
HIDE_MENU_MOD_FOOTER = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
footer:after {
    content:'Made with Streamlit by Sebastian Lobentanzer, Copyright 2023, Heidelberg University';
    visibility: visible;
    display: block;
    height: 50px;
    clear: both;
    color: darkgrey;
    }
</style>
"""


class ChatGSE:
    def __init__(self):
        if "input" not in st.session_state:
            st.session_state.input = ""

        if "history" not in st.session_state:
            st.session_state.history = []
            self._history_only("Assistant", "Welcome to ``ChatGSE``!")

    def _display_init(self):
        st.markdown(HIDE_MENU_MOD_FOOTER, unsafe_allow_html=True)

    def _display_history(self):
        for item in st.session_state.history:
            for role, msg in item.items():
                if role == "tool":
                    st.markdown(
                        f"""
                        ```
                        {msg}
                        """
                    )
                else:
                    st.markdown(self._render_msg(role, msg))

    @staticmethod
    def _render_msg(role: str, msg: str):
        return f"`{role}`: {msg}"

    def _history_only(self, role: str, msg: str):
        st.session_state.history.append({role: msg})

    def _write_and_history(self, role: str, msg: str):
        logger.info(f"Writing message from {role}: {msg}")
        st.markdown(self._render_msg(role, msg))
        st.session_state.history.append({role: msg})
        with open("chatgse-logs.txt", "a") as f:
            f.write(f"{role}: {msg}\n")

    def set_model(self, model_name: str):
        """
        Set the LLM model to use for the conversation.
        """
        if st.session_state.get("conversation"):
            logger.warning("Conversation already exists, overwriting.")

        if model_name == "gpt-3.5-turbo":
            st.session_state.conversation = GptConversation()
        elif model_name == "bigscience/bloom":
            st.session_state.conversation = BloomConversation()

    def _check_for_api_key(self, write: bool = True):
        if st.session_state.primary_model == "gpt-3.5-turbo":
            key = st.session_state.get("openai_api_key")
            st.session_state.token_limit = 4097
        elif st.session_state.primary_model == "bigscience/bloom":
            key = st.session_state.get("huggingfacehub_api_key")
            st.session_state.token_limit = 1000

        if not key:
            if st.session_state.primary_model == "gpt-3.5-turbo":
                msg = """
                    Please enter your [OpenAI API
                    key](https://platform.openai.com/account/api-keys). You can
                    get one by signing up [here](https://platform.openai.com/).
                    We will not store your key, and only use it for the requests
                    made in this session. If you run the app locally, you can
                    prevent this message by setting the environment variable
                    `OPENAI_API_KEY` to your key. If there are community credits
                    available (see in the sidebar), you can press the
                    corresponding button to use them, but please be considerate
                    of other users and only use the community credits if you
                    need to.
                    """
                self._history_only("Assistant", msg)
                st.session_state.show_community_select = True
            elif st.session_state.primary_model == "bigscience/bloom":
                msg = """
                    Please enter your [HuggingFace Hub API
                    key](https://huggingface.co/settings/token). You can get one by
                    signing up [here](https://huggingface.co/). We will not store
                    your key, and only use it for the requests made in this session.
                    If you run the app locally, you can prevent this message by
                    setting the environment variable `HUGGINGFACEHUB_API_TOKEN` to
                    your key.
                    """
                self._history_only("Assistant", msg)

            return "getting_key"

        success = self._try_api_key(key)

        if not success:
            msg = """
                The API key in your environment is not valid. Please enter a
                valid key.
                """
            self._history_only("Assistant", msg)

            return "getting_key"

        if not st.session_state.get("asked_for_name"):
            st.session_state.asked_for_name = True
            msg = """
                I am the model's assistant. For more explanation, please see the 
                :red[About] text in the sidebar. We will now be going through some
                initial setup steps together. To get started, could you please tell
                me your name?
                """
            if write:
                self._write_and_history("Assistant", msg)
            else:
                self._history_only("Assistant", msg)

        st.session_state.show_community_select = False

        return "getting_name"

    def _try_api_key(self, key: str = None):
        success = st.session_state.conversation.set_api_key(
            key,
            st.session_state.user,
        )
        if not success:
            return False
        return True

    def _get_api_key(self, key: str = None):
        logger.info("Getting API Key.")
        sucess = self._try_api_key(key)
        if not sucess:
            msg = """
                The API key you entered is not valid. Please try again.
                """
            self._write_and_history("Assistant", msg)

            return "getting_key"

        if not st.session_state.get("asked_for_name"):
            st.session_state.asked_for_name = True
            msg = """
                Thank you! I am the model's assistant. For more explanation, please
                see the :red[About] text in the sidebar. We will now be going
                through some initial setup steps together. To get started, could you
                please tell me your name?
                """
            self._write_and_history("Assistant", msg)

        st.session_state.show_community_select = False

        return "getting_name"

    def _ask_for_user_name(self):
        msg = """
                Thank you! I am the model's assistant. For more explanation, please
                see the :red[About] text in the sidebar. We will now be going
                through some initial setup steps together. To get started, could you
                please tell me your name?
                """
        self._write_and_history("Assistant", msg)

        return "getting_name"

    def _get_user_name(self):
        logger.info("Getting user name.")
        name = st.session_state.input
        st.session_state.conversation.set_user_name(name)
        self._write_and_history(
            name,
            name,
        )
        msg = (
            f"Thank you, `{name}`! "
            "What is the context of your inquiry? For instance, this could be a "
            "disease, an experimental design, or a research area."
        )
        self._write_and_history("Assistant", msg)

        return "getting_context"

    def _get_context(self):
        logger.info("Getting context.")
        self._write_and_history(
            st.session_state.conversation.user_name,
            st.session_state.input,
        )
        st.session_state.conversation.setup(st.session_state.input)

    def _ask_for_data_input(self):
        if not st.session_state.tool_data:
            msg1 = f"""
                You have selected `{st.session_state.conversation.context}` as
                your context. Do you want to provide input files from analytic
                methods? They will not be stored or analysed beyond your
                queries. If so, please provide the files by uploading them in
                the sidebar and press 'Yes' once you are finished. I will
                recognise methods if their names are mentioned in the file name.
                These are the tools I am familiar with: {', '.join([f"`{name}`"
                for name in KNOWN_TOOLS])}. Please keep in mind that all data
                you provide will count towards the token usage of your
                conversation prompt. The limit of the currently active model is
                {st.session_state.token_limit}.
                """
            self._write_and_history("Assistant", msg1)
            msg2 = """
                If you don't want to provide any files, please press 'No'. You
                will still be able to provide free text information about your
                results later. Any free text you provide will also not be stored
                or analysed beyond your queries.
                """
            self._write_and_history("Assistant", msg2)
            return "getting_data_file_input"

        file_names = [f"`{f.name}`" for f in st.session_state.tool_data]

        msg1 = f"""
            You have selected `{st.session_state.conversation.context}` as
            your context. I see you have already uploaded some data files:
            {', '.join(file_names)}. If you wish to add
            more, please do so now. Once you are done, please press 'Yes'.
            """
        self._write_and_history("Assistant", msg1)

        return "getting_data_file_input"

    def _get_data_input(self):
        logger.info("--- Biomedical data input ---")

        if not st.session_state.get(
            "tool_data"
        ) and not "demo" in st.session_state.get("mode"):
            msg = """
                No files detected. Please upload your files in the sidebar, or
                press 'No' to continue without providing any files.
                """
            self._write_and_history("Assistant", msg)
            return "getting_data_file_input"

        if not st.session_state.get("started_tool_input"):
            st.session_state.started_tool_input = True

            logger.info("Tool data provided.")

            # mock for demo mode
            if "demo" in st.session_state.get("mode"):
                st.session_state.tool_list = st.session_state.demo_tool_data
            else:
                st.session_state.tool_list = st.session_state.tool_data

            msg = f"""
                Thank you! I have read the following 
                {len(st.session_state.tool_list)} files:
                {', '.join([f"`{f.name}`" for f in st.session_state.tool_list])}.
                """
            self._write_and_history("Assistant", msg)

        if not st.session_state.get("read_tools"):
            st.session_state.read_tools = []

        if len(st.session_state.read_tools) == len(st.session_state.tool_list):
            msg = f"""
                I have read all the files you provided.
                {PLEASE_ENTER_QUESTIONS}
                """
            self._write_and_history("Assistant", msg)
            return "chat"

        for fl in st.session_state.tool_list:
            tool = fl.name.split(".")[0].lower()
            if tool in st.session_state.read_tools:
                continue

            if "tsv" in fl.name:
                df = pd.read_csv(fl, sep="\t")
            else:
                df = pd.read_csv(fl)
            st.session_state.read_tools.append(tool)

            self._write_and_history(
                "Assistant",
                f"""
                `{tool}` results
                """,
            )
            st.markdown(
                f"""
                ```
                {df.to_markdown()}
                """
            )

            st.session_state.history.append({"tool": df.to_markdown()})
            logger.info("<Tool data displayed.>")

            if not any([tool in fl.name for tool in KNOWN_TOOLS]):
                self._write_and_history(
                    "Assistant",
                    f"""
                    Sorry, `{tool}` is not among the tools I know 
                    ({KNOWN_TOOLS}). Please provide information about the data
                    below (what are rows and columns, what are the values, 
                    etc.).
                    """,
                )
                return "getting_data_file_description"

            st.session_state.conversation.setup_data_input_tool(
                df.to_json(), tool
            )

            self._write_and_history(
                "Assistant",
                """
                Would you like to provide additional information, for instance
                on a contrast or experimental design? If so, please enter it
                below; if not, please enter 'no'.
                """,
            )

            return "getting_data_file_description"

    def _get_data_file_description(self):
        logger.info("Asking for additional data input info.")

        response = str(st.session_state.input)
        st.session_state.input = ""

        self._write_and_history(
            st.session_state.conversation.user_name,
            response,
        )

        if response.lower() in ["n", "no", "no."]:
            logger.info("No additional data input provided.")
            msg = """
                Okay, I will use the information from the tool without further
                specification.
                """
            self._write_and_history("Assistant", msg)
            return self._get_data_input()

        logger.info("Additional data input provided.")
        st.session_state.conversation.append_user_message(response)
        data_input_response = "Thank you for the input!"
        self._write_and_history("Assistant", data_input_response)
        return self._get_data_input()

    def _ask_for_manual_data_input(self):
        logger.info("Asking for manual data input.")
        msg = """
            Please provide a list of biological data points (activities of
            pathways or transcription factors, expression of transcripts or
            proteins), optionally with directional information and/or a
            contrast. Since you did not provide any tool data, please try to be
            as specific as possible. You can also paste `markdown` tables or
            other structured data here.
            """
        self._write_and_history("Assistant", msg)
        return "getting_manual_data_input"

    def _get_data_input_manual(self):
        logger.info("No tool info provided. Getting manual data input.")

        st.session_state.conversation.setup_data_input_manual(
            st.session_state.input
        )

        self._write_and_history(
            st.session_state.conversation.user_name,
            st.session_state.input,
        )

        data_input_response = (
            "Thank you for the input. " f"{PLEASE_ENTER_QUESTIONS}"
        )
        self._write_and_history("Assistant", data_input_response)

        return "chat"

    def _get_response(self):
        logger.info("Getting response from LLM.")

        response, token_usage, correction = st.session_state.conversation.query(
            st.session_state.input
        )

        if not token_usage:
            # indicates error
            msg = "The model appears to have encountered an error. " + response
            self._write_and_history("Assistant", msg)
            st.session_state.error = True

            token_usage = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }

            return response, token_usage

        self._write_and_history(
            st.session_state.conversation.user_name, st.session_state.input
        )

        if correction:
            self._write_and_history("ChatGSE", response)
            self._write_and_history("Correcting agent", correction)

        else:
            self._write_and_history("ChatGSE", response)

        return response, token_usage
