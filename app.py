from typing import Tuple, Dict, List
from dotenv import load_dotenv
import streamlit as st
import requests
import json
import io
import os

load_dotenv()

@st.cache_data
def get_chat_param() -> Tuple[str, str, str]:
    api_key: str = os.getenv("API_KEY")
    url: str = os.getenv("URL")
    model = "your-model-id"
    return api_key, url, model

class ReasoningChat(object):
    def __init__(self, api_key: str, url: str, model: str) -> None:
        self.api_key: str = api_key
        self.url: str = url
        self.model: str = model
    
    @st.cache_data
    def init_headers(_self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {_self.api_key}"
        }
        return headers
    
    @st.fragment
    def chat_response(
        self,
        query: str,
        a_session: List,
        r_session: List,
        inst: str | None,
        max_tokens: int,
        temperature: float,
        top_p: float,
        top_k: int,
        url: str,
        headers: Dict
    ) -> None:
        a_session.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        messages = [{"role": "system", "content": inst}] if inst is not None else []
        messages += a_session

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "stream": True
        }

        r_buffer = io.StringIO()
        a_buffer = io.StringIO()

        with st.expander("Thinking", True):
            r_placeholder = st.empty()
        with st.chat_message("assistant"):
            a_placeholder = st.empty()
        
        try:
            response = requests.request("POST", url, headers=headers, json=payload, stream=True)
            if response.status_code == 200:
                for chunk in response.iter_lines():
                    if not chunk:
                        continue
                    decoded_chunk: str = chunk.decode("utf-8")
                    if decoded_chunk.startswith("data: [DONE]"):
                        break
                    if decoded_chunk.startswith("data:"):
                        json_chunk = json.loads(decoded_chunk.split("data:")[1].strip())
                        if not json_chunk["choices"]:
                            continue
                        delta = json_chunk["choices"][0]["delta"]
                        if "reasoning_content" in delta and delta["reasoning_content"] is not None:
                            r_buffer.write(delta["reasoning_content"])
                            r_placeholder.markdown(r_buffer.getvalue())
                        if "content" in delta and delta["content"] is not None:
                            a_buffer.write(delta["content"])
                            a_placeholder.markdown(a_buffer.getvalue())
                
                r_content = r_buffer.getvalue()
                a_content = a_buffer.getvalue()

                r_session.append(r_content)
                a_session.append({"role": "assistant", "content": a_content})

                r_buffer.close()
                a_buffer.close()

                st.rerun()
            else:
                st.warning(f"{response.status_code}:\n\n{response.text}")
        except Exception as e:
            st.error(f"Response Error:\n\n{e}")

@st.cache_resource
def init_client(api_key: str, url: str) -> ReasoningChat:
    client = ReasoningChat(api_key=api_key, url=url)
    return client

@st.fragment
def display_conversation(a_session: List, r_session: List) -> None:
    index = 0
    for i in a_session:
        if i["role"] == "user":
            with st.chat_message("user"):
                st.markdown(i["content"])
            if index < len(r_session):
                with st.expander("Thinking", False):
                    st.markdown(r_session[index])
                index += 1
        elif i["role"] == "assistant":
            with st.chat_message("assistant"):
                st.markdown(i["content"])

def main() -> None:
    api_key, url, model = get_chat_param()
    client = ReasoningChat(api_key=api_key, url=url, model=model)
    headers: Dict[str, str] = client.init_headers()

    if "a_content" not in st.session_state:
        st.session_state.a_content = []
    if "r_content" not in st.session_state:
        st.session_state.r_content = []
    
    @st.fragment
    def clear_conversation() -> None:
        if st.button("Clear", "_clear", type="primary", use_container_width=True):
            st.session_state.a_content = []
            st.session_state.r_content = []
            st.rerun()
    
    with st.sidebar:
        clear_conversation()
        system_prompt: str = st.text_area("System Prompt", "", key="_inst")
        max_tokens: int = st.slider("Max Tokens", 1, 16384, 16384, 1, key="_tokens")
        temperature: float = st.slider("Temperature", 0.00, 2.00, 0.60, 0.01, key="_temp")
        top_p: float = st.slider("Top P", 0.01, 1.00, 0.95, 0.01, key="_topp")
        top_k: int = st.slider("Top K", 1, 100, 40, 1, key="_topk")
    
    display_conversation(st.session_state.a_content, st.session_state.r_content)

    if query := st.chat_input("Say something...", key="_query"):
        if system_prompt:
            client.chat_response(
                query=query,
                a_session=st.session_state.a_content,
                r_session=st.session_state.r_content,
                inst=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                url=url,
                headers=headers
            )
        else:
            client.chat_response(
                query=query,
                a_session=st.session_state.a_content,
                r_session=st.session_state.r_content,
                inst=None,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                url=url,
                headers=headers
            )

if __name__ == "__main__":
    main()
