import streamlit as st
import pickle
import numpy as np
import os
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences


# ------------------------------
# Load saved files
# ------------------------------
@st.cache_resource
def load_resources():

    # Folder where app.py exists
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Full paths
    model_path = os.path.join(base_dir, "lstm_model.h5")
    tokenizer_path = os.path.join(base_dir, "tokenizer.pkl")
    max_len_path = os.path.join(base_dir, "max_len.pkl")

    # Debug check (optional)
    st.write("Looking for model at:", model_path)

    # Load files
    model = load_model(model_path)

    with open(tokenizer_path, "rb") as f:
        tokenizer = pickle.load(f)

    with open(max_len_path, "rb") as f:
        max_len = pickle.load(f)

    return model, tokenizer, max_len


# Load resources
model, tokenizer, max_len = load_resources()


# ------------------------------
# Prediction function
# ------------------------------
def predict_next_word(text):
    sequence = tokenizer.texts_to_sequences([text])[0]

    if len(sequence) == 0:
        return "No prediction"

    sequence = pad_sequences(
        [sequence],
        maxlen=max_len - 1,
        padding="pre"
    )

    preds = model.predict(sequence, verbose=0)
    predicted_index = np.argmax(preds)

    for word, index in tokenizer.word_index.items():
        if index == predicted_index:
            return word

    return "Word not found"


# ------------------------------
# UI
# ------------------------------
st.set_page_config(page_title="Next Word Prediction")

st.title("🧠 Next Word Prediction")

user_input = st.text_input("Enter text")

if st.button("Predict"):
    if user_input.strip():
        next_word = predict_next_word(user_input)
        st.success(f"Predicted word: {next_word}")
    else:
        st.warning("Please enter text.")