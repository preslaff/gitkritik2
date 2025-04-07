# gitkritik/core/llms/local_llm.py

from gitkritik2.core.config import Settings
from typing import Dict, Any
import requests
import os

from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from transformers.pipelines import TextGenerationPipeline

_local_model_cache = {}

def call_local(system_prompt: str, user_prompt: str, settings: Settings, common: Dict[str, Any]) -> str:
    """
    Unified local model interface supporting:
    - Ollama API (http://localhost:11434)
    - Hugging Face Transformers (locally loaded models)
    """
    backend = os.getenv("GITKRITIK_LOCAL_BACKEND", "ollama").lower()

    if backend == "ollama":
        return _call_ollama(system_prompt, user_prompt)
    elif backend == "huggingface":
        return _call_huggingface(system_prompt, user_prompt, settings)
    else:
        return f"⚠️ Unknown local backend '{backend}'. Use 'ollama' or 'huggingface'."

def _call_ollama(system_prompt: str, user_prompt: str) -> str:
    prompt = f"{system_prompt}\n\n{user_prompt}"
    try:
        response = requests.post("http://localhost:11434/api/generate", json={
            "model": os.getenv("GITKRITIK_LOCAL_MODEL", "llama2"),
            "prompt": prompt,
            "stream": False
        }, timeout=30)
        response.raise_for_status()
        return response.json()["response"].strip()
    except Exception as e:
        return f"❌ Ollama error: {e}"

def _call_huggingface(system_prompt: str, user_prompt: str, settings: Settings) -> str:
    global _local_model_cache

    model_id = os.getenv("GITKRITIK_LOCAL_MODEL", "tiiuae/falcon-7b-instruct")
    prompt = f"{system_prompt}\n\n{user_prompt}"

    if model_id not in _local_model_cache:
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(model_id)
        generator = pipeline("text-generation", model=model, tokenizer=tokenizer)
        _local_model_cache[model_id] = generator
    else:
        generator = _local_model_cache[model_id]

    outputs = generator(prompt, max_length=settings.max_tokens, temperature=settings.temperature, num_return_sequences=1)
    return outputs[0]["generated_text"].strip()
