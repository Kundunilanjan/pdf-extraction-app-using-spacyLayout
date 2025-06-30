import streamlit as st
import subprocess
import spacy
from spacy_layout import spaCyLayout
import pandas as pd
from collections import Counter

# Ensure model is downloaded
subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])

st.set_page_config(page_title="📄 PDF Extractor", layout="wide")
st.title("📄 Extract Info from PDF using spaCyLayout")

uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])
if uploaded_file:
    with open("temp.pdf", "wb") as f:
        f.write(uploaded_file.read())

    try:
        # Load NLP pipeline
        nlp = spacy.load("en_core_web_sm")
        layout = spaCyLayout(nlp)
        doc = layout("temp.pdf")

        # Display full text
        st.subheader("📜 Full Text")
        st.text_area("Text", doc.text, height=300)

        # Extract tables safely
        st.subheader("📊 Tables")
        if doc._.tables:
            for i, table in enumerate(doc._.tables):
                st.write(f"Table {i+1}")

                raw_data = table._.data
                df = pd.DataFrame(raw_data)

                # Fix empty column names
                df.columns = [col if str(col).strip() else f"Unnamed_{i}" for i, col in enumerate(df.columns)]

                # Fix duplicate column names
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

        # Show layout-labeled spans (headers, footers, authors, abstracts, etc.)
        st.subheader("🔍 Detected Spans (Headers, Abstracts, Authors, etc.)")
        if "layout" in doc.spans:
            for span in doc.spans["layout"]:
                st.markdown(f"**{span.label_}:** {span.text}")
        else:
            st.warning("No layout spans detected.")

    except Exception as e:
        st.error(f"Error while processing the PDF: {e}")
