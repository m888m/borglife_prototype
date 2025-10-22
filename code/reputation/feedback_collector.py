from typing import Dict, Any, Optional
import streamlit as st
from .rating_system import BorgRatingSystem

class FeedbackCollector:
    """UI integration for collecting borg ratings"""

    def __init__(self, rating_system: BorgRatingSystem):
        self.rating_system = rating_system

    def display_rating_widget(
        self,
        borg_id: str,
        sponsor_id: str,
        task_result: Any,
        task_description: str = ""
    ) -> Optional[int]:
        """
        Display rating widget in Streamlit UI

        Args:
            borg_id: Borg being rated
            sponsor_id: Sponsor providing rating
            task_result: Result of the task performed
            task_description: Description of the task

        Returns:
            Rating value if submitted, None otherwise
        """
        with st.container():
            st.markdown("---")
            st.subheader("⭐ Rate Borg Performance")
            st.write("How useful was this borg's response?")

            # Rating slider
            rating = st.slider(
                "Rating",
                min_value=1,
                max_value=5,
                value=3,
                help="1 = Not useful, 5 = Extremely useful",
                key=f"rating_{borg_id}_{sponsor_id}"
            )

            # Optional feedback
            feedback = st.text_area(
                "Optional feedback",
                placeholder="What did you like or dislike about this borg's performance?",
                height=80,
                key=f"feedback_{borg_id}_{sponsor_id}"
            )

            # Task context summary
            if task_description:
                st.caption(f"Task: {task_description[:100]}...")

            # Submit button
            submit_key = f"submit_rating_{borg_id}_{sponsor_id}"
            if st.button("Submit Rating", key=submit_key):
                # Submit rating
                success = asyncio.run(self.rating_system.submit_rating(
                    borg_id=borg_id,
                    sponsor_id=sponsor_id,
                    rating=rating,
                    feedback=feedback if feedback.strip() else None,
                    task_context=task_description[:200]  # Truncate for storage
                ))

                if success:
                    st.success("✅ Rating submitted! Thank you for your feedback.")
                    st.balloons()  # Celebration effect

                    # Show current reputation
                    reputation = asyncio.run(self.rating_system.calculate_reputation(borg_id))
                    if reputation['total_ratings'] > 0:
                        st.info(f"📊 Borg now has {reputation['total_ratings']} rating(s) with an average of {reputation['average_rating']} ⭐")

                    return rating
                else:
                    st.error("❌ Failed to submit rating. Please try again.")
                    return None

        return None

    def display_reputation_summary(self, borg_id: str):
        """
        Display reputation summary for a borg
        """
        reputation = asyncio.run(self.rating_system.calculate_reputation(borg_id))

        if reputation['total_ratings'] == 0:
            st.caption("No ratings yet")
            return

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Average Rating", f"{reputation['average_rating']} ⭐")

        with col2:
            st.metric("Total Ratings", reputation['total_ratings'])

        with col3:
            # Show star distribution
            stars = []
            for star in range(5, 0, -1):
                count = reputation['rating_distribution'].get(star, 0)
                if count > 0:
                    stars.append(f"{star}⭐: {count}")
            st.caption(" | ".join(stars))

    async def collect_rating_async(
        self,
        borg_id: str,
        sponsor_id: str,
        rating: int,
        feedback: Optional[str] = None,
        task_context: Optional[str] = None
    ) -> bool:
        """
        Async method for programmatic rating collection
        """
        return await self.rating_system.submit_rating(
            borg_id=borg_id,
            sponsor_id=sponsor_id,
            rating=rating,
            feedback=feedback,
            task_context=task_context
        )