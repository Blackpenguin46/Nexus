"""
LLM provider implementations for local and remote models.

This module provides a unified interface for different LLM providers,
with optimizations for Apple Silicon Macs and free local models.
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

import torch
from transformers import (
    AutoModelForCausalLM, 
    AutoTokenizer, 
    BitsAndBytesConfig,
    pipeline,
    TextGenerationPipeline
)

from .config import LLMConfig
from .exceptions import LLMError
from ..utils.logger import get_logger


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.logger = get_logger(__name__)
    
    @abstractmethod
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass


class HuggingFaceProvider(LLMProvider):
    """
    Hugging Face local model provider optimized for Apple Silicon.
    
    Supports various open-source models with memory optimization
    and Apple Metal Performance Shaders acceleration.
    """
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self._model_loaded = False
        
        # Recommended models for different use cases
        self.recommended_models = {
            "code": [
                "microsoft/CodeGPT-small-py",  # 124M - Fast for code
                "Salesforce/codet5-small",     # 60M - Very fast
                "microsoft/DialoGPT-small",    # 117M - General purpose
            ],
            "chat": [
                "microsoft/DialoGPT-medium",   # 355M - Good balance
                "facebook/blenderbot-400M-distill",  # 400M - Conversational
                "microsoft/DialoGPT-small",    # 117M - Lightweight
            ],
            "reasoning": [
                "microsoft/DialoGPT-large",    # 762M - Better reasoning
                "facebook/blenderbot-1B-distill",    # 1B - More capable
                "microsoft/DialoGPT-medium",   # 355M - Fallback
            ]
        }
    
    async def initialize(self) -> None:
        """Initialize the model and tokenizer."""
        if self._model_loaded:
            return
        
        try:
            self.logger.info(f"Loading Hugging Face model: {self.config.model}")
            
            # Configure device
            if torch.backends.mps.is_available() and self.config.device == "mps":
                device = "mps"
                self.logger.info("Using Apple Metal Performance Shaders (MPS)")
            elif torch.cuda.is_available() and self.config.device == "cuda":
                device = "cuda"
                self.logger.info("Using CUDA")
            else:
                device = "cpu"
                self.logger.info("Using CPU")
            
            # Configure quantization for memory efficiency
            quantization_config = None
            if self.config.load_in_4bit and device != "mps":  # MPS doesn't support quantization yet
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
                self.logger.info("Using 4-bit quantization")
            elif self.config.load_in_8bit and device != "mps":
                quantization_config = BitsAndBytesConfig(load_in_8bit=True)
                self.logger.info("Using 8-bit quantization")
            
            # Load tokenizer
            await asyncio.to_thread(self._load_tokenizer)
            
            # Load model
            await asyncio.to_thread(self._load_model, device, quantization_config)
            
            # Create pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=device if device != "mps" else -1,  # -1 for MPS
                torch_dtype=getattr(torch, self.config.torch_dtype),
                return_full_text=False,
                max_new_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                do_sample=self.config.temperature > 0,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            self._model_loaded = True
            self.logger.info("Model loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            raise LLMError(
                f"Failed to initialize Hugging Face model: {e}",
                api_provider="huggingface",
                details={"model": self.config.model}
            )
    
    def _load_tokenizer(self) -> None:
        """Load the tokenizer."""
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.model,
            trust_remote_code=self.config.trust_remote_code,
            padding_side="left"  # For batch processing
        )
        
        # Add pad token if not present
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
    
    def _load_model(self, device: str, quantization_config: Optional[Any]) -> None:
        """Load the model."""
        model_kwargs = {
            "trust_remote_code": self.config.trust_remote_code,
            "torch_dtype": getattr(torch, self.config.torch_dtype),
        }
        
        if quantization_config and device != "mps":
            model_kwargs["quantization_config"] = quantization_config
        elif device == "mps":
            # MPS-specific optimizations
            model_kwargs["device_map"] = None  # Let us handle device placement
        
        self.model = AutoModelForCausalLM.from_pretrained(
            self.config.model,
            **model_kwargs
        )
        
        # Move to device if MPS
        if device == "mps":
            self.model = self.model.to("mps")
        
        # Enable memory optimizations
        if self.config.enable_attention_slicing:
            if hasattr(self.model, 'enable_attention_slicing'):
                self.model.enable_attention_slicing()
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Generate a response from the Hugging Face model."""
        if not self._model_loaded:
            await self.initialize()
        
        try:
            # Convert messages to prompt format
            prompt = self._format_messages_to_prompt(messages, tools)
            
            # Generate response
            start_time = time.time()
            
            result = await asyncio.to_thread(
                self._generate_text, 
                prompt
            )
            
            generation_time = time.time() - start_time
            
            # Parse response for tool calls if tools are available
            response_data = self._parse_response(result, tools)
            response_data["generation_time"] = generation_time
            
            return response_data
            
        except Exception as e:
            self.logger.error(f"Generation failed: {e}")
            raise LLMError(
                f"Failed to generate response: {e}",
                api_provider="huggingface",
                details={"model": self.config.model}
            )
    
    def _generate_text(self, prompt: str) -> str:
        """Generate text using the pipeline."""
        # Truncate prompt if too long
        max_input_length = self.config.max_context_window - self.config.max_tokens
        input_ids = self.tokenizer.encode(prompt, return_tensors="pt")
        
        if input_ids.shape[1] > max_input_length:
            input_ids = input_ids[:, -max_input_length:]
            prompt = self.tokenizer.decode(input_ids[0], skip_special_tokens=True)
        
        # Generate
        outputs = self.pipeline(
            prompt,
            max_new_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            do_sample=self.config.temperature > 0,
            num_return_sequences=1,
            clean_up_tokenization_spaces=True
        )
        
        return outputs[0]['generated_text'].strip()
    
    def _format_messages_to_prompt(
        self, 
        messages: List[Dict[str, str]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Format messages into a single prompt."""
        prompt_parts = []
        
        # Add system context
        prompt_parts.append("You are Manus, an autonomous AI agent that helps users complete tasks.")
        prompt_parts.append("You can analyze problems, plan solutions, and execute actions to achieve goals.")
        
        # Add tool information if available
        if tools:
            tool_descriptions = []
            for tool in tools:
                tool_desc = f"- {tool['name']}: {tool.get('description', 'No description')}"
                tool_descriptions.append(tool_desc)
            
            prompt_parts.append("\nAvailable tools:")
            prompt_parts.extend(tool_descriptions)
            prompt_parts.append("\nTo use a tool, respond with: TOOL_CALL: tool_name(arg1='value1', arg2='value2')")
        
        # Add conversation history
        prompt_parts.append("\nConversation:")
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "user":
                prompt_parts.append(f"Human: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
            elif role == "system":
                prompt_parts.append(f"System: {content}")
        
        prompt_parts.append("Assistant:")
        
        return "\n".join(prompt_parts)
    
    def _parse_response(self, text: str, tools: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Parse response text for tool calls and content."""
        response = {
            "text_content": text,
            "tool_calls": [],
            "is_complete": False
        }
        
        # Check for completion signals
        completion_signals = ["TASK_COMPLETE", "task complete", "completed successfully"]
        if any(signal.lower() in text.lower() for signal in completion_signals):
            response["is_complete"] = True
        
        # Parse tool calls if tools are available
        if tools and "TOOL_CALL:" in text:
            tool_calls = self._extract_tool_calls(text, tools)
            response["tool_calls"] = tool_calls
        
        return response
    
    def _extract_tool_calls(self, text: str, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract tool calls from text."""
        tool_calls = []
        tool_names = {tool["name"] for tool in tools}
        
        lines = text.split("\n")
        for line in lines:
            if "TOOL_CALL:" in line:
                try:
                    # Extract tool call - simple parsing
                    call_part = line.split("TOOL_CALL:", 1)[1].strip()
                    
                    # Parse tool_name(args) format
                    if "(" in call_part and call_part.endswith(")"):
                        tool_name = call_part.split("(")[0].strip()
                        args_str = call_part[len(tool_name)+1:-1]
                        
                        if tool_name in tool_names:
                            # Simple argument parsing - in production, use proper parser
                            args = {}
                            if args_str.strip():
                                # Basic parsing for key='value' format
                                import re
                                arg_matches = re.findall(r"(\w+)=['\"]([^'\"]*)['\"]", args_str)
                                args = {k: v for k, v in arg_matches}
                            
                            tool_calls.append({
                                "id": f"call_{len(tool_calls)}",
                                "name": tool_name,
                                "input": args
                            })
                
                except Exception as e:
                    self.logger.warning(f"Failed to parse tool call: {e}")
        
        return tool_calls
    
    async def cleanup(self) -> None:
        """Clean up model resources."""
        if self.model is not None:
            del self.model
            self.model = None
        
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        
        if self.pipeline is not None:
            del self.pipeline
            self.pipeline = None
        
        # Clear GPU cache if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif torch.backends.mps.is_available():
            torch.mps.empty_cache()
        
        self._model_loaded = False
        self.logger.info("Cleaned up model resources")


class OllamaProvider(LLMProvider):
    """Ollama provider for running local models."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.api_base_url or "http://localhost:11434"
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Generate response using Ollama API."""
        import aiohttp
        
        # Format prompt
        prompt = self._format_messages_to_prompt(messages, tools)
        
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.request_timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "text_content": data.get("response", ""),
                            "tool_calls": [],
                            "is_complete": "TASK_COMPLETE" in data.get("response", "").upper()
                        }
                    else:
                        raise LLMError(
                            f"Ollama API error: {response.status}",
                            api_provider="ollama",
                            status_code=response.status
                        )
        
        except Exception as e:
            raise LLMError(
                f"Ollama request failed: {e}",
                api_provider="ollama"
            )
    
    def _format_messages_to_prompt(
        self, 
        messages: List[Dict[str, str]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Format messages for Ollama."""
        # Simple prompt formatting
        prompt_parts = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "user":
                prompt_parts.append(f"Human: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        prompt_parts.append("Assistant:")
        return "\n".join(prompt_parts)
    
    async def cleanup(self) -> None:
        """No cleanup needed for Ollama."""
        pass


class MockProvider(LLMProvider):
    """Mock provider for testing and demonstration purposes."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Generate a mock response that demonstrates tool usage."""
        
        # Get the user's message
        user_message = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        # Simple pattern matching for common requests
        user_lower = user_message.lower()
        
        if any(word in user_lower for word in ["hello", "hi", "introduce"]):
            response = """Hello! I'm Nexus, your autonomous AI assistant. I have access to 21 powerful tools including:

• File operations (read, write, copy, move files)
• Shell commands (execute terminal commands safely)  
• Browser automation (navigate websites, click elements)
• Web search and information gathering
• System monitoring and file management

I can help you with coding, file management, web automation, research, and much more. What would you like me to help you with today?"""
        
        elif any(word in user_lower for word in ["list", "files", "directory"]):
            response = "I'll list the files in the current directory for you."
            return {
                "text_content": response,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "name": "shell_ls",
                        "input": {"path": "."}
                    }
                ],
                "is_complete": False
            }
            
        elif any(word in user_lower for word in ["create", "write", "script"]):
            response = "I'll help you create a script. Let me first check what directory we're in and then create the file."
            return {
                "text_content": response,
                "tool_calls": [
                    {
                        "id": "call_1", 
                        "name": "shell_pwd",
                        "input": {}
                    }
                ],
                "is_complete": False
            }
            
        elif any(word in user_lower for word in ["status", "system", "info"]):
            response = "I'll check the system status for you."
            return {
                "text_content": response,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "name": "shell_exec", 
                        "input": {"command": "uname -a"}
                    }
                ],
                "is_complete": False
            }
            
        else:
            response = f"""I understand you want me to: "{user_message}"

I'm currently running in demonstration mode with local tools. I can help you with:

1. File operations - reading, writing, managing files
2. Shell commands - executing terminal commands safely
3. System information - checking status, processes, etc.
4. Basic automation tasks

Try asking me to:
• "List files in the current directory"
• "Create a Python hello world script"
• "Check system information"
• "Show current directory"

What specific task would you like me to help with?"""
        
        return {
            "text_content": response,
            "tool_calls": [],
            "is_complete": True
        }
    
    async def cleanup(self) -> None:
        """No cleanup needed for mock provider."""
        pass


def create_llm_provider(config: LLMConfig) -> LLMProvider:
    """Factory function to create LLM provider based on config."""
    if config.provider == "huggingface":
        return HuggingFaceProvider(config)
    elif config.provider == "ollama":
        return OllamaProvider(config)
    elif config.provider == "mock":
        return MockProvider(config)
    else:
        raise ValueError(f"Unsupported LLM provider: {config.provider}")