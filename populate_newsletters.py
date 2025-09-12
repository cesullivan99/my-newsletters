#!/usr/bin/env python3
"""
Script to populate the database with test newsletter data.
Run this to have sample data for testing the briefing feature.
"""

import asyncio
import os
import uuid
from datetime import datetime, timedelta
import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def populate_test_data():
    """Populate database with test newsletter data."""
    
    database_url = os.getenv("DATABASE_URL")
    conn = await asyncpg.connect(database_url)
    
    try:
        # Get the first user
        user = await conn.fetchrow("SELECT id, email FROM users LIMIT 1")
        
        if not user:
            print("No user found. Please login through the app first.")
            return
        
        user_id = user['id']
        print(f"Creating test newsletters for user: {user['email']}")
        
        # Create a test newsletter
        newsletter_id = uuid.uuid4()
        await conn.execute("""
            INSERT INTO newsletters (id, name, publisher, description)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (name) DO UPDATE SET id = EXCLUDED.id
            RETURNING id
        """, newsletter_id, "TechCrunch Daily", "TechCrunch", "Daily tech news digest")
        
        print(f"Created newsletter: TechCrunch Daily")
        
        # Create user subscription
        await conn.execute("""
            INSERT INTO user_subscriptions (user_id, newsletter_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
        """, user_id, newsletter_id)
        
        # Create an issue for today
        issue_id = uuid.uuid4()
        await conn.execute("""
            INSERT INTO issues (id, newsletter_id, date, subject, raw_content)
            VALUES ($1, $2, $3, $4, $5)
        """, issue_id, newsletter_id, datetime.now(), 
            "Today's Tech Headlines", 
            "<html><body>Newsletter content here</body></html>")
        
        print(f"Created issue for today")
        
        # Create some stories
        stories = [
            {
                "headline": "AI Startup Raises $100M in Series B Funding",
                "summary": "A prominent AI startup has secured major funding to expand operations.",
                "full_summary": "The AI startup, focused on natural language processing, has raised $100 million in Series B funding led by major venture capital firms. The funding will be used to expand the team and accelerate product development.",
                "url": "https://example.com/ai-funding"
            },
            {
                "headline": "New iPhone Features Announced at Apple Event",
                "summary": "Apple unveils innovative features for the next iPhone generation.",
                "full_summary": "At today's Apple event, the company announced several groundbreaking features for the upcoming iPhone, including advanced AI capabilities, improved camera systems, and extended battery life.",
                "url": "https://example.com/iphone-features"
            },
            {
                "headline": "Cloud Computing Market Reaches New Heights",
                "summary": "Global cloud computing market surpasses $500 billion valuation.",
                "full_summary": "The cloud computing market has reached a new milestone with a valuation exceeding $500 billion. Major providers like AWS, Azure, and Google Cloud continue to dominate the market while new players emerge with specialized solutions.",
                "url": "https://example.com/cloud-market"
            }
        ]
        
        for story in stories:
            story_id = uuid.uuid4()
            await conn.execute("""
                INSERT INTO stories (
                    id, issue_id, headline, one_sentence_summary, 
                    full_text_summary, url
                )
                VALUES ($1, $2, $3, $4, $5, $6)
            """, story_id, issue_id, 
                story["headline"], 
                story["summary"],
                story["full_summary"],
                story["url"])
            print(f"  - Added story: {story['headline']}")
        
        print("\n✅ Successfully populated test newsletter data!")
        print("You can now test the briefing feature in the app.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(populate_test_data())