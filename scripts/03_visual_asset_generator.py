#!/usr/bin/env python3
"""
03_visual_asset_generator.py - Visual Asset Generator (Local FLUX / API)

Reads `assets_manifest.json` from Step 2, calls Local Open-Source FLUX.1 (or API),
and outputs character turnaround sheets and location keyframe reference images into:
  - `assets/characters/`
  - `assets/locations/`

Usage:
    python scripts/03_visual_asset_generator.py --manifest output/assets_manifest.json
    python scripts/03_visual_asset_generator.py --dry-run
"""

import argparse
from dotenv import load_dotenv

load_dotenv()
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict


class VisualAssetGenerator:
    """FLUX Image Generator for characters and locations."""

    def __init__(self, mode: str = "local_flux", char_dir: str = None, loc_dir: str = None, ref_image: str = None):
        self.mode = mode
        self.char_dir = Path(char_dir) if char_dir else Path("assets/characters")
        self.loc_dir = Path(loc_dir) if loc_dir else Path("assets/locations")
        self.pipeline = None
        self.ref_image = ref_image

    def generate_assets(self, manifest: Dict[str, Any]) -> None:
        """Generate all character and location image assets defined in manifest."""
        characters = manifest.get("characters", [])
        locations = manifest.get("locations", [])

        self.char_dir.mkdir(parents=True, exist_ok=True)
        self.loc_dir.mkdir(parents=True, exist_ok=True)

        print(f"[*] Processing {len(characters)} characters & {len(locations)} locations...")

        for char in characters:
            out_path = self.char_dir / char["output_filename"]
            
            # Automatic reference image detection (if sheet exists but ref does not, rename it to ref)
            ref_path = out_path.with_name(f"{out_path.stem}_ref{out_path.suffix}")
            if not ref_path.exists() and out_path.exists():
                out_path.rename(ref_path)
                print(f"[*] Automatically renamed reference image to: {ref_path.name}")
                
            ref_to_use = str(ref_path) if ref_path.exists() else self.ref_image

            if out_path.exists():
                print(f"[*] Character asset {out_path.name} already exists. Skipping generation.")
                continue
            print(f"[*] Generating character asset: {char['name']} -> {out_path}")
            self._render_image(char["prompt"], str(out_path), asset_name=char["name"], asset_type="character", ref_image=ref_to_use)

        for loc in locations:
            out_path = self.loc_dir / loc["output_filename"]
            if out_path.exists():
                print(f"[*] Location asset {out_path.name} already exists. Skipping generation.")
                continue
            print(f"[*] Generating location asset: {loc['name']} -> {out_path}")
            self._render_image(loc["prompt"], str(out_path), asset_name=loc["name"], asset_type="location")

    def _draw_placeholder(self, prompt: str, output_path: str, asset_name: str, asset_type: str) -> None:
        from PIL import Image, ImageDraw
        # Set dimensions: 1920x1080 for character sheet, 1280x720 for locations
        width, height = (1920, 1080) if asset_type == "character" else (1280, 720)
        
        # Color palette
        bg_color = (13, 15, 20)
        accent_color = (0, 220, 255) if asset_type == "character" else (255, 180, 0)
        text_color = (230, 235, 245)
        muted_color = (100, 110, 130)
        
        # Create image
        image = Image.new("RGB", (width, height), color=bg_color)
        draw = ImageDraw.Draw(image)
        
        # Draw tech frame
        draw.rectangle([20, 20, width - 20, height - 20], outline=accent_color, width=4)
        draw.rectangle([30, 30, width - 30, height - 30], outline=(accent_color[0]//2, accent_color[1]//2, accent_color[2]//2), width=1)
        
        # Corner decorative accents
        accent_len = 80
        draw.line([20, 20, 20 + accent_len, 20], fill=(255, 255, 255), width=8)
        draw.line([20, 20, 20, 20 + accent_len], fill=(255, 255, 255), width=8)
        
        draw.line([width - 20, 20, width - 20 - accent_len, 20], fill=(255, 255, 255), width=8)
        draw.line([width - 20, 20, width - 20, 20 + accent_len], fill=(255, 255, 255), width=8)
        
        draw.line([20, height - 20, 20 + accent_len, height - 20], fill=(255, 255, 255), width=8)
        draw.line([20, height - 20, 20, height - 20 - accent_len], fill=(255, 255, 255), width=8)
        
        draw.line([width - 20, height - 20, width - 20 - accent_len, height - 20], fill=(255, 255, 255), width=8)
        draw.line([width - 20, height - 20, width - 20, height - 20 - accent_len], fill=(255, 255, 255), width=8)
        
        # Draw Text
        draw.text((60, 60), "AI FILM STUDIO - PLACEHOLDER REF SHEET", fill=muted_color)
        draw.text((60, 100), f"TYPE: {asset_type.upper()}", fill=accent_color)
        draw.text((60, 140), f"ASSET NAME: {asset_name}", fill=text_color)
        
        # Wrap prompt text
        draw.text((60, 220), "GENERATION PROMPT:", fill=accent_color)
        
        # simple word wrap
        words = prompt.split()
        lines = []
        current_line = []
        for word in words:
            if len(" ".join(current_line + [word])) * 8 > (width - 120):
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                current_line.append(word)
        if current_line:
            lines.append(" ".join(current_line))
            
        y_offset = 260
        for line in lines[:20]: # Limit to 20 lines of prompt
            draw.text((60, y_offset), f"> {line}", fill=text_color)
            y_offset += 30
            
        # Draw status watermark
        draw.text((60, height - 80), "STATUS: OFFLINE MOCK / HF HUB CONNECTION TIMEOUT (FALLBACK)", fill=(255, 50, 80))
        
        # Save image
        image.save(output_path)
        print(f"[PLACEHOLDER CREATED] Saved mock image to: {output_path}")

    def _render_image(self, prompt: str, output_path: str, asset_name: str, asset_type: str, ref_image: str = None) -> None:
        """Render prompt using local FLUX diffusers pipeline or fallback placeholder."""
        try:
            import torch
            from PIL import Image, ImageDraw, ImageFont

            if self.mode == "placeholder":
                self._draw_placeholder(prompt, output_path, asset_name, asset_type)
                return

            if self.mode in ("local_flux", "sdxl_turbo", "sd_turbo"):
                # Try FLUX, SDXL-Turbo, or SD-Turbo
                try:
                    from diffusers import AutoPipelineForText2Image, FluxPipeline

                    hf_token = os.getenv("HF_TOKEN")
                    if self.pipeline is None:
                        if self.mode == "local_flux":
                            print(f"[*] Executing Local FLUX.1 Schnell generation...")
                            from diffusers import FluxTransformer2DModel
                            
                            print("[*] Loading Transformer in FP8 (float8_e4m3fn) to fit in 8GB VRAM...")
                            transformer = FluxTransformer2DModel.from_pretrained(
                                "black-forest-labs/FLUX.1-schnell",
                                subfolder="transformer",
                                torch_dtype=torch.float8_e4m3fn,
                                local_files_only=True
                            )
                            self.pipeline = FluxPipeline.from_pretrained(
                                "black-forest-labs/FLUX.1-schnell",
                                transformer=transformer,
                                torch_dtype=torch.bfloat16,
                                local_files_only=True
                            )
                            print("[*] Activating model CPU offloading...")
                            self.pipeline.enable_model_cpu_offload()
                        else:
                            model_name = "stabilityai/sdxl-turbo" if self.mode == "sdxl_turbo" else "stabilityai/sd-turbo"
                            print(f"[*] Loading and caching pipeline: {model_name}...")
                            self.pipeline = AutoPipelineForText2Image.from_pretrained(
                                model_name,
                                torch_dtype=torch.float16,
                                variant="fp16" if self.mode == "sdxl_turbo" else None,
                                local_files_only=True
                            ).to("cuda")

                    if ref_image and os.path.exists(ref_image):
                        try:
                            from diffusers import AutoPipelineForImage2Image, FluxImg2ImgPipeline
                            print(f"[*] Executing Image-to-Image character consistency using reference: {ref_image}...")
                            
                            ref_img = Image.open(ref_image).convert("RGB")
                            target_size = 1024 if self.mode in ("local_flux", "sdxl_turbo") else 512
                            ref_img = ref_img.resize((target_size, target_size), Image.Resampling.LANCZOS)
                            
                            if self.mode == "local_flux":
                                img_pipe = FluxImg2ImgPipeline.from_pipe(self.pipeline)
                            else:
                                img_pipe = AutoPipelineForImage2Image.from_pipe(self.pipeline)
                            
                            image = img_pipe(
                                prompt=prompt,
                                image=ref_img,
                                strength=0.7,
                                guidance_scale=0.0 if self.mode == "local_flux" else 0.0,
                                num_inference_steps=4 if self.mode == "local_flux" else 2,
                            ).images[0]
                            image.save(output_path)
                            print(f"[SUCCESS] Img2Img Character Asset saved: {output_path}")
                            return
                        except Exception as ex_img:
                            print(f"[!] Img2Img consistency generation failed ({ex_img}). Falling back to Text-to-Image.")

                    pipe = self.pipeline
                    image = pipe(
                        prompt,
                        guidance_scale=0.0 if self.mode == "local_flux" else 0.0,
                        num_inference_steps=4 if self.mode == "local_flux" else 2,
                    ).images[0]
                    image.save(output_path)
                    print(f"[SUCCESS] Asset saved: {output_path}")
                    return
                except Exception as ex:
                    print(f"[!] Local diffusion pipeline fallback ({ex}). Generating placeholder.")
                    self._draw_placeholder(prompt, output_path, asset_name, asset_type)
                    return

            if self.mode == "gemini":
                try:
                    from google import genai
                    from google.genai import types
                    
                    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("STITCH_GOOG_API_KEY")
                    if not api_key:
                        raise ValueError("Neither GEMINI_API_KEY nor STITCH_GOOG_API_KEY found in environment.")
                    
                    print(f"[*] Executing Google Gemini (Nano Banana / Imagen 3) generation...")
                    client = genai.Client(api_key=api_key)
                    
                    response = client.models.generate_images(
                        model='imagen-3.0-generate-002',
                        prompt=prompt,
                        config=types.GenerateImagesConfig(
                            number_of_images=1,
                            output_mime_type='image/png',
                            aspect_ratio="1:1" if asset_type == "character" else "16:9"
                        )
                    )
                    image_data = response.generated_images[0].image
                    image_data.save(output_path)
                    print(f"[SUCCESS] Gemini (Imagen 3) Asset saved: {output_path}")
                    return
                except Exception as ex_gem:
                    print(f"[!] Gemini generation failed ({ex_gem}). Falling back to placeholder.")
                    self._draw_placeholder(prompt, output_path, asset_name, asset_type)
                    return

            if self.mode == "api":
                fal_key = os.getenv("FAL_KEY")
                if fal_key and fal_key != "your_fal_ai_key":
                    import httpx
                    print(f"[*] Executing Fal.ai Cloud FLUX.1 Schnell generation...")
                    headers = {"Authorization": f"Key {fal_key}", "Content-Type": "application/json"}
                    payload = {"prompt": prompt, "image_size": "landscape_16_9", "num_inference_steps": 4}
                    with httpx.Client(timeout=60.0) as client:
                        res = client.post("https://fal.run/fal-ai/flux/schnell", headers=headers, json=payload)
                        if res.status_code == 200:
                            img_url = res.json()["images"][0]["url"]
                            img_bytes = client.get(img_url).content
                            with open(output_path, "wb") as f:
                                f.write(img_bytes)
                            print(f"[SUCCESS] Fal.ai FLUX Asset saved: {output_path}")
                            return
                        else:
                            print(f"[!] Fal.ai API Error ({res.status_code}): {res.text}")
                else:
                    print("[!] FAL_KEY not found or invalid in .env. Falling back to placeholder.")
                
                self._draw_placeholder(prompt, output_path, asset_name, asset_type)

        except Exception as e:
            print(f"[ERROR] Asset generation failed: {e}. Generating placeholder.")
            try:
                self._draw_placeholder(prompt, output_path, asset_name, asset_type)
            except Exception as e_inner:
                print(f"[CRITICAL ERROR] Failed to generate even a placeholder: {e_inner}")


def load_settings_dirs():
    char_dir = "assets/characters"
    loc_dir = "assets/locations"
    settings_path = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"
    if settings_path.exists():
        try:
            import yaml
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = yaml.safe_load(f)
                if settings and "paths" in settings:
                    char_dir = settings["paths"].get("characters_dir", char_dir)
                    loc_dir = settings["paths"].get("locations_dir", loc_dir)
        except Exception as e:
            print(f"[!] Warning: Failed to load config/settings.yaml: {e}")
    return char_dir, loc_dir


def main():
    default_char, default_loc = load_settings_dirs()
    
    parser = argparse.ArgumentParser(description="Auto-MV Pipeline Step 3: Visual Asset Generator")
    parser.add_argument("--manifest", type=str, default="output/assets_manifest.json", help="Path to assets_manifest.json")
    parser.add_argument("--mode", type=str, default="local_flux", choices=["local_flux", "sdxl_turbo", "sd_turbo", "gemini", "api", "placeholder"], help="Generation engine mode")
    parser.add_argument("--char-dir", type=str, default=default_char, help="Output directory for character sheets")
    parser.add_argument("--loc-dir", type=str, default=default_loc, help="Output directory for location keyframes")
    parser.add_argument("--ref-image", type=str, default=None, help="Reference image for character consistency (Image-to-Image)")
    parser.add_argument("--dry-run", action="store_true", help="Generate mock placeholder assets")

    args = parser.parse_args()

    if args.dry_run or not os.path.exists(args.manifest):
        print("[!] Running visual asset generator in --dry-run / placeholder mode.")
        manifest = {
            "characters": [
                {
                    "id": "character_main",
                    "name": "Main Singer",
                    "prompt": "4-view character sheet, cyberpunk aesthetic",
                    "output_filename": "character_main_sheet.png",
                }
            ],
            "locations": [
                {
                    "id": "location_sec_1",
                    "name": "Intro City",
                    "prompt": "Cyberpunk city street at night",
                    "output_filename": "location_sec_1.png",
                }
            ],
        }
    else:
        with open(args.manifest, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    gen = VisualAssetGenerator(
        mode="placeholder" if args.dry_run else args.mode,
        char_dir=args.char_dir,
        loc_dir=args.loc_dir,
        ref_image=args.ref_image
    )
    gen.generate_assets(manifest)

    print("[SUCCESS] All visual assets generated successfully!")


if __name__ == "__main__":
    main()
