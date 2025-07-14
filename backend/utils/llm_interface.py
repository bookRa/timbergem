import os
import json
import asyncio
import base64
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class LLMRequest:
    """Standard request format for LLM providers."""
    system_prompt: str
    user_message: str
    images: List[str] = None  # List of image file paths
    max_tokens: int = 4000
    temperature: float = 0.1


@dataclass
class LLMResponse:
    """Standard response format from LLM providers."""
    content: str
    success: bool
    error_message: Optional[str] = None
    usage: Optional[Dict] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the provider is properly configured."""
        pass


class GeminiProvider(LLMProvider):
    """Google Gemini provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        
    def is_configured(self) -> bool:
        return self.api_key is not None
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Gemini API."""
        if not self.is_configured():
            return LLMResponse(
                content="",
                success=False,
                error_message="Gemini API key not configured"
            )
        
        try:
            import google.generativeai as genai
            
            # Configure the API
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)
            
            # Prepare the content
            content_parts = []
            
            # Add text content
            full_prompt = f"{request.system_prompt}\n\nUser Request:\n{request.user_message}"
            content_parts.append(full_prompt)
            
            # Add images if provided
            if request.images:
                for image_path in request.images:
                    if os.path.exists(image_path):
                        # Read and encode image
                        with open(image_path, 'rb') as f:
                            image_data = f.read()
                        
                        # Gemini expects PIL Image objects or file uploads
                        from PIL import Image
                        import io
                        
                        pil_image = Image.open(io.BytesIO(image_data))
                        content_parts.append(pil_image)
            
            # Generate response
            response = model.generate_content(
                content_parts,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=request.max_tokens,
                    temperature=request.temperature,
                )
            )
            
            return LLMResponse(
                content=response.text,
                success=True,
                usage={"prompt_tokens": 0, "completion_tokens": 0}  # Gemini doesn't provide detailed usage
            )
            
        except Exception as e:
            return LLMResponse(
                content="",
                success=False,
                error_message=str(e)
            )


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4-vision-preview"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        
    def is_configured(self) -> bool:
        return self.api_key is not None
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response using OpenAI API."""
        if not self.is_configured():
            return LLMResponse(
                content="",
                success=False,
                error_message="OpenAI API key not configured"
            )
        
        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=self.api_key)
            
            # Prepare messages
            messages = [
                {"role": "system", "content": request.system_prompt},
            ]
            
            # Prepare user message content
            user_content = [{"type": "text", "text": request.user_message}]
            
            # Add images if provided
            if request.images:
                for image_path in request.images:
                    if os.path.exists(image_path):
                        with open(image_path, 'rb') as f:
                            image_data = base64.b64encode(f.read()).decode('utf-8')
                        
                        # Determine image format
                        image_format = image_path.split('.')[-1].lower()
                        if image_format == 'jpg':
                            image_format = 'jpeg'
                        
                        user_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{image_format};base64,{image_data}"
                            }
                        })
            
            messages.append({"role": "user", "content": user_content})
            
            # Generate response
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                success=True,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens
                }
            )
            
        except Exception as e:
            return LLMResponse(
                content="",
                success=False,
                error_message=str(e)
            )


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        
    def is_configured(self) -> bool:
        return self.api_key is not None
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Claude API."""
        if not self.is_configured():
            return LLMResponse(
                content="",
                success=False,
                error_message="Claude API key not configured"
            )
        
        try:
            import anthropic
            
            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            
            # Prepare message content
            content_parts = [{"type": "text", "text": request.user_message}]
            
            # Add images if provided
            if request.images:
                for image_path in request.images:
                    if os.path.exists(image_path):
                        with open(image_path, 'rb') as f:
                            image_data = base64.b64encode(f.read()).decode('utf-8')
                        
                        # Determine media type
                        image_format = image_path.split('.')[-1].lower()
                        media_type = f"image/{image_format}"
                        if image_format == 'jpg':
                            media_type = "image/jpeg"
                        
                        content_parts.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data
                            }
                        })
            
            # Generate response
            response = await client.messages.create(
                model=self.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                system=request.system_prompt,
                messages=[{"role": "user", "content": content_parts}]
            )
            
            return LLMResponse(
                content=response.content[0].text,
                success=True,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens
                }
            )
            
        except Exception as e:
            return LLMResponse(
                content="",
                success=False,
                error_message=str(e)
            )


class MockProvider(LLMProvider):
    """Mock provider for testing purposes."""
    
    def __init__(self, mock_response: str = "Mock HTML response"):
        self.mock_response = mock_response
        
    def is_configured(self) -> bool:
        return True
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate a mock response for testing."""
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        # Generate a simple mock HTML response
        mock_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Mock Page Conversion</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .mock-content {{ border: 1px solid #ccc; padding: 15px; }}
    </style>
</head>
<body>
    <div class="mock-content">
        <h2>Mock Page Conversion</h2>
        <p>This is a mock response for testing purposes.</p>
        <p>System prompt length: {len(request.system_prompt)} characters</p>
        <p>User message length: {len(request.user_message)} characters</p>
        <p>Images provided: {len(request.images) if request.images else 0}</p>
        <p>Generated at: {asyncio.get_event_loop().time()}</p>
    </div>
</body>
</html>"""
        
        return LLMResponse(
            content=mock_html,
            success=True,
            usage={"prompt_tokens": 100, "completion_tokens": 200}
        )


class LLMInterface:
    """Main interface for interacting with LLM providers."""
    
    def __init__(self, provider: LLMProvider):
        self.provider = provider
    
    async def generate_html_from_page(
        self, 
        system_prompt: str,
        pixmap_path: str,
        text_path: Optional[str] = None,
        tables_path: Optional[str] = None,
        page_number: int = 1
    ) -> LLMResponse:
        """
        Generate HTML from page artifacts using the configured LLM provider.
        
        Args:
            system_prompt: The system prompt for HTML generation
            pixmap_path: Path to the page pixmap image
            text_path: Optional path to extracted text
            tables_path: Optional path to extracted tables
            page_number: Page number for context
            
        Returns:
            LLMResponse containing the generated HTML
        """
        # Build user message
        user_message_parts = [
            f"Please convert page {page_number} of this construction document into structured HTML."
        ]
        
        # Add text content if available
        if text_path and os.path.exists(text_path):
            with open(text_path, 'r', encoding='utf-8') as f:
                text_content = f.read().strip()
            if text_content:
                user_message_parts.append(f"\n**Extracted Text:**\n{text_content}")
        
        # Add table content if available
        if tables_path and os.path.exists(tables_path):
            with open(tables_path, 'r', encoding='utf-8') as f:
                table_content = f.read().strip()
            if table_content:
                user_message_parts.append(f"\n**Extracted Tables:**\n{table_content}")
        
        user_message = "\n".join(user_message_parts)
        
        # Prepare images
        images = [pixmap_path] if os.path.exists(pixmap_path) else []
        
        # Create request
        request = LLMRequest(
            system_prompt=system_prompt,
            user_message=user_message,
            images=images,
            max_tokens=8000,  # Increased for HTML output
            temperature=0.1
        )
        
        return await self.provider.generate_response(request)
    
    @classmethod
    def create_provider(cls, provider_name: str, **kwargs) -> LLMProvider:
        """Factory method to create LLM providers."""
        providers = {
            "gemini": GeminiProvider,
            "openai": OpenAIProvider,
            "claude": ClaudeProvider,
            "mock": MockProvider
        }
        
        if provider_name not in providers:
            raise ValueError(f"Unknown provider: {provider_name}. Available: {list(providers.keys())}")
        
        return providers[provider_name](**kwargs) 