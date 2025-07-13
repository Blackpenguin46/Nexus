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

# Import torch and transformers conditionally for testing
try:
    import torch
    from transformers import (
        AutoModelForCausalLM, 
        AutoTokenizer, 
        BitsAndBytesConfig,
        pipeline,
        TextGenerationPipeline
    )
    TORCH_AVAILABLE = True
except ImportError:
    # Mock the imports for testing without PyTorch
    torch = None
    AutoModelForCausalLM = None
    AutoTokenizer = None
    BitsAndBytesConfig = None
    pipeline = None
    TextGenerationPipeline = None
    TORCH_AVAILABLE = False

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
        
        if not TORCH_AVAILABLE:
            raise LLMError(
                "PyTorch and transformers are required for HuggingFace provider",
                api_provider="huggingface",
                details={"missing_dependencies": "torch, transformers"}
            )
        
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
        """Initialize the model and tokenizer with timeout protection."""
        if self._model_loaded:
            return
        
        try:
            self.logger.info(f"Loading Hugging Face model: {self.config.model}")
            
            # Add timeout for model loading to prevent freezing
            try:
                await asyncio.wait_for(
                    self._initialize_model(),
                    timeout=300.0  # 5 minute timeout for model loading
                )
            except asyncio.TimeoutError:
                raise LLMError(
                    "Model loading timed out after 5 minutes",
                    api_provider="huggingface",
                    details={"model": self.config.model, "timeout": "300s"}
                )
                
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            raise LLMError(
                f"Failed to initialize Hugging Face model: {e}",
                api_provider="huggingface",
                details={"model": self.config.model}
            )
    
    async def _initialize_model(self) -> None:
        """Internal model initialization."""
            
            
        # Configure device with fallback
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
        
        # Load components with individual timeouts
        self.logger.info("Loading tokenizer...")
        await asyncio.wait_for(
            asyncio.to_thread(self._load_tokenizer),
            timeout=60.0
        )
        
        self.logger.info("Loading model...")
        await asyncio.wait_for(
            asyncio.to_thread(self._load_model, device, quantization_config),
            timeout=180.0  # 3 minutes for model loading
        )
        
        self.logger.info("Creating pipeline...")
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
        if TORCH_AVAILABLE and torch:
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


class ManusReasoningProvider(LLMProvider):
    """
    Sophisticated reasoning provider that mimics Manus autonomous agent logic.
    
    This provider implements ReAct + CodeAct hybrid reasoning patterns:
    - Observes context and analyzes tasks
    - Reasons through multi-step plans  
    - Acts with appropriate tool selection
    - Reflects on results and adapts strategy
    """
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.conversation_count = 0
        self.task_history = []
        self.working_memory = {}
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate sophisticated autonomous responses following CLAUDE.md reasoning patterns:
        1. Initial Analysis and Planning
        2. Task Structure Planning  
        3. Plan Verification
        4. Task Execution
        5. Process Documentation
        6. Review Process
        """
        
        # Extract current context
        user_message = self._extract_user_message(messages)
        conversation_context = self._analyze_conversation_context(messages)
        
        # Step 1: Initial Analysis and Planning - Think through the problem
        analysis = self._initial_analysis_and_planning(user_message, conversation_context, tools)
        
        # Step 2: Task Structure Planning - Create todo items that can be checked off
        task_plan = self._create_task_structure(analysis)
        
        # Step 3: Plan Verification - Check if plan makes sense (simplified internal verification)
        verified_plan = self._verify_plan(task_plan, user_message)
        
        # Step 4: Task Execution - Execute with simplicity principle
        action = self._select_simple_action(verified_plan)
        result = await self._execute_action_simply(action, user_message)
        
        # Step 5: Process Documentation - Log actions (simplified)
        self._document_process(action, result)
        
        # Step 6: Review Process - Add review information
        reviewed_result = self._add_review_summary(result, action)
        
        return reviewed_result
    
    def _extract_user_message(self, messages: List[Dict[str, str]]) -> str:
        """Extract the latest user message from conversation."""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return msg.get("content", "")
        return ""
    
    def _analyze_conversation_context(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Analyze conversation for context and continuity."""
        context = {
            "message_count": len(messages),
            "has_assistant_responses": any(msg.get("role") == "assistant" for msg in messages),
            "recent_topics": [],
            "task_complexity": "simple"
        }
        
        # Analyze recent conversation for patterns
        recent_messages = messages[-3:] if len(messages) > 3 else messages
        for msg in recent_messages:
            content = msg.get("content", "").lower()
            if any(word in content for word in ["complex", "multi-step", "several", "multiple"]):
                context["task_complexity"] = "complex"
            elif any(word in content for word in ["analyze", "research", "investigate", "examine"]):
                context["task_complexity"] = "analytical"
        
        return context
    
    def _observe_context(self, user_message: str, context: Dict[str, Any], tools: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """ReAct Observation: Analyze current situation and available resources."""
        observation = {
            "user_intent": self._classify_user_intent(user_message),
            "task_type": self._classify_task_type(user_message),
            "complexity_level": context.get("task_complexity", "simple"),
            "available_tools": tools or [],
            "environment_status": "local_development",
            "requires_multi_step": self._requires_multi_step_execution(user_message)
        }
        
        # Add context from working memory
        observation["previous_context"] = self.working_memory.get("last_task", {})
        
        return observation
    
    def _classify_user_intent(self, message: str) -> str:
        """Classify the user's intent from their message."""
        message_lower = message.lower()
        
        # Enhanced intent classification with priority order and better patterns
        intent_patterns = {
            # Date/time requests (highest priority)
            "datetime_query": ["date", "time", "today", "current date", "what day", "when is", "now"],
            
            # System information requests  
            "system_query": ["system", "info", "computer", "uname", "os", "operating system", "machine"],
            
            # File listing and exploration
            "exploration": ["list", "show", "display", "see", "view", "find", "search", "ls", "dir", "files", "directories"],
            
            # File creation and manipulation
            "file_manipulation": ["create", "write", "make", "build", "generate", "save", "edit", "modify"],
            
            # Information gathering
            "information_gathering": ["what", "how", "why", "where", "tell me", "explain", "describe", "help"],
            
            # System interaction  
            "system_interaction": ["run", "execute", "command", "shell", "terminal", "bash"],
            
            # Development tasks
            "development": ["script", "code", "program", "python", "project", "development", "coding"],
            
            # Greetings and introductions
            "greeting": ["hello", "hi", "hey", "greetings", "introduce"],
            
            # Analysis tasks
            "analysis": ["analyze", "examine", "investigate", "review", "assess", "check"]
        }
        
        # Check patterns in priority order
        for intent, keywords in intent_patterns.items():
            for keyword in keywords:
                if keyword in message_lower:
                    return intent
        
        return "general_assistance"
    
    def _classify_task_type(self, message: str) -> str:
        """Classify the type of task being requested."""
        message_lower = message.lower()
        
        task_patterns = {
            "development": ["code", "script", "program", "function", "class", "api"],
            "file_operations": ["file", "directory", "folder", "document", "text"],
            "system_administration": ["system", "process", "service", "configuration", "setup"],
            "data_processing": ["data", "csv", "json", "process", "transform", "parse"],
            "web_automation": ["web", "browser", "scrape", "crawl", "website"],
            "research": ["research", "information", "learn", "study", "investigate"]
        }
        
        for task_type, keywords in task_patterns.items():
            if any(keyword in message_lower for keyword in keywords):
                return task_type
        
        return "general"
    
    def _requires_multi_step_execution(self, message: str) -> bool:
        """Determine if task requires multiple steps."""
        multi_step_indicators = [
            "and then", "after that", "first", "second", "finally", "step by step",
            "multiple", "several", "complex", "comprehensive", "complete",
            "workflow", "process", "pipeline", "sequence"
        ]
        
        message_lower = message.lower()
        return any(indicator in message_lower for indicator in multi_step_indicators)
    
    def _reason_about_task(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """ReAct Reasoning: Think through the task and approach."""
        reasoning = {
            "task_understanding": self._understand_task_requirements(observation),
            "approach_strategy": self._determine_approach_strategy(observation),
            "risk_assessment": self._assess_task_risks(observation),
            "success_criteria": self._define_success_criteria(observation)
        }
        
        return reasoning
    
    def _understand_task_requirements(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """Understand what the task actually requires."""
        intent = observation["user_intent"]
        task_type = observation["task_type"]
        
        requirements = {
            "primary_action": intent,
            "domain": task_type,
            "tools_needed": self._identify_required_tools(observation),
            "dependencies": self._identify_dependencies(observation),
            "constraints": self._identify_constraints(observation)
        }
        
        return requirements
    
    def _determine_approach_strategy(self, observation: Dict[str, Any]) -> str:
        """Determine the best approach strategy."""
        if observation["requires_multi_step"]:
            if observation["complexity_level"] == "complex":
                return "decompose_and_execute_incrementally"
            else:
                return "sequential_execution"
        elif observation["user_intent"] == "information_gathering":
            return "gather_and_synthesize"
        elif observation["user_intent"] == "analysis":
            return "systematic_analysis"
        else:
            return "direct_execution"
    
    def _assess_task_risks(self, observation: Dict[str, Any]) -> List[str]:
        """Assess potential risks in task execution."""
        risks = []
        
        if observation["task_type"] == "system_administration":
            risks.append("system_modification_risk")
        if observation["requires_multi_step"]:
            risks.append("cascading_failure_risk")
        if "delete" in str(observation).lower():
            risks.append("data_loss_risk")
        
        return risks
    
    def _define_success_criteria(self, observation: Dict[str, Any]) -> List[str]:
        """Define what constitutes success for this task."""
        criteria = ["task_completion"]
        
        if observation["user_intent"] == "file_manipulation":
            criteria.append("file_integrity_maintained")
        if observation["user_intent"] == "information_gathering":
            criteria.append("comprehensive_information_provided")
        if observation["requires_multi_step"]:
            criteria.append("all_steps_completed_successfully")
        
        return criteria
    
    def _create_execution_plan(self, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """Create detailed execution plan based on reasoning."""
        strategy = reasoning["approach_strategy"]
        requirements = reasoning["task_understanding"]
        
        plan = {
            "strategy": strategy,
            "steps": self._generate_execution_steps(strategy, requirements),
            "tool_sequence": self._plan_tool_sequence(requirements),
            "contingencies": self._plan_contingencies(reasoning["risk_assessment"])
        }
        
        return plan
    
    def _generate_execution_steps(self, strategy: str, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate specific execution steps."""
        if strategy == "direct_execution":
            return [{"step": "execute_primary_action", "tools": requirements.get("tools_needed", [])}]
        elif strategy == "gather_and_synthesize":
            return [
                {"step": "gather_information", "tools": ["file_list", "file_read", "shell_exec"]},
                {"step": "synthesize_response", "tools": []}
            ]
        elif strategy == "sequential_execution":
            return [
                {"step": "prepare_environment", "tools": ["shell_pwd", "file_list"]},
                {"step": "execute_main_task", "tools": requirements.get("tools_needed", [])},
                {"step": "verify_completion", "tools": ["file_list", "file_read"]}
            ]
        else:
            return [{"step": "adaptive_execution", "tools": requirements.get("tools_needed", [])}]
    
    def _plan_tool_sequence(self, requirements: Dict[str, Any]) -> List[str]:
        """Plan the sequence of tools to use."""
        tools_needed = requirements.get("tools_needed", [])
        
        # Intelligent tool ordering
        ordered_tools = []
        
        # Always start with environmental awareness if needed
        if any(tool in tools_needed for tool in ["file_write", "file_delete", "shell_exec"]):
            ordered_tools.append("shell_pwd")
        
        # Add primary tools in logical order
        for tool in tools_needed:
            if tool not in ordered_tools:
                ordered_tools.append(tool)
        
        return ordered_tools
    
    def _plan_contingencies(self, risks: List[str]) -> Dict[str, str]:
        """Plan contingency actions for identified risks."""
        contingencies = {}
        
        for risk in risks:
            if risk == "data_loss_risk":
                contingencies[risk] = "create_backup_before_operation"
            elif risk == "system_modification_risk":
                contingencies[risk] = "validate_permissions_first"
            elif risk == "cascading_failure_risk":
                contingencies[risk] = "implement_rollback_capability"
        
        return contingencies
    
    def _select_action(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Select the immediate action to take based on plan."""
        steps = plan.get("steps", [])
        if not steps:
            return {"type": "default_response", "details": {}}
        
        first_step = steps[0]
        step_type = first_step.get("step", "")
        tools = first_step.get("tools", [])
        
        # Map step types to specific actions
        if step_type == "prepare_environment":
            return {
                "type": "environment_check",
                "tool": "shell_pwd",
                "follow_up": "file_list"
            }
        elif step_type == "gather_information":
            return {
                "type": "information_gathering",
                "tool": "file_list",
                "target": "."
            }
        elif step_type == "execute_primary_action":
            if tools:
                return {
                    "type": "direct_tool_execution",
                    "tool": tools[0],
                    "context": "primary_task"
                }
        
        return {"type": "adaptive_response", "details": plan}
    
    def _identify_required_tools(self, observation: Dict[str, Any]) -> List[str]:
        """Identify which tools are needed for this task."""
        intent = observation["user_intent"]
        task_type = observation["task_type"]
        
        # Enhanced tool mapping with specific intent handling
        tool_mapping = {
            # Specific intent mappings
            "datetime_query": ["shell_exec"],
            "system_query": ["shell_exec"],
            "exploration": ["file_list", "shell_pwd"],
            "file_manipulation": ["file_write", "file_read", "file_list"],
            "development": ["file_write", "file_read", "shell_exec"],
            "greeting": ["shell_pwd"],  # Check environment first
            "information_gathering": ["file_list", "shell_exec"],
            "system_interaction": ["shell_exec", "shell_pwd"],
            "analysis": ["file_list", "file_read", "shell_exec"]
        }
        
        return tool_mapping.get(intent, ["file_list", "shell_pwd"])
    
    def _identify_dependencies(self, observation: Dict[str, Any]) -> List[str]:
        """Identify task dependencies."""
        dependencies = []
        
        if observation["task_type"] == "development":
            dependencies.append("working_directory_access")
        if observation["user_intent"] == "file_manipulation":
            dependencies.append("file_system_permissions")
        
        return dependencies
    
    def _identify_constraints(self, observation: Dict[str, Any]) -> List[str]:
        """Identify task constraints."""
        constraints = ["security_validation", "timeout_limits"]
        
        if observation["task_type"] == "system_administration":
            constraints.append("elevated_privileges_required")
        
        return constraints
    
    async def _execute_action(self, action: Dict[str, Any], user_message: str) -> Dict[str, Any]:
        """Execute the planned action and return response."""
        action_type = action.get("type", "default_response")
        
        # Store task context in working memory
        self.working_memory["last_task"] = {
            "message": user_message,
            "action_type": action_type,
            "timestamp": time.time()
        }
        
        if action_type == "environment_check":
            return await self._execute_environment_check()
        elif action_type == "information_gathering":
            return await self._execute_information_gathering(action)
        elif action_type == "direct_tool_execution":
            return await self._execute_direct_tool(action, user_message)
        elif action_type == "adaptive_response":
            return await self._execute_adaptive_response(action, user_message)
        else:
            return await self._execute_default_response(user_message)
    
    async def _execute_environment_check(self) -> Dict[str, Any]:
        """Execute environment check action."""
        return {
            "text_content": "Let me check our current environment and working directory to understand the context better.",
            "tool_calls": [
                {
                    "id": "call_1",
                    "name": "shell_pwd",
                    "input": {}
                }
            ],
            "is_complete": False
        }
    
    async def _execute_information_gathering(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute information gathering action."""
        target = action.get("target", ".")
        
        return {
            "text_content": "I'll gather information about the current environment to better understand your request.",
            "tool_calls": [
                {
                    "id": "call_1",
                    "name": "file_list",
                    "input": {"directory": target}
                }
            ],
            "is_complete": False
        }
    
    async def _execute_direct_tool(self, action: Dict[str, Any], user_message: str) -> Dict[str, Any]:
        """Execute direct tool action based on user intent."""
        tool = action.get("tool", "file_list")
        
        # Intelligent tool parameter inference based on context
        if tool == "file_write":
            return await self._execute_file_creation(user_message)
        elif tool == "shell_exec":
            return await self._execute_shell_command(user_message)
        elif tool == "file_read":
            return await self._execute_file_reading(user_message)
        elif tool == "file_list":
            return await self._execute_file_listing(user_message)
        elif tool == "shell_pwd":
            return await self._execute_pwd_command(user_message)
        else:
            return await self._execute_default_tool(tool)
    
    async def _execute_file_creation(self, user_message: str) -> Dict[str, Any]:
        """Execute intelligent file creation based on user request."""
        message_lower = user_message.lower()
        
        if "python" in message_lower or "script" in message_lower:
            filename = "script.py"
            content = """#!/usr/bin/env python3

def main():
    print("Hello from Nexus Agent!")
    print("This script was created autonomously.")
    
    # Add your code here
    pass

if __name__ == "__main__":
    main()
"""
            explanation = "I'll create a Python script template for you with a proper structure."
        elif "readme" in message_lower or "documentation" in message_lower:
            filename = "README.md"
            content = """# Project Documentation

## Overview
This document was created by Nexus Agent.

## Description
Add your project description here.

## Usage
Add usage instructions here.

## Notes
- Created autonomously by AI agent
- Modify as needed for your project
"""
            explanation = "I'll create a README.md file with a basic documentation template."
        else:
            filename = "note.txt"
            content = f"""Note created by Nexus Agent

Request: {user_message}
Created: {time.strftime('%Y-%m-%d %H:%M:%S')}

This file demonstrates autonomous file creation capabilities.
"""
            explanation = "I'll create a text file documenting your request."
        
        return {
            "text_content": explanation,
            "tool_calls": [
                {
                    "id": "call_1",
                    "name": "file_write",
                    "input": {
                        "path": filename,
                        "content": content
                    }
                }
            ],
            "is_complete": False
        }
    
    async def _execute_shell_command(self, user_message: str) -> Dict[str, Any]:
        """Execute intelligent shell command based on user request."""
        message_lower = user_message.lower()
        
        # Enhanced command mapping with better pattern matching
        if any(word in message_lower for word in ["date", "time", "today", "current date", "what day", "when is", "now"]):
            command = "date"
            explanation = "I'll check the current date and time for you."
        elif any(word in message_lower for word in ["system", "info", "computer", "uname", "os", "operating system", "machine"]):
            command = "uname -a && echo '---' && sw_vers 2>/dev/null || lsb_release -a 2>/dev/null || cat /etc/os-release 2>/dev/null"
            explanation = "I'll get comprehensive system information for you."
        elif any(word in message_lower for word in ["process", "running", "ps"]):
            command = "ps aux | head -10"
            explanation = "I'll show you the running processes."
        elif any(word in message_lower for word in ["memory", "ram", "usage"]):
            command = "free -h 2>/dev/null || vm_stat | head -10"
            explanation = "I'll check memory usage for you."
        elif any(word in message_lower for word in ["disk", "space", "storage"]):
            command = "df -h ."
            explanation = "I'll check disk space for you."
        else:
            command = "pwd && ls -la"
            explanation = "I'll show you the current directory and its contents."
        
        return {
            "text_content": explanation,
            "tool_calls": [
                {
                    "id": "call_1",
                    "name": "shell_exec",
                    "input": {"command": command}
                }
            ],
            "is_complete": False
        }
    
    async def _execute_file_listing(self, user_message: str) -> Dict[str, Any]:
        """Execute intelligent file listing based on user request."""
        message_lower = user_message.lower()
        
        # Determine target directory and explanation
        if "parent" in message_lower or ".." in message_lower:
            target = ".."
            explanation = "I'll list files in the parent directory."
        elif "root" in message_lower or "/" in message_lower:
            target = "."  # Stay safe, list current directory
            explanation = "I'll list files in the current directory for security."
        else:
            target = "."
            explanation = "I'll list the files in the current directory."
        
        return {
            "text_content": explanation,
            "tool_calls": [
                {
                    "id": "call_1",
                    "name": "file_list",
                    "input": {"directory": target}
                }
            ],
            "is_complete": False
        }
    
    async def _execute_pwd_command(self, user_message: str) -> Dict[str, Any]:
        """Execute pwd command for directory context."""
        return {
            "text_content": "Let me check our current working directory.",
            "tool_calls": [
                {
                    "id": "call_1",
                    "name": "shell_pwd",
                    "input": {}
                }
            ],
            "is_complete": False
        }
    
    async def _execute_file_reading(self, user_message: str) -> Dict[str, Any]:
        """Execute intelligent file reading based on user request."""
        message_lower = user_message.lower()
        
        if "readme" in message_lower:
            filepath = "README.md"
            explanation = "I'll read the README file for you."
        elif "config" in message_lower:
            filepath = ".env"
            explanation = "I'll check the configuration file."
        else:
            # First list files to see what's available
            explanation = "I'll list the available files so you can choose which one to read."
            return {
                "text_content": explanation,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "name": "file_list",
                        "input": {"directory": "."}
                    }
                ],
                "is_complete": False
            }
        
        return {
            "text_content": explanation,
            "tool_calls": [
                {
                    "id": "call_1",
                    "name": "file_read",
                    "input": {"path": filepath}
                }
            ],
            "is_complete": False
        }
    
    async def _execute_default_tool(self, tool: str) -> Dict[str, Any]:
        """Execute default tool action."""
        return {
            "text_content": f"I'll use the {tool} tool to help with your request.",
            "tool_calls": [
                {
                    "id": "call_1",
                    "name": tool,
                    "input": {}
                }
            ],
            "is_complete": False
        }
    
    async def _execute_adaptive_response(self, action: Dict[str, Any], user_message: str) -> Dict[str, Any]:
        """Execute adaptive response based on complex reasoning."""
        plan_details = action.get("details", {})
        strategy = plan_details.get("strategy", "direct_execution")
        
        if strategy == "decompose_and_execute_incrementally":
            return {
                "text_content": f"""I understand you have a complex request: "{user_message}"

Let me break this down into manageable steps. I'll start by analyzing the current environment and then proceed systematically.""",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "name": "shell_pwd",
                        "input": {}
                    }
                ],
                "is_complete": False
            }
        else:
            return await self._execute_default_response(user_message)
    
    async def _execute_default_response(self, user_message: str) -> Dict[str, Any]:
        """Execute default response when specific patterns don't match."""
        return {
            "text_content": f"""I'm analyzing your request: "{user_message}"

As an autonomous AI agent, I can help with:
• File operations and management
• System administration tasks  
• Code development and scripting
• Information gathering and analysis
• Workflow automation

Let me start by understanding our current environment:""",
            "tool_calls": [
                {
                    "id": "call_1",
                    "name": "file_list",
                    "input": {"directory": "."}
                }
            ],
            "is_complete": False
        }
    
    def _initial_analysis_and_planning(self, user_message: str, context: Dict[str, Any], tools: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Step 1: Initial Analysis and Planning
        Think through the problem, read context for relevant information
        """
        analysis = {
            "problem_statement": user_message,
            "complexity_assessment": self._assess_complexity(user_message),
            "required_capabilities": self._identify_required_capabilities(user_message),
            "context_understanding": context,
            "available_tools": [tool.get("name", "") for tool in (tools or [])],
            "approach": self._determine_approach(user_message)
        }
        return analysis
    
    def _create_task_structure(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 2: Task Structure Planning
        Create todo items that can be checked off as completed
        """
        approach = analysis.get("approach", "simple_execution")
        
        if approach == "information_gathering":
            tasks = [
                {"task": "gather_environment_context", "completed": False},
                {"task": "analyze_user_request", "completed": False}, 
                {"task": "provide_structured_response", "completed": False}
            ]
        elif approach == "file_manipulation":
            tasks = [
                {"task": "determine_file_parameters", "completed": False},
                {"task": "execute_file_operation", "completed": False},
                {"task": "verify_operation_success", "completed": False}
            ]
        elif approach == "system_interaction":
            tasks = [
                {"task": "prepare_safe_command", "completed": False},
                {"task": "execute_system_command", "completed": False},
                {"task": "interpret_results", "completed": False}
            ]
        else:
            tasks = [
                {"task": "understand_request", "completed": False},
                {"task": "execute_simple_action", "completed": False}
            ]
        
        return {
            "approach": approach,
            "tasks": tasks,
            "simplicity_principle": "Each task impacts minimal code and follows simple patterns"
        }
    
    def _verify_plan(self, task_plan: Dict[str, Any], user_message: str) -> Dict[str, Any]:
        """
        Step 3: Plan Verification
        Check if plan makes sense before execution (simplified internal verification)
        """
        approach = task_plan.get("approach", "simple_execution")
        tasks = task_plan.get("tasks", [])
        
        # Simple verification logic
        plan_valid = True
        verification_notes = []
        
        if len(tasks) == 0:
            plan_valid = False
            verification_notes.append("No tasks defined")
        
        if approach == "file_manipulation" and "create" not in user_message.lower() and "write" not in user_message.lower():
            if not any("list" in user_message.lower() or "show" in user_message.lower()):
                verification_notes.append("File manipulation approach may not match user intent")
        
        return {
            "plan_valid": plan_valid,
            "verified_approach": approach,
            "verified_tasks": tasks,
            "verification_notes": verification_notes,
            "ready_for_execution": plan_valid
        }
    
    def _select_simple_action(self, verified_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 4: Task Execution - Select action following simplicity principle
        Make every change as simple as possible, impacting minimal code
        """
        if not verified_plan.get("ready_for_execution", False):
            return {"type": "default_response", "explanation": "Plan verification failed"}
        
        approach = verified_plan.get("verified_approach", "simple_execution")
        
        # Follow simplicity principle - minimal, focused actions
        if approach == "information_gathering":
            return {
                "type": "direct_tool_execution",
                "tool": "file_list",
                "explanation": "Simple directory listing to understand context"
            }
        elif approach == "file_manipulation":
            return {
                "type": "direct_tool_execution", 
                "tool": "file_write",
                "explanation": "Simple file creation with minimal complexity"
            }
        elif approach == "system_interaction":
            return {
                "type": "direct_tool_execution",
                "tool": "shell_exec", 
                "explanation": "Simple system command execution"
            }
        else:
            return {
                "type": "adaptive_response",
                "explanation": "Simple adaptive response for general queries"
            }
    
    async def _execute_action_simply(self, action: Dict[str, Any], user_message: str) -> Dict[str, Any]:
        """
        Step 4 continued: Execute action with simplicity focus
        """
        # Use existing execution methods but with simple focus
        result = await self._execute_action(action, user_message)
        
        # Add simplicity documentation
        result["execution_approach"] = "simple"
        result["complexity_minimized"] = True
        
        return result
    
    def _document_process(self, action: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        Step 5: Process Documentation 
        Write log of actions (simplified for autonomous operation)
        """
        # Store in working memory for context
        process_log = {
            "timestamp": time.time(),
            "action_type": action.get("type", "unknown"),
            "tool_used": action.get("tool", "none"),
            "explanation": action.get("explanation", ""),
            "success": result.get("tool_calls") is not None or result.get("text_content") is not None
        }
        
        # Keep last 5 actions for context
        if "process_history" not in self.working_memory:
            self.working_memory["process_history"] = []
        
        self.working_memory["process_history"].append(process_log)
        if len(self.working_memory["process_history"]) > 5:
            self.working_memory["process_history"].pop(0)
    
    def _add_review_summary(self, result: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 6: Review Process
        Add review section with summary of changes and relevant information
        """
        review_summary = {
            "action_taken": action.get("explanation", "Executed user request"),
            "approach_used": action.get("type", "standard"),
            "simplicity_applied": True,
            "tools_utilized": [action.get("tool")] if action.get("tool") else [],
            "complexity_level": "minimal",
            "ready_for_next_task": True
        }
        
        # Add review to result
        result["review_summary"] = review_summary
        
        return result
    
    def _assess_complexity(self, user_message: str) -> str:
        """Assess task complexity for planning."""
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ["multiple", "several", "complex", "advanced"]):
            return "high"
        elif any(word in message_lower for word in ["analyze", "research", "investigate"]):
            return "medium"
        else:
            return "low"
    
    def _identify_required_capabilities(self, user_message: str) -> List[str]:
        """Identify what capabilities are needed."""
        capabilities = []
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ["file", "create", "write", "save"]):
            capabilities.append("file_operations")
        if any(word in message_lower for word in ["system", "command", "run", "execute"]):
            capabilities.append("system_interaction")
        if any(word in message_lower for word in ["list", "show", "display", "find"]):
            capabilities.append("information_retrieval")
        
        return capabilities
    
    def _determine_approach(self, user_message: str) -> str:
        """Determine the best approach based on user message."""
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ["create", "write", "make", "generate"]):
            return "file_manipulation"
        elif any(word in message_lower for word in ["list", "show", "display", "find", "search"]):
            return "information_gathering"
        elif any(word in message_lower for word in ["run", "execute", "command", "system"]):
            return "system_interaction"
        else:
            return "simple_execution"
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        self.working_memory.clear()
        self.task_history.clear()


# Alias for backward compatibility
MockProvider = ManusReasoningProvider


def create_llm_provider(config) -> "LLMProvider":
    """Factory function to create LLM provider based on config."""
    if config.provider == "huggingface":
        return HuggingFaceProvider(config)
    elif config.provider == "ollama":
        return OllamaProvider(config)
    elif config.provider == "mock":
        return MockProvider(config)
    else:
        raise ValueError(f"Unsupported LLM provider: {config.provider}")
