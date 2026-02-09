"""
Failure Clustering Module

Groups similar failures together to reduce redundancy and improve AI analysis efficiency.
This matches Recommendation #1 from the AI analysis improvement plan.
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import re
from collections import defaultdict

from core.execution.intelligence.models import FailureSignal, ExecutionEvent
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FailureCluster:
    """Represents a cluster of similar failures"""
    
    representative_signal: FailureSignal
    cluster_signals: List[FailureSignal]
    count: int
    pattern: str
    severity: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "count": self.count,
            "pattern": self.pattern,
            "representative_message": self.representative_signal.message,
            "signal_type": self.representative_signal.signal_type.value,
            "severity": self.severity,
        }


class FailureClusterer:
    """
    Clusters similar failures to reduce AI analysis redundancy.
    
    Uses rule-based similarity matching and optional semantic embeddings.
    This significantly reduces LLM token usage and improves output quality.
    """
    
    def __init__(self, similarity_threshold: float = 0.8):
        """
        Initialize clusterer.
        
        Args:
            similarity_threshold: Minimum similarity score (0.0-1.0) to cluster
        """
        self.similarity_threshold = similarity_threshold
    
    def cluster(
        self,
        signals: List[FailureSignal],
        use_semantic: bool = False
    ) -> List[FailureCluster]:
        """
        Cluster similar failure signals.
        
        Args:
            signals: List of failure signals to cluster
            use_semantic: Use semantic embeddings (requires embeddings model)
            
        Returns:
            List of failure clusters, sorted by count (descending)
        """
        if not signals:
            return []
        
        logger.debug(f"Clustering {len(signals)} failure signals (semantic={use_semantic})")
        
        if use_semantic and self._has_embeddings():
            clusters = self._cluster_with_embeddings(signals)
        else:
            clusters = self._cluster_with_rules(signals)
        
        # Sort by count (most common first)
        clusters.sort(key=lambda c: c.count, reverse=True)
        
        logger.info(
            f"Clustered {len(signals)} signals into {len(clusters)} groups "
            f"(reduction: {(1 - len(clusters)/len(signals))*100:.1f}%)"
        )
        
        return clusters
    
    def _cluster_with_rules(self, signals: List[FailureSignal]) -> List[FailureCluster]:
        """
        Cluster using rule-based pattern matching.
        
        This is fast and works without embeddings/AI.
        """
        # Pattern-based clustering
        pattern_groups: Dict[str, List[FailureSignal]] = defaultdict(list)
        
        for signal in signals:
            pattern = self._extract_pattern(signal.message)
            pattern_groups[pattern].append(signal)
        
        # Build clusters
        clusters = []
        for pattern, group_signals in pattern_groups.items():
            # Choose representative (first occurrence)
            representative = group_signals[0]
            
            # Determine severity
            severity = self._infer_severity(representative)
            
            cluster = FailureCluster(
                representative_signal=representative,
                cluster_signals=group_signals,
                count=len(group_signals),
                pattern=pattern,
                severity=severity
            )
            clusters.append(cluster)
        
        return clusters
    
    def _cluster_with_embeddings(
        self,
        signals: List[FailureSignal]
    ) -> List[FailureCluster]:
        """
        Cluster using semantic embeddings.
        
        Requires embeddings model (more accurate but slower).
        """
        try:
            from sklearn.cluster import DBSCAN
            import numpy as np
            
            # Generate embeddings
            messages = [s.message for s in signals]
            embeddings = self._generate_embeddings(messages)
            
            # DBSCAN clustering
            clustering = DBSCAN(
                eps=1 - self.similarity_threshold,
                min_samples=1,
                metric='cosine'
            ).fit(embeddings)
            
            # Group by cluster label
            cluster_groups: Dict[int, List[int]] = defaultdict(list)
            for idx, label in enumerate(clustering.labels_):
                cluster_groups[label].append(idx)
            
            # Build clusters
            clusters = []
            for label, indices in cluster_groups.items():
                group_signals = [signals[i] for i in indices]
                representative = group_signals[0]
                pattern = self._extract_pattern(representative.message)
                severity = self._infer_severity(representative)
                
                cluster = FailureCluster(
                    representative_signal=representative,
                    cluster_signals=group_signals,
                    count=len(group_signals),
                    pattern=pattern,
                    severity=severity
                )
                clusters.append(cluster)
            
            return clusters
        
        except ImportError:
            logger.warning("Semantic clustering requires sklearn - falling back to rule-based")
            return self._cluster_with_rules(signals)
        
        except Exception as e:
            logger.error(f"Semantic clustering failed: {e} - falling back to rule-based")
            return self._cluster_with_rules(signals)
    
    def _extract_pattern(self, message: str) -> str:
        """
        Extract generalized pattern from error message.
        
        Replaces specific values with placeholders for grouping.
        """
        # Normalize message
        pattern = message.lower().strip()
        
        # Replace numbers
        pattern = re.sub(r'\b\d+\b', '{NUM}', pattern)
        
        # Replace IDs/UUIDs
        pattern = re.sub(
            r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b',
            '{UUID}',
            pattern
        )
        
        # Replace file paths
        pattern = re.sub(r'/[\w/.-]+', '{PATH}', pattern)
        pattern = re.sub(r'[a-z]:\\[\w\\.-]+', '{PATH}', pattern, flags=re.IGNORECASE)
        
        # Replace URLs
        pattern = re.sub(r'https?://[^\s]+', '{URL}', pattern)
        
        # Replace quoted strings
        pattern = re.sub(r'["\'].*?["\']', '{STRING}', pattern)
        
        # Replace timestamps
        pattern = re.sub(
            r'\d{4}[-/]\d{2}[-/]\d{2}[T\s]\d{2}:\d{2}:\d{2}',
            '{TIMESTAMP}',
            pattern
        )
        
        return pattern
    
    def _infer_severity(self, signal: FailureSignal) -> str:
        """
        Infer severity from signal characteristics.
        
        Returns: "High", "Medium", or "Low"
        """
        message_lower = signal.message.lower()
        
        # High severity indicators
        high_severity_keywords = [
            'http 500', 'http 503', 'internal server error',
            'data loss', 'corrupted', 'fatal error',
            'security', 'authentication failed', 'unauthorized',
            'database connection failed', 'out of memory'
        ]
        
        if any(kw in message_lower for kw in high_severity_keywords):
            return "High"
        
        # Medium severity indicators
        medium_severity_keywords = [
            'timeout', 'http 400', 'http 404',
            'not found', 'connection refused',
            'assertion failed', 'validation error'
        ]
        
        if any(kw in message_lower for kw in medium_severity_keywords):
            return "Medium"
        
        return "Low"
    
    def _has_embeddings(self) -> bool:
        """Check if semantic embeddings are available"""
        try:
            import sklearn
            # Could also check for sentence-transformers or similar
            return True
        except ImportError:
            return False
    
    def _generate_embeddings(self, messages: List[str]) -> Any:
        """
        Generate semantic embeddings for messages.
        
        This is a placeholder - in production, use:
        - sentence-transformers
        - OpenAI embeddings
        - CrossBridge's existing embedding service
        """
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            return model.encode(messages)
        except ImportError:
            # Fallback: simple TF-IDF vectors
            from sklearn.feature_extraction.text import TfidfVectorizer
            vectorizer = TfidfVectorizer(max_features=100)
            return vectorizer.fit_transform(messages).toarray()


def cluster_similar_failures(
    signals: List[FailureSignal],
    threshold: float = 0.8,
    use_semantic: bool = False
) -> List[FailureCluster]:
    """
    Convenience function to cluster similar failures.
    
    Args:
        signals: List of failure signals
        threshold: Similarity threshold (0.0-1.0)
        use_semantic: Use semantic embeddings
        
    Returns:
        List of failure clusters
    """
    clusterer = FailureClusterer(similarity_threshold=threshold)
    return clusterer.cluster(signals, use_semantic=use_semantic)
