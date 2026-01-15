"""Job description extraction and parsing.

This module provides functionality for extracting structured job description
data from job posting URLs using Browser Use with LLM-based extraction.

Public API:
    - JobExtractor: Main service class for job extraction
    - JobDescription: Pydantic model for extracted job data
    - ExtractorConfig: Configuration settings for the extractor
    - get_extractor_config: Get the extractor configuration singleton
"""

from src.extractor.config import ExtractorConfig, get_extractor_config
from src.extractor.models import JobDescription
from src.extractor.service import JobExtractor

__all__ = [
    "JobExtractor",
    "JobDescription",
    "ExtractorConfig",
    "get_extractor_config",
]
