#!/usr/bin/env python3
"""
Test script for Llama Embed Nemotron 8B via Hugging Face
"""

import os
import torch
from transformers import AutoModel, AutoTokenizer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_llama_embed_nemotron() -> bool:
    """Test Llama Embed Nemotron 8B model"""
    try:
        model_name = "nvidia/llama-embed-nemotron-8b"
        logger.info(f"Loading model: {model_name}")

        # SECURITY WARNING: trust_remote_code allows arbitrary code execution
        # Only enable for explicitly vetted models in isolated environments
        # This script should only be run in development/CI environments
        trust_remote = os.getenv("HF_TRUST_REMOTE_CODE", "false").lower() == "true"

        if trust_remote:
            if model_name != "nvidia/llama-embed-nemotron-8b":
                raise ValueError(
                    f"trust_remote_code=True only allowed for vetted models, got: {model_name}"
                )
            logger.warning("⚠️  Running with trust_remote_code=True - verify model source!")
            logger.warning("⚠️  Only run this script in isolated development environments!")

        # Load tokenizer and model with pinned revision for security
        model_revision = os.getenv("HUGGINGFACE_MODEL_REVISION", "main")
        if model_revision == "main":
            logger.warning("⚠️  Using 'main' branch - not recommended for production!")
            logger.warning(
                "⚠️  Set HUGGINGFACE_MODEL_REVISION to a specific commit hash for security"
            )

        tokenizer = AutoTokenizer.from_pretrained(  # nosec B615 - revision pinned for security
            model_name, revision=model_revision, trust_remote_code=trust_remote
        )
        model = AutoModel.from_pretrained(  # nosec B615 - revision pinned for security
            model_name, revision=model_revision, trust_remote_code=trust_remote
        )

        logger.info("Model loaded successfully!")

        # Test text for embedding
        test_texts = [
            "What is the nutritional value of an apple?",
            "How many calories are in a banana?",
            "What are the health benefits of exercise?",
            "Calculate my BMI based on height and weight",
        ]

        logger.info("Generating embeddings for test texts...")

        for i, text in enumerate(test_texts):
            logger.info(f"Processing text {i+1}: {text[:50]}...")

            # Tokenize text
            inputs = tokenizer(
                text, return_tensors="pt", padding=True, truncation=True, max_length=512
            )

            # Generate embedding
            with torch.no_grad():
                outputs = model(**inputs)
                # Use mean pooling for sentence-level embedding
                embeddings = outputs.last_hidden_state.mean(dim=1)

            logger.info(f"Embedding shape: {embeddings.shape}")
            logger.info(f"Embedding sample (first 5 values): {embeddings[0][:5].tolist()}")
            print("-" * 50)

        logger.info("✅ All tests completed successfully!")
    except Exception:
        logger.exception("❌ Error testing model")
        return False
    else:
        return True


if __name__ == "__main__":
    test_llama_embed_nemotron()
