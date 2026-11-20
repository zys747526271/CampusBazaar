"""卖家自定义商品分类。"""
from datetime import datetime
from . import db


class SellerCategory(db.Model):
    """卖家专属分类：每个卖家独立维护，与平台公共分类（Tag）互不干扰。"""
    __tablename__ = 'seller_categories'
    __table_args__ = (
        db.UniqueConstraint('seller_id', 'name', name='uq_seller_category_name'),
    )

    id = db.Column(db.Integer, primary_key=True, comment='分类ID')
    name = db.Column(db.String(50), nullable=False, comment='分类名称')
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True,
                          comment='所属卖家ID')
    sort_order = db.Column(db.Integer, default=0, comment='排序值，越小越靠前')
    is_deleted = db.Column(db.Boolean, default=False, comment='是否软删除')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'seller_id': self.seller_id,
            'sort_order': self.sort_order or 0,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<SellerCategory {self.name}>'
