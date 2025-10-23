#!/usr/bin/env python3
"""
Test script for Llama Embed Nemotron 8B via Hugging Face
"""

import torch
from transformers import AutoModel, AutoTokenizer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_llama_embed_nemotron():
    """Test Llama Embed Nemotron 8B model"""
    try:
        model_name = "nvidia/llama-embed-nemotron-8b"
        logger.info(f"Loading model: {model_name}")

        # Load tokenizer and model
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModel.from_pretrained(model_name, trust_remote_code=True)

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
        return True

    except Exception as e:
        logger.error(f"❌ Error testing model: {e}")
        return False


if __name__ == "__main__":
    success = test_llama_embed_nemotron()
    exit(0 if success else 1)
