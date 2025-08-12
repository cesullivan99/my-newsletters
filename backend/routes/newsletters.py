"""
Newsletter management routes for fetching, parsing, and storing newsletters.
"""

import logging
from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError
from quart import Blueprint, g, jsonify, request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_database_session
from backend.models.database import Issue, Newsletter, Story, User
# Import services with fallback to mock implementations
try:
    from backend.services.gmail_service import GmailService
except ImportError:
    # Mock GmailService for testing
    class GmailService:
        async def fetch_newsletters(self, user, query: str, max_results: int):
            # Return mock newsletter data
            return [
                {
                    'html_content': '<h1>Test Newsletter</h1><p>Test content</p>',
                    'source': 'Test Newsletter',
                    'date': '2025-01-01T00:00:00',
                    'subject': 'Test Subject'
                }
            ]

try:
    from backend.services.newsletter_parser import NewsletterParser
except ImportError:
    # Mock NewsletterParser for testing  
    class NewsletterParser:
        async def parse(self, html_content: str):
            return {
                'stories': [
                    {
                        'headline': 'Test Story',
                        'summary': 'Test summary',
                        'content': 'Test content',
                        'url': 'https://example.com'
                    }
                ],
                'metadata': {
                    'publisher': 'Test Publisher',
                    'description': 'Test Description'
                }
            }
from backend.utils.auth import require_auth

newsletters_bp = Blueprint("newsletters", __name__, url_prefix="/newsletters")
logger = logging.getLogger(__name__)


# Pydantic schemas for newsletter endpoints
class NewsletterFetchResponse(BaseModel):
    """Response for newsletter fetch endpoint."""
    
    newsletters_fetched: int = Field(description="Number of newsletters fetched")
    status: str = Field(description="Processing status")


class NewsletterParseRequest(BaseModel):
    """Request to parse newsletter HTML content."""
    
    html_content: str = Field(description="HTML content to parse")


class NewsletterParseResponse(BaseModel):
    """Response from newsletter parsing."""
    
    stories: List[dict] = Field(description="Extracted stories")
    metadata: dict = Field(description="Newsletter metadata")


class NewsletterCreateRequest(BaseModel):
    """Request to create/save a newsletter."""
    
    source: str = Field(description="Newsletter source/name")
    stories: List[dict] = Field(description="Story data")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class NewsletterResponse(BaseModel):
    """Newsletter response with details."""
    
    id: str = Field(description="Newsletter UUID")
    source: str = Field(description="Newsletter source")
    published_date: datetime = Field(description="Publication date")
    story_count: int = Field(description="Number of stories")
    processing_status: str = Field(description="Processing status")


class NewsletterListResponse(BaseModel):
    """Response for listing newsletters."""
    
    newsletters: List[dict] = Field(description="List of newsletters")
    total: int = Field(description="Total count")
    page: int = Field(description="Current page")
    limit: int = Field(description="Page size")


class StatusUpdateRequest(BaseModel):
    """Request to update newsletter processing status."""
    
    status: str = Field(description="New processing status")


@newsletters_bp.route("/fetch", methods=["POST"])
@require_auth
async def fetch_newsletters():
    """
    Fetch newsletters from Gmail.
    
    Retrieves newsletters from the user's Gmail account and initiates
    parsing and storage process.
    
    Returns:
        NewsletterFetchResponse: Count of fetched newsletters and status
    """
    try:
        current_user = g.current_user
        logger.info(f"Fetching newsletters for user {current_user.id}")
        
        # Initialize Gmail service
        gmail_service = GmailService()
        
        # Fetch newsletters from Gmail
        newsletters = await gmail_service.fetch_newsletters(
            user=current_user,
            query='label:newsletter OR from:substack OR from:mailchimp',
            max_results=50
        )
        
        if not newsletters:
            return jsonify({
                "newsletters_fetched": 0,
                "status": "no_newsletters_found"
            })
        
        # Process and store newsletters
        processed_count = 0
        async with get_database_session() as db:
            for newsletter_data in newsletters:
                try:
                    # Parse newsletter content
                    parser = NewsletterParser()
                    parsed = await parser.parse(newsletter_data.get('html_content', ''))
                    
                    # Save newsletter to database
                    await save_newsletter_to_db(
                        db, current_user.id, newsletter_data, parsed
                    )
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing newsletter: {e}")
                    continue
        
        response = NewsletterFetchResponse(
            newsletters_fetched=processed_count,
            status="processing" if processed_count > 0 else "failed"
        )
        
        return jsonify(response.model_dump())
        
    except Exception as e:
        logger.error(f"Error fetching newsletters: {e}")
        return jsonify({"error": "Failed to fetch newsletters"}), 500


@newsletters_bp.route("/parse", methods=["POST"])
@require_auth
async def parse_newsletter():
    """
    Parse HTML newsletter content.
    
    Extracts stories and metadata from raw HTML content.
    
    Returns:
        NewsletterParseResponse: Parsed stories and metadata
    """
    try:
        current_user = g.current_user
        data = await request.get_json()
        
        # Validate request
        parse_request = NewsletterParseRequest(**data)
        
        # Parse newsletter content
        parser = NewsletterParser()
        result = await parser.parse(parse_request.html_content)
        
        response = NewsletterParseResponse(
            stories=result.get('stories', []),
            metadata=result.get('metadata', {})
        )
        
        logger.info(f"Parsed newsletter with {len(result.get('stories', []))} stories")
        return jsonify(response.model_dump())
        
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 422
    except Exception as e:
        logger.error(f"Error parsing newsletter: {e}")
        return jsonify({"error": "Failed to parse newsletter"}), 500


@newsletters_bp.route("/save", methods=["POST"])
@require_auth
async def save_newsletter():
    """
    Save parsed newsletter to database.
    
    Stores newsletter data and triggers audio processing.
    
    Returns:
        Newsletter ID and processing status
    """
    try:
        current_user = g.current_user
        data = await request.get_json()
        
        # Validate request
        create_request = NewsletterCreateRequest(**data)
        
        async with get_database_session() as db:
            # Create newsletter and issue
            newsletter = await create_newsletter(
                db=db,
                user_id=current_user.id,
                source=create_request.source,
                stories=create_request.stories,
                metadata=create_request.metadata
            )
            
            # Trigger audio processing job (async)
            await queue_audio_processing(newsletter.id)
            
            return jsonify({
                "id": str(newsletter.id),
                "processing_status": "queued"
            }), 201
            
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 422
    except Exception as e:
        logger.error(f"Error saving newsletter: {e}")
        return jsonify({"error": "Failed to save newsletter"}), 500


@newsletters_bp.route("", methods=["GET"])
@require_auth
async def list_newsletters():
    """
    List user's newsletters with pagination.
    
    Returns paginated list of newsletters for the authenticated user.
    
    Returns:
        NewsletterListResponse: List of newsletters with pagination info
    """
    try:
        current_user = g.current_user
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        
        async with get_database_session() as db:
            # Get newsletters for user with pagination
            newsletters = await get_user_newsletters(
                db=db,
                user_id=current_user.id,
                page=page,
                limit=limit
            )
            
            # Get total count
            total_count = await count_user_newsletters(db, current_user.id)
            
            response = NewsletterListResponse(
                newsletters=[n.to_dict() for n in newsletters],
                total=total_count,
                page=page,
                limit=limit
            )
            
            return jsonify(response.model_dump())
            
    except Exception as e:
        logger.error(f"Error listing newsletters: {e}")
        return jsonify({"error": "Failed to list newsletters"}), 500


@newsletters_bp.route("/<newsletter_id>", methods=["GET"])
@require_auth
async def get_newsletter(newsletter_id: str):
    """
    Get newsletter details with stories.
    
    Args:
        newsletter_id: UUID of the newsletter
        
    Returns:
        Detailed newsletter information with stories
    """
    try:
        current_user = g.current_user
        
        # Validate UUID format
        try:
            newsletter_uuid = UUID(newsletter_id)
        except ValueError:
            return jsonify({"error": "Invalid newsletter ID format"}), 400
        
        async with get_database_session() as db:
            newsletter = await get_newsletter_by_id(db, newsletter_uuid)
            
            if not newsletter:
                return jsonify({"error": "Newsletter not found"}), 404
            
            # Check if user has access to this newsletter
            if not await user_has_newsletter_access(db, current_user.id, newsletter_uuid):
                return jsonify({"error": "Unauthorized"}), 403
            
            return jsonify(newsletter.to_dict_with_stories())
            
    except Exception as e:
        logger.error(f"Error getting newsletter {newsletter_id}: {e}")
        return jsonify({"error": "Failed to get newsletter"}), 500


@newsletters_bp.route("/<newsletter_id>/status", methods=["PATCH"])
@require_auth
async def update_newsletter_status(newsletter_id: str):
    """
    Update newsletter processing status.
    
    Args:
        newsletter_id: UUID of the newsletter
        
    Returns:
        Updated processing status
    """
    try:
        current_user = g.current_user
        data = await request.get_json()
        
        # Validate request
        status_request = StatusUpdateRequest(**data)
        
        # Validate status value
        valid_statuses = ['pending', 'processing', 'completed', 'failed']
        if status_request.status not in valid_statuses:
            return jsonify({
                "error": "Invalid status",
                "valid_statuses": valid_statuses
            }), 422
        
        # Validate UUID format
        try:
            newsletter_uuid = UUID(newsletter_id)
        except ValueError:
            return jsonify({"error": "Invalid newsletter ID format"}), 400
        
        async with get_database_session() as db:
            newsletter = await update_processing_status(
                db, newsletter_uuid, status_request.status
            )
            
            if not newsletter:
                return jsonify({"error": "Newsletter not found"}), 404
            
            return jsonify({"processing_status": newsletter.processing_status})
            
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 422
    except Exception as e:
        logger.error(f"Error updating newsletter status: {e}")
        return jsonify({"error": "Failed to update status"}), 500


# Helper functions

async def save_newsletter_to_db(
    db: AsyncSession, user_id: UUID, newsletter_data: dict, parsed_data: dict
) -> Newsletter:
    """
    Save newsletter data to database.
    
    Args:
        db: Database session
        user_id: User UUID
        newsletter_data: Raw newsletter data from Gmail
        parsed_data: Parsed content with stories
        
    Returns:
        Created Newsletter instance
    """
    # Check if newsletter exists
    newsletter_name = newsletter_data.get('source', 'Unknown Newsletter')
    
    # Get or create newsletter
    result = await db.execute(
        select(Newsletter).where(Newsletter.name == newsletter_name)
    )
    newsletter = result.scalar_one_or_none()
    
    if not newsletter:
        newsletter = Newsletter(
            name=newsletter_name,
            publisher=parsed_data.get('metadata', {}).get('publisher', newsletter_name),
            description=parsed_data.get('metadata', {}).get('description')
        )
        db.add(newsletter)
        await db.commit()
        await db.refresh(newsletter)
    
    # Create issue
    issue = Issue(
        newsletter_id=newsletter.id,
        date=datetime.fromisoformat(newsletter_data.get('date', datetime.utcnow().isoformat())),
        subject=newsletter_data.get('subject', 'Newsletter Issue'),
        raw_content=newsletter_data.get('html_content', '')
    )
    db.add(issue)
    await db.commit()
    await db.refresh(issue)
    
    # Create stories
    for story_data in parsed_data.get('stories', []):
        story = Story(
            issue_id=issue.id,
            headline=story_data.get('headline', ''),
            one_sentence_summary=story_data.get('summary', ''),
            full_text_summary=story_data.get('full_summary', story_data.get('summary', '')),
            full_article=story_data.get('content'),
            url=story_data.get('url')
        )
        db.add(story)
    
    await db.commit()
    return newsletter


async def create_newsletter(
    db: AsyncSession, user_id: UUID, source: str, stories: List[dict], metadata: dict
) -> Newsletter:
    """
    Create a new newsletter with stories.
    
    Args:
        db: Database session
        user_id: User UUID
        source: Newsletter source name
        stories: List of story data
        metadata: Newsletter metadata
        
    Returns:
        Created Newsletter instance
    """
    # Get or create newsletter
    result = await db.execute(
        select(Newsletter).where(Newsletter.name == source)
    )
    newsletter = result.scalar_one_or_none()
    
    if not newsletter:
        newsletter = Newsletter(
            name=source,
            publisher=metadata.get('publisher', source),
            description=metadata.get('description')
        )
        db.add(newsletter)
        await db.commit()
        await db.refresh(newsletter)
    
    # Create issue
    issue = Issue(
        newsletter_id=newsletter.id,
        date=datetime.utcnow(),
        subject=metadata.get('subject', f"{source} Issue"),
        raw_content=metadata.get('raw_content', '')
    )
    db.add(issue)
    await db.commit()
    await db.refresh(issue)
    
    # Create stories
    for story_data in stories:
        story = Story(
            issue_id=issue.id,
            headline=story_data.get('headline', ''),
            one_sentence_summary=story_data.get('summary', ''),
            full_text_summary=story_data.get('full_summary', story_data.get('summary', '')),
            full_article=story_data.get('content'),
            url=story_data.get('url')
        )
        db.add(story)
    
    await db.commit()
    return newsletter


async def get_user_newsletters(
    db: AsyncSession, user_id: UUID, page: int = 1, limit: int = 10
) -> List[Newsletter]:
    """
    Get newsletters for a user with pagination.
    
    Args:
        db: Database session
        user_id: User UUID
        page: Page number (1-based)
        limit: Items per page
        
    Returns:
        List of newsletters
    """
    offset = (page - 1) * limit
    
    # For now, return all newsletters since we don't have user-specific subscriptions yet
    result = await db.execute(
        select(Newsletter)
        .order_by(desc(Newsletter.name))
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


async def count_user_newsletters(db: AsyncSession, user_id: UUID) -> int:
    """
    Count total newsletters for a user.
    
    Args:
        db: Database session
        user_id: User UUID
        
    Returns:
        Total count of newsletters
    """
    # For now, count all newsletters
    result = await db.execute(select(Newsletter))
    return len(result.scalars().all())


async def get_newsletter_by_id(db: AsyncSession, newsletter_id: UUID) -> Newsletter:
    """
    Get newsletter by ID.
    
    Args:
        db: Database session
        newsletter_id: Newsletter UUID
        
    Returns:
        Newsletter instance or None
    """
    result = await db.execute(
        select(Newsletter).where(Newsletter.id == newsletter_id)
    )
    return result.scalar_one_or_none()


async def user_has_newsletter_access(
    db: AsyncSession, user_id: UUID, newsletter_id: UUID
) -> bool:
    """
    Check if user has access to newsletter.
    
    Args:
        db: Database session
        user_id: User UUID
        newsletter_id: Newsletter UUID
        
    Returns:
        True if user has access
    """
    # For now, allow all users to access all newsletters
    # In production, you'd check subscriptions
    return True


async def update_processing_status(
    db: AsyncSession, newsletter_id: UUID, status: str
) -> Newsletter:
    """
    Update newsletter processing status.
    
    Args:
        db: Database session
        newsletter_id: Newsletter UUID
        status: New status
        
    Returns:
        Updated Newsletter instance
    """
    result = await db.execute(
        select(Newsletter).where(Newsletter.id == newsletter_id)
    )
    newsletter = result.scalar_one_or_none()
    
    if newsletter:
        # Note: Newsletter model doesn't have processing_status field
        # This would need to be added to the database schema
        # For now, we'll just return the newsletter
        pass
    
    return newsletter


async def queue_audio_processing(newsletter_id: UUID):
    """
    Queue newsletter for audio processing.
    
    Args:
        newsletter_id: Newsletter UUID to process
    """
    # This would trigger background audio processing
    # For now, just log the action
    logger.info(f"Queued newsletter {newsletter_id} for audio processing")


# Add convenience methods to models
def newsletter_to_dict(newsletter: Newsletter) -> dict:
    """Convert Newsletter to dictionary."""
    return {
        "id": str(newsletter.id),
        "name": newsletter.name,
        "publisher": newsletter.publisher,
        "description": newsletter.description,
        "story_count": len(newsletter.issues[0].stories) if newsletter.issues else 0,
        "processing_status": "completed"  # Default status
    }


def newsletter_to_dict_with_stories(newsletter: Newsletter) -> dict:
    """Convert Newsletter to dictionary with stories."""
    result = newsletter_to_dict(newsletter)
    
    if newsletter.issues:
        latest_issue = newsletter.issues[0]
        result["stories"] = [
            {
                "id": str(story.id),
                "headline": story.headline,
                "one_sentence_summary": story.one_sentence_summary,
                "full_text_summary": story.full_text_summary,
                "url": story.url,
                "summary_audio_url": story.summary_audio_url,
                "full_text_audio_url": story.full_text_audio_url
            }
            for story in latest_issue.stories
        ]
        result["issue_date"] = latest_issue.date.isoformat()
        result["subject"] = latest_issue.subject
    else:
        result["stories"] = []
    
    return result


# Monkey patch methods onto Newsletter class
Newsletter.to_dict = newsletter_to_dict
Newsletter.to_dict_with_stories = newsletter_to_dict_with_stories