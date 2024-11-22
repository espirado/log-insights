# src/analyzers/llm.py
from typing import List, Dict, Any
import time
import openai
from datetime import datetime
from .base import BaseAnalyzer

class ContextAwareLLMAnalyzer(BaseAnalyzer):
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        super().__init__()
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.context_patterns = {
            'kubernetes': ['pod', 'node', 'deployment', 'container', 'namespace', 'kubectl'],
            'database': ['postgresql', 'mysql', 'database', 'query', 'sql'],
            'infrastructure': ['ec2', 'vm', 'instance', 'cpu', 'memory', 'disk'],
            'application': ['application', 'service', 'api', 'endpoint']
        }

    def process_stream(self, log_stream: Any):
        """
        Implementation of abstract method for stream processing
        """
        raise NotImplementedError("Real-time stream processing not implemented yet")

    def _build_analysis_prompt(self, logs: List[str]) -> str:
        """
        Build a context-aware prompt for log analysis
        """
        return f"""As an experienced SRE, analyze these logs with focus on infrastructure context.
        First, determine the log context (type of system generating these logs).
        Then identify specific issues and their impact.

        Context Categories:
        1. Kubernetes Logs - Container orchestration issues (pods, nodes, deployments)
        2. Database Logs - Database performance, connectivity, query issues
        3. Infrastructure Logs - VM/EC2 resource utilization (CPU, memory, disk)
        4. Application Logs - Service-level issues, API errors

        For each issue, determine:
        1. Primary Context: Which system is generating these logs
        2. Secondary Context: Specific component involved
        3. Issue Type: Specific problem or error condition
        4. Resource Impact: What resources are affected

        Return analysis in JSON format:
        {{
            "context": "Primary system context (Kubernetes/Database/Infrastructure/Application)",
            "category": "Specific category (CPU/Memory/Network/Storage/Security)",
            "severity": "Critical/High/Medium/Low",
            "component": "Specific component affected",
            "root_cause": "Technical explanation of the issue",
            "remediation": "Specific actions to resolve",
            "timestamp": "timestamp from relevant log"
        }}

        Ensure categorization is precise:
        - Database issues should be categorized as Database even if they appear in Kubernetes logs
        - Resource issues (CPU/Memory) should specify if they're VM/Container level
        - Security issues should note the affected system level

        Logs to analyze:
        {'\n'.join(logs)}
        """

    def analyze_chunk(self, logs: List[str]) -> Dict[str, Any]:
        """
        Analyze a chunk of logs using LLM with context awareness
        """
        start_time = time.time()
        
        # Determine predominant context
        context = self._determine_context(logs)
        
        prompt = self._build_analysis_prompt(logs)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": f"You are an expert SRE analyzing {context} logs. Focus on precise categorization and technical accuracy."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            print(f"\nLLM Response: {response.choices[0].message.content}")
            
            # Parse and validate response
            analysis = self._parse_and_validate_response(response.choices[0].message.content, context)
            
            # Update metrics
            self._update_results(analysis)
            
            # Update processing time
            self.processing_time += time.time() - start_time
            
            return analysis
            
        except Exception as e:
            print(f"Error in analysis: {str(e)}")
            return self._get_error_analysis()

    def _determine_context(self, logs: List[str]) -> str:
        """
        Determine the predominant context of the logs
        """
        context_counts = {context: 0 for context in self.context_patterns.keys()}
        
        for log in logs:
            log_lower = log.lower()
            for context, patterns in self.context_patterns.items():
                if any(pattern in log_lower for pattern in patterns):
                    context_counts[context] += 1
        
        # Get context with highest count
        predominant_context = max(context_counts.items(), key=lambda x: x[1])[0]
        print(f"Detected context: {predominant_context}")
        return predominant_context

    def _parse_and_validate_response(self, response: str, detected_context: str) -> Dict[str, Any]:
        """
        Parse and validate LLM response with context awareness
        """
        try:
            import json
            analysis = json.loads(response)
            
            # Validate and enhance context
            if 'context' not in analysis:
                analysis['context'] = detected_context
            
            # Ensure component specification
            if 'component' not in analysis:
                analysis['component'] = 'undefined'
            
            required_fields = [
                'category', 'severity', 'root_cause', 'remediation', 'timestamp'
            ]
            
            for field in required_fields:
                if field not in analysis:
                    analysis[field] = None
            
            return analysis
            
        except json.JSONDecodeError:
            print("Failed to parse LLM response")
            return self._get_error_analysis()

    def _get_error_analysis(self) -> Dict[str, Any]:
        """
        Return a default analysis object for error cases
        """
        return {
            'context': 'Unknown',
            'category': 'Unknown',
            'severity': 'Unknown',
            'component': 'Unknown',
            'root_cause': 'Analysis failed',
            'remediation': 'Manual investigation required',
            'timestamp': datetime.now().isoformat()
        }

    def _update_results(self, analysis: Dict[str, Any]):
        """
        Update the analyzer's results with new analysis
        """
        # Update issue counts by context and category
        context = analysis.get('context', 'Unknown')
        category = analysis.get('category', 'Unknown')
        
        # Update context-based issues
        self.results['issues'][context] = self.results['issues'].get(context, 0) + 1
        
        # Update severity counts
        severity = analysis.get('severity', 'Unknown')
        self.results['severities'][severity] = self.results['severities'].get(severity, 0) + 1
        
        # Add to timeline with enhanced context
        self.results['timeline'].append({
            'timestamp': analysis.get('timestamp', datetime.now().isoformat()),
            'context': context,
            'category': category,
            'component': analysis.get('component', 'Unknown'),
            'severity': severity,
            'root_cause': analysis.get('root_cause', ''),
            'remediation': analysis.get('remediation', '')
        })