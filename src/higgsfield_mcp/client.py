"""
Higgsfield AI API Client
Async wrapper for the Higgsfield AI platform API
"""
import httpx
from typing import Optional, List, Dict, Any, Union


class HiggsfieldClient:
    """Async client for Higgsfield AI API"""

    def __init__(self, api_key: str, secret: str, base_url: str = "https://platform.higgsfield.ai"):
        """
        Initialize Higgsfield AI client

        Args:
            api_key: Your Higgsfield API key
            secret: Your Higgsfield secret key
            base_url: API base URL (default: https://platform.higgsfield.ai)
        """
        self.base_url = base_url
        self.headers = {
            "hf-api-key": api_key,
            "hf-secret": secret,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def generate_image(
        self,
        prompt: str,
        quality: str = "1080p",
        batch_size: int = 1,
        custom_reference_id: Optional[str] = None,
        style_id: Optional[str] = None,
        width_and_height: str = "2048x1152",
        enhance_prompt: bool = False,
        webhook_url: Optional[str] = None,
        webhook_secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate image using Soul text-to-image model

        Args:
            prompt: Text description of the image to generate
            quality: Image quality - "720p" or "1080p" (default)
            batch_size: Number of images to generate (1 or 4)
            custom_reference_id: Optional character ID for consistent generation
            style_id: Optional style preset ID
            width_and_height: Image dimensions (default: "2048x1152")
            enhance_prompt: Whether to enhance the prompt automatically
            webhook_url: Optional webhook URL for completion notification
            webhook_secret: Secret for webhook verification

        Returns:
            Job set response with job ID for polling
        """
        params = {
            "prompt": prompt,
            "width_and_height": width_and_height,
            "enhance_prompt": enhance_prompt,
            "quality": quality,
            "batch_size": batch_size
        }

        if custom_reference_id:
            params["custom_reference_id"] = custom_reference_id

        if style_id:
            params["style_id"] = style_id

        if webhook_url:
            params["webhook"] = {
                "url": webhook_url,
                "secret": webhook_secret or ""
            }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/text2image/soul",
                headers=self.headers,
                json={"params": params}
            )
            response.raise_for_status()
            return response.json()

    async def generate_video(
        self,
        image_url: str,
        motion_id: str,
        prompt: str = "",
        model: str = "dop-preview",
        webhook_url: Optional[str] = None,
        webhook_secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate video from image using DoP model

        Args:
            image_url: URL of the source image (must be publicly accessible)
            motion_id: Motion preset ID (use list_motions to get available)
            prompt: Description of the image/scene (auto-generated if empty)
            model: DoP model - "dop-lite", "dop-turbo", or "dop-preview" (default)
            webhook_url: Optional webhook URL for completion notification
            webhook_secret: Secret for webhook verification

        Returns:
            Job set response with job ID for polling

        Note:
            The API requires both 'prompt' and 'input_images' fields.
            If no prompt is provided, a generic one will be used.
        """
        # Use generic prompt if none provided
        if not prompt:
            prompt = "Cinematic video with natural motion"

        # API requires input_images array format, not image_url string
        params = {
            "model": model,
            "prompt": prompt,
            "input_images": [{
                "type": "image_url",
                "image_url": image_url
            }],
            "motions": [{
                "id": motion_id,
                "strength": 0.5
            }]
        }

        # Build request body with params
        request_body = {"params": params}

        # Webhook goes at top level, not in params
        if webhook_url:
            request_body["webhook"] = {
                "url": webhook_url,
                "secret": webhook_secret or ""
            }

        # Debug: write request/response to file
        import json as json_module
        debug_file = "/tmp/higgsfield_debug.txt"

        try:
            with open(debug_file, "a") as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"REQUEST at {__import__('datetime').datetime.now()}\n")
                f.write(f"Body: {json_module.dumps(request_body, indent=2)}\n")
                f.flush()
        except Exception as e:
            # If debug fails, write error to another file
            try:
                with open("/tmp/higgsfield_debug_error.txt", "a") as f:
                    f.write(f"Debug write error: {e}\n")
                    f.flush()
            except:
                pass

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/image2video/dop",
                headers=self.headers,
                json=request_body
            )

            try:
                with open(debug_file, "a") as f:
                    f.write(f"RESPONSE status: {response.status_code}\n")
                    f.write(f"RESPONSE body: {response.text}\n")
                    f.flush()
            except:
                pass

            response.raise_for_status()
            return response.json()

    async def create_character(
        self,
        name: str,
        image_urls: List[str]
    ) -> Dict[str, Any]:
        """
        Create a character reference for consistent generation

        Args:
            name: Name for the character reference
            image_urls: List of 1-5 image URLs showing the character's face

        Returns:
            Character reference response with ID
        """
        payload = {
            "name": name,
            "input_images": [
                {"type": "image_url", "image_url": url}
                for url in image_urls
            ]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/custom-references",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def get_job_results(self, job_set_id: str) -> Dict[str, Any]:
        """
        Get status and results of a generation job

        Args:
            job_set_id: Job set ID from generate_image or generate_video

        Returns:
            Job set with status and results (if completed)
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/job-sets/{job_set_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def list_styles(self) -> List[Dict[str, Any]]:
        """
        Get available Soul image style presets

        Returns:
            List of style presets with ID, name, description, preview URL
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/text2image/soul-styles",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def list_motions(self) -> List[Dict[str, Any]]:
        """
        Get available video motion presets

        Returns:
            List of motion presets with ID, name, description, preview URL
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/motions",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def list_characters(
        self,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        List created character references

        Args:
            page: Page number (starts at 1)
            page_size: Number of items per page

        Returns:
            Paginated list of character references
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/custom-references/list",
                headers=self.headers,
                params={"page": page, "page_size": page_size}
            )
            response.raise_for_status()
            return response.json()

    async def get_character(self, character_id: str) -> Dict[str, Any]:
        """
        Get details of a specific character reference

        Args:
            character_id: Character reference ID

        Returns:
            Character details including source images
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/custom-references/{character_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def delete_character(self, character_id: str) -> None:
        """
        Delete a character reference

        Args:
            character_id: Character reference ID to delete
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.base_url}/v1/custom-references/{character_id}",
                headers=self.headers
            )
            response.raise_for_status()
