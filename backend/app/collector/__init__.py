"""
Viral Intelligence System — Backend module for Betty AI Video Platform.
Provides: trending discovery, viral scoring, growth analysis, hook detection,
sentiment analysis, prompt generation, and Redis Streams pipeline.

Import models lazily to avoid circular deps with app.models.
"""
# Lazy imports — use explicit imports at call sites:
#   from app.collector.engine import viral_engine
#   from app.collector.models import TrendingTopic, ViralSignal, TrendReport
