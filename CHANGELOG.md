# Changelog

All notable changes to the Higgsfield AI MCP Server will be documented in this file.

## [Fixed] - 2025-11-02

### 🐛 Critical Bug Fix: Video Generation

**Problem**:
The `generate_video` function was failing with `422 Unprocessable Content` errors because it was using incorrect API payload format.

**Root Cause**:
- API was sending `image_url` as a direct string parameter
- Missing required `prompt` field
- Higgsfield API actually requires:
  - `prompt` (string, required): Description of the image/scene
  - `input_images` (array, required): Array with format `[{"type": "image_url", "image_url": "https://..."}]`

**Changes Made**:

#### `src/higgsfield_mcp/client.py`
- ✅ Added `prompt` parameter (optional, with default value)
- ✅ Changed payload from `{"image_url": url}` to `{"input_images": [{"type": "image_url", "image_url": url}]}`
- ✅ Added auto-generation of generic prompt if none provided
- ✅ Enhanced docstring with important notes about API requirements

**Before** (broken):
```python
params = {
    "image_url": image_url,  # ❌ API doesn't accept this
    "motion_id": motion_id,
    "quality": quality
}
```

**After** (working):
```python
params = {
    "prompt": prompt or "Cinematic video with natural motion",  # ✅ Required
    "input_images": [{                                           # ✅ Correct format
        "type": "image_url",
        "image_url": image_url
    }],
    "motion_id": motion_id,
    "quality": quality
}
```

#### `src/higgsfield_mcp/server.py`
- ✅ Added `prompt` parameter to MCP tool signature (optional)
- ✅ Updated docstring with examples showing prompt usage
- ✅ Added "Important" section explaining HTTPS requirement and processing times
- ✅ Improved example with realistic use case

**Before**:
```python
async def generate_video(
    image_url: str,
    motion_id: str,
    quality: str = "standard"
) -> str:
```

**After**:
```python
async def generate_video(
    image_url: str,
    motion_id: str,
    prompt: Optional[str] = None,  # ✅ New parameter
    quality: str = "standard"
) -> str:
```

#### Documentation Updates
- ✅ Updated `README.md` with fix announcement and enhanced `generate_video` documentation
- ✅ Created comprehensive `HIGGSFIELD_VIDEO_GENERATION_GUIDE.md` in parent directory
- ✅ Added this `CHANGELOG.md` file

### 📚 New Documentation

Created `../HIGGSFIELD_VIDEO_GENERATION_GUIDE.md` with:
- Complete step-by-step workflow
- Correct API usage examples (curl, Python)
- Motion preset reference table
- Troubleshooting guide
- Real-world working example from this project
- Quality levels comparison
- Processing time expectations

### ✅ Testing

Successfully tested with:
- Image: `higgsfield_generated.png` (2048x1152)
- Uploaded to: DigitalOcean Spaces (publicly accessible)
- Motion: "General" preset (`31177282-bde3-4870-b283-1135ca0a201a`)
- Quality: "turbo"
- Result: Video generated successfully in ~40 seconds

**Output**:
- Job ID: `fd898e16-1908-456d-a39c-e97705d1a13e`
- Video URL: https://cloud-cdn.higgsfield.ai/ac793fe7-3023-415d-bcae-f72836dddd22/bcc4a162-df13-461e-bf46-fca98c7642f3.mp4
- Downloaded as: `higgsfield_video_general_motion.mp4`

### 🎯 Impact

**Before**: Video generation would always fail with 422 error, making the feature completely unusable.

**After**: Video generation works correctly and reliably, matching Higgsfield API requirements.

### 🤖 AI Agent Improvements

The enhanced documentation and parameter naming makes it easier for AI assistants to:
1. **Understand requirements**: Clear parameter descriptions explain what the API needs
2. **Provide correct prompts**: The `prompt` parameter is now exposed and documented
3. **Handle errors**: Better error messages guide towards correct usage
4. **Set expectations**: Documentation explains processing times and requirements

### 📝 Migration Guide

If you have existing code using the old API:

**Old (broken) usage**:
```python
# This would fail with 422 error
await client.generate_video(
    image_url="https://example.com/image.png",
    motion_id="motion-id",
    quality="turbo"
)
```

**New (working) usage**:
```python
# This works correctly
await client.generate_video(
    image_url="https://example.com/image.png",
    motion_id="31177282-bde3-4870-b283-1135ca0a201a",
    prompt="A woman at a beach taking a selfie",  # Now optional but recommended
    quality="turbo"
)
```

**For MCP tool users** (via Claude Desktop):
The function signature is backward compatible - existing calls will work, but adding a `prompt` parameter is recommended for better results.

---

## [Initial Release] - 2025-11-01

- Initial implementation of Higgsfield AI MCP server
- Text-to-image generation (Soul model)
- Image-to-video conversion (DoP model) - **Note: Had bug, fixed 2025-11-02**
- Character reference creation and management
- Style and motion preset resources
- FastMCP integration
- Claude Desktop compatibility
