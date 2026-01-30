"""
Embedding Reliability Extensions for CrossBridge Memory System.













































































































































































































































































































































































































































































































































- Discord: https://discord.gg/crossbridge- Docs: https://docs.crossbridge.ai/reliability- Issues: https://github.com/crossbridge/crossbridge/issues## 📞 SupportSee CONTRIBUTING.md for guidelines.## 🤝 ContributingPart of CrossBridge AI - See LICENSE file for details.## 📄 License- [ ] Incremental embedding updates- [ ] Cost optimization (avoid unnecessary reindexing)- [ ] Automatic model selection- [ ] Embedding quality scoring- [ ] A/B testing for embedding models### Phase 3 Advanced Features- [ ] Distributed queue (Redis/RabbitMQ)- [ ] Multi-tenant isolation- [ ] Scheduled automatic reindexing- [ ] Drift prediction models- [ ] Adaptive thresholds based on entity type- [ ] Graph-aware drift detection (neighbors changing)### Phase 2 Enhancements## 🛣️ Roadmap```        """Process next reindex job from queue."""    ) -> bool:        text_builder: Any        embedding_provider: EmbeddingProvider,        self,    def process_next_job(            """Queue entity for drift-triggered reindex."""    ) -> bool:        similarity_score: float        entity_type: MemoryType,        entity_id: str,        self,    def queue_for_drift(            """Check staleness and queue if needed."""    ) -> bool:        current_text: str        entity_type: MemoryType,        entity_id: str,        self,    def check_and_queue_stale(            """Initialize reindex manager."""    ):        max_queue_size: int = 10000        drift_detector: DriftDetector,        staleness_detector: StalenessDetector,        vector_store: VectorStore,        self,    def __init__(class ReindexManager:```python### ReindexManager```        """Compute cosine similarity (0.0-1.0)."""    ) -> float:        vec2: List[float]        vec1: List[float],     def cosine_similarity(    @staticmethod            """            DriftResult with similarity score and drift status        Returns:                Check semantic drift.        """    ) -> DriftResult:        new_embedding: List[float]        record_id: str,         self,     def check_drift(            """Initialize drift detector."""    ):        threshold: float = 0.85        vector_store: VectorStore,        self,     def __init__(class DriftDetector:```python### DriftDetector```        """Manually mark embedding as stale."""    def mark_stale(self, record_id: str) -> bool:            """            StaleEmbedding if stale, None if fresh        Returns:                Check if embedding is stale.        """    ) -> Optional[StaleEmbedding]:        current_text: str        record_id: str,         self,     def is_stale(            """Initialize staleness detector."""    ):        current_version: Optional[EmbeddingVersion] = None        max_age_days: int = 90,        vector_store: VectorStore,        self,     def __init__(class StalenessDetector:```python### StalenessDetector## 📚 API Reference4. Profile embedding provider performance3. Use connection pooling for database2. Optimize text builder (reduce entity text length)1. Increase batch size: `queue.process_batch_size: 200`**Solutions**:**Symptoms**: Long processing times per job### Issue: Slow Reindexing4. Check for model version changes3. Review text extraction logic (may be inconsistent)2. Increase check interval: `drift.check_interval_days: 60`1. Lower drift threshold: `drift.threshold: 0.80`**Solutions**:**Symptoms**: Many drift alerts, high reindex rate### Issue: Frequent Drift Detection4. Temporarily increase rate limits3. Adjust priorities to focus on critical items2. Reduce staleness checks: `staleness.check_interval_hours: 48`1. Increase worker concurrency: `worker.max_concurrent_jobs: 10`**Solutions**:**Symptoms**: Queue size growing continuously### Issue: High Queue Size## 🔧 Troubleshooting```pytest tests/memory/reliability/test_performance.py --benchmark# Performance testspytest tests/memory/reliability/test_integration.py# Full pipeline test```bash### Integration Tests```pytest tests/memory/reliability/test_reindex_manager.pypytest tests/memory/reliability/test_drift_detection.pypytest tests/memory/reliability/test_staleness.pypytest tests/memory/reliability/test_version_tracking.py# Specific test modulespytest tests/memory/reliability/# Run all reliability tests```bash### Unit Tests## 🧪 Testing```}    "manually_stale": false    "drift_detected": false,    "drift_score": 0.92,    "fingerprint_updated_at": "2024-01-15T10:30:00",    "fingerprint": "a3f2e8d...",  # SHA-256 hash    "embedding_version": "v1::text-only::openai",{```pythonAll reliability data stored in `MemoryRecord.metadata`:### Metadata Storage4. **Update Vector Store** → Update metadata → Mark complete3. **Queue Processing** → Get highest priority job → Regenerate embedding2. **Staleness Detected** → Create ReindexJob → Add to queue1. **Entity Update** → Check staleness → Check drift### Data Flow```                   └────────────────┘                   │  Worker        │                   │  Background    │                   ┌────────────────┐                            ▼                            │                   └────────┬───────┘                   │  Queue         │                   │  Priority      │                   ┌────────────────┐                            ▼                            │└───────────────────────────┼─────────────────────────────────┘│                           │                                 ││                  └────────┬───────┘                         ││                  │  Manager       │                         ││                  │  Reindex       │                         ││                  ┌────────────────┐                         ││                           ▼                                 ││                           │                                 ││                  └────────┬───────┘                         ││                  │  Detector      │                         ││                  │  Drift         │                         ││                  ┌────────────────┐                         ││                           ▼                                 ││         └─────────────────┼──────────────────┘              ││         │                 │                  │              ││  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘       ││  │  Tracking    │  │   Tracker    │  │  Detector   │       ││  │  Version     │  │  Fingerprint │  │  Staleness  │       ││  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐       ││                                                              │├─────────────────────────────────────────────────────────────┤│          (core/memory/reliability/)                          ││              Reliability Subsystem                           │┌─────────────────────────────────────────────────────────────┐               ▼               │└──────────────┬──────────────────────────────────────────────┘│  (core/ai/embeddings/semantic_service.py)                   ││                    Ingestion Pipeline                        │┌─────────────────────────────────────────────────────────────┐```### Component Interaction## 🏗️ Architecture```WHERE drift_score IS NOT NULL;FROM test_embedding    COUNT(*) FILTER (WHERE drift_detected) as drifted_count    MIN(drift_score) as min_drift,    AVG(drift_score) as avg_drift,SELECT -- Drift statisticsLIMIT 10;ORDER BY priority DESC, created_at ASCWHERE status = 'pending'FROM embedding_reindex_queueSELECT entity_id, reason, priority, created_at-- Pending reindex jobsGROUP BY staleness_reason;FROM stale_embeddings SELECT staleness_reason, COUNT(*) -- Count by staleness reasonSELECT * FROM stale_embeddings;-- View all stale embeddings```sql### Database Queries```print(f"Oldest Job: {stats['oldest_job_age']} seconds")print(f"Processed: {stats['processed_count']}")print(f"Queue Size: {stats['queue_size']}")stats = reindex_manager.get_stats()```python### Queue Metrics## 🔍 Monitoring```worker_thread.start()worker_thread = threading.Thread(target=reindex_worker, daemon=True)import threading# Run in background thread or process        time.sleep(config.reindex.worker.interval_seconds)                            break  # Queue empty                if not success:                )                    text_builder                    embedding_provider,                success = reindex_manager.process_next_job(            for _ in range(config.reindex.queue.process_batch_size):            # Process batch of jobs        if config.reindex.worker.enabled:    while True:    """Background worker for automatic reindexing."""def reindex_worker():config = get_config()from core.memory.reliability import get_configimport time```python### Background Worker```print(f"Oldest job: {stats['oldest_job_age']}")print(f"Queue size: {stats['queue_size']}")stats = reindex_manager.get_stats()# Get queue stats    print("✓ Reindexing job completed")if success:)    text_builder=EmbeddingTextBuilder()    embedding_provider=embedding_provider,success = reindex_manager.process_next_job(# Process next jobfrom core.ai.embeddings.text_builder import EmbeddingTextBuilder```python### Process Reindex Queue```    )        drift_result.similarity_score        entity_type,        entity_id,    reindex_manager.queue_for_drift(    # Queue for reindex        print(f"Drift detected! Similarity: {drift_result.similarity_score:.3f}")if drift_result.has_drifted:drift_result = drift_detector.check_drift(record_id, new_embedding)new_embedding = embedding_provider.embed(updated_text)# After generating new embedding```python### Detect Drift```    )        current_text        entity_type,         entity_id,     reindex_manager.check_and_queue_stale(    # Queue for reindex        print(f"Age: {stale_info.age_days} days")    print(f"Stale: {stale_info.reason}")if stale_info:stale_info = staleness_detector.is_stale(record_id, current_text)# Check if embedding is stale```python### Check Staleness```reindex_manager = ReindexManager(vector_store, staleness_detector, drift_detector)drift_detector = DriftDetector(vector_store, threshold=config.drift.threshold))    max_age_days=config.staleness.max_age_days    vector_store,staleness_detector = StalenessDetector(vector_store = PgVectorStore(connection)# Initialize componentsconfig = get_config()# Load configurationfrom core.memory.vector_store import PgVectorStore)    get_config    ReindexManager,    DriftDetector,    StalenessDetector,from core.memory.reliability import (```python### Basic Usage## 🚀 Usage```      log_drift_events: true      log_stale_embeddings: true      enabled: true    metrics:    # Observability            max_per_hour: 1000      rate_limit:        max_concurrent_jobs: 5        interval_seconds: 60        enabled: true      worker:        content_changed: 60        drift_detected: 70        version_mismatch: 80      priorities:        process_batch_size: 100        max_size: 10000      queue:      enabled: true    reindex:    # Reindexing          alert_threshold: 0.70      threshold: 0.85      enabled: true    drift:    # Drift detection          auto_upgrade: true      check_version: true      check_fingerprint: true      max_age_days: 90      enabled: true    staleness:    # Staleness detection        enabled: true  reliability:semantic_search:```yaml### crossbridge.yml## ⚙️ Configuration- Indexes for performance- Helper functions and triggers- `embedding_reindex_queue` table- Reliability columns to `test_embedding` tableThis adds:```python migration/run_embedding_reliability_migration.py# Run the reliability migration```bash### Database Migration```CREATE EXTENSION IF NOT EXISTS vector;# PostgreSQL with pgvector extensionpip install psycopg2-binary numpy pyyaml# Required Python packages```bash### Prerequisites## 📦 Installation- Retry logic for failures- Rate limiting- Concurrent job processing- Configurable processing intervalsAutomated maintenance:### 6. **Background Workers**- **Age threshold**: Priority 30 (lowest)- **No embedding**: Priority 50- **Content changed**: Priority 60- **Manual request**: Priority 70- **Drift detected**: Priority 70- **Version mismatch**: Priority 80 (highest)Intelligent reindexing pipeline with priority queue:### 5. **Priority-based Reindexing**- Automatic drift logging- **Alert threshold**: 0.70 (warnings)- **Drift threshold**: 0.85 (configurable)- **Cosine similarity** comparison (old vs new)Monitor embedding quality over time:### 4. **Semantic Drift Detection**- 🚩 **Manual Stale** - User-flagged- ⏰ **Age Threshold** - Older than max age (default: 90 days)- 📝 **Content Changed** - Fingerprint mismatch- ⚠️ **Version Mismatch** - Outdated version- ❌ **No Version** - Missing version metadata- ❌ **No Embedding** - Vector not storedComprehensive staleness checks:### 3. **Staleness Detection** (6 Criteria)- Trigger reindex when content changes- Compare fingerprints on updates- Compute fingerprint when storing embeddingLightweight SHA-256 fingerprinting to detect entity changes:### 2. **Fingerprint-based Change Detection**- **Automatic version upgrades** trigger reindexing- **Compatibility checking** between versions- **Example**: `v1::text-only::openai`- **Format**: `schema_version::content_version::model_family`Track embedding versions to detect when reindexing is needed:### 1. **Semantic Versioning**## 🎯 FeaturesComprehensive reliability tracking for semantic embeddings in CrossBridge. This system extends the existing memory/embedding infrastructure with automatic quality monitoring and reindexing capabilities.
Extends the existing memory/embedding system with:
- Version tracking
- Staleness detection  
- Fingerprint-based change detection
- Semantic drift monitoring
- Automatic reindexing
- Configuration management

This module enhances the existing core.memory and core.ai.embeddings systems
without replacing them.

Usage:
    from core.memory.reliability import (
        ReindexManager,
        StalenessDetector,
        get_config
    )
    
    config = get_config()
    if config.enabled:
        detector = StalenessDetector(
            vector_store, 
            max_age_days=config.staleness.max_age_days
        )
"""

from .version_tracking import (
    EmbeddingVersion,
    VersionTracker,
    get_current_version,
    CURRENT_VERSION,
    SCHEMA_VERSION,
    CONTENT_VERSION,
    MODEL_FAMILY
)
from .staleness import (
    StalenessDetector,
    StalenessReason,
    StaleEmbedding
)
from .fingerprint import (
    compute_fingerprint,
    FingerprintTracker
)
from .drift_detection import (
    DriftDetector,
    DriftResult,
    DRIFT_THRESHOLD
)
from .reindex_manager import (
    ReindexManager,
    ReindexJob,
    ReindexReason,
    ReindexQueue
)
from .config import (
    ReliabilityConfig,
    StalenessConfig,
    DriftConfig,
    ReindexConfig,
    MetricsConfig,
    get_config,
    get_reliability_config,
    validate_config,
    reload_config
)

__all__ = [
    # Version tracking
    'EmbeddingVersion',
    'VersionTracker',
    'get_current_version',
    'CURRENT_VERSION',
    'SCHEMA_VERSION',
    'CONTENT_VERSION',
    'MODEL_FAMILY',
    
    # Staleness detection
    'StalenessDetector',
    'StalenessReason',
    'StaleEmbedding',
    
    # Fingerprinting
    'compute_fingerprint',
    'FingerprintTracker',
    
    # Drift detection
    'DriftDetector',
    'DriftResult',
    'DRIFT_THRESHOLD',
    
    # Reindexing
    'ReindexManager',
    'ReindexJob',
    'ReindexReason',
    'ReindexQueue',
    
    # Configuration
    'ReliabilityConfig',
    'StalenessConfig',
    'DriftConfig',
    'ReindexConfig',
    'MetricsConfig',
    'get_config',
    'get_reliability_config',
    'validate_config',
    'reload_config',
]
    'ReindexManager',
    'ReindexJob',
    'ReindexReason',
]
