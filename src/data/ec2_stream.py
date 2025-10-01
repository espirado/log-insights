from typing import Generator, Optional
import os
import time
from datetime import datetime, timedelta


class CloudWatchEC2Stream:
    """
    Pull logs from CloudWatch for a given log group/stream and yield lines.
    Requires AWS credentials configured in environment (boto3 default chain).
    """

    def __init__(
        self,
        log_group: str,
        log_stream: Optional[str] = None,
        region: Optional[str] = None,
        poll_seconds: int = 5
    ):
        import boto3
        self.client = boto3.client('logs', region_name=region)
        self.log_group = log_group
        self.log_stream = log_stream
        self.poll_seconds = poll_seconds
        self.next_token = None

    def poll(self) -> Generator[str, None, None]:
        while True:
            try:
                kwargs = {
                    'logGroupName': self.log_group,
                    'limit': 10000
                }
                if self.log_stream:
                    kwargs['logStreamNames'] = [self.log_stream]
                if self.next_token:
                    kwargs['nextToken'] = self.next_token

                resp = self.client.filter_log_events(**kwargs)
                events = resp.get('events', [])
                for e in events:
                    msg = e.get('message', '').strip()
                    if msg:
                        yield msg
                self.next_token = resp.get('nextToken', self.next_token)
            except Exception as e:
                print(f"CloudWatch poll error: {str(e)}")

            time.sleep(self.poll_seconds)








