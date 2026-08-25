import os
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.embeddings import Embeddings

def get_dynamic_llm(provider: str, model_name: str, temp: float = 0.2) -> BaseChatModel:
    """Dynamically returns the requested text generation model."""
    
    # Catch both deprecated Llama models and upgrade to the active 20B model!
    if provider.lower() == "groq" and model_name in ["llama3-8b-8192", "llama-3.1-8b-instant"]:
        model_name = "openai/gpt-oss-20b"

    if provider.lower() == "gemini":
        return ChatGoogleGenerativeAI(
            model=model_name, 
            temperature=temp, 
            google_api_key=os.getenv("GEMINI_API_KEY")
        )
    elif provider.lower() == "groq":
        return ChatGroq(
            model_name=model_name, 
            temperature=temp, 
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def get_dynamic_embeddings() -> Embeddings:
    """Returns the Gemini embedding model forced to 768 dimensions."""
    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        output_dimensionality=768,
        google_api_key=os.getenv("GEMINI_API_KEY")
    )