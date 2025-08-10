"""
Gmail API integration service for newsletter email ingestion.

Provides OAuth 2.0 authentication, email fetching, and newsletter parsing
with rate limiting and error handling.
"""

import asyncio
import base64
import json
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Tuple

import aiohttp
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..config import get_config

logger = logging.getLogger(__name__)
config = get_config()


class GmailService:
    """
    Gmail API service for newsletter email management.
    
    Handles OAuth 2.0 authentication, token refresh, and email fetching
    with proper rate limiting and error handling.
    """

    def __init__(self):
        """Initialize Gmail service with configuration."""
        self.client_id = config.gmail_client_id
        self.client_secret = config.gmail_client_secret
        self.redirect_uri = config.gmail_redirect_uri
        self.scopes = config.get_gmail_scopes()
        self.rate_limit = config.gmail_api_rate_limit
        
        # Rate limiting state
        self._requests_made = 0
        self._window_start = datetime.utcnow()
        self._request_lock = asyncio.Lock()

    async def get_authorization_url(self) -> str:
        """
        Generate Gmail OAuth 2.0 authorization URL.
        
        Returns:
            Authorization URL for user to visit.
        """
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri],
                    }
                },
                scopes=self.scopes,
            )
            flow.redirect_uri = self.redirect_uri
            
            authorization_url, _ = flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                prompt="consent",  # Force consent to get refresh token
            )
            
            logger.info("Generated Gmail authorization URL")
            return authorization_url
            
        except Exception as e:
            logger.error(f"Failed to generate authorization URL: {e}")
            raise

    async def exchange_code_for_tokens(self, authorization_code: str) -> Dict[str, str]:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            authorization_code: OAuth 2.0 authorization code from callback.
            
        Returns:
            Token information including access_token, refresh_token, expires_in.
            
        Raises:
            ValueError: If token exchange fails.
        """
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri],
                    }
                },
                scopes=self.scopes,
            )
            flow.redirect_uri = self.redirect_uri
            
            # Exchange code for tokens
            flow.fetch_token(code=authorization_code)
            credentials = flow.credentials
            
            # Get user email
            service = build("gmail", "v1", credentials=credentials)
            profile = service.users().getProfile(userId="me").execute()
            
            token_info = {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "expires_in": 3600,  # Default to 1 hour
                "user_email": profile.get("emailAddress"),
                "scopes": credentials.scopes,
            }
            
            logger.info(f"Successfully exchanged code for tokens for user: {token_info['user_email']}")
            return token_info
            
        except Exception as e:
            logger.error(f"Failed to exchange code for tokens: {e}")
            raise ValueError(f"Token exchange failed: {e}")

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """
        Refresh expired access token using refresh token.
        
        Args:
            refresh_token: OAuth 2.0 refresh token.
            
        Returns:
            New token information.
            
        Raises:
            ValueError: If token refresh fails.
        """
        try:
            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
            )
            
            # Refresh the token
            credentials.refresh(Request())
            
            token_info = {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token or refresh_token,
                "expires_in": 3600,  # Default to 1 hour
            }
            
            logger.info("Successfully refreshed access token")
            return token_info
            
        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            raise ValueError(f"Token refresh failed: {e}")

    async def _check_rate_limit(self) -> None:
        """
        Enforce rate limiting with exponential backoff.
        
        Uses a sliding window approach to track API requests per hour.
        """
        async with self._request_lock:
            now = datetime.utcnow()
            
            # Reset window if an hour has passed
            if now - self._window_start > timedelta(hours=1):
                self._requests_made = 0
                self._window_start = now
            
            # Check if we've exceeded the rate limit
            if self._requests_made >= self.rate_limit:
                # Calculate wait time until window resets
                wait_time = 3600 - (now - self._window_start).total_seconds()
                if wait_time > 0:
                    logger.warning(f"Rate limit exceeded, waiting {wait_time:.1f} seconds")
                    await asyncio.sleep(wait_time)
                    # Reset counters
                    self._requests_made = 0
                    self._window_start = datetime.utcnow()
            
            self._requests_made += 1

    async def fetch_newsletter_emails(
        self,
        access_token: str,
        days_back: int = 7,
        newsletter_keywords: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Fetch newsletter emails from Gmail inbox.
        
        Args:
            access_token: Valid Gmail API access token.
            days_back: Number of days to look back for emails.
            newsletter_keywords: Keywords to filter newsletter emails.
            
        Returns:
            List of email data dictionaries.
        """
        await self._check_rate_limit()
        
        try:
            credentials = Credentials(token=access_token)
            service = build("gmail", "v1", credentials=credentials)
            
            # Build search query
            query_parts = []
            
            # Date filter
            date_filter = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y/%m/%d")
            query_parts.append(f"after:{date_filter}")
            
            # Newsletter keywords filter
            if newsletter_keywords:
                keyword_query = " OR ".join([f'"{keyword}"' for keyword in newsletter_keywords])
                query_parts.append(f"({keyword_query})")
            
            # Common newsletter indicators
            query_parts.append("(unsubscribe OR newsletter OR digest OR briefing)")
            
            # Exclude spam and trash
            query_parts.append("-in:spam -in:trash")
            
            query = " ".join(query_parts)
            logger.info(f"Searching emails with query: {query}")
            
            # Search for messages
            await self._check_rate_limit()
            messages_response = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=100  # Limit to prevent excessive API usage
            ).execute()
            
            messages = messages_response.get("messages", [])
            logger.info(f"Found {len(messages)} potential newsletter messages")
            
            # Fetch full message details
            emails = []
            for message in messages:
                try:
                    await self._check_rate_limit()
                    msg = service.users().messages().get(
                        userId="me",
                        id=message["id"],
                        format="full"
                    ).execute()
                    
                    email_data = await self._parse_email_message(msg)
                    if email_data:
                        emails.append(email_data)
                        
                except HttpError as e:
                    if e.resp.status == 429:  # Rate limited
                        logger.warning("Rate limited, implementing exponential backoff")
                        await asyncio.sleep(2 ** len(emails))  # Exponential backoff
                        continue
                    else:
                        logger.error(f"Error fetching message {message['id']}: {e}")
                        continue
                        
                except Exception as e:
                    logger.error(f"Unexpected error processing message {message['id']}: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(emails)} newsletter emails")
            return emails
            
        except HttpError as e:
            if e.resp.status == 401:  # Unauthorized
                raise ValueError("Access token expired or invalid")
            else:
                logger.error(f"Gmail API error: {e}")
                raise
                
        except Exception as e:
            logger.error(f"Failed to fetch newsletter emails: {e}")
            raise

    async def _parse_email_message(self, message: Dict) -> Optional[Dict]:
        """
        Parse Gmail API message into structured email data.
        
        Args:
            message: Gmail API message object.
            
        Returns:
            Parsed email data or None if parsing fails.
        """
        try:
            headers = {h["name"]: h["value"] for h in message["payload"].get("headers", [])}
            
            # Extract basic information
            email_data = {
                "id": message["id"],
                "thread_id": message["threadId"],
                "subject": headers.get("Subject", ""),
                "sender": headers.get("From", ""),
                "date": headers.get("Date", ""),
                "received_timestamp": int(message["internalDate"]) / 1000,  # Convert to seconds
            }
            
            # Parse sender information
            sender_parts = email_data["sender"].split(" ")
            if len(sender_parts) >= 2:
                email_data["sender_name"] = " ".join(sender_parts[:-1]).strip("<>\"")
                email_data["sender_email"] = sender_parts[-1].strip("<>")
            else:
                email_data["sender_email"] = email_data["sender"]
                email_data["sender_name"] = ""
            
            # Extract email body
            body = await self._extract_email_body(message["payload"])
            if not body:
                logger.warning(f"No body content found for message {message['id']}")
                return None
                
            email_data["body_html"] = body.get("html", "")
            email_data["body_text"] = body.get("text", "")
            
            # Determine if this looks like a newsletter
            is_newsletter = await self._is_newsletter_email(email_data)
            if not is_newsletter:
                logger.debug(f"Email {message['id']} doesn't appear to be a newsletter")
                return None
            
            return email_data
            
        except Exception as e:
            logger.error(f"Error parsing email message: {e}")
            return None

    async def _extract_email_body(self, payload: Dict) -> Optional[Dict[str, str]]:
        """
        Extract HTML and text body from email payload.
        
        Args:
            payload: Gmail API message payload.
            
        Returns:
            Dictionary with 'html' and 'text' keys.
        """
        body = {"html": "", "text": ""}
        
        try:
            # Handle multipart messages
            if "parts" in payload:
                for part in payload["parts"]:
                    mime_type = part.get("mimeType", "")
                    
                    if mime_type == "text/plain" and "data" in part["body"]:
                        text_data = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                        body["text"] = text_data
                        
                    elif mime_type == "text/html" and "data" in part["body"]:
                        html_data = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                        body["html"] = html_data
                        
                    elif "parts" in part:  # Nested multipart
                        nested_body = await self._extract_email_body(part)
                        if nested_body:
                            body["html"] = body["html"] or nested_body["html"]
                            body["text"] = body["text"] or nested_body["text"]
            
            # Handle simple messages
            else:
                mime_type = payload.get("mimeType", "")
                if "data" in payload.get("body", {}):
                    data = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
                    
                    if mime_type == "text/html":
                        body["html"] = data
                    elif mime_type == "text/plain":
                        body["text"] = data
            
            return body if (body["html"] or body["text"]) else None
            
        except Exception as e:
            logger.error(f"Error extracting email body: {e}")
            return None

    async def _is_newsletter_email(self, email_data: Dict) -> bool:
        """
        Determine if an email is likely a newsletter.
        
        Args:
            email_data: Parsed email data.
            
        Returns:
            True if email appears to be a newsletter.
        """
        # Newsletter indicators
        newsletter_indicators = [
            "newsletter", "digest", "briefing", "update", "weekly", "daily",
            "unsubscribe", "subscription", "mailing list", "bulletin"
        ]
        
        # Check subject and sender
        text_to_check = f"{email_data.get('subject', '')} {email_data.get('sender_name', '')}".lower()
        
        # Look for newsletter keywords
        has_keywords = any(indicator in text_to_check for indicator in newsletter_indicators)
        
        # Check for unsubscribe links in body (strong newsletter indicator)
        body_text = f"{email_data.get('body_html', '')} {email_data.get('body_text', '')}".lower()
        has_unsubscribe = "unsubscribe" in body_text
        
        # Check for common newsletter patterns
        has_newsletter_patterns = any(
            pattern in body_text
            for pattern in ["view in browser", "view this email in your browser", "manage preferences"]
        )
        
        return has_keywords or has_unsubscribe or has_newsletter_patterns

    async def get_user_profile(self, access_token: str) -> Dict[str, str]:
        """
        Get Gmail user profile information.
        
        Args:
            access_token: Valid Gmail API access token.
            
        Returns:
            User profile information.
        """
        await self._check_rate_limit()
        
        try:
            credentials = Credentials(token=access_token)
            service = build("gmail", "v1", credentials=credentials)
            
            profile = service.users().getProfile(userId="me").execute()
            
            return {
                "email": profile.get("emailAddress", ""),
                "messages_total": profile.get("messagesTotal", 0),
                "threads_total": profile.get("threadsTotal", 0),
                "history_id": profile.get("historyId", ""),
            }
            
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            raise


# Service instance
gmail_service = GmailService()


def get_gmail_service() -> GmailService:
    """Get Gmail service instance."""
    return gmail_service