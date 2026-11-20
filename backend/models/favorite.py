"""收藏与浏览记录模型。"""
from datetime import datetime
from . import db


class Favorite(db.Model):
    """用户收藏的商品。"""
    __tablename__ = 'favorites'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'product_id', name='uq_favorite_user_product'),
    )

    product = db.relationship('Product', backref=db.backref('favorited_by', lazy='dynamic'))

    def to_dict(self):
        p = self.product
        return {
            'id': self.id,
            'product_id': self.product_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'product': p.to_dict(with_seller=True) if p else None
        }


class BrowseHistory(db.Model):
    """用户浏览记录（每次查看详情记录一条，按用户+商品保留最新）。"""
    __tablename__ = 'browse_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'product_id', name='uq_history_user_product'),
    )

    product = db.relationship('Product', backref=db.backref('browsed_by', lazy='dynamic'))

    def to_dict(self):
        p = self.product
        return {
            'id': self.id,
            'product_id': self.product_id,
            'viewed_at': self.viewed_at.isoformat() if self.viewed_at else None,
            'product': p.to_dict(with_seller=True) if p else None
        }
