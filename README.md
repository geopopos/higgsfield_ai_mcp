# Higgsfield AI MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that provides access to [Higgsfield AI](https://higgsfield.ai)'s cinematic-grade image and video generation capabilities. Built with [FastMCP](https://github.com/jlowin/fastmcp).

## Features

- **Text-to-Image Generation**: Create high-quality images using the Soul model
- **Image-to-Video**: Convert static images into cinematic 5-second videos with motion presets
- **Character Consistency**: Create reusable character references for consistent appearance across generations
- **Style Presets**: Browse and apply cinematic style presets
- **Motion Library**: Access pre-designed motion effects for video generation

## Installation

### Prerequisites

- Python 3.10 or higher
- [Poetry](https://python-poetry.org/) for dependency management
- Higgsfield AI account with API credentials ([Sign up](https://cloud.higgsfield.ai))

### Setup

1. **Clone or download this repository**

2. **Install Poetry** (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Install dependencies**:
   ```bash
   cd mcp_creator
   poetry install
   ```

4. **Configure API credentials**:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your Higgsfield AI credentials:
   ```
   HF_API_KEY=your-api-key-here
   HF_SECRET=your-secret-key-here
   ```

   Get your API keys from: https://cloud.higgsfield.ai/api-keys

## Usage

### Local Development & Testing

Test the server using FastMCP's dev mode:

```bash
# Activate poetry environment
poetry shell

# Run in development mode with auto-reload
fastmcp dev src/higgsfield_mcp/server.py

# Or run directly
python -m higgsfield_mcp.server
```

### Claude Desktop Integration

Add this server to your Claude Desktop configuration:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "higgsfield": {
      "command": "poetry",
      "args": [
        "run",
        "python",
        "-m",
        "higgsfield_mcp.server"
      ],
      "cwd": "/absolute/path/to/mcp_creator",
      "env": {
        "HF_API_KEY": "your-api-key-here",
        "HF_SECRET": "your-secret-key-here"
      }
    }
  }
}
```

**Note**: Replace `/absolute/path/to/mcp_creator` with the actual path to this directory.

After adding the configuration, restart Claude Desktop.

### FastMCP Cloud Deployment

Deploy to FastMCP Cloud for remote access:

```bash
# Install FastMCP CLI
pip install fastmcp

# Deploy (requires FastMCP Cloud account)
fastmcp deploy src/higgsfield_mcp/server.py
```

## Available Tools

### `generate_image`
Generate high-quality images from text prompts.

**Parameters**:
- `prompt` (required): Detailed text description
- `quality`: "720p" or "1080p" (default)
- `character_id`: Optional character reference ID for consistency
- `style_id`: Optional style preset ID

**Example**:
```
Generate an image: "A woman with sharp eyes sitting on a minimalist bench in a desert garden, wearing a sand-colored suit, late afternoon sunlight"
```

### `generate_video`
Convert images to cinematic videos with motion effects.

**Parameters**:
- `image_url` (required): Source image URL
- `motion_id` (required): Motion preset ID (browse with resources)
- `quality`: "lite", "turbo", or "standard" (default)

### `create_character`
Create a reusable character reference for consistent generation.

**Parameters**:
- `name` (required): Descriptive name for the character
- `image_urls` (required): List of 1-5 image URLs showing the face

**Cost**: 40 credits ($2.50)

### `get_generation_status`
Check job status and retrieve results.

**Parameters**:
- `job_set_id` (required): Job ID from generate_image/generate_video

**Job Statuses**:
- `queued`: Waiting to start
- `in_progress`: Currently generating
- `completed`: Done! Results available
- `failed`: Generation failed
- `nsfw`: Content filter triggered

### `list_characters`
List all your created character references with IDs and status.

## Available Resources

Browse data sources using MCP resources:

- **`higgsfield://styles`**: Available Soul image style presets
- **`higgsfield://motions`**: Video motion presets for DoP model
- **`higgsfield://characters`**: Your created character references

## Workflow Example

1. **Browse available styles**:
   - Access `higgsfield://styles` resource to see style options

2. **Generate an image**:
   ```
   generate_image(
     prompt="Professional headshot in modern office",
     quality="1080p",
     style_id="1cb4b936-77bf-4f9a-9039-f3d349a4cdbe"
   )
   ```
   → Returns `job_set_id`

3. **Check status and get results**:
   ```
   get_generation_status(job_set_id="...")
   ```
   → Returns download URLs when complete

4. **Create character for consistency** (optional):
   ```
   create_character(
     name="Jane Doe",
     image_urls=["https://example.com/face1.jpg", "https://example.com/face2.jpg"]
   )
   ```
   → Returns `character_id`

5. **Generate with character**:
   ```
   generate_image(
     prompt="Same person in a different scene",
     character_id="3eb3ad49-775d-40bd-b5e5-38b105108780"
   )
   ```

6. **Animate the result**:
   - Browse `higgsfield://motions` for motion presets
   ```
   generate_video(
     image_url="https://result-from-step-5.jpg",
     motion_id="motion-preset-id",
     quality="standard"
   )
   ```

## Pricing

Credits are charged when generation completes successfully (not on failures):

- **Image Generation (Soul)**:
  - 720p: 1.5 credits ($0.09) per image
  - 1080p: 3 credits ($0.19) per image
  - First 1000 generations: 1 credit ($0.06) for 1080p

- **Video Generation (DoP)**:
  - Lite: 2 credits ($0.125)
  - Turbo: 6.5 credits ($0.406) - 2x speed
  - Standard: 9 credits ($0.563) - Highest quality

- **Character Creation**: 40 credits ($2.50) one-time

Rate: $1 = 16 credits
Add credits at: https://cloud.higgsfield.ai/credits

## Troubleshooting

### "Missing required environment variables"
- Ensure `.env` file exists with `HF_API_KEY` and `HF_SECRET`
- Or set environment variables in your shell or Claude Desktop config

### "401 Unauthorized"
- Verify your API key and secret are correct
- Check they haven't expired or been revoked

### "402 Payment Required"
- Add credits to your Higgsfield account
- Visit: https://cloud.higgsfield.ai/credits

### Server not appearing in Claude Desktop
- Check the `cwd` path is absolute, not relative
- Verify Poetry is installed and accessible
- Restart Claude Desktop after config changes
- Check Claude Desktop logs for errors

### Generation stuck in "queued"
- Wait a few seconds and poll again
- Check your account has sufficient credits
- During high load, jobs may take longer

## Project Structure

```
mcp_creator/
├── src/
│   └── higgsfield_mcp/
│       ├── __init__.py
│       ├── server.py          # FastMCP server with tools & resources
│       └── client.py          # Async Higgsfield API wrapper
├── pyproject.toml             # Poetry configuration
├── .env.example               # Credential template
├── .env                       # Your credentials (gitignored)
├── .gitignore
└── README.md
```

## Development

### Running Tests
```bash
poetry shell
fastmcp dev src/higgsfield_mcp/server.py
```

### Adding New Tools
Edit `src/higgsfield_mcp/server.py` and add new `@mcp.tool` decorated functions.

### Adding New API Methods
Edit `src/higgsfield_mcp/client.py` to add new API client methods.

## Resources

- [Higgsfield AI Platform](https://higgsfield.ai)
- [Higgsfield API Documentation](https://platform.higgsfield.ai/docs)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Claude Desktop](https://claude.ai/download)

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please open an issue or pull request.

## Support

- Higgsfield AI Support: https://cloud.higgsfield.ai/support
- MCP Documentation: https://modelcontextprotocol.io
- File issues: Create an issue in this repository
