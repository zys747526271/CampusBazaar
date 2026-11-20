"""站内消息工具（未读计数用统一存储适配层，local 模式无需 Redis）。"""
from flask import current_app
from ..models import db, Message
from ..utils.runtime_cache import get_store
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def send_system_message(user_id, title, content, message_type='system'):
    """发送系统消息。"""
    message = Message(user_id=user_id, title=title, content=content,
                      type=message_type, create_time=datetime.utcnow())
    try:
        db.session.add(message)
        db.session.commit()
        get_store().incr(f'unread_messages:{user_id}')
        logger.info(f"系统消息已发送给用户 {user_id}: {title}")
        return message
    except Exception as e:
        db.session.rollback()
        logger.error(f"发送系统消息失败 user {user_id}: {str(e)}")
        raise


def send_trade_message(user_id, title, content, order_id=None):
    """发送交易消息。"""
    message = Message(user_id=user_id, title=title, content=content,
                      type='trade', order_id=order_id, create_time=datetime.utcnow())
    try:
        db.session.add(message)
        db.session.commit()
        get_store().incr(f'unread_messages:{user_id}')
        logger.info(f"交易消息已发送给用户 {user_id}: {title}")
        return message
    except Exception as e:
        db.session.rollback()
        logger.error(f"发送交易消息失败 user {user_id}: {str(e)}")
        raise


def get_unread_count(user_id):
    """获取未读消息数量（缓存缺失时从数据库同步）。"""
    key = f'unread_messages:{user_id}'
    count = get_store().get(key)
    if count is None:
        count = Message.query.filter_by(user_id=user_id, is_read=False).count()
        get_store().set(key, count)
    else:
        try:
            count = int(count)
        except (ValueError, TypeError):
            count = 0
    return count


def reset_unread_count(user_id):
    """重置未读消息计数。"""
    get_store().delete(f'unread_messages:{user_id}')
