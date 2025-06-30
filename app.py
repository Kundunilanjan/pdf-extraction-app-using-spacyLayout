import streamlit as st
import pdfplumber
import spacy
import layoutparser as lp
import pandas as pd
import re
from collections import defaultdict
import tempfile

# Set page config
st.set_page_config(
    page_title="PDF Structure Analyzer",
    page_icon="📄",
    layout="wide"
)

@st.cache_resource
def load_nlp_model():
    """Load spaCy model with caching"""
    try:
        return spacy.load("en_core_web_sm")
    except:
        from spacy.cli import download
        download("en_core_web_sm")
        return spacy.load("en_core_web_sm")

nlp = load_nlp_model()

def analyze_pdf(uploaded_file):
    """Main analysis function"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getbuffer())
        return extract_pdf_structure(tmp.name)

def extract_pdf_structure(pdf_path):
    """Extract document structure with layout analysis"""
    results = {
        'metadata': {},
        'headers': set(),
        'footers': set(),
        'paragraphs': [],
        'toc': [],
        'sections': []
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Extract metadata
            results['metadata'] = {
                'pages': len(pdf.pages),
                'author': pdf.metadata.get('Author', 'Unknown'),
                'title': pdf.metadata.get('Title', 'Untitled')
            }
            
            # Layout analysis setup
            model = lp.Detectron2LayoutModel(
                'lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config',
                extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.8],
                label_map={0: "Text", 1: "Title", 2: "List", 3: "Table", 4: "Figure"}
            )
            
            # Analyze sample pages
            sample_pages = min(5, len(pdf.pages))
            for i in range(sample_pages):
                page = pdf.pages[i]
                im = page.to_image(resolution=72).original
                layout = model.detect(im)
                
                # Detect headers/footers
                header_zone = page.height * 0.15
                footer_zone = page.height * 0.85
                
                for block in layout:
                    if block.type == 'Title' and block.block.y_1 < header_zone:
                        results['headers'].add(block.text)
                    elif block.block.y_2 > footer_zone:
                        results['footers'].add(block.text)
            
            # Convert sets to lists
            results['headers'] = list(results['headers'])
            results['footers'] = list(results['footers'])
            
            # Extract all text for NLP processing
            full_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
            doc = nlp(full_text)
            
            # Paragraph extraction
            results['paragraphs'] = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 20]
            
            # TOC detection
            results['toc'] = detect_toc(doc)
            
            # Section detection
            results['sections'] = detect_sections(doc)
            
    except Exception as e:
        st.error(f"Error analyzing PDF: {str(e)}")
    
    return results

def detect_toc(doc):
    """Detect table of contents"""
    toc_items = []
    toc_patterns = [
        r'contents', r'table of contents', r'chapters?', r'sections?',
        r'^\s*(chapter|section|part|appendix)\s+[ivx\d]+',
        r'^\s*\d+(\.\d+)*\s+',
        r'^\s*[ivx]+(\s+[a-z])?\s*[–-]',
        r'\.{3,}\s*\d+$'
    ]
    
    for sent in doc.sents:
        if any(re.search(pattern, sent.text.lower()) for pattern in toc_patterns):
            toc_items.append(sent.text)
    
    return toc_items

def detect_sections(doc):
    """Detect document sections"""
    sections = []
    current_section = None
    
    heading_patterns = [
        r'^\s*(chapter|section|part|appendix)\s+[ivx\d]+',
        r'^\s*\d+(\.\d+)*\s+',
        r'^\s*[A-Z][A-Z0-9\s]+\s*$'
    ]
    
    for sent in doc.sents:
        if any(re.search(pattern, sent.text) for pattern in heading_patterns):
            if current_section:
                sections.append(current_section)
            current_section = {
                'heading': sent.text,
                'content': []
            }
        elif current_section:
            current_section['content'].append(sent.text)
    
    if current_section:
        sections.append(current_section)
    
    return sections

def main():
    st.title("📄 Advanced PDF Structure Analyzer")
    st.markdown("""
    Upload a PDF to analyze its structure including:
    - Headers and footers
    - Table of contents
    - Document sections
    - Paragraph structure
    """)
    
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file:
        with st.spinner("Analyzing document structure..."):
            analysis = analyze_pdf(uploaded_file)
        
        st.success("Analysis complete!")
        
        # Display results in tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Structure", "Contents", "Raw Text"])
        
        with tab1:
            st.subheader("Document Metadata")
            col1, col2, col3 = st.columns(3)
            col1.metric("Pages", analysis['metadata']['pages'])
            col2.metric("Title", analysis['metadata']['title'])
            col3.metric("Author", analysis['metadata']['author'])
            
            st.subheader("Document Statistics")
            col1, col2, col3 = st.columns(3)
            col1.metric("Headers", len(analysis['headers']))
            col2.metric("Footers", len(analysis['footers']))
            col3.metric("Paragraphs", len(analysis['paragraphs']))
        
        with tab2:
            st.subheader("Headers")
            if analysis['headers']:
                for header in analysis['headers']:
                    st.code(header)
            else:
                st.warning("No headers detected")
            
            st.subheader("Footers")
            if analysis['footers']:
                for footer in analysis['footers']:
                    st.code(footer)
            else:
                st.warning("No footers detected")
            
            st.subheader("Table of Contents")
            if analysis['toc']:
                st.dataframe(pd.DataFrame(analysis['toc'], columns=["TOC Items"]))
            else:
                st.warning("No table of contents detected")
        
        with tab3:
            st.subheader("Document Sections")
            if analysis['sections']:
                for section in analysis['sections']:
                    with st.expander(section['heading']):
                        st.write(" ".join(section['content'][:3]))
            else:
                st.info("No sections detected")
        
        with tab4:
            st.subheader("Extracted Paragraphs")
            min_len = st.slider("Minimum paragraph length", 20, 200, 50)
            filtered = [p for p in analysis['paragraphs'] if len(p) >= min_len]
            
            for i, para in enumerate(filtered, 1):
                st.markdown(f"**Paragraph {i}** ({len(para)} characters)")
                st.write(para)
                st.divider()

if __name__ == "__main__":
    main()
