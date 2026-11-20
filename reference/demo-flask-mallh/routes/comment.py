from flask import Blueprint, request, session, jsonify
from models.models import db, Comment
from utils.utils import result, getNowDateTime

comment_bp = Blueprint('comment', __name__)

@comment_bp.route("/api/add/comment", methods=["POST"])
def add_comment():
    """添加评论"""
    sId = session.get("_id")
    if not sId:
        return result(203, {"info": "未登录"})
    form = request.form
    image = request.files["image"]
    save_path = "./static/comments/" + image.filename
    image.save(save_path)
    data = {
        "createTime": getNowDateTime(),
        "content": form["content"],
        "points": form["points"],
        "user": sId,
        "good": form["goodsId"],
        "screenCut": save_path
    }
    db.session.add(Comment(**data))
    db.session.commit()
    return result(200)

@comment_bp.route("/api/comment/<int:goodsId>", methods=["GET", "DELETE"])
def comment(goodsId):
    """获取或删除商品评论"""
    if request.method == "GET":
        comments = Comment.query.filter_by(good=goodsId).all()
        data = {"data": [dict(c.__dict__, _sa_instance_state=None) for c in comments]}
        return result(200, data)
    if request.method == "DELETE":
        Comment.query.filter_by(good=goodsId).delete()
        db.session.commit()
        return result(200)