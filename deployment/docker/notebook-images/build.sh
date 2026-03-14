#!/bin/bash
# One Data Studio Lite - Build Notebook Images
# Build all notebook images for Jupyter Hub

set -e

REGISTRY="${REGISTRY:-one-data-studio}"
TAG="${TAG:-latest}"

echo "Building notebook images for registry: $REGISTRY, tag: $TAG"

# Build base image first
echo "Building base notebook image..."
docker build -t ${REGISTRY}/notebook-base:${TAG} -f base/Dockerfile .

# Build PyTorch image
echo "Building PyTorch notebook image..."
docker build -t ${REGISTRY}/notebook-pytorch:${TAG} -f pytorch/Dockerfile .

# Build TensorFlow image
echo "Building TensorFlow notebook image..."
docker build -t ${REGISTRY}/notebook-tensorflow:${TAG} -f tensorflow/Dockerfile .

# Build sklearn image
echo "Building sklearn notebook image..."
docker build -t ${REGISTRY}/notebook-sklearn:${TAG} -f sklearn/Dockerfile .

# Build NLP image
echo "Building NLP notebook image..."
docker build -t ${REGISTRY}/notebook-nlp:${TAG} -f nlp/Dockerfile .

echo "All notebook images built successfully!"
echo ""
echo "Images:"
echo "  ${REGISTRY}/notebook-base:${TAG}"
echo "  ${REGISTRY}/notebook-pytorch:${TAG}"
echo "  ${REGISTRY}/notebook-tensorflow:${TAG}"
echo "  ${REGISTRY}/notebook-sklearn:${TAG}"
echo "  ${REGISTRY}/notebook-nlp:${TAG}"
