from __future__ import annotations

import datetime
import json
from pathlib import Path

from akms.core.message import Message, Role


class ConversationLogger:
    def __init__(self, logs_dir: str) -> None:
        self._logs_dir = Path(logs_dir)

    def _log_path(self, agent_type: str, conversation_id: str) -> Path:
        date = datetime.date.today().isoformat()
        return self._logs_dir / agent_type / f"{date}_{conversation_id}.jsonl"

    def log_message(self, agent_type: str, conversation_id: str, message: Message) -> None:
        path = self._log_path(agent_type, conversation_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(json.dumps(message.to_dict()) + "\n")

    def load_conversation(self, agent_type: str, conversation_id: str) -> list[Message]:
        path = self._log_path(agent_type, conversation_id)
        if not path.exists():
            return []
        messages = []
        with path.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    messages.append(Message.from_dict(json.loads(line)))
        return messages

    def list_conversations(self, agent_type: str) -> list[str]:
        agent_dir = self._logs_dir / agent_type
        if not agent_dir.exists():
            return []
        result = []
        for p in agent_dir.glob("*.jsonl"):
            name = p.stem
            parts = name.split("_", 1)
            if len(parts) == 2:
                result.append(parts[1])
        return result
