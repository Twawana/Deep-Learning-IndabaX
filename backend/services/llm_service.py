"""
Gemini Service

Responsible for communicating with the Gemini API.
"""

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException
from google import genai
from google.genai import types

from prompts.system_prompt import SYSTEM_PROMPT
from schemas.pasture_data import PastureData
from schemas.weather_data import WeatherData
from schemas.recommendation_response import RecommendationResponse
from utils.prompt_builder import build_prompt

# Configure logger
logger = logging.getLogger(__name__)


class GeminiService:
    """
    Handles all communication with the Gemini API.
    """

    def __init__(self):
        """
        Initializes the Gemini client.
        """

        # Load environment variables
        load_dotenv(Path(__file__).resolve().parent.parent / ".env")

        gemini_api_key = os.getenv("GEMINI_API_KEY")

        if not gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY was not found in the environment variables."
            )

        self.client = genai.Client(api_key=gemini_api_key)

        # Current Gemini model
        self.model_name = "gemini-flash-latest"

    def generate_recommendation(
        self,
        farmer_question: str,
        pasture_data: PastureData,
        weather_data: WeatherData,
    ) -> RecommendationResponse:
        """
        Generates a grazing recommendation using Gemini.
        """

        prompt = build_prompt(
            farmer_question=farmer_question,
            pasture_data=pasture_data,
            weather_data=weather_data,
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                ),
            )

            if not response.text:
                logger.error("Gemini returned an empty response.")

                raise HTTPException(
                    status_code=500,
                    detail="Gemini returned an empty response.",
                )

            try:
                data = json.loads(response.text)

            except json.JSONDecodeError:
                logger.exception("Gemini returned invalid JSON.")

                raise HTTPException(
                    status_code=500,
                    detail="Gemini returned invalid JSON.",
                )

            recommendation = RecommendationResponse(**data)

            return recommendation

        except HTTPException:
            raise

        except Exception as e:
            logger.exception("Unexpected error while communicating with Gemini.")

            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate recommendation: {str(e)}",
            )