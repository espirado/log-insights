# src/analyzers/enhanced_analyzer.py
from typing import List, Dict, Any, Generator
import time
import asyncio
from datetime import datetime
from collections import defaultdict
import openai

class EnhancedLogAnalyzer:
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.analysis_history = defaultdict(list)
        self.performance_metrics = {
            'response_times': [],
            'success_rate': [],
            'error_counts': defaultdict(int)
        }

    async def analyze_logs(self, logs: List[str]) -> Dict[str, Any]:
        """Analyze logs with performance tracking and error handling"""
        start_time = time.time()
        
        try:
            # Determine log context
            context = self._determine_context(logs)
            prompt = self._build_analysis_prompt(logs, context)
            
            # Get LLM analysis
            response = await self._get_llm_analysis(prompt)
            analysis = self._parse_and_validate_response(response, context)
            
            # Update metrics
            self._update_metrics(time.time() - start_time, True)
            
            # Store analysis for pattern detection
            self._store_analysis(analysis)
            
            return analysis
            
        except Exception as e:
            self._update_metrics(time.time() - start_time, False)
            self.performance_metrics['error_counts'][str(e)] += 1
            return self._get_error_analysis(str(e))

    def _determine_context(self, logs: List[str]) -> str:
        """Determine the primary context of logs"""
        context_patterns = {
            'kubernetes': ['pod', 'node', 'container', 'k8s', 'deployment'],
            'database': ['sql', 'db', 'query', 'database', 'postgres'],
            'security': ['auth', 'permission', 'access', 'security', 'breach'],
            'network': ['connection', 'timeout', 'latency', 'network'],
            'application': ['error', 'exception', 'service', 'api']
        }
        
        context_scores = defaultdict(int)
        for log in logs:
            log_lower = log.lower()
            for context, patterns in context_patterns.items():
                if any(pattern in log_lower for pattern in patterns):
                    context_scores[context] += 1
        
        return max(context_scores.items(), key=lambda x: x[1])[0] if context_scores else 'unknown'

    async def _get_llm_analysis(self, prompt: str) -> Dict[str, Any]:
        """Get analysis from LLM with error handling"""
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[{
                    "role": "system",
                    "content": "You are an expert log analyzer. Provide detailed technical analysis."
                }, {
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"LLM Analysis failed: {str(e)}")

    def _parse_and_validate_response(self, response: str, context: str) -> Dict[str, Any]:
        """Parse and validate LLM response"""
        import json
        try:
            analysis = json.loads(response)
            
            # Validate required fields
            required_fields = ['category', 'severity', 'root_cause', 'remediation']
            for field in required_fields:
                if field not in analysis:
                    analysis[field] = 'unknown'
            
            # Add metadata
            analysis['context'] = context
            analysis['timestamp'] = datetime.now().isoformat()
            analysis['confidence_score'] = self._calculate_confidence(analysis)
            
            return analysis
            
        except json.JSONDecodeError:
            raise Exception("Invalid JSON response from LLM")

    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calculate confidence score for analysis"""
        score = 1.0
        
        # Reduce score for unknown values
        for key in ['category', 'severity', 'root_cause', 'remediation']:
            if analysis.get(key) == 'unknown':
                score *= 0.8
        
        # Check root cause length
        if len(analysis.get('root_cause', '')) < 20:
            score *= 0.9
            
        # Check remediation specificity
        if len(analysis.get('remediation', '')) < 30:
            score *= 0.9
            
        return round(score, 2)

    def _store_analysis(self, analysis: Dict[str, Any]):
        """Store analysis for pattern detection"""
        category = analysis['category']
        self.analysis_history[category].append({
            'timestamp': analysis['timestamp'],
            'severity': analysis['severity'],
            'confidence': analysis['confidence_score']
        })

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get analyzer performance metrics"""
        if not self.performance_metrics['response_times']:
            return {'error': 'No metrics available'}
            
        return {
            'avg_response_time': sum(self.performance_metrics['response_times']) / len(self.performance_metrics['response_times']),
            'success_rate': sum(self.performance_metrics['success_rate']) / len(self.performance_metrics['success_rate']),
            'error_distribution': dict(self.performance_metrics['error_counts']),
            'total_analyses': len(self.performance_metrics['response_times'])
        }

    def _update_metrics(self, response_time: float, success: bool):
        """Update performance metrics"""
        self.performance_metrics['response_times'].append(response_time)
        self.performance_metrics['success_rate'].append(1 if success else 0)