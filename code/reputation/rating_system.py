import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class BorgRating(BaseModel):
    """Individual borg rating"""

    borg_id: str
    sponsor_id: str
    rating: int  # 1-5 stars
    feedback: Optional[str] = None
    task_context: Optional[str] = None
    rated_at: datetime = datetime.utcnow()


class BorgReputation(BaseModel):
    """Aggregated reputation data"""

    average_rating: float
    total_ratings: int
    rating_distribution: Dict[int, int]  # {1: count, 2: count, ..., 5: count}
    last_rated: Optional[datetime] = None


class BorgRatingSystem:
    """Simple 1-5 star rating system for borg evaluation"""

    def __init__(self, supabase_client=None):
        self.supabase = supabase_client

    async def submit_rating(
        self,
        borg_id: str,
        sponsor_id: str,
        rating: int,
        feedback: Optional[str] = None,
        task_context: Optional[str] = None,
    ) -> bool:
        """
        Submit a rating for a borg

        Args:
            borg_id: Unique borg identifier
            sponsor_id: Sponsor providing the rating
            rating: 1-5 star rating
            feedback: Optional text feedback
            task_context: Context about the task performed

        Returns:
            True if rating submitted successfully
        """
        if not (1 <= rating <= 5):
            raise ValueError("Rating must be between 1 and 5 stars")

        rating_data = {
            "borg_id": borg_id,
            "sponsor_id": sponsor_id,
            "rating": rating,
            "feedback": feedback,
            "task_context": task_context,
            "rated_at": datetime.utcnow().isoformat(),
        }

        if self.supabase:
            # Store in Supabase
            try:
                await self.supabase.table("borg_ratings").upsert(
                    rating_data, on_conflict="borg_id,sponsor_id"
                )
                return True
            except Exception as e:
                print(f"Failed to store rating: {e}")
                return False
        else:
            # In-memory storage for testing
            if not hasattr(self, "_ratings"):
                self._ratings = []
            self._ratings.append(rating_data)
            return True

    async def get_borg_ratings(self, borg_id: str) -> List[Dict[str, Any]]:
        """
        Get all ratings for a specific borg

        Returns:
            List of rating records
        """
        if self.supabase:
            try:
                result = (
                    await self.supabase.table("borg_ratings")
                    .select("*")
                    .eq("borg_id", borg_id)
                )
                return result.data if result.data else []
            except Exception as e:
                print(f"Failed to fetch ratings: {e}")
                return []
        else:
            # Return in-memory ratings
            if hasattr(self, "_ratings"):
                return [r for r in self._ratings if r["borg_id"] == borg_id]
            return []

    async def calculate_reputation(self, borg_id: str) -> Dict[str, Any]:
        """
        Calculate reputation metrics for a borg

        Returns:
            {
                'average_rating': float,
                'total_ratings': int,
                'rating_distribution': {1: count, 2: count, ..., 5: count},
                'last_rated': datetime
            }
        """
        ratings = await self.get_borg_ratings(borg_id)

        if not ratings:
            return {
                "average_rating": 0.0,
                "total_ratings": 0,
                "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                "last_rated": None,
            }

        total_ratings = len(ratings)
        sum_ratings = sum(r["rating"] for r in ratings)
        average_rating = sum_ratings / total_ratings

        # Calculate distribution
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for rating in ratings:
            distribution[rating["rating"]] += 1

        # Find last rated timestamp
        last_rated = max(r["rated_at"] for r in ratings) if ratings else None

        return {
            "average_rating": round(average_rating, 2),
            "total_ratings": total_ratings,
            "rating_distribution": distribution,
            "last_rated": last_rated,
        }

    async def get_top_rated_borgs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top-rated borgs for leaderboard/evolution selection

        Returns:
            List of borgs sorted by average rating
        """
        # This would require a more complex query in production
        # For now, return placeholder
        return []

    async def collect_rating(
        self, borg_id: str, sponsor_id: str, task_result: Any
    ) -> Optional[int]:
        """
        Collect rating through UI (placeholder for UI integration)

        Returns:
            Rating value if collected, None otherwise
        """
        # This would be called from the UI
        # For now, return a mock rating for testing
        return 4  # Mock 4-star rating
