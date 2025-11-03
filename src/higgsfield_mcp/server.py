"""
Higgsfield AI MCP Server
FastMCP server exposing Higgsfield AI capabilities to LLMs
"""
import os
import json
import sys
import argparse
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from fastmcp import FastMCP

# Add parent directory to path for imports when run as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from higgsfield_mcp.client import HiggsfieldClient
except ImportError:
    from .client import HiggsfieldClient

# Parse command line arguments
parser = argparse.ArgumentParser(description='Higgsfield AI MCP Server')
parser.add_argument('--api-key', type=str, help='Higgsfield API key')
parser.add_argument('--secret', type=str, help='Higgsfield secret key')
args, unknown = parser.parse_known_args()

# Load environment variables from .env file
load_dotenv()

# Initialize MCP server
mcp = FastMCP(
    name="Higgsfield AI",
    instructions="""
    This server provides access to Higgsfield AI's cinematic-grade image and video generation capabilities.

    Core Features:
    - Generate high-quality images from text prompts using the Soul model
    - Convert images to cinematic videos with motion presets using DoP model
    - Create talking head videos from image and audio using Speak v2 model
    - Create and manage character references for consistent character generation
    - Browse available styles and motion presets

    All generation operations are asynchronous - you'll receive a job ID that you must poll
    using get_generation_status to retrieve results. Results are retained for 7 days.
    """,
    version="0.1.0"
)

# Get credentials from: 1) command line args, 2) environment variables, 3) .env file
api_key = args.api_key or os.getenv("HF_API_KEY", "")
secret = args.secret or os.getenv("HF_SECRET", "")

# Only validate credentials when actually running (not during inspection)
if not api_key or not secret:
    # Use dummy values for inspection/testing
    api_key = api_key or "dummy-api-key-for-inspection"
    secret = secret or "dummy-secret-for-inspection"

    # Show warning if this is not just an inspection
    import warnings
    warnings.warn(
        "Missing HF_API_KEY and/or HF_SECRET. Provide via --api-key and --secret arguments "
        "or set HF_API_KEY and HF_SECRET environment variables.",
        RuntimeWarning
    )

client = HiggsfieldClient(api_key=api_key, secret=secret)


# ============================================================================
# MCP TOOLS - Core functionality
# ============================================================================

@mcp.tool
async def generate_image(
    prompt: str,
    quality: str = "1080p",
    character_id: Optional[str] = None,
    style_id: Optional[str] = None
) -> str:
    """
    Generate a high-quality image from a text prompt using Soul model.

    This starts an asynchronous generation job. Use get_generation_status with the
    returned job_set_id to check completion and retrieve results.

    Args:
        prompt: Detailed text description of the image to generate
        quality: Image quality - "720p" or "1080p" (default: "1080p")
        character_id: Optional character reference ID for consistent character generation
        style_id: Optional style preset ID (use higgsfield://styles resource to browse)

    Returns:
        Job information including job_set_id for polling status

    Example:
        generate_image(
            prompt="A woman with sharp eyes sitting on a bench in a desert garden",
            quality="1080p",
            style_id="1cb4b936-77bf-4f9a-9039-f3d349a4cdbe"
        )
    """
    try:
        result = await client.generate_image(
            prompt=prompt,
            quality=quality,
            custom_reference_id=character_id,
            style_id=style_id,
            batch_size=1
        )

        return json.dumps({
            "success": True,
            "job_set_id": result["id"],
            "job_type": result["type"],
            "status": "Job started - use get_generation_status to check completion",
            "created_at": result["created_at"],
            "jobs": result["jobs"]
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to start image generation"
        }, indent=2)


@mcp.tool
async def generate_video(
    image_url: str,
    motion_id: str,
    prompt: Optional[str] = None,
    quality: str = "standard"
) -> str:
    """
    Convert an image to a 5-second cinematic video with motion effects using DoP model.

    This starts an asynchronous generation job. Use get_generation_status with the
    returned job_set_id to check completion and retrieve results.

    Args:
        image_url: URL of the source image to animate (must be publicly accessible via HTTPS)
        motion_id: Motion preset ID (use higgsfield://motions resource to browse available)
        prompt: Optional description of the image/scene. If not provided, a generic prompt is used.
                Example: "A woman taking a selfie at a beach construction site"
        quality: Video quality - "lite" (cheapest/fastest), "turbo" (2x speed), or "standard" (highest quality, default)

    Returns:
        Job information including job_set_id for polling status

    Example:
        generate_video(
            image_url="https://example.com/image.jpg",
            motion_id="31177282-bde3-4870-b283-1135ca0a201a",
            prompt="A serene mountain landscape at sunset",
            quality="turbo"
        )

    Important:
        - Image URL must be publicly accessible (Higgsfield servers need to fetch it)
        - Processing takes 20-60 seconds depending on quality
        - Poll get_generation_status every 10 seconds to check completion
    """
    try:
        # Map quality to model parameter
        model_map = {
            "lite": "dop-lite",
            "turbo": "dop-turbo",
            "standard": "dop-preview"
        }
        model = model_map.get(quality, "dop-preview")

        result = await client.generate_video(
            image_url=image_url,
            motion_id=motion_id,
            prompt=prompt or "",
            model=model
        )

        return json.dumps({
            "success": True,
            "job_set_id": result["id"],
            "job_type": result["type"],
            "status": "Job started - use get_generation_status to check completion",
            "created_at": result["created_at"],
            "jobs": result["jobs"]
        }, indent=2)
    except Exception as e:
        # Debug: capture more error details
        import traceback
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc(),
            "message": "Failed to start video generation",
            "debug_info": {
                "image_url": image_url,
                "motion_id": motion_id,
                "model": model_map.get(quality, "dop-preview"),
                "prompt_provided": bool(prompt),
                "api_key_configured": bool(client.headers.get("hf-api-key")),
                "api_key_preview": client.headers.get("hf-api-key", "")[:8] + "..." if client.headers.get("hf-api-key") else "NOT SET"
            }
        }, indent=2)


@mcp.tool
async def generate_talking_head(
    image_url: str,
    audio_url: str,
    prompt: str,
    quality: str = "high",
    duration: int = 5,
    enhance_prompt: bool = False,
    seed: int = 42
) -> str:
    """
    Generate a talking head video from an image and audio file using Speak v2 model.

    This starts an asynchronous generation job. Use get_generation_status with the
    returned job_set_id to check completion and retrieve results.

    Args:
        image_url: URL of the source image (portrait/headshot, must be publicly accessible)
        audio_url: URL of the audio file in WAV format (must be publicly accessible, will be cut to selected duration)
        prompt: Text description of the image/scene (e.g., "A professional woman in business attire")
        quality: Video quality - "high" (default) or "mid"
        duration: Video duration in seconds - 5 (default), 10, or 15
        enhance_prompt: Whether to enhance the prompt automatically (default: False)
        seed: Random seed for reproducibility, 1-1,000,000 (default: 42)

    Returns:
        Job information including job_set_id for polling status

    Example:
        generate_talking_head(
            image_url="https://example.com/portrait.jpg",
            audio_url="https://example.com/speech.wav",
            prompt="A professional woman giving a presentation",
            quality="high",
            duration=10
        )

    Important:
        - Both image_url and audio_url must be publicly accessible via HTTPS
        - Audio MUST be in WAV format (not MP3). Use ffmpeg to convert: ffmpeg -i input.mp3 -acodec pcm_s16le -ar 44100 output.wav
        - Image should be a portrait/headshot for best results
        - Audio will be automatically trimmed to match the selected duration
        - Processing takes 2-3 minutes depending on duration and quality
        - Poll get_generation_status every 10-15 seconds to check completion
    """
    try:
        result = await client.generate_talking_head(
            image_url=image_url,
            audio_url=audio_url,
            prompt=prompt,
            quality=quality,
            duration=duration,
            enhance_prompt=enhance_prompt,
            seed=seed
        )

        return json.dumps({
            "success": True,
            "job_set_id": result["id"],
            "job_type": result["type"],
            "status": "Job started - use get_generation_status to check completion",
            "created_at": result["created_at"],
            "jobs": result["jobs"],
            "duration": duration,
            "quality": quality
        }, indent=2)
    except Exception as e:
        import traceback
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc(),
            "message": "Failed to start talking head video generation"
        }, indent=2)


@mcp.tool
async def create_character(
    name: str,
    image_urls: list[str]
) -> str:
    """
    Create a reusable character reference for consistent character generation across images.

    Provide 1-5 clear images of a person's face from different angles. The character ID
    can then be used in generate_image calls to maintain consistent appearance.

    Character creation costs 40 credits ($2.50) and takes a few minutes to process.
    Use get_generation_status to check when ready.

    Args:
        name: Descriptive name for this character reference
        image_urls: List of 1-5 image URLs showing the character's face clearly

    Returns:
        Character reference information with ID for use in image generation

    Example:
        create_character(
            name="Jane Doe - Corporate Headshots",
            image_urls=[
                "https://example.com/face-front.jpg",
                "https://example.com/face-side.jpg"
            ]
        )
    """
    try:
        result = await client.create_character(
            name=name,
            image_urls=image_urls
        )

        return json.dumps({
            "success": True,
            "character_id": result["id"],
            "name": result["name"],
            "status": result["status"],
            "message": "Character creation started. Status will progress: not_ready -> queued -> in_progress -> completed",
            "created_at": result["created_at"],
            "note": "Use list_characters tool or get_generation_status to check when ready"
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to create character reference"
        }, indent=2)


@mcp.tool
async def get_generation_status(job_set_id: str) -> str:
    """
    Check the status and retrieve results of an image or video generation job.

    Poll this endpoint to check if your generation is complete. Job statuses:
    - queued: Waiting to start
    - in_progress: Currently generating
    - completed: Done! Results available
    - failed: Generation failed
    - nsfw: Content filter triggered

    Results are retained for 7 days after generation.

    Args:
        job_set_id: The job_set_id returned from generate_image or generate_video

    Returns:
        Current job status and results (if completed)

    Example:
        get_generation_status(job_set_id="3c90c3cc-0d44-4b50-8888-8dd25736052a")
    """
    try:
        result = await client.get_job_results(job_set_id)

        # Extract key information
        response = {
            "success": True,
            "job_set_id": result["id"],
            "type": result["type"],
            "created_at": result["created_at"],
            "jobs": []
        }

        for job in result["jobs"]:
            job_info = {
                "job_id": job["id"],
                "status": job["status"],
            }

            # Add results if completed
            if job.get("results"):
                job_info["results"] = {
                    "preview_url": job["results"]["min"]["url"],
                    "full_quality_url": job["results"]["raw"]["url"],
                    "type": job["results"]["raw"]["type"]
                }

            response["jobs"].append(job_info)

        # Add helpful message based on status
        statuses = [j["status"] for j in result["jobs"]]
        if all(s == "completed" for s in statuses):
            response["message"] = "Generation complete! Download URLs above."
        elif any(s == "failed" for s in statuses):
            response["message"] = "One or more jobs failed."
        elif any(s == "nsfw" for s in statuses):
            response["message"] = "Content filter triggered - regenerate with different prompt."
        else:
            response["message"] = "Still processing - check again in a few seconds."

        return json.dumps(response, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve job status"
        }, indent=2)


@mcp.tool
async def debug_credentials() -> str:
    """
    Debug tool to check if credentials are properly configured.

    Returns:
        Information about credential configuration
    """
    return json.dumps({
        "api_key_configured": bool(client.headers.get("hf-api-key")),
        "secret_configured": bool(client.headers.get("hf-secret")),
        "api_key_preview": client.headers.get("hf-api-key", "")[:8] + "..." if client.headers.get("hf-api-key") else "NOT SET",
        "base_url": client.base_url,
        "headers_keys": list(client.headers.keys())
    }, indent=2)


@mcp.tool
async def list_characters() -> str:
    """
    List all character references you've created.

    Shows character IDs, names, status, and thumbnails. Use the character_id
    in generate_image calls for consistent character generation.

    Returns:
        List of your character references with IDs and status
    """
    try:
        result = await client.list_characters(page=1, page_size=50)

        characters = []
        for item in result.get("items", []):
            characters.append({
                "character_id": item["id"],
                "name": item["name"],
                "status": item["status"],
                "thumbnail_url": item.get("thumbnail_url"),
                "created_at": item["created_at"]
            })

        return json.dumps({
            "success": True,
            "total": result.get("total", 0),
            "characters": characters,
            "message": f"Found {len(characters)} character reference(s)"
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to list characters"
        }, indent=2)


# ============================================================================
# MCP RESOURCES - Browsable data
# ============================================================================

@mcp.resource("higgsfield://styles")
async def list_soul_styles() -> str:
    """
    Browse available Soul image generation style presets.

    Returns style IDs, names, descriptions, and preview images that can be used
    in the generate_image tool.
    """
    try:
        styles = await client.list_styles()

        formatted = []
        for style in styles:
            formatted.append({
                "style_id": style["id"],
                "name": style["name"],
                "description": style["description"],
                "preview_url": style.get("preview_url")
            })

        return json.dumps({
            "available_styles": formatted,
            "usage": "Use style_id parameter in generate_image tool"
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "Failed to fetch styles"
        }, indent=2)


@mcp.resource("higgsfield://motions")
async def list_motion_presets() -> str:
    """
    Browse available video motion presets for the DoP model.

    Returns motion IDs, names, descriptions, and preview videos that can be used
    in the generate_video tool.
    """
    try:
        motions = await client.list_motions()

        formatted = []
        for motion in motions:
            formatted.append({
                "motion_id": motion["id"],
                "name": motion["name"],
                "description": motion["description"],
                "preview_url": motion.get("preview_url"),
                "start_end_frame": motion.get("start_end_frame", False)
            })

        return json.dumps({
            "available_motions": formatted,
            "usage": "Use motion_id parameter in generate_video tool"
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "Failed to fetch motion presets"
        }, indent=2)


@mcp.resource("higgsfield://characters")
async def list_character_resources() -> str:
    """
    Browse your created character references.

    Shows all character IDs that can be used in generate_image for consistent
    character appearance across multiple generations.
    """
    try:
        result = await client.list_characters(page=1, page_size=100)

        characters = []
        for item in result.get("items", []):
            characters.append({
                "character_id": item["id"],
                "name": item["name"],
                "status": item["status"],
                "thumbnail_url": item.get("thumbnail_url"),
                "created_at": item["created_at"]
            })

        return json.dumps({
            "total_characters": result.get("total", 0),
            "characters": characters,
            "usage": "Use character_id parameter in generate_image tool"
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "Failed to fetch characters"
        }, indent=2)


# ============================================================================
# Server entry point
# ============================================================================

def main():
    """Run the MCP server"""
    # Run with STDIO transport (default for Claude Desktop integration)
    mcp.run(transport="stdio")

    # For HTTP deployment (uncomment to use):
    # mcp.run(transport="http", host="0.0.0.0", port=8000, path="/mcp")


if __name__ == "__main__":
    main()
