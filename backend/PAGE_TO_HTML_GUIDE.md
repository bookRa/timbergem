# Page-to-HTML Pipeline Guide

## Overview

The page-to-HTML pipeline converts PDF pages into structured HTML documents using AI. It's designed to be modular, allowing you to swap between different LLM providers (Gemini, OpenAI, Claude) and fallback to cloud services like AWS Textract or Google DocumentAI in the future.

## Features

- **Modular Architecture**: Easy to swap LLM providers or entire processing pipelines
- **Testing Mode**: Generate mock HTML files without making expensive API calls
- **Parallel Processing**: Process multiple pages simultaneously with controlled concurrency
- **Artifact Extraction**: Extracts text, tables, and high-resolution images from PDF pages
- **Comprehensive Results**: Detailed logging and result tracking

## Quick Start

### 1. Testing Mode (No API Keys Required)

```bash
# Start the Flask server
cd backend
python app.py

# In another terminal, test the pipeline
python test_api.py
```

### 2. Production Mode with Real LLM

```bash
# Set environment variables
export GEMINI_API_KEY="your_gemini_api_key"
# OR
export OPENAI_API_KEY="your_openai_api_key"
# OR
export ANTHROPIC_API_KEY="your_claude_api_key"

# Install additional dependencies
pip install google-generativeai openai anthropic pillow
```

## API Endpoints

### Process PDF to HTML
```
POST /api/process_pdf_to_html
```

**Request Body:**
```json
{
  "docId": "TEST",
  "config": {
    "llm_provider": "mock|gemini|openai|claude",
    "llm_model": "optional_model_name",
    "testing_mode": true,
    "dpi": 200,
    "high_res_dpi": 300,
    "max_concurrent_requests": 3,
    "gemini_api_key": "optional_override",
    "openai_api_key": "optional_override",
    "anthropic_api_key": "optional_override"
  }
}
```

### Load Processing Results
```
GET /api/load_html_results/{docId}
```

### Get Page HTML
```
GET /api/get_page_html/{docId}/{pageNumber}
```

## Configuration Options

### LLM Providers

#### Mock Provider (Testing)
```json
{
  "llm_provider": "mock",
  "testing_mode": true
}
```

#### Google Gemini
```json
{
  "llm_provider": "gemini",
  "llm_model": "gemini-1.5-flash",
  "testing_mode": false,
  "gemini_api_key": "your_key_here"
}
```

#### OpenAI GPT-4 Vision
```json
{
  "llm_provider": "openai",
  "llm_model": "gpt-4-vision-preview",
  "testing_mode": false,
  "openai_api_key": "your_key_here"
}
```

#### Anthropic Claude
```json
{
  "llm_provider": "claude",
  "llm_model": "claude-3-5-sonnet-20241022",
  "testing_mode": false,
  "anthropic_api_key": "your_key_here"
}
```

## File Structure

After processing, each document creates the following structure:

```
data/processed/{docId}/
├── original.pdf                      # Original PDF file
├── processing_metadata.json          # PDF processing results
├── page_to_html_results.json        # HTML generation results
├── page_1/
│   ├── page_1_pixmap.png            # High-res page image
│   ├── page_1_text.txt              # Extracted text
│   ├── page_1_tables.csv            # Extracted tables (if any)
│   └── page_1.html                  # Generated HTML
├── page_2/
│   └── ...
└── ...
```

## Testing with the TEST Document

The system includes a TEST document at `data/processed/TEST/original.pdf` for testing:

```python
# Direct Python usage
import asyncio
from utils.page_to_html_pipeline import PageToHTMLPipeline, PageToHTMLConfig

config = PageToHTMLConfig(
    llm_provider="mock",
    testing_mode=True
)

pipeline = PageToHTMLPipeline(config)
results = asyncio.run(pipeline.process_pdf_to_html(
    "../data/processed/TEST/original.pdf",
    "../data/processed/TEST",
    "TEST"
))
```

## Production Usage Example

```python
import asyncio
from utils.page_to_html_pipeline import PageToHTMLPipeline, PageToHTMLConfig

# Configure for production with Gemini
config = PageToHTMLConfig(
    llm_provider="gemini",
    llm_model="gemini-1.5-flash",
    testing_mode=False,
    max_concurrent_requests=2,  # Lower for production
    gemini_api_key="your_api_key"
)

pipeline = PageToHTMLPipeline(config)

# Process a PDF
results = asyncio.run(pipeline.process_pdf_to_html(
    "path/to/your/document.pdf",
    "output/directory",
    "unique_doc_id"
))

print(f"Processed {results['html_generation']['successful_pages']} pages")
print(f"Total tokens used: {results['html_generation']['total_tokens_used']}")
```

## Customizing System Prompts

Edit `backend/system_prompts/page_to_html.md` to customize how the AI processes your documents.

## Adding New LLM Providers

1. Create a new provider class in `utils/llm_interface.py` that implements `LLMProvider`
2. Add it to the `LLMInterface.create_provider()` factory method
3. Update the configuration options

## Troubleshooting

### Common Issues

1. **Missing API Keys**: Set environment variables or pass keys in config
2. **Rate Limits**: Reduce `max_concurrent_requests` in config
3. **Large Documents**: Increase timeouts or process in smaller batches
4. **Memory Issues**: Lower `high_res_dpi` or process fewer pages at once

### Debug Mode

Enable detailed logging by setting the Flask app to debug mode:

```python
app.run(debug=True, port=5001)
```

## Future Enhancements

The modular design allows for easy integration of:
- AWS Textract
- Google DocumentAI  
- Azure Form Recognizer
- Custom processing pipelines
- Different output formats (Markdown, structured JSON, etc.) 