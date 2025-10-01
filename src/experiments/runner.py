from __future__ import annotations

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import os
import json
import time
import subprocess
from datetime import datetime

from src.data.ec2_stream import CloudWatchEC2Stream
from src.analyzers.llm import ContextAwareLLMAnalyzer
from src.analyzers.ollama_analyzer import OllamaAnalyzer
from src.data.log_filters import apply_filters, drop_health_checks, drop_noise_levels, redact_secrets
from src.visualization.charts import ChartGenerator


@dataclass
class TerraformOutputs:
    public_ip: str
    log_group_name: str


def _run(cmd: List[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    return result


def terraform_apply(terraform_dir: str, variables: Dict[str, Any]) -> TerraformOutputs:
    _run(["terraform", "init"], cwd=terraform_dir)
    apply_cmd = ["terraform", "apply", "-auto-approve"]
    for k, v in variables.items():
        apply_cmd.extend(["-var", f"{k}={v}"])
    _run(apply_cmd, cwd=terraform_dir)
    out = _run(["terraform", "output", "-json"], cwd=terraform_dir)
    outputs = json.loads(out.stdout)
    return TerraformOutputs(
        public_ip=str(outputs["public_ip"]["value"]),
        log_group_name=str(outputs["log_group_name"]["value"])
    )


def terraform_destroy(terraform_dir: str, variables: Dict[str, Any]) -> None:
    destroy_cmd = ["terraform", "destroy", "-auto-approve"]
    for k, v in variables.items():
        destroy_cmd.extend(["-var", f"{k}={v}"])
    _run(destroy_cmd, cwd=terraform_dir)


def stream_and_analyze(
    log_group: str,
    region: Optional[str],
    api_key: Optional[str],
    duration_seconds: int,
    chunk_size: int,
    output_dir: str,
    dashboard_filename: str = "stream_dashboard.html",
    provider: str = "openai",
    model: str = "gpt-4o-mini",
    ollama_host: str = "http://localhost:11434",
    enable_filters: bool = True
) -> Dict[str, Any]:
    os.makedirs(output_dir, exist_ok=True)
    if provider == 'openai':
        analyzer = ContextAwareLLMAnalyzer(api_key=api_key or "", model=model)
    else:
        analyzer = OllamaAnalyzer(model=model, host=ollama_host)
    streamer = CloudWatchEC2Stream(log_group=log_group, region=region)
    generator = ChartGenerator()

    buffer: List[str] = []
    end_time = time.monotonic() + duration_seconds
    last_write = 0.0

    for line in streamer.poll():
        line_in = line
        buffer.append(line_in)
        if len(buffer) >= chunk_size:
            chunk = buffer
            if enable_filters:
                chunk = apply_filters(chunk, [redact_secrets, drop_health_checks, drop_noise_levels])
            analyzer.analyze_chunk(chunk)
            buffer = []

        now = time.monotonic()
        if now - last_write > 30.0:
            results = analyzer.get_results()
            generator.create_dashboard(results, filename=os.path.join(output_dir, dashboard_filename))
            last_write = now

        if now >= end_time:
            break

    final_results = analyzer.get_results()
    results_path = os.path.join(output_dir, "analyzer_results.json")
    with open(results_path, 'w') as f:
        json.dump(final_results, f, indent=2)

    return final_results


def _safe_write_json(path: str, data: Any) -> None:
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        with open(path, 'w') as f:
            f.write(json.dumps({"error": str(e)}))


def query_elk_optional(endpoint: Optional[str], cloud_id: Optional[str], api_key: Optional[str], index: Optional[str], term_field: Optional[str], term_value: Optional[str], query_json: Optional[str]) -> Dict[str, Any]:
    if not index:
        return {}
    try:
        from src.data.elk import ElasticsearchClient
        client = ElasticsearchClient(endpoint=endpoint or "", api_key=api_key, cloud_id=cloud_id)
        if query_json:
            query = json.loads(query_json)
            docs = client.search_logs(index=index, query=query)
        else:
            if not (term_field and term_value):
                return {}
            docs = client.term_query(index=index, field=term_field, value=term_value)
        return {"count": len(docs), "samples": docs[:10]}
    except Exception as e:
        return {"error": str(e)}


def query_splunk_optional(host: Optional[str], port: int, username: Optional[str], password: Optional[str], query: Optional[str], earliest: str, latest: str) -> Dict[str, Any]:
    if not (host and username and password and query):
        return {}
    try:
        from src.data.splunk import SplunkClient
        client = SplunkClient(host=host, port=port, username=username, password=password)
        rows = client.search(query=query, earliest=earliest, latest=latest)
        return {"count": len(rows), "samples": rows[:10]}
    except Exception as e:
        return {"error": str(e)}


def run_experiment(
    terraform_dir: str,
    region: str,
    key_name: str,
    api_key: str,
    duration_seconds: int = 300,
    chunk_size: int = 5,
    out_root: str = None,
    destroy_after: bool = True,
    elk_params: Optional[Dict[str, Any]] = None,
    splunk_params: Optional[Dict[str, Any]] = None,
    provider: str = "openai",
    model: str = "gpt-4o-mini",
    ollama_host: str = "http://localhost:11434",
    enable_filters: bool = True
) -> str:
    if out_root is None:
        out_root = os.getenv('RESULTS_ROOT', 'results') + '/experiments'
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(out_root, f"run_{ts}")
    os.makedirs(out_dir, exist_ok=True)

    variables = {
        "region": region,
        "key_name": key_name
    }

    meta: Dict[str, Any] = {
        "start_time": datetime.now().isoformat(),
        "region": region
    }

    try:
        tf_out = terraform_apply(terraform_dir, variables)
        meta["public_ip"] = tf_out.public_ip
        meta["log_group_name"] = tf_out.log_group_name

        # Allow time for containers to start and logs to appear
        time.sleep(45)

        final_results = stream_and_analyze(
            log_group=tf_out.log_group_name,
            region=region,
            api_key=api_key,
            duration_seconds=duration_seconds,
            chunk_size=chunk_size,
            output_dir=out_dir,
            provider=provider,
            model=model,
            ollama_host=ollama_host,
            enable_filters=enable_filters
        )

        # Optional ELK/Splunk comparisons
        elk_params = elk_params or {}
        elk_result = query_elk_optional(
            endpoint=elk_params.get("endpoint"),
            cloud_id=elk_params.get("cloud_id"),
            api_key=elk_params.get("api_key"),
            index=elk_params.get("index"),
            term_field=elk_params.get("term_field"),
            term_value=elk_params.get("term_value"),
            query_json=elk_params.get("query_json")
        )
        _safe_write_json(os.path.join(out_dir, "elk_samples.json"), elk_result)

        splunk_params = splunk_params or {}
        splunk_result = query_splunk_optional(
            host=splunk_params.get("host"),
            port=int(splunk_params.get("port", 8089)),
            username=splunk_params.get("username"),
            password=splunk_params.get("password"),
            query=splunk_params.get("query"),
            earliest=splunk_params.get("earliest", "-24h"),
            latest=splunk_params.get("latest", "now")
        )
        _safe_write_json(os.path.join(out_dir, "splunk_samples.json"), splunk_result)

        meta["end_time"] = datetime.now().isoformat()
        meta_path = os.path.join(out_dir, "experiment_meta.json")
        _safe_write_json(meta_path, meta)
        return out_dir

    finally:
        if destroy_after:
            try:
                terraform_destroy(terraform_dir, variables)
            except Exception as e:
                with open(os.path.join(out_dir, "destroy_error.txt"), 'w') as f:
                    f.write(str(e))


