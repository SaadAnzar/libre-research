import os
import asyncio
from typing import Any, Dict
from dotenv import load_dotenv
import uuid
import json

# Load environment variables
load_dotenv()

# Gemini system prompt for research
SYSTEM_PROMPT = r"""
You are an expert research assistant built by Md Anzar Ahmad (mdanzarahmad.vercel.app). Your task is to conduct comprehensive, deep research on the given topic and prepare a detailed, academic-quality report with the following components:

1. Executive Summary: A concise yet comprehensive overview of the topic and key findings (minimum 250 words)
2. Introduction: Thorough background information and context of the topic, including its significance and relevance (minimum 300 words)
3. Main Body: Detailed analysis divided into at least 3-5 relevant sections and subsections, with each section exploring a different aspect of the topic in depth (minimum 500 words per section)
4. Findings & Insights: Comprehensive key discoveries and their implications, including data-driven insights when applicable (minimum 300 words)
5. Conclusion: Thorough summary of the research and potential future directions (minimum 250 words)
6. Sources: Extensive list of all sources used, with URLs, ensuring at least 8-10 high-quality sources

For each fact or claim, include a citation linking to the source. Be thorough in your research, considering multiple perspectives and addressing potential counterarguments. Use clear, precise language and maintain an objective, academic tone throughout the report.

Format your response as a structured JSON object with the following schema:
{
  "summary": "Executive summary text with markdown formatting (do not include 'Executive Summary' as a title within this text)",
  "sections": [
    {
      "title": "Section title",
      "content": "Section content with markdown formatting for headings, lists, emphasis, etc. (do not repeat the section title at the beginning of the content)"
    }
  ],
  "sources": [
    {
      "title": "Source title",
      "url": "Source URL",
      "snippet": "Detailed description of the source with markdown formatting"
    }
  ]
}

IMPORTANT FORMATTING INSTRUCTIONS:
1. Use proper markdown formatting in all text fields:
   - Use # for main headings, ## for subheadings, etc.
   - Use **bold** for emphasis
   - Use *italics* for definitions or special terms
   - Use bullet points (- item) and numbered lists (1. item) where appropriate
   - Use > for quotes or important callouts
   - Use markdown tables for structured data with | and - characters

2. DO NOT include the field name as a heading in the content:
   - In the "summary" field, do not start with "Executive Summary:" or "# Executive Summary"
   - In each section's "content" field, do not repeat the section title at the beginning

CRITICAL JSON FORMATTING REQUIREMENTS:
1. Your response MUST be valid JSON that can be parsed by Python's json.loads() function
2. Properly escape all special characters in JSON strings:
   - Use \\\\ for backslashes
   - Use \\" for quotes within strings
   - Use \\n for newlines
   - Avoid using single backslashes (\\) before any character except the ones listed above
3. Do NOT include any text, markdown formatting, or code blocks outside the JSON structure. Do not include any text like backticks or ```json before the JSON structure.
4. The entire response should be a single, valid JSON object

This format will be used to generate a downloadable PDF report, so ensure your content is well-structured, comprehensive, and professionally formatted.

IMPORTANT: Return ONLY valid JSON without any additional text or code block markers. The content inside the JSON should use markdown formatting, but the JSON itself must be valid and parseable.
"""


async def test_research_without_db_save():
    # Track active research tasks
    active_research_tasks: Dict[str, Any] = {}

    # Generate a random research ID
    research_id = str(uuid.uuid4())

    # Mock active_research_tasks entry
    active_research_tasks[research_id] = {"status": "in_progress"}

    # Test topic
    topic = "The impact of artificial intelligence on healthcare"

    print(f"Starting research on: {topic}")
    print(f"Research ID: {research_id}")

    try:
        # Import the necessary modules
        from google import genai
        from google.genai import types

        # Update the status to processing
        active_research_tasks[research_id]["status"] = "processing"

        # Prepare the prompt
        prompt = f"Topic: {topic}"

        # Using the exact code provided
        client = genai.Client(
            api_key=os.environ.get("GEMINI_API_KEY"),
        )

        model = "gemini-2.0-flash"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=SYSTEM_PROMPT
                        + '\n\nPlease format your response as valid JSON with the following structure: {"summary": "...", "sections": [{"title": "...", "content": "..."}], "sources": [{"title": "...", "url": "...", "snippet": "..."}]}\n\n'
                        + prompt
                    ),
                ],
            ),
        ]
        tools = [types.Tool(google_search=types.GoogleSearch())]
        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            top_k=64,
            max_output_tokens=8192,
            tools=tools,
            response_mime_type="text/plain",
        )

        # Collect the response
        # full_response = ""
        # for chunk in client.models.generate_content_stream(
        #     model=model,
        #     contents=contents,
        #     config=generate_content_config,
        # ):
        #     if chunk.text:
        #         full_response += chunk.text
        #         # Print a dot to show progress
        #         print(".", end="", flush=True)

        # Collect the response without streaming
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )

        full_response = response.text

        print("\n")
        print(
            f"Raw response preview: {full_response[:200]}..."
        )  # Print first 200 chars for debugging

        # Try to extract JSON from the response
        try:
            # Look for JSON-like structure in the response
            json_start = full_response.find("{")
            json_end = full_response.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = full_response[json_start:json_end]
                result = json.loads(json_str)
                print("Successfully parsed JSON response!")
                print(f"Summary: {result.get('summary', '')[:100]}...")
                print(f"Number of sections: {len(result.get('sections', []))}")
                print(f"Number of sources: {len(result.get('sources', []))}")
            else:
                print("No JSON structure found in the response")
                result = {
                    "summary": "Failed to parse response as JSON",
                    "sections": [{"title": "Raw Response", "content": full_response}],
                    "sources": [],
                }
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            result = {
                "summary": "Failed to parse response as JSON",
                "sections": [{"title": "Raw Response", "content": full_response}],
                "sources": [],
            }

        # Update the status
        active_research_tasks[research_id]["status"] = "completed"
        print("Research completed successfully!")

    except Exception as e:
        # Handle errors
        active_research_tasks[research_id]["status"] = "failed"
        active_research_tasks[research_id]["error"] = str(e)
        print(f"Research error: {e}")


if __name__ == "__main__":
    asyncio.run(test_research_without_db_save())
