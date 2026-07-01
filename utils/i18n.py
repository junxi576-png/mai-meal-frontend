import streamlit as st
from config import EN_DICT, MAP_DICT

def t(text):
    if st.session_state.lang == 'en': 
        return EN_DICT.get(text, text)
    return text

def tf(category, text):
    if st.session_state.lang == 'en': 
        return MAP_DICT[category].get(text, text)
    else:
        if category == 'allergens' and ' (' in text and text.endswith(')'):
            return text.split(' (')[1].rstrip(')')
        return text