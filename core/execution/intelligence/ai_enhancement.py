"""
AI Enhancement Layer (OPTIONAL)

Provides optional AI-powered enhancements to deterministic classification.

CRITICAL: AI never overrides deterministic classification.
AI only enhances by:
- Adjusting confidence based on historical patterns
- Providing more detailed explanations
- Suggesting potential fixes
- Correlating with similar past failures

IMPROVEMENTS (Based on AI Analysis Feedback):
1. Failure clustering to reduce redundancy
2. Structured prompt templates with mandatory JSON output
3. Post-processing to remove LLM verbosity/noise
4. Severity and confidence scoring
5. Evidence linking back to logs

System works perfectly WITHOUT AI - this is purely additive.
"""

from typing import List, Dict, Any, Optional
import logging
import re
import json

from core.execution.intelligence.models import (
    FailureClassification,
    FailureSignal,
    ExecutionEvent,
    FailureType,
)
from core.execution.intelligence.failure_clustering import (
    cluster_similar_failures,
    FailureCluster
)
from core.logging import get_logger

logger = get_logger(__name__)


class AIEnhancer:
    """
    AI enhancement layer for failure classification.
    
    Works as an OPTIONAL plugin - system functions fully without it.
    
    IMPROVEMENTS:
    - Clusters similar failures before AI analysis (reduces redundancy)
    - Uses structured prompts with mandatory JSON output
    - Sanitizes LLM verbosity and noise
    - Provides severity scoring and confidence metadata
    - Links evidence back to original logs
    """
    
    def __init__(
        self,
        ai_provider: Any,
        enable_clustering: bool = True,
        cluster_threshold: float = 0.8
    ):
        """
        Initialize AI enhancer.
        
        Args:
            ai_provider: AI provider instance (e.g., OpenAI, Anthropic, Ollama)
            enable_clustering: Enable failure clustering before analysis
            cluster_threshold: Similarity threshold for clustering (0.0-1.0)
        """
        self.ai_provider = ai_provider
        self.enable_clustering = enable_clustering
        self.cluster_threshold = cluster_threshold
    
    def enhance(
        self,
        classification: FailureClassification,
        signals: List[FailureSignal],
        events: List[ExecutionEvent],
        context: Dict[str, Any]
    ) -> FailureClassification:
        """
        Enhance classification with AI reasoning.
        
        Args:
            classification: Original deterministic classification
            signals: Extracted failure signals
            events: Execution events
            context: Additional context
            
        Returns:
            Enhanced classification (never overrides failure_type)
        """
        try:
            # Step 1: Cluster similar failures (if enabled)
            if self.enable_clustering and len(signals) > 1:
                logger.debug(f"Clustering {len(signals)} failure signals")
                clusters = cluster_similar_failures(
                    signals,
                    threshold=self.cluster_threshold,
                    use_semantic=False  # Use rule-based for speed
                )
                logger.info(
                    f"Reduced {len(signals)} signals to {len(clusters)} clusters "
                    f"({(1-len(clusters)/len(signals))*100:.1f}% reduction)"
                )
            else:
                # No clustering - treat each signal as its own cluster
                clusters = []
            
            # Step 2: Build structured AI prompt
            prompt = self._build_structured_prompt(
                classification,
                clusters if clusters else signals,
                events,
                context
            )
            
            # Step 3: Query AI with structured output enforcement
            ai_response = self._query_ai_structured(prompt)
            
            # Step 4: Sanitize LLM output (remove noise/apologies)
            ai_response = self._sanitize_llm_output(ai_response)
            
            # Step 5: Parse AI response and enhance classification
            enhanced_classification = self._parse_ai_response(
                classification,
                ai_response,
                signals
            )
            
            # Mark as AI-enhanced
            enhanced_classification.ai_enhanced = True
            enhanced_classification.ai_reasoning = ai_response.get('reasoning', '')
            
            logger.info(
                f"AI enhancement applied: confidence {classification.confidence:.2f} -> "
                f"{enhanced_classification.confidence:.2f}, "
                f"severity: {ai_response.get('severity', 'N/A')}"
            )
            
            return enhanced_classification
        
        except Exception as e:
            logger.error(f"AI enhancement failed: {str(e)}", exc_info=True)
            # Return original classification on error
            return classification
    
    def _build_structured_prompt(
        self,
        classification: FailureClassification,
        data: Any,  # Can be clusters or signals
        events: List[ExecutionEvent],
        context: Dict[str, Any]
    ) -> str:
        """
        Build structured prompt with mandatory JSON output format.
        
        This enforces consistent, actionable outputs across all AI providers.
        Matches Recommendation #2: Standardize LLM Prompt Template.
        """
        # Build evidence summary
        if isinstance(data, list) and len(data) > 0:
            if hasattr(data[0], 'representative_signal'):
                # Clustered data
                evidence_lines = []
                for cluster in data[:5]:  # Top 5 clusters
                    evidence_lines.append(
                        f"- [{cluster.severity}] {cluster.representative_signal.message[:100]} "
                        f"(occurred {cluster.count}x)"
                    )
                evidence_summary = '\n'.join(evidence_lines)
            else:
                # Raw signals
                evidence_summary = '\n'.join([
                    f"- {s.signal_type.value}: {s.message[:100]}"
                    for s in data[:5]
                ])
        else:
            evidence_summary = "No specific signals extracted"
        
        # Build strict structured prompt
        prompt = f"""You are an expert test failure analyzer. Analyze this test failure and provide structured output.

### DETERMINED CLASSIFICATION (DO NOT OVERRIDE)
- Failure Type: {classification.failure_type.value}
- Confidence: {classification.confidence:.2f}
- Rule Matched: {classification.rule_matched or 'N/A'}
- Reason: {classification.reason}

### FAILURE EVIDENCE
{evidence_summary}

### INSTRUCTIONS (STRICT - VIOLATIONS WILL BE REJECTED)
1. NEVER include apologies like "I'm sorry", "Unfortunately", "I cannot"
2. NEVER include disclaimers like "As an AI", "based on my training", "I don't have access"
3. NEVER include hedging like "It appears", "It seems", "likely", "probably" in root cause
4. NEVER include model/company references (Deepseek, OpenAI, Anthropic, Claude)
5. DO NOT change the failure type classification
6. START directly with technical analysis - no preamble
7. Group similar failures and identify concrete patterns
8. For each finding, provide:
   - Root Cause: Direct, specific technical cause (no hedging)
   - Evidence: Exact log entries that prove the cause
   - Recommended Action: Concrete fix steps with code/config examples
   - Severity: High/Medium/Low based on impact
   - Confidence Score: 0.0-1.0 (1.0 = certain, 0.5 = uncertain)

### OUTPUT JSON (MANDATORY FORMAT)
Respond ONLY with valid JSON in this exact structure:
{{
  "findings": [
    {{
      "rootCause": "Concise root cause description",
      "evidence": [
        {{"text": "Log message", "logIndex": 0}}
      ],
      "recommendedAction": "Specific action to fix",
      "severity": "High|Medium|Low",
      "confidenceScore": 0.85
    }}
  ],
  "overallSeverity": "High|Medium|Low",
  "confidenceAdjustment": 0.0,
  "reasoning": "Brief explanation of analysis"
}}

CRITICAL: Output ONLY the JSON. No extra text, no apologies, no markdown.
"""
        return prompt
    
    def _query_ai_structured(self, prompt: str) -> Dict[str, Any]:
        """
        Query AI provider with structured output enforcement.
        
        Handles different AI providers and enforces JSON output.
        """
        try:
            # Query based on provider capabilities
            if hasattr(self.ai_provider, 'complete'):
                response_text = self.ai_provider.complete(prompt)
            elif hasattr(self.ai_provider, 'chat'):
                response_text = self.ai_provider.chat([
                    {"role": "system", "content": "You are a test failure analyzer. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ])
            else:
                raise ValueError("AI provider does not support completion or chat")
            
            # Parse JSON response
            return self._extract_json_from_response(response_text)
        
        except Exception as e:
            logger.error(f"AI query failed: {e}")
            # Return minimal fallback response
            return {
                "findings": [],
                "overallSeverity": "Medium",
                "confidenceAdjustment": 0.0,
                "reasoning": f"AI query failed: {str(e)}"
            }
    
    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """
        Extract JSON from AI response.
        
        Handles various response formats:
        - Pure JSON
        - JSON in markdown code blocks
        - JSON with extra text
        """
        # Try direct JSON parse first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try extracting from markdown code blocks
        json_patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'\{.*\}',  # Find any JSON object
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                try:
                    json_str = match.group(1) if match.lastindex else match.group(0)
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue
        
        # Fallback: return error wrapped as valid response
        logger.warning(f"Could not extract valid JSON from AI response: {response[:200]}")
        return {
            "findings": [],
            "overallSeverity": "Medium",
            "confidenceAdjustment": 0.0,
            "reasoning": "Could not parse AI response"
        }
    
    def _sanitize_llm_output(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove LLM verbosity, apologies, and generic disclaimers.
        
        Aggressively filters wordy AI responses to keep only technical content.
        Matches Recommendation #3: Post-Process LLM Outputs.
        """
        # Expanded patterns to remove (case-insensitive)
        noise_patterns = [
            # Direct apologies
            r"(?i)I'?m sorry(?:,| that| but)?.*?\.",
            r"(?i)I am sorry(?:,| that| but)?.*?\.",
            r"(?i)Unfortunately(?:,)?.*?\.",
            # AI/Model references
            r"(?i)As an? (?:large language model|AI|assistant|language model).*?\.",
            r"(?i)(?:developed|created|trained) by (?:Deepseek|OpenAI|Anthropic|Claude).*?\.",
            r"(?i)My (?:training data|primary function|main purpose|knowledge cutoff).*?\.",
            # Capability disclaimers
            r"(?i)I (?:don'?t|do not|can'?t|cannot) (?:have access|provide|determine|verify|confirm).*?\.",
            r"(?i)Without (?:more|actual|specific|complete|additional) (?:context|information|details|data).*?\.",
            # Generic hedging (when used as standalone sentence)
            r"(?i)(?:^|\. )(?:Please note|It'?s (?:important|worth) noting?|Keep in mind|However|Nevertheless) that.*?\.",
            r"(?i)(?:^|\. )(?:It appears|It seems|This (?:might|could|may) (?:be|indicate)).*?\.",
            # Based on my analysis (when vague)
            r"(?i)Based on (?:my|the) (?:training|analysis),.*?\.",
        ]
        
        def clean_text(text: str) -> str:
            """Remove noise patterns from text and strip leading hedging phrases"""
            if not text:
                return text
            
            # Apply all noise removal patterns
            for pattern in noise_patterns:
                text = re.sub(pattern, '', text)
            
            # Strip leading hedging words that start sentences
            text = re.sub(r'^(?:Likely|Probably|Possibly|Perhaps|Maybe|Potentially)[,:]?\s*', '', text, flags=re.IGNORECASE)
            text = re.sub(r'^(?:The|This) (?:root cause|issue|error|failure) (?:appears to be|seems to be|is likely|is probably)\s*', '', text, flags=re.IGNORECASE)
            
            # Clean up extra whitespace
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            # Remove if text is now too short or meaningless
            if len(text) < 10:
                return ""
            
            return text
        
        # Clean all text fields
        if 'reasoning' in response:
            response['reasoning'] = clean_text(response['reasoning'])
        
        if 'findings' in response:
            for finding in response['findings']:
                if 'rootCause' in finding:
                    finding['rootCause'] = clean_text(finding['rootCause'])
                if 'recommendedAction' in finding:
                    finding['recommendedAction'] = clean_text(finding['recommendedAction'])
        
        return response
    
    def _parse_ai_response(
        self,
        classification: FailureClassification,
        ai_response: Dict[str, Any],
        signals: List[FailureSignal]
    ) -> FailureClassification:
        """
        Parse AI response and enhance classification.
        
        Includes:
        - Confidence adjustment (clamped to ±0.1)
        - Severity scoring
        - Evidence linking back to logs
        - Structured findings with actionable recommendations
        """
        # Extract confidence adjustment (small adjustments only)
        confidence_adj = ai_response.get('confidenceAdjustment', 0.0)
        confidence_adj = max(-0.1, min(0.1, confidence_adj))  # Clamp to ±0.1
        
        new_confidence = classification.confidence + confidence_adj
        new_confidence = max(0.0, min(1.0, new_confidence))  # Clamp to [0, 1]
        
        # Build enhanced reason from AI findings
        reason_parts = [classification.reason]
        
        # Extract severity
        severity = ai_response.get('overallSeverity', 'Medium')
        
        # Process AI findings
        findings = ai_response.get('findings', [])
        if findings:
            reason_parts.append("\n\n=== AI Analysis ===")
            
            for idx, finding in enumerate(findings[:3], 1):  # Top 3 findings
                root_cause = finding.get('rootCause', '')
                action = finding.get('recommendedAction', '')
                finding_severity = finding.get('severity', 'Medium')
                confidence = finding.get('confidenceScore', 0.0)
                
                if root_cause:
                    reason_parts.append(
                        f"\n{idx}. [{finding_severity}] {root_cause} "
                        f"(confidence: {confidence:.2f})"
                    )
                
                if action:
                    reason_parts.append(f"   → Fix: {action}")
                
                # Add evidence references
                evidence_list = finding.get('evidence', [])
                if evidence_list and len(evidence_list) > 0:
                    evidence_text = evidence_list[0].get('text', '') if isinstance(evidence_list[0], dict) else str(evidence_list[0])
                    if evidence_text:
                        reason_parts.append(f"   → Evidence: {evidence_text[:80]}...")
        
        # Add AI reasoning if available
        if ai_response.get('reasoning'):
            reason_parts.append(f"\n\nReasoning: {ai_response['reasoning']}")
        
        enhanced_reason = '\n'.join(reason_parts)
        
        # Create enhanced classification
        return FailureClassification(
            failure_type=classification.failure_type,  # NEVER change this
            confidence=new_confidence,
            reason=enhanced_reason,
            evidence=classification.evidence,
            code_reference=classification.code_reference,
            rule_matched=classification.rule_matched,
            ai_enhanced=True,
            ai_reasoning=ai_response.get('reasoning', ''),
            similar_failures_count=classification.similar_failures_count,
            last_seen=classification.last_seen,
        )


class HistoricalCorrelation:
    """
    Correlates current failure with historical failures.
    
    This can help identify:
    - Flaky tests (intermittent failures)
    - Known issues (recurring patterns)
    - Recent regressions (new failure patterns)
    """
    
    def __init__(self, database_path: Optional[str] = None):
        """
        Initialize historical correlation.
        
        Args:
            database_path: Path to historical failure database
        """
        self.database_path = database_path
    
    def correlate(
        self,
        classification: FailureClassification,
        test_name: str,
        lookback_days: int = 30
    ) -> FailureClassification:
        """
        Correlate with historical failures.
        
        Args:
            classification: Current classification
            test_name: Test name
            lookback_days: Days to look back
            
        Returns:
            Enhanced classification with historical context
        """
        # TODO: Implement database query
        # This would query a historical failure database and:
        # 1. Count similar failures
        # 2. Find last occurrence
        # 3. Identify if this is a new pattern
        # 4. Check if this is a known flaky test
        
        # For now, return as-is
        return classification


class MultiProviderAggregator:
    """
    Aggregates insights from multiple AI providers for consensus-based analysis.
    
    Matches Recommendation #6: Provide Multiple Suggestions Based on Models.
    """
    
    def __init__(self, providers: Dict[str, Any]):
        """
        Initialize multi-provider aggregator.
        
        Args:
            providers: Dict mapping provider names to provider instances
                       e.g., {"openai": openai_provider, "anthropic": anthropic_provider}
        """
        self.providers = providers
        self.enhancers = {
            name: AIEnhancer(provider)
            for name, provider in providers.items()
        }
    
    def enhance_with_consensus(
        self,
        classification: FailureClassification,
        signals: List[FailureSignal],
        events: List[ExecutionEvent],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get consensus analysis from multiple AI providers.
        
        Args:
            classification: Original classification
            signals: Failure signals
            events: Execution events
            context: Additional context
            
        Returns:
            Dict with consensus and individual provider reports:
            {
                "consensus": enhanced_classification,
                "provider_reports": {
                    "openai": {...},
                    "anthropic": {...},
                    ...
                },
                "agreement_score": 0.85
            }
        """
        provider_results = {}
        
        # Get analysis from each provider
        for provider_name, enhancer in self.enhancers.items():
            try:
                enhanced = enhancer.enhance(
                    classification, signals, events, context
                )
                provider_results[provider_name] = {
                    "classification": enhanced,
                    "confidence": enhanced.confidence,
                    "reasoning": enhanced.ai_reasoning
                }
            except Exception as e:
                logger.error(f"Provider {provider_name} failed: {e}")
                provider_results[provider_name] = {"error": str(e)}
        
        # Calculate consensus
        confidences = [
            r["confidence"]
            for r in provider_results.values()
            if "confidence" in r
        ]
        
        if not confidences:
            # No providers succeeded - return original
            return {
                "consensus": classification,
                "provider_reports": provider_results,
                "agreement_score": 0.0
            }
        
        # Consensus confidence is average
        consensus_confidence = sum(confidences) / len(confidences)
        
        # Agreement score (how similar the confidences are)
        if len(confidences) > 1:
            confidence_variance = sum(
                (c - consensus_confidence) ** 2
                for c in confidences
            ) / len(confidences)
            agreement_score = max(0.0, 1.0 - confidence_variance)
        else:
            agreement_score = 1.0
        
        # Build consensus classification
        consensus = FailureClassification(
            failure_type=classification.failure_type,
            confidence=consensus_confidence,
            reason=self._merge_reasoning(provider_results, classification),
            evidence=classification.evidence,
            code_reference=classification.code_reference,
            rule_matched=classification.rule_matched,
            ai_enhanced=True,
            ai_reasoning=f"Consensus from {len(confidences)} providers (agreement: {agreement_score:.2f})"
        )
        
        return {
            "consensus": consensus,
            "provider_reports": provider_results,
            "agreement_score": agreement_score
        }
    
    def _merge_reasoning(
        self,
        provider_results: Dict[str, Dict],
        original: FailureClassification
    ) -> str:
        """Merge reasoning from multiple providers"""
        parts = [original.reason, "\n\n=== Multi-Provider Analysis ==="]
        
        for provider_name, result in provider_results.items():
            if "reasoning" in result and result["reasoning"]:
                parts.append(f"\n[{provider_name.upper()}]: {result['reasoning']}")
        
        return '\n'.join(parts)
