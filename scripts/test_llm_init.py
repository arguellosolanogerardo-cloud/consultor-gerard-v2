import os
import pytest

api_key = os.environ.get('GOOGLE_API_KEY')
print('API key present?', bool(api_key))

# During automated test runs we may not have Google credentials available.
# Skip this module-level test if the API key is not set so pytest collection
# doesn't fail due to authentication/ADC errors.
if not api_key:
	pytest.skip("Skipping LLM init test: GOOGLE_API_KEY not set", allow_module_level=True)

# The import below intentionally occurs after the skip check to avoid initializing
# the Google client during pytest collection when no credentials are available.
# Tell ruff to ignore E402 for this line.
from langchain_google_genai import GoogleGenerativeAI  # noqa: E402

llm = GoogleGenerativeAI(model='models/gemini-2.5-pro', google_api_key=api_key)
print('LLM init OK:', type(llm))
