# One Data Studio Lite - PyTorch Notebook Image
FROM one-data-studio/notebook-base:latest

LABEL maintainer="One Data Studio <dev@one-data-studio.local>"
LABEL description="PyTorch notebook image with CUDA support"

# Switch to root to install PyTorch
USER root

# Install PyTorch with CUDA support
# Adjust CUDA version based on your driver
RUN pip install --no-cache-dir \
    torch>=2.1.0 \
    torchvision>=0.16.0 \
    torchaudio>=2.1.0 \
    --index-url https://download.pytorch.org/whl/cu118

# Install additional ML libraries
RUN pip install --no-cache-dir \
    # Training utilities
    pytorch-lightning>=2.1.0 \
    lightning-utilities>=0.10.0 \
    torchmetrics>=1.2.0 \
    # Optimizers
    accelerate>=0.25.0 \
    deepspeed>=0.12.0 \
    # Data processing
    albumentations>=1.3.0 \
    opencv-python>=4.8.0 \
    pillow>=10.1.0 \
    # Visualization
    wandb>=0.16.0 \
    tensorboard>=2.15.0 \
    # Model utilities
    timm>=0.9.12 \
    transformers>=4.35.0 \
    # Sentence embeddings
    sentence-transformers>=2.2.0 \
    # Differential privacy
    opacus>=1.3.0

# Clean up
RUN apt-get clean && rm -rf /tmp/*

# Switch to jovyan user
USER ${NB_USER}
WORKDIR ${HOME}

# Set default command
CMD ["start-notebook.sh"]
