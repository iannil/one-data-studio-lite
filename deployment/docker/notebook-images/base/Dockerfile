# One Data Studio Lite - Base Notebook Image
FROM jupyter/scipy-notebook:latest

LABEL maintainer="One Data Studio <dev@one-data-studio.local>"
LABEL description="Base Jupyter notebook image for One Data Studio Lite"

# Set environment variables
ENV NB_USER=jovyan \
    NB_UID=1000 \
    NB_GID=100 \
    HOME=/home/jovyan \
    JUPYTER_ENABLE_LAB=yes

# Switch to root to install system dependencies
USER root

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    wget \
    vim \
    htop \
    procps \
    # GPU support dependencies
    libcuda1 \
    libnvinfer7 \
    libnvinfer-plugin7 \
    libnvonnxplugins7 \
    libnvparsers7 \
    libnvrtc-inference7.2 \
    libnvinfer-plugin-dev \
    libnvinfer-dev \
    libnvonnxplugins-dev \
    libnvparsers-dev \
    libnvrtc-inference-dev \
    # PostgreSQL client
    postgresql-client \
    # Redis client
    redis-tools \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages common to all images
RUN pip install --no-cache-dir \
    jupyterlab>=4.0.0 \
    jupyterlab-git>=0.41.0 \
    jupyterlab-lsp>=4.0.0 \
    # Python language server
    python-lsp-server[all]>=1.8.0 \
    # Extensions
    jupyterlab-code-formatter>=2.2.0 \
    jupyterlab-variable-inspector>=3.1.0 \
    ipywidgets>=8.0.0 \
    # Data utilities
    kaggle>=1.5.16 \
    # AWS S3
    boto3>=1.28.0 \
    # MLflow
    mlflow>=2.9.0 \
    # Plotting
    plotly>=5.18.0 \
    seaborn>=0.13.0 \
    # Utilities
    python-dotenv>=1.0.0 \
    pyyaml>=6.0.0 \
    requests>=2.31.0 \
    tqdm>=4.66.0 \
    ipykernel>=6.28.0

# Copy custom Jupyter configuration
COPY jupyter_lab_config.py /etc/jupyter/jupyter_lab_config.py

# Create working directories
RUN mkdir -p /home/jovyan/data \
             /home/jovyan/shared \
             /home/jovyan/datasets \
             /home/jovyan/models \
             /home/jovyan/exports

# Set ownership
RUN chown -R ${NB_UID}:${NB_GID} /home/jovyan

# Switch to jovyan user
USER ${NB_USER}
WORKDIR ${HOME}

# Expose ports
EXPOSE 8888

# Set default command
CMD ["start-notebook.sh"]
