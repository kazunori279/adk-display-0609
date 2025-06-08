# adk-display-0609

## Index Building Module

### Installation

1. Navigate to the index-building directory:

   ```bash
   cd index-building
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the index-building directory with your Google API key:

   ```bash
   GOOGLE_GENAI_USE_VERTEXAI=FALSE
   GOOGLE_API_KEY=your_api_key_here
   ```

### Testing

Run all tests (including integration tests that make real API calls):

```bash
python -m pytest -v
```

Note: Integration tests require a valid `GOOGLE_API_KEY` in the `.env` file and will consume API quota.