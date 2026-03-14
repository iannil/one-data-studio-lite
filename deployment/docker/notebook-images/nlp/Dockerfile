# One Data Studio Lite - NLP Notebook Image
FROM one-data-studio/notebook-base:latest

LABEL maintainer="One Data Studio <dev@one-data-studio.local>"
LABEL description="NLP notebook with Transformers and spaCy"

# Switch to root to install NLP packages
USER root

# Install NLP libraries
RUN pip install --no-cache-dir \
    # Transformers
    transformers>=4.35.0 \
    datasets>=2.15.0 \
    tokenizers>=0.15.0 \
    evaluate>=0.4.0 \
    # Accelerate
    accelerate>=0.25.0 \
    # PEFT and LoRA
    peft>=0.7.0 \
    bitsandbytes>=0.1.0 \
    # Text generation
    text-generation>=0.6.0 \
    # Embeddings
    sentence-transformers>=2.2.0 \
    # LLM
    langchain>=0.1.0 \
    openai>=1.3.0 \
    anthropic>=0.7.0 \
    # spaCy
    spacy>=3.7.0 \
    # NLP utilities
    nltk>=3.8.0 \
    textacy>=0.14.0 \
    gensim>=4.3.0 \
    # Information extraction
    spacy-lookups-data>=1.0.0 \
    # Question answering
    farm>=0.9.0 \
    haystack>=2.0.0 \
    # Translation
    sacremoses>=0.1.1 \
    # OCR
    pytesseract>=0.3.10 \
    pdf2image>=1.16.0 \
    # Document processing
    pypdf>=3.17.0 \
    docx2txt>=0.8 \
    # Vector stores
    faiss-cpu>=1.7.4 \
    chromadb>=0.4.0 \
    qdrant-client>=1.6.0 \
    # Evaluation
    rouge-score>=0.1.2 \
    sacrebleu>=2.3.1 \
    bert-score>=0.4.0 \
    # Visualization
    spacy-streamlit>=1.0.0 \
    streamlit>=1.29.0

# Download spaCy models
RUN python -m spacy download en_core_web_sm && \
    python -m spacy download en_core_web_md && \
    python -m spacy download en_core_web_lg

# Download NLTK data
RUN python -c "import nltk; nltk.download('popular'); nltk.download('punkt'); nltk.download('averaged_perceptron_tagger'); nltk.download('maxent_ne_chunker'); nltk.download('words')"

# Install system dependencies for OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-chi-sim \
    tesseract-ocr-chi-tra \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Clean up
RUN apt-get clean && rm -rf /tmp/*

# Switch to jovyan user
USER ${NB_USER}
WORKDIR ${HOME}

# Set default command
CMD ["start-notebook.sh"]
