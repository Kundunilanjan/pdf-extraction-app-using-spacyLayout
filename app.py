import streamlit as st
import spacy
from spacy_layout import spaCyLayout
import pandas as pd
from collections import Counter

# Set page config
st.set_page_config(page_title="📄 PDF Extractor", layout="wide")
st.title("📄 Extract Info from PDF using spaCyLayout")

# Load spaCy model (with error handling)
@st.cache_resource
def load_spacy_model():
    try:
        nlp = spacy.load("en_core_web_sm")
        return nlp
    except OSError:
        st.error("The spaCy English model is not installed. Please wait while we download it...")
        import subprocess
        import sys
        subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
        nlp = spacy.load("en_core_web_sm")
        return nlp

uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])
if uploaded_file:
    with st.spinner("Processing PDF..."):
        try:
            # Save the uploaded file temporarily
            with open("temp.pdf", "wb") as f:
                f.write(uploaded_file.read())

            # Load models
            nlp = load_spacy_model()
            layout = spaCyLayout(nlp)
            doc = layout("temp.pdf")

            # Full text
            st.subheader("📜 Full Text")
            st.text_area("Text", doc.text, height=300)

            # Tables
            st.subheader("📊 Tables")
            if doc._.tables:
                for i, table in enumerate(doc._.tables):
                    st.write(f"Table {i+1}")
                    raw_data = table._.data
                    df = pd.DataFrame(raw_data)
                    df.columns = [col if str(col).strip() else f"Unnamed_{i}" for i, col in enumerate(df.columns)]
                    counts = Counter()
                    new_cols = []
                    for col in df.columns:
                        counts[col] += 1
                        if counts[col] > 1:
                            new_cols.append(f"{col}.{counts[col]-1}")
                        else:
                            new_cols.append(col)
                    df.columns = new_cols
                    st.dataframe(df)
            else:
                st.info("No tables detected.")

            # Spans
            st.subheader("🔍 Detected Spans (Headers, Abstracts, Authors, etc.)")
            if "layout" in doc.spans:
                for span in doc.spans["layout"]:
                    st.markdown(f"**{span.label_}:** {span.text}")
            else:
                st.warning("No layout spans detected.")

        except Exception as e:
            st.error(f"Error while processing the PDF: {str(e)}")
        finally:
            # Clean up the temporary file
            import os
            if os.path.exists("temp.pdf"):
                os.remove("temp.pdf")
