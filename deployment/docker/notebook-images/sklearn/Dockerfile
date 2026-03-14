# One Data Studio Lite - Scikit-learn Notebook Image
FROM one-data-studio/notebook-base:latest

LABEL maintainer="One Data Studio <dev@one-data-studio.local>"
LABEL description="Data science notebook with scikit-learn"

# Switch to root to install additional packages
USER root

# Install Python data science packages
RUN pip install --no-cache-dir \
    # Core ML
    scikit-learn>=1.3.0 \
    xgboost>=2.0.0 \
    lightgbm>=4.1.0 \
    catboost>=1.2.0 \
    # Imbalanced learning
    imbalanced-learn>=0.11.0 \
    # Feature engineering
    feature-engine>=1.6.0 \
    category_encoders>=2.6.0 \
    # Hyperparameter optimization
    optuna>=3.4.0 \
    optuna-integration>=3.4.0 \
    # Model interpretation
    shap>=0.43.0 \
    lime>=0.2.0 \
    eli5>=0.13.0 \
    # AutoML
    auto-sklearn>=0.15.0 \
    tpot>=0.12.0 \
    # Time series
    sktime>=0.24.0 \
    pmdarima>=2.0.0 \
    prophet>=2.0.0 \
    # Geospatial
    geopandas>=0.14.0 \
    # Network analysis
    networkx>=3.2.0 \
    # NLP
    spacy>=3.7.0 \
    nltk>=3.8.0 \
    textacy>=0.14.0 \
    # Web scraping
    beautifulsoup4>=4.12.0 \
    scrapy>=2.11.0 \
    selenium>=4.15.0

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Download NLTK data
RUN python -c "import nltk; nltk.download('popular'); nltk.download('punkt')"

# Clean up
RUN apt-get clean && rm -rf /tmp/*

# Switch to jovyan user
USER ${NB_USER}
WORKDIR ${HOME}

# Set default command
CMD ["start-notebook.sh"]
