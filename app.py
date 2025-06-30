import streamlit as st
import spacy
from spacy_layout import spaCyLayout
import os
import sys
from pathlib import Path

# ---- SPAKY MODEL LOADER WITH COMPLETE ERROR HANDLING ----
@st.cache_resource
def load_nlp_model():
    try:
        # Try direct load first
        return spacy.load("en_core_web_sm")
    except OSError:
        st.warning("First-time setup: Installing spaCy model...")
        
        # Installation methods from most to least reliable
        install_attempts = [
            lambda: os.system(f"{sys.executable} -m spacy download en_core_web_sm"),
            lambda: os.system(f"{sys.executable} -m pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1.tar.gz"),
            lambda: os.system(f"{sys.executable} -m pip install en_core_web_sm")
        ]
        
        for attempt in install_attempts:
            if attempt() == 0:  # If installation succeeded
                try:
                    return spacy.load("en_core_web_sm")
                except Exception as e:
                    continue
        
        # If all attempts failed
        model_path = Path(spacy.util.get_data_path()) / "en_core_web_sm"
        st.error(f"""
            Failed to load spaCy model. Please try:
            1. Manually run: `python -m spacy download en_core_web_sm`
            2. Check model exists at: {model_path}
            3. Restart your application
            """)
        st.stop()

# Load model once when app starts
           nlp = load_nlp_model()
           layout = spaCyLayout(nlp)

# ---- REST OF YOUR APP CODE ----
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
