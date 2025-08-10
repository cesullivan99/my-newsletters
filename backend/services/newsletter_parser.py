"""
Newsletter parsing service for extracting stories from email content.

Provides HTML parsing, story extraction, and content summarization
using OpenAI for natural language processing.
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import aiohttp
import openai
from bs4 import BeautifulSoup
from openai import AsyncOpenAI

from ..config import get_config

logger = logging.getLogger(__name__)
config = get_config()


class NewsletterParser:
    """
    Newsletter content parser and story extractor.
    
    Parses HTML newsletter content, identifies individual stories,
    and creates summaries for audio briefing.
    """

    def __init__(self):
        """Initialize newsletter parser with OpenAI client."""
        self.openai_client = AsyncOpenAI(api_key=config.openai_api_key)
        self.max_stories_per_newsletter = 15  # Limit to prevent excessive processing
        self.min_story_length = 50  # Minimum characters for a valid story

    async def parse_newsletter_content(self, email_data: Dict) -> Dict:
        """
        Parse newsletter email into structured stories.
        
        Args:
            email_data: Email data from Gmail service.
            
        Returns:
            Parsed newsletter with stories and metadata.
        """
        try:
            # Extract newsletter metadata
            newsletter_info = {
                "email_id": email_data["id"],
                "subject": email_data["subject"],
                "sender_name": email_data.get("sender_name", ""),
                "sender_email": email_data.get("sender_email", ""),
                "date": datetime.fromtimestamp(email_data["received_timestamp"]),
                "raw_content": email_data.get("body_html", "") or email_data.get("body_text", ""),
                "stories": [],
            }
            
            # Parse HTML content
            soup = BeautifulSoup(newsletter_info["raw_content"], "html.parser")
            
            # Clean up the HTML
            cleaned_content = await self._clean_html_content(soup)
            
            # Extract story candidates
            story_candidates = await self._extract_story_candidates(cleaned_content, soup)
            
            # Filter and validate stories
            valid_stories = await self._filter_valid_stories(story_candidates)
            
            # Limit number of stories
            if len(valid_stories) > self.max_stories_per_newsletter:
                logger.info(f"Limiting stories to {self.max_stories_per_newsletter} from {len(valid_stories)}")
                valid_stories = valid_stories[:self.max_stories_per_newsletter]
            
            # Generate summaries for each story
            for i, story_text in enumerate(valid_stories):
                try:
                    story_data = await self._create_story_summaries(story_text, i)
                    if story_data:
                        newsletter_info["stories"].append(story_data)
                except Exception as e:
                    logger.error(f"Failed to create summaries for story {i}: {e}")
                    continue
            
            # Identify newsletter publisher if not already set
            if not newsletter_info["sender_name"]:
                newsletter_info["sender_name"] = await self._identify_publisher(soup)
            
            logger.info(f"Successfully parsed newsletter with {len(newsletter_info['stories'])} stories")
            return newsletter_info
            
        except Exception as e:
            logger.error(f"Failed to parse newsletter content: {e}")
            raise

    async def _clean_html_content(self, soup: BeautifulSoup) -> str:
        """
        Clean HTML content by removing unwanted elements.
        
        Args:
            soup: BeautifulSoup parsed HTML.
            
        Returns:
            Cleaned text content.
        """
        # Remove unwanted elements
        unwanted_tags = ['script', 'style', 'head', 'meta', 'link', 'noscript']
        for tag in unwanted_tags:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Remove common newsletter navigation/footer elements
        unwanted_classes = [
            'footer', 'header', 'navigation', 'nav', 'unsubscribe', 
            'social', 'share', 'advertisement', 'ad', 'sponsor'
        ]
        
        for class_name in unwanted_classes:
            for element in soup.find_all(class_=re.compile(class_name, re.I)):
                element.decompose()
        
        # Remove elements with common newsletter footer text
        footer_patterns = [
            r'unsubscribe', r'manage.*preferences', r'view.*browser',
            r'forward.*friend', r'social.*media', r'copyright.*\d{4}'
        ]
        
        for pattern in footer_patterns:
            for element in soup.find_all(text=re.compile(pattern, re.I)):
                if element.parent:
                    element.parent.decompose()
        
        return soup.get_text()

    async def _extract_story_candidates(self, cleaned_text: str, soup: BeautifulSoup) -> List[str]:
        """
        Extract potential story sections from newsletter content.
        
        Args:
            cleaned_text: Cleaned text content.
            soup: Original BeautifulSoup object for structure analysis.
            
        Returns:
            List of story candidate texts.
        """
        story_candidates = []
        
        # Method 1: Look for structured HTML sections
        structural_candidates = await self._extract_by_structure(soup)
        story_candidates.extend(structural_candidates)
        
        # Method 2: Split by common newsletter patterns
        pattern_candidates = await self._extract_by_patterns(cleaned_text)
        story_candidates.extend(pattern_candidates)
        
        # Method 3: Use AI to identify story boundaries
        if len(story_candidates) < 2:  # Only if other methods didn't work well
            ai_candidates = await self._extract_by_ai_analysis(cleaned_text)
            story_candidates.extend(ai_candidates)
        
        return story_candidates

    async def _extract_by_structure(self, soup: BeautifulSoup) -> List[str]:
        """Extract stories using HTML structure analysis."""
        stories = []
        
        # Look for common newsletter structures
        selectors = [
            'article', '.story', '.article', '.news-item', '.newsletter-story',
            '.content-block', '.story-block', 'section', '.post', '.item',
            'div[class*="story"]', 'div[class*="article"]', 'div[class*="news"]'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text().strip()
                if len(text) > self.min_story_length:
                    stories.append(text)
        
        # Look for repeated table structures (common in email newsletters)
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) > 1:  # Skip single-row tables (likely layout)
                for row in rows:
                    text = row.get_text().strip()
                    if len(text) > self.min_story_length:
                        stories.append(text)
        
        return stories

    async def _extract_by_patterns(self, text: str) -> List[str]:
        """Extract stories using text pattern analysis."""
        stories = []
        
        # Split on common newsletter separators
        separators = [
            r'\n\s*[-=_]{3,}\s*\n',  # Horizontal separators
            r'\n\s*\*{3,}\s*\n',     # Star separators
            r'\n\s*#{2,}[^#\n]*#{2,}\s*\n',  # Header patterns
            r'\n\s*\d+\.\s+',        # Numbered lists
            r'\n\s*[••·]\s+',        # Bullet points
        ]
        
        split_text = text
        for separator in separators:
            parts = re.split(separator, split_text)
            if len(parts) > 1:
                for part in parts:
                    cleaned_part = part.strip()
                    if len(cleaned_part) > self.min_story_length:
                        stories.append(cleaned_part)
                break  # Use the first successful separator
        
        # If no separators worked, try paragraph-based splitting
        if not stories:
            paragraphs = text.split('\n\n')
            current_story = ""
            
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if not paragraph:
                    continue
                
                current_story += paragraph + "\n\n"
                
                # End story if paragraph seems like a conclusion
                if any(ending in paragraph.lower() for ending in 
                       ['read more', 'learn more', 'continue reading', 'full article']):
                    if len(current_story.strip()) > self.min_story_length:
                        stories.append(current_story.strip())
                    current_story = ""
            
            # Add remaining content as final story
            if current_story.strip() and len(current_story.strip()) > self.min_story_length:
                stories.append(current_story.strip())
        
        return stories

    async def _extract_by_ai_analysis(self, text: str) -> List[str]:
        """Use AI to identify and split story boundaries."""
        try:
            prompt = f"""
            Analyze this newsletter content and identify individual news stories or articles.
            Split the content into separate stories, maintaining the original text.
            
            Return only the stories as a JSON array of strings, with each story as a complete text block.
            Do not include headers, footers, advertisements, or subscription information.
            
            Newsletter content:
            {text[:4000]}  # Limit input to avoid token limits
            """
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2000
            )
            
            # Parse JSON response
            import json
            stories = json.loads(response.choices[0].message.content)
            
            # Validate stories
            valid_stories = []
            for story in stories:
                if isinstance(story, str) and len(story.strip()) > self.min_story_length:
                    valid_stories.append(story.strip())
            
            return valid_stories
            
        except Exception as e:
            logger.error(f"AI story extraction failed: {e}")
            return []

    async def _filter_valid_stories(self, candidates: List[str]) -> List[str]:
        """Filter story candidates to keep only valid stories."""
        valid_stories = []
        seen_stories = set()
        
        for candidate in candidates:
            # Skip very short content
            if len(candidate) < self.min_story_length:
                continue
            
            # Skip duplicates (using first 100 characters as key)
            key = candidate[:100].lower().strip()
            if key in seen_stories:
                continue
            seen_stories.add(key)
            
            # Skip if it's mostly navigation/footer content
            if await self._is_navigation_content(candidate):
                continue
            
            # Skip if it doesn't have story-like characteristics
            if not await self._has_story_characteristics(candidate):
                continue
            
            valid_stories.append(candidate)
        
        return valid_stories

    async def _is_navigation_content(self, text: str) -> bool:
        """Check if text is likely navigation or footer content."""
        text_lower = text.lower()
        
        # Navigation/footer indicators
        nav_indicators = [
            'unsubscribe', 'manage preferences', 'view in browser',
            'forward to friend', 'social media', 'follow us',
            'privacy policy', 'terms of service', 'copyright',
            'all rights reserved', 'mailing address'
        ]
        
        # Count indicators
        indicator_count = sum(1 for indicator in nav_indicators if indicator in text_lower)
        
        # If more than 2 indicators or text is very short with indicators, it's likely navigation
        return indicator_count > 2 or (len(text) < 200 and indicator_count > 0)

    async def _has_story_characteristics(self, text: str) -> bool:
        """Check if text has characteristics of a news story."""
        # Must have some sentence structure
        sentence_count = len([s for s in text.split('.') if len(s.strip()) > 10])
        if sentence_count < 2:
            return False
        
        # Should have some narrative elements
        narrative_words = [
            'said', 'according', 'reported', 'announced', 'revealed',
            'discovered', 'found', 'shows', 'indicates', 'suggests'
        ]
        
        has_narrative = any(word in text.lower() for word in narrative_words)
        
        # Should have reasonable word count
        word_count = len(text.split())
        has_good_length = 20 <= word_count <= 1000
        
        return has_narrative or has_good_length

    async def _create_story_summaries(self, story_text: str, index: int) -> Optional[Dict]:
        """
        Create headline and summaries for a story using OpenAI.
        
        Args:
            story_text: Raw story text.
            index: Story index for tracking.
            
        Returns:
            Story data with headline and summaries.
        """
        try:
            # Generate headline and summaries
            prompt = f"""
            Given this news story text, create:
            1. A clear, engaging headline (max 80 characters)
            2. A one-sentence summary (max 150 characters)
            3. A detailed summary for audio reading (2-3 sentences, conversational tone)
            
            Return as JSON with keys: "headline", "one_sentence_summary", "full_text_summary"
            
            Story text:
            {story_text[:2000]}  # Limit input
            """
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300
            )
            
            # Parse response
            import json
            summaries = json.loads(response.choices[0].message.content)
            
            # Extract URLs if present
            url_match = re.search(r'https?://[^\s<>"]+', story_text)
            story_url = url_match.group(0) if url_match else None
            
            return {
                "index": index,
                "headline": summaries.get("headline", f"Story {index + 1}")[:80],
                "one_sentence_summary": summaries.get("one_sentence_summary", "")[:150],
                "full_text_summary": summaries.get("full_text_summary", ""),
                "full_article": story_text,
                "url": story_url,
            }
            
        except Exception as e:
            logger.error(f"Failed to create summaries for story {index}: {e}")
            
            # Fallback: Create basic summaries
            return {
                "index": index,
                "headline": f"Story {index + 1}",
                "one_sentence_summary": story_text[:150] + "...",
                "full_text_summary": story_text[:500] + "...",
                "full_article": story_text,
                "url": None,
            }

    async def _identify_publisher(self, soup: BeautifulSoup) -> str:
        """Identify newsletter publisher from HTML content."""
        # Look for common publisher indicators
        selectors = [
            'title', '.publisher', '.sender', '.from', '.brand',
            '[class*="brand"]', '[class*="publisher"]'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text().strip()
                if text and len(text) < 100:  # Reasonable publisher name length
                    return text
        
        # Fallback: Extract from domain or first meaningful text
        return "Unknown Publisher"

    async def identify_newsletter_type(self, newsletter_info: Dict) -> str:
        """
        Identify the type/category of newsletter.
        
        Args:
            newsletter_info: Parsed newsletter information.
            
        Returns:
            Newsletter category/type.
        """
        try:
            # Analyze content to determine type
            content_sample = " ".join([
                newsletter_info.get("subject", ""),
                newsletter_info.get("sender_name", ""),
                " ".join([story["headline"] for story in newsletter_info.get("stories", [])])
            ])
            
            prompt = f"""
            Analyze this newsletter content and identify its primary category.
            Choose from: technology, business, politics, health, science, entertainment, sports, general_news
            
            Return only the category name.
            
            Content: {content_sample[:1000]}
            """
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=50
            )
            
            category = response.choices[0].message.content.strip().lower()
            
            # Validate category
            valid_categories = [
                'technology', 'business', 'politics', 'health', 'science',
                'entertainment', 'sports', 'general_news'
            ]
            
            return category if category in valid_categories else 'general_news'
            
        except Exception as e:
            logger.error(f"Failed to identify newsletter type: {e}")
            return 'general_news'


# Service instance
newsletter_parser = NewsletterParser()


def get_newsletter_parser() -> NewsletterParser:
    """Get newsletter parser instance."""
    return newsletter_parser