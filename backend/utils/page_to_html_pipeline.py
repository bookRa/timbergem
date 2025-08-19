import os
import json
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .pdf_processor import PDFProcessor
from .llm_interface import LLMInterface, LLMProvider, LLMResponse


@dataclass
class PageToHTMLConfig:
    """Configuration for the page-to-HTML pipeline."""

    llm_provider: str = "mock"  # Default to mock for testing
    llm_model: Optional[str] = None
    dpi: int = 300
    high_res_dpi: int = 300
    max_concurrent_requests: int = 7  # Allow full parallelism for typical documents
    # Note: Use llm_provider="mock" for testing without API costs

    # Provider-specific configurations
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None


@dataclass
class PageHTMLResult:
    """Result of HTML generation for a single page."""

    page_number: int
    success: bool
    html_content: Optional[str] = None
    html_file_path: Optional[str] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    token_usage: Optional[Dict] = None


class PageToHTMLPipeline:
    """
    Main pipeline for converting PDF pages to structured HTML.

    This pipeline:
    1. Processes PDF to extract artifacts (pixmaps, text)
    2. Uses LLM to convert each page to HTML
    3. Saves results and provides comprehensive feedback
    """

    def __init__(self, config: PageToHTMLConfig):
        self.config = config
        self.pdf_processor = PDFProcessor(
            dpi=config.dpi, high_res_dpi=config.high_res_dpi
        )

        # Initialize LLM interface
        llm_provider = self._create_llm_provider()
        self.llm_interface = LLMInterface(llm_provider)

        # Load system prompt
        self.system_prompt = self._load_system_prompt()

    def _create_llm_provider(self) -> LLMProvider:
        """Create the appropriate LLM provider based on configuration."""
        provider_kwargs = {}

        if self.config.llm_provider == "gemini":
            provider_kwargs["api_key"] = self.config.gemini_api_key
            if self.config.llm_model:
                provider_kwargs["model"] = self.config.llm_model
        elif self.config.llm_provider == "openai":
            provider_kwargs["api_key"] = self.config.openai_api_key
            if self.config.llm_model:
                provider_kwargs["model"] = self.config.llm_model
        elif self.config.llm_provider == "claude":
            provider_kwargs["api_key"] = self.config.anthropic_api_key
            if self.config.llm_model:
                provider_kwargs["model"] = self.config.llm_model

        return LLMInterface.create_provider(self.config.llm_provider, **provider_kwargs)

    def _load_system_prompt(self) -> str:
        """Load the system prompt for HTML generation."""
        try:
            # Look for system prompt in the expected location
            script_dir = os.path.dirname(os.path.abspath(__file__))
            backend_dir = os.path.dirname(script_dir)
            prompt_path = os.path.join(backend_dir, "system_prompts", "page_to_html.md")

            if os.path.exists(prompt_path):
                with open(prompt_path, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                print(f"⚠️  System prompt not found at {prompt_path}, using default")
                return self._get_default_system_prompt()
        except Exception as e:
            print(f"⚠️  Error loading system prompt: {e}, using default")
            return self._get_default_system_prompt()

    def _get_default_system_prompt(self) -> str:
        """Get a basic default system prompt if the file is not found."""
        return """You are an expert at converting construction documents to structured HTML.
        
Given a page image and optionally extracted text and tables, convert the page to clean,
structured HTML that accurately represents the document layout and content.

Include appropriate HTML structure, semantic elements, and basic CSS styling.
For images and diagrams, provide detailed descriptions in div elements.
Ensure the HTML is valid and well-formatted."""

    async def process_pdf_to_html(
        self, pdf_path: str, output_dir: str, doc_id: str
    ) -> Dict:
        """
        Complete pipeline to process a PDF and generate HTML for all pages.

        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save all outputs
            doc_id: Unique document identifier

        Returns:
            Dictionary containing complete processing results
        """
        print(f"🚀 Starting page-to-HTML pipeline for {pdf_path}")
        print(f"   Configuration: {self.config.llm_provider} provider")

        # Step 1: Process PDF to extract artifacts
        print(f"\n📄 Step 1: Processing PDF...")
        processing_results = self.pdf_processor.process_pdf(
            pdf_path, output_dir, doc_id
        )

        # Step 2: Generate HTML for each page using LLM
        print(f"\n🤖 Step 2: Generating HTML using {self.config.llm_provider}...")
        html_results = await self._generate_html_for_all_pages(
            processing_results, output_dir
        )

        # Step 3: Compile final results
        final_results = {
            "docId": doc_id,
            "pdf_processing": processing_results,
            "html_generation": {
                "provider": self.config.llm_provider,
                "model": self.config.llm_model,
                "total_pages": len(html_results),
                "successful_pages": len([r for r in html_results if r.success]),
                "failed_pages": len([r for r in html_results if not r.success]),
                "total_tokens_used": sum(
                    (
                        r.token_usage.get("prompt_tokens", 0)
                        + r.token_usage.get("completion_tokens", 0)
                    )
                    for r in html_results
                    if r.token_usage
                ),
                "results": [self._serialize_html_result(r) for r in html_results],
            },
            "pipeline_metadata": {
                "config": {
                    "llm_provider": self.config.llm_provider,
                    "llm_model": self.config.llm_model,
                    "dpi": self.config.dpi,
                    "high_res_dpi": self.config.high_res_dpi,
                    "max_concurrent_requests": self.config.max_concurrent_requests,
                }
            },
        }

        # Save final results
        results_file = os.path.join(output_dir, "page_to_html_results.json")
        with open(results_file, "w") as f:
            json.dump(final_results, f, indent=2)

        print(f"\n✅ Pipeline complete!")
        print(
            f"   -> Successful pages: {final_results['html_generation']['successful_pages']}"
        )
        print(f"   -> Failed pages: {final_results['html_generation']['failed_pages']}")
        if final_results["html_generation"]["total_tokens_used"] > 0:
            print(
                f"   -> Total tokens used: {final_results['html_generation']['total_tokens_used']}"
            )
        print(f"   -> Results saved to: {results_file}")

        return final_results

    async def _generate_html_for_all_pages(
        self, processing_results: Dict, output_dir: str
    ) -> List[PageHTMLResult]:
        """Generate HTML for all pages using LLM, with controlled concurrency."""
        pages = processing_results["pages"]

        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)

        # Create tasks for all pages
        tasks = []
        for page_num, page_data in pages.items():
            task = self._generate_html_for_page_with_semaphore(
                semaphore, int(page_num), page_data, output_dir
            )
            tasks.append(task)

        # Execute all tasks
        html_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        final_results = []
        for i, result in enumerate(html_results):
            if isinstance(result, Exception):
                page_num = list(pages.keys())[i]
                final_results.append(
                    PageHTMLResult(
                        page_number=int(page_num),
                        success=False,
                        error_message=str(result),
                    )
                )
            else:
                final_results.append(result)

        return final_results

    async def _generate_html_for_page_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        page_number: int,
        page_data: Dict,
        output_dir: str,
    ) -> PageHTMLResult:
        """Generate HTML for a single page with semaphore control."""
        async with semaphore:
            return await self._generate_html_for_page(
                page_number, page_data, output_dir
            )

    async def _generate_html_for_page(
        self, page_number: int, page_data: Dict, output_dir: str
    ) -> PageHTMLResult:
        """Generate HTML for a single page."""
        import time

        start_time = time.time()

        print(f"     🔄 Generating HTML for page {page_number}...")

        try:
            # Get artifact paths
            artifacts = page_data["artifacts"]
            pixmap_path = artifacts.get("pixmap")
            text_path = artifacts.get("text")

            # Generate HTML using LLM
            llm_response = await self.llm_interface.generate_html_from_page(
                system_prompt=self.system_prompt,
                pixmap_path=pixmap_path,
                text_path=text_path,
                page_number=page_number,
            )

            processing_time = time.time() - start_time
            page_dir = page_data["page_dir"]

            if llm_response.success:
                # Save raw LLM response as JSON for debugging/analysis
                raw_response_file = os.path.join(
                    page_dir, f"page_{page_number}_raw_response.json"
                )
                raw_response_data = {
                    "page_number": page_number,
                    "timestamp": time.time(),
                    "provider": self.config.llm_provider,
                    "model": self.config.llm_model,
                    "processing_time": processing_time,
                    "raw_content": llm_response.content,
                    "content_length": len(llm_response.content),
                    "token_usage": llm_response.usage,
                    "success": True,
                    "gemini_response_data": llm_response.raw_response_data,  # Add comprehensive Gemini data
                }

                with open(raw_response_file, "w", encoding="utf-8") as f:
                    json.dump(raw_response_data, f, indent=2, ensure_ascii=False)

                print(f"       💾 Raw response saved: {raw_response_file}")

                # Extract and clean HTML content
                html_content = self._extract_html_content(llm_response.content)

                # Save cleaned HTML to file
                html_file = os.path.join(page_dir, f"page_{page_number}.html")

                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(html_content)

                print(f"       ✅ HTML saved: {html_file} ({processing_time:.1f}s)")
                print(
                    f"       📊 Content: {len(llm_response.content)} chars raw → {len(html_content)} chars HTML"
                )

                return PageHTMLResult(
                    page_number=page_number,
                    success=True,
                    html_content=html_content,
                    html_file_path=html_file,
                    processing_time=processing_time,
                    token_usage=llm_response.usage,
                )
            else:
                # Save failed response for debugging
                raw_response_file = os.path.join(
                    page_dir, f"page_{page_number}_raw_response.json"
                )
                raw_response_data = {
                    "page_number": page_number,
                    "timestamp": time.time(),
                    "provider": self.config.llm_provider,
                    "model": self.config.llm_model,
                    "processing_time": processing_time,
                    "raw_content": llm_response.content,
                    "error_message": llm_response.error_message,
                    "success": False,
                    "token_usage": llm_response.usage,
                    "gemini_response_data": getattr(
                        llm_response, "raw_response_data", None
                    ),
                }

                with open(raw_response_file, "w", encoding="utf-8") as f:
                    json.dump(raw_response_data, f, indent=2, ensure_ascii=False)

                print(f"       ❌ HTML generation failed: {llm_response.error_message}")
                print(f"       💾 Error response saved: {raw_response_file}")

                return PageHTMLResult(
                    page_number=page_number,
                    success=False,
                    error_message=llm_response.error_message,
                    processing_time=processing_time,
                )

        except Exception as e:
            processing_time = time.time() - start_time
            print(f"       ❌ Exception during HTML generation: {e}")

            # Save exception details
            page_dir = page_data["page_dir"]
            raw_response_file = os.path.join(
                page_dir, f"page_{page_number}_raw_response.json"
            )
            raw_response_data = {
                "page_number": page_number,
                "timestamp": time.time(),
                "provider": self.config.llm_provider,
                "model": self.config.llm_model,
                "processing_time": processing_time,
                "exception": str(e),
                "success": False,
            }

            with open(raw_response_file, "w", encoding="utf-8") as f:
                json.dump(raw_response_data, f, indent=2, ensure_ascii=False)

            return PageHTMLResult(
                page_number=page_number,
                success=False,
                error_message=str(e),
                processing_time=processing_time,
            )

    def _serialize_html_result(self, result: PageHTMLResult) -> Dict:
        """Convert PageHTMLResult to a serializable dictionary."""
        return {
            "page_number": result.page_number,
            "success": result.success,
            "html_file_path": result.html_file_path,
            "error_message": result.error_message,
            "processing_time": result.processing_time,
            "token_usage": result.token_usage,
            "html_content_length": (
                len(result.html_content) if result.html_content else 0
            ),
        }

    def _extract_html_content(self, raw_content: str) -> str:
        """
        Extract HTML content from LLM response, handling potential markdown code blocks.

        Args:
            raw_content: Raw response from LLM

        Returns:
            Cleaned HTML content
        """
        content = raw_content.strip()

        # Check if content is wrapped in markdown code blocks
        if content.startswith("```html") and content.endswith("```"):
            # Remove markdown code block markers
            content = content[7:-3].strip()  # Remove ```html and ```
            print(f"       🧹 Extracted HTML from complete markdown code block")
        elif content.startswith("```html"):
            # Handle incomplete markdown block (missing closing backticks)
            content = content[7:].strip()  # Remove ```html
            print(f"       🧹 Extracted HTML from incomplete markdown code block")
        elif content.startswith("```") and content.endswith("```"):
            # Generic code block - find the first newline and remove markers
            lines = content.split("\n")
            if len(lines) > 2:
                content = "\n".join(lines[1:-1])  # Remove first and last lines
                print(f"       🧹 Extracted content from generic code block")
        elif content.startswith("```"):
            # Handle incomplete generic code block
            lines = content.split("\n")
            if len(lines) > 1:
                content = "\n".join(lines[1:])  # Remove first line
                print(f"       🧹 Extracted content from incomplete generic code block")

        # Additional cleanup: remove any leading/trailing whitespace
        content = content.strip()

        # If content doesn't start with HTML tags, assume it's raw HTML
        if not content.startswith("<!DOCTYPE") and not content.startswith("<html"):
            print(f"       ⚠️  Content doesn't start with HTML tags - using as-is")

        return content
