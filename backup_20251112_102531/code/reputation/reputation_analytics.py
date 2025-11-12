from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .rating_system import BorgRatingSystem

class ReputationAnalytics:
    """Analytics for reputation data to support Phase 2 evolution"""

    def __init__(self, rating_system: BorgRatingSystem):
        self.rating_system = rating_system

    async def get_reputation_leaderboard(
        self,
        min_ratings: int = 3,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get leaderboard of highest-rated borgs

        Args:
            min_ratings: Minimum number of ratings required
            limit: Maximum number of borgs to return

        Returns:
            List of borgs sorted by average rating
        """
        # This would require database aggregation in production
        # For now, return placeholder data
        return [
            {
                'borg_id': 'borg-001',
                'average_rating': 4.8,
                'total_ratings': 12,
                'rank': 1
            },
            {
                'borg_id': 'borg-002',
                'average_rating': 4.6,
                'total_ratings': 8,
                'rank': 2
            }
        ]

    async def analyze_rating_patterns(
        self,
        borg_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze rating patterns over time

        Returns:
            Rating trend analysis
        """
        ratings = await self.rating_system.get_borg_ratings(borg_id)

        if not ratings:
            return {'trend': 'no_data', 'insights': []}

        # Analyze trends (simplified)
        recent_ratings = [
            r for r in ratings
            if datetime.fromisoformat(r['rated_at']) > datetime.utcnow() - timedelta(days=days)
        ]

        if len(recent_ratings) < 2:
            return {'trend': 'insufficient_data', 'insights': []}

        avg_recent = sum(r['rating'] for r in recent_ratings) / len(recent_ratings)
        avg_all = sum(r['rating'] for r in ratings) / len(ratings)

        trend = 'stable'
        if avg_recent > avg_all + 0.5:
            trend = 'improving'
        elif avg_recent < avg_all - 0.5:
            trend = 'declining'

        return {
            'trend': trend,
            'recent_average': round(avg_recent, 2),
            'overall_average': round(avg_all, 2),
            'insights': [
                f"Recent performance trend: {trend}",
                f"Rating consistency: {self._calculate_consistency(ratings)}"
            ]
        }

    def _calculate_consistency(self, ratings: List[Dict[str, Any]]) -> str:
        """Calculate rating consistency"""
        if len(ratings) < 2:
            return "insufficient_data"

        ratings_list = [r['rating'] for r in ratings]
        variance = sum((x - sum(ratings_list)/len(ratings_list))**2 for x in ratings_list) / len(ratings_list)

        if variance < 0.5:
            return "very_consistent"
        elif variance < 1.5:
            return "consistent"
        elif variance < 3.0:
            return "variable"
        else:
            return "highly_variable"

    async def get_evolution_candidates(
        self,
        min_rating: float = 4.0,
        min_ratings: int = 5
    ) -> List[str]:
        """
        Identify borgs suitable for evolution (high ratings, sufficient data)

        Returns:
            List of borg IDs suitable for evolution
        """
        leaderboard = await self.get_reputation_leaderboard(min_ratings=min_ratings)

        return [
            borg['borg_id'] for borg in leaderboard
            if borg['average_rating'] >= min_rating
        ]

    async def generate_rating_report(self, borg_id: str) -> Dict[str, Any]:
        """
        Generate comprehensive rating report for a borg

        Returns:
            Complete rating analysis
        """
        reputation = await self.rating_system.calculate_reputation(borg_id)
        patterns = await self.analyze_rating_patterns(borg_id)

        return {
            'borg_id': borg_id,
            'reputation': reputation,
            'patterns': patterns,
            'evolution_ready': reputation['average_rating'] >= 4.0 and reputation['total_ratings'] >= 5,
            'generated_at': datetime.utcnow().isoformat()
        }