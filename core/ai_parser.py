"""
AI-assisted media filename parser using OpenAI as fallback when
regex/TMDB recognition has low confidence.
"""

import json
import asyncio
from dataclasses import dataclass
from typing import Optional

from core.config import get_config


@dataclass
class AIParseResult:
    """Structured result returned by the AI parser."""

    title: str
    media_type: Optional[str] = None  # "movie" | "tv" | None
    year: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None


SYSTEM_PROMPT = (
    "You extract media metadata from messy file names of movies and TV "
    "series (often torrents). Always reply with a single compact JSON "
    "object and nothing else. Schema: "
    '{"title": string, "media_type": "movie"|"tv"|null, '
    '"year": string|null, "season": number|null, "episode": number|null}. '
    "Rules: title must be the canonical title in its original language "
    "without quality tags, language tags, release group, codec, year, "
    "or episode markers. Use null when a field cannot be determined. "
    "Year must be a 4-digit string. Do not invent values."
)


class AIParser:
    """OpenAI-based fallback parser for difficult filenames."""

    def __init__(self):
        self.config = get_config()
        self.openai_config = self.config.openai
        self.logger = self.config.logger
        self._client = None

        if self.openai_config.is_enabled:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(api_key=self.openai_config.api_key)
            except ImportError:
                self.logger.warning(
                    "openai package not installed; AI fallback disabled"
                )
            except Exception as e:
                self.logger.error(f"Failed to init OpenAI client: {e}")

    @property
    def is_available(self) -> bool:
        return self._client is not None

    async def parse(self, filename: str) -> Optional[AIParseResult]:
        """
        Ask the LLM to extract structured info from a filename.

        Returns None on any error or when the LLM cannot identify a title.
        """
        if not self.is_available:
            return None

        try:
            response = await asyncio.wait_for(
                self._client.chat.completions.create(
                    model=self.openai_config.model,
                    response_format={"type": "json_object"},
                    temperature=0,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": filename},
                    ],
                ),
                timeout=self.openai_config.timeout_seconds,
            )
        except asyncio.TimeoutError:
            self.logger.warning(f"OpenAI request timed out for: {filename}")
            return None
        except Exception as e:
            self.logger.error(f"OpenAI request failed: {e}")
            return None

        content = response.choices[0].message.content if response.choices else None
        if not content:
            return None

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            self.logger.warning(f"OpenAI returned non-JSON content: {content!r}")
            return None

        title = (data.get("title") or "").strip()
        if not title:
            return None

        media_type = data.get("media_type")
        if media_type not in ("movie", "tv", None):
            media_type = None

        year = data.get("year")
        if year is not None:
            year = str(year).strip() or None
            if year and (not year.isdigit() or len(year) != 4):
                year = None

        season = data.get("season")
        episode = data.get("episode")
        if not isinstance(season, int):
            season = None
        if not isinstance(episode, int):
            episode = None

        return AIParseResult(
            title=title,
            media_type=media_type,
            year=year,
            season=season,
            episode=episode,
        )
