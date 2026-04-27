import random
import time
from typing import List

from openai import OpenAI, OpenAIError

def get_llm_response(messages: List[str], opt):
    client = OpenAI(api_key=opt.api_key, base_url=opt.base_url)
    messages = [{"role": "user" if i % 2 == 0 else "assistant", "content": messages[i]} for i in range(len(messages))]
    max_retries = getattr(opt, "llm_max_retries", 8)
    retry_base_seconds = getattr(opt, "llm_retry_base_seconds", 5.0)

    for attempt in range(max_retries + 1):
        try:
            chat_completion = client.chat.completions.create(
                messages=messages,
                model=opt.model,
            )
            return chat_completion.choices[0].message.content
        except (OpenAIError, TimeoutError, ConnectionError) as exc:
            if attempt >= max_retries:
                raise
            sleep_seconds = min(retry_base_seconds * (2 ** attempt), 120.0)
            sleep_seconds += random.uniform(0, retry_base_seconds)
            print(
                f"LLM request failed ({exc.__class__.__name__}: {exc}); "
                f"retrying {attempt + 1}/{max_retries} in {sleep_seconds:.1f}s",
                flush=True,
            )
            time.sleep(sleep_seconds)
