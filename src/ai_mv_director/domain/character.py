"""
Character Bible & Domain Models for AI MV Director
Defines immutable character identities, wardrobe, traits, acting directions, references, and prompt compile logic.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from .ids import generate_character_id


@dataclass(frozen=True)
class CharacterRecord:
    character_id: str
    name: str
    age_range: str
    appearance: str
    wardrobe: str
    hairstyle: str
    physical_traits: str
    personality: str
    acting_direction: str
    voice_description: str = ""
    visual_references: List[str] = field(default_factory=list)
    negative_constraints: List[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        name: str,
        age_range: str,
        appearance: str,
        wardrobe: str,
        hairstyle: str = "",
        physical_traits: str = "",
        personality: str = "",
        acting_direction: str = "",
        voice_description: str = "",
        visual_references: Optional[List[str]] = None,
        negative_constraints: Optional[List[str]] = None,
    ) -> CharacterRecord:
        char_id = generate_character_id(name)
        return cls(
            character_id=char_id,
            name=name,
            age_range=age_range,
            appearance=appearance,
            wardrobe=wardrobe,
            hairstyle=hairstyle,
            physical_traits=physical_traits,
            personality=personality,
            acting_direction=acting_direction,
            voice_description=voice_description,
            visual_references=visual_references or [],
            negative_constraints=negative_constraints or [],
        )

    def compile_prompt_snippet(self) -> str:
        """Compile character specifications into a concise visual prompt snippet."""
        parts = [f"{self.name} ({self.age_range}, {self.appearance})"]
        if self.hairstyle:
            parts.append(f"hair: {self.hairstyle}")
        if self.wardrobe:
            parts.append(f"wearing: {self.wardrobe}")
        if self.acting_direction:
            parts.append(f"expression/acting: {self.acting_direction}")
        return ", ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CharacterBible:
    """Registry and query engine for project characters."""

    def __init__(self, characters: Optional[List[CharacterRecord]] = None):
        self._characters: Dict[str, CharacterRecord] = {}
        if characters:
            for char in characters:
                self.register(char)

    def register(self, character: CharacterRecord) -> None:
        self._characters[character.character_id] = character
        self._characters[character.name.lower()] = character

    def get(self, identifier: str) -> Optional[CharacterRecord]:
        return self._characters.get(identifier) or self._characters.get(identifier.lower())

    def list_all(self) -> List[CharacterRecord]:
        # Return unique records
        seen = set()
        unique = []
        for c in self._characters.values():
            if c.character_id not in seen:
                seen.add(c.character_id)
                unique.append(c)
        return unique

    def compile_shot_characters(self, character_names: List[str]) -> str:
        """Compile all referenced characters into shot-level prompt descriptors."""
        snippets = []
        for name in character_names:
            char = self.get(name)
            if char:
                snippets.append(char.compile_prompt_snippet())
            else:
                snippets.append(name)
        return " | ".join(snippets)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "characters": [c.to_dict() for c in self.list_all()]
        }
