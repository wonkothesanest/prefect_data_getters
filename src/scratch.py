from langchain_huggingface import HuggingFacePipeline
from transformers import pipeline
import torch

# Check if CUDA (GPU) is available
device = 0 if torch.cuda.is_available() else -1

# Load DistilBART model optimized for summarization
summarizer_pipeline = pipeline(
    "summarization", 
    model="sshleifer/distilbart-cnn-6-6",
    device=device  # This ensures the model runs on GPU if available
)

# Wrap in LangChain's HuggingFace integration
llm = HuggingFacePipeline(pipeline=summarizer_pipeline)

# Function to summarize text
def summarize_text(text):
    summary = llm.invoke(text)
    return summary

# Example text
document = """
Solar energy is one of the most promising renewable energy sources. The advancement in photovoltaic technology has led to
increased efficiency and lower costs. Many countries are adopting solar energy to reduce their reliance on fossil fuels
and combat climate change. Governments and private entities are investing heavily in large-scale solar farms as well as
rooftop solar installations.
"""
for i in range(10):
    summary = summarize_text(document)
    print("Summary:", summary)
