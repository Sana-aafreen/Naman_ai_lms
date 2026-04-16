
"""
Monitoring Agent - Tracks user learning progress and provides AI-driven insights.

This agent monitors:
- Course completion progress
- Quiz performance and scores
- Learning goals and milestones
- Skill gaps and recommendations
- Department rankings and comparisons
- Weekly engagement metrics
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()

# -- Configuration ----------------------------------------------------------

class MonitoringAgent:
    """
    AI-powered monitoring agent for tracking user learning progress and providing insights.
    """
    
    def __init__(self, user_id: str, user_data: Dict[str, Any]):
        """
        Initialize the monitoring agent.
        
        Args:
            user_id: Unique user identifier
            user_data: Dict containing user profile info (name, role, department, etc.)
        """
        self.user_id = user_id
        self.user_data = user_data
        self.google_sheets_api = os.getenv("GOOGLE_SHEETS_API", "")
        self.base_url = os.getenv("API_BASE_URL", "http://localhost:5000")
        
    def get_progress_metrics(self) -> Dict[str, Any]:
        """
        Fetch and calculate user's learning progress metrics.
        
        Returns:
            Dict with progress data (courses_completed, current_streak, quiz_avg, etc.)
        """
        try:
            # TODO: Connect to Google Sheets API or database
            # Fetch: courses completed, quiz scores, time spent, goals progress
            metrics = {
                "courses_completed": 0,
                "courses_in_progress": 0,
                "quiz_average": 0,
                "total_hours": 0,
                "current_streak": 0,
                "department_rank": 0,
                "goals_completed": 0,
            }
            return metrics
        except Exception as e:
            print(f"Error fetching progress metrics: {e}")
            return {}
    
    def analyze_performance(self) -> Dict[str, Any]:
        """
        Analyze user's learning performance against benchmarks.
        
        Returns:
            Dict with performance analysis and insights
        """
        metrics = self.get_progress_metrics()
        
        analysis = {
            "strengths": self._identify_strengths(metrics),
            "improvement_areas": self._identify_gaps(metrics),
            "recommendations": self._generate_recommendations(metrics),
            "insights": self._generate_insights(metrics),
        }
        return analysis
    
    def _identify_strengths(self, metrics: Dict[str, Any]) -> List[str]:
        """Identify user's learning strengths."""
        strengths = []
        
        if metrics.get("quiz_average", 0) >= 85:
            strengths.append("Strong quiz performance - excellent mastery of course material")
        if metrics.get("current_streak", 0) >= 7:
            strengths.append("Excellent consistency - maintaining strong learning habit")
        if metrics.get("courses_completed", 0) >= 3:
            strengths.append("Prolific learner - completing multiple courses successfully")
        
        return strengths if strengths else ["Keep building momentum and exploring new topics"]
    
    def _identify_gaps(self, metrics: Dict[str, Any]) -> List[str]:
        """Identify areas for improvement."""
        gaps = []
        
        if metrics.get("quiz_average", 0) < 70:
            gaps.append("Quiz performance needs improvement - focus on challenging topics")
        if metrics.get("courses_in_progress", 0) > metrics.get("courses_completed", 0):
            gaps.append("Complete in-progress courses before starting new ones")
        if metrics.get("current_streak", 0) == 0:
            gaps.append("Restart consistent daily learning habits")
        
        return gaps
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate personalized learning recommendations."""
        recommendations = []
        
        department = self.user_data.get("department", "")
        role = self.user_data.get("role", "")
        
        if department and role:
            recommendations.append(
                f"Focus on {department}-specific courses to improve department ranking"
            )
        
        if metrics.get("quiz_average", 0) < 80:
            recommendations.append("Practice quiz-style problems for at least 30 mins daily")
        
        if metrics.get("courses_in_progress", 0) == 0:
            recommendations.append("Explore advanced courses related to your career goals")
        
        return recommendations
    
    def _generate_insights(self, metrics: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate AI-driven insights with celebratory/warning messages."""
        insights = []
        
        # Positive insights
        if metrics.get("current_streak", 0) >= 14:
            insights.append({
                "type": "celebration",
                "text": f"  Amazing! {metrics['current_streak']}-day learning streak! Keep it up!"
            })
        
        if metrics.get("quiz_average", 0) >= 90:
            insights.append({
                "type": "celebration",
                "text": "  Outstanding quiz performance! You're mastering the material!"
            })
        
        # Warning insights
        if metrics.get("current_streak", 0) == 0:
            insights.append({
                "type": "warning",
                "text": "   No recent activity. Start learning today to build momentum!"
            })
        
        # Tips
        insights.append({
            "type": "tip",
            "text": "  Pro tip: Schedule 30-min daily learning sessions for consistent progress"
        })
        
        return insights
    
    def get_daily_greeting(self) -> str:
        """Generate personalized daily greeting."""
        name = self.user_data.get("name", "there").split()[0]
        metrics = self.get_progress_metrics()
        
        streak = metrics.get("current_streak", 0)
        
        if streak > 0:
            return f"Namaste {name}   Great to see you again! You're on a {streak}-day streak!"
        else:
            return f"Namaste {name}   I'm your personal Monitoring AI. Let's get back on track!"
    
    def generate_weekly_report(self) -> Dict[str, Any]:
        """Generate comprehensive weekly learning report."""
        metrics = self.get_progress_metrics()
        analysis = self.analyze_performance()
        
        report = {
            "week": datetime.now().strftime("%Y-W%U"),
            "user_id": self.user_id,
            "metrics": metrics,
            "analysis": analysis,
            "greeting": self.get_daily_greeting(),
            "generated_at": datetime.now().isoformat(),
        }
        return report


# -- API Endpoint Handler ---------------------------------------------------

def handle_monitoring_request(user_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main handler for monitoring API requests.
    
    Args:
        user_id: User identifier
        user_data: User profile data
        
    Returns:
        Response with insights, greeting, and metrics
    """
    try:
        agent = MonitoringAgent(user_id, user_data)
        
        metrics = agent.get_progress_metrics()
        analysis = agent.analyze_performance()
        insights = analysis.get("insights", [])
        greeting = agent.get_daily_greeting()
        
        return {
            "success": True,
            "user_id": user_id,
            "metrics": metrics,
            "insights": insights,
            "greeting": greeting,
            "recommendations": analysis.get("recommendations", []),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        print(f"Error handling monitoring request: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


if __name__ == "__main__":
    # Test the monitoring agent
    test_user = {
        "id": "test_user_123",
        "name": "John Doe",
        "role": "Engineer",
        "department": "Engineering",
    }
    
    agent = MonitoringAgent("test_user_123", test_user)
    report = agent.generate_weekly_report()
    
    print(json.dumps(report, indent=2, default=str))
