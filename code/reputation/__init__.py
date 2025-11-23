"""
Borglife Reputation & Feedback System

Collects user satisfaction ratings to provide feedback signals for borg evaluation
and Phase 2 evolution.
"""

from .feedback_collector import FeedbackCollector
from .rating_system import BorgRating, BorgRatingSystem, BorgReputation
from .reputation_analytics import ReputationAnalytics

__all__ = [
    "BorgRatingSystem",
    "BorgRating",
    "BorgReputation",
    "FeedbackCollector",
    "ReputationAnalytics",
]
