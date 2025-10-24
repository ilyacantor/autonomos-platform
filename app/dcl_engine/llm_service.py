import os
import time
import json
import re
import traceback
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import google.generativeai as genai  # type: ignore


class LLMService(ABC):
    """Abstract LLM service interface for different providers"""
    
    @abstractmethod
    def generate(self, prompt: str, source_key: str) -> Optional[Dict[str, Any]]:
        """Generate structured JSON output from prompt"""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Return model identifier for telemetry"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider name for logging"""
        pass


class GeminiService(LLMService):
    """Gemini LLM implementation using gemini-2.5-flash"""
    
    def __init__(self, model: str = "gemini-2.5-flash"):
        self.model = model
        if not os.getenv("GEMINI_API_KEY"):
            raise ValueError("GEMINI_API_KEY not set")
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    
    def generate(self, prompt: str, source_key: str) -> Optional[Dict[str, Any]]:
        """
        Wrapper around Gemini calls that guarantees a result with proper logging.
        Refactored from safe_llm_call() - preserves all original error handling.
        """
        gemini_start = time.time()
        try:
            resp = genai.GenerativeModel(self.model).generate_content(prompt)
            
            # Extract token usage
            tokens = 0
            try:
                usage = resp.usage_metadata
                if hasattr(usage, 'total_token_count'):
                    tokens = usage.total_token_count
            except Exception:
                pass
            
            # Parse JSON from response
            try:
                text = resp.text.strip()
                if text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\n?", "", text)
                    text = re.sub(r"\n?```$", "", text)
                    text = text.strip()
                m = re.search(r"\{.*\}", text, re.DOTALL)
                if not m:
                    raise ValueError("No JSON object found in response")
                result = json.loads(m.group(0))
                
                # Log timing
                gemini_elapsed = time.time() - gemini_start
                print(f"⏱️ {self.get_model_name()} call: {gemini_elapsed:.2f}s | {tokens} tokens", flush=True)
                
                return result
            except Exception as parse_err:
                os.makedirs("logs", exist_ok=True)
                with open("logs/llm_failures.log", "a") as f:
                    f.write(f"--- PARSE ERROR ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---\n")
                    f.write(f"Model: {self.get_model_name()}\n")
                    f.write(f"Source: {source_key}\n")
                    f.write(f"Response: {resp.text if hasattr(resp, 'text') else 'N/A'}\n")
                    f.write(f"Error: {parse_err}\n\n")
                print(f"[LLM PARSE ERROR] {self.get_model_name()} - Falling back to heuristic for {source_key}", flush=True)
                return None
        
        except Exception as e:
            os.makedirs("logs", exist_ok=True)
            with open("logs/llm_failures.log", "a") as f:
                f.write(f"--- LLM ERROR ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---\n")
                f.write(f"Model: {self.get_model_name()}\n")
                f.write(f"Source: {source_key}\n")
                f.write(f"{traceback.format_exc()}\n\n")
            print(f"[LLM ERROR] {self.get_model_name()} - {e} - Falling back to heuristic for {source_key}", flush=True)
            return None
    
    def get_model_name(self) -> str:
        return self.model
    
    def get_provider_name(self) -> str:
        return "Gemini"


class OpenAIService(LLMService):
    """OpenAI LLM implementation for gpt-5-mini and gpt-5-nano"""
    
    def __init__(self, model: str):
        self.model = model
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not set")
        
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except ImportError:
            raise ImportError("OpenAI package not installed. Install with: pip install openai")
    
    def generate(self, prompt: str, source_key: str) -> Optional[Dict[str, Any]]:
        """
        OpenAI implementation with same error handling as Gemini.
        Uses structured output for reliable JSON parsing.
        """
        openai_start = time.time()
        try:
            # GPT-5 mini and nano only support default temperature (1)
            temp = 1.0 if ("nano" in self.model or "mini" in self.model) else 0.1
            
            # Use chat completions with JSON mode for structured output
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data integration planner. Output ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=temp
            )
            
            # Extract token usage
            tokens = 0
            try:
                tokens = response.usage.total_tokens
            except Exception:
                pass
            
            # Parse JSON from response
            try:
                text = response.choices[0].message.content.strip()
                if text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\n?", "", text)
                    text = re.sub(r"\n?```$", "", text)
                    text = text.strip()
                m = re.search(r"\{.*\}", text, re.DOTALL)
                if not m:
                    raise ValueError("No JSON object found in response")
                result = json.loads(m.group(0))
                
                # Log timing
                openai_elapsed = time.time() - openai_start
                print(f"⏱️ {self.get_model_name()} call: {openai_elapsed:.2f}s | {tokens} tokens", flush=True)
                
                return result
            except Exception as parse_err:
                os.makedirs("logs", exist_ok=True)
                with open("logs/llm_failures.log", "a") as f:
                    f.write(f"--- PARSE ERROR ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---\n")
                    f.write(f"Model: {self.get_model_name()}\n")
                    f.write(f"Source: {source_key}\n")
                    f.write(f"Response: {text}\n")
                    f.write(f"Error: {parse_err}\n\n")
                print(f"[LLM PARSE ERROR] {self.get_model_name()} - Falling back to heuristic for {source_key}", flush=True)
                return None
        
        except Exception as e:
            os.makedirs("logs", exist_ok=True)
            with open("logs/llm_failures.log", "a") as f:
                f.write(f"--- LLM ERROR ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---\n")
                f.write(f"Model: {self.get_model_name()}\n")
                f.write(f"Source: {source_key}\n")
                f.write(f"{traceback.format_exc()}\n\n")
            print(f"[LLM ERROR] {self.get_model_name()} - {e} - Falling back to heuristic for {source_key}", flush=True)
            return None
    
    def get_model_name(self) -> str:
        return self.model
    
    def get_provider_name(self) -> str:
        return "OpenAI"


def get_llm_service(model: str = "gemini-2.5-flash") -> LLMService:
    """
    Factory function to get appropriate LLM service based on model name.
    
    Args:
        model: Model identifier (e.g., "gemini-2.5-flash", "gpt-4o-mini", "gpt-4o")
    
    Returns:
        LLMService instance (GeminiService or OpenAIService)
    
    Raises:
        ValueError: If required API key is not set
    """
    if model.startswith("gpt"):
        return OpenAIService(model)
    return GeminiService(model)
