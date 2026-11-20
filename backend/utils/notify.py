"""站内消息通知（PRD FR-MSG-01/03）。

``notify()`` 只做入库，提交由调用方负责，保证与业务写入同事务。
新增渠道（邮件/短信/微信模板消息）时实现 ``Notifier`` 协议并在 ``_CHANNELS`` 注册即可，
业务代码不需要改动。
"""
from __future__ import annotations

from typing import Protocol

from backend.constants import MessageType
from backend.extensions import db


class Notifier(Protocol):
    def send(self, user_id: int, msg_type: str, title: str, content: str, link: str) -> None: ...


class InboxNotifier:
    """站内信：写入 messages 表。"""

    def send(self, user_id: int, msg_type: str, title: str, content: str, link: str) -> None:
        from backend.models import Message

        db.session.add(
            Message(
                user_id=user_id,
                type=msg_type if msg_type in MessageType.ALL else MessageType.SYSTEM,
                title=title[:80],
                content=content[:500],
                link=link[:200],
            )
        )


_CHANNELS: list[Notifier] = [InboxNotifier()]


def notify(user_id: int, msg_type: str, title: str, content: str = "", link: str = "") -> None:
    if not user_id:
        return
    for channel in _CHANNELS:
        channel.send(user_id, msg_type, title, content, link)


def notify_many(user_ids, msg_type: str, title: str, content: str = "", link: str = "") -> None:
    for user_id in set(user_ids):
        notify(user_id, msg_type, title, content, link)
