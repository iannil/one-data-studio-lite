# One Data Studio Lite - TensorFlow Notebook Image
FROM one-data-studio/notebook-base:latest

LABEL maintainer="One Data Studio <dev@one-data-studio.local>"
LABEL description="TensorFlow notebook image with Keras"

# Switch to root to install TensorFlow
USER root

# Install TensorFlow with GPU support
RUN pip install --no-cache-dir \
    tensorflow>=2.14.0 \
    tensorflow-gpu>=2.14.0 \
    keras>=2.14.0 \
    tensorflow-datasets>=4.9.0 \
    tensorflow-hub>=0.15.0

# Install additional ML libraries
RUN pip install --no-cache-dir \
    # Training utilities
    keras-tuner>=1.3.0 \
    keras-cv>=0.6.0 \
    keras-nlp>=0.7.0 \
    # Visualization
    tensorboard>=2.15.0 \
    wandb>=0.16.0 \
    # Model utilities
    tensorflow-model-optimization>=0.7.0 \
    tensorflow-privacy>=0.8.0 \
    # Data processing
    opencv-python>=4.8.0 \
    albumentations>=1.3.0

# Clean up
RUN apt-get clean && rm -rf /tmp/*

# Switch to jovyan user
USER ${NB_USER}
WORKDIR ${HOME}

# Set default command
CMD ["start-notebook.sh"]
