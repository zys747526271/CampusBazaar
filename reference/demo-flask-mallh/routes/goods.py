from flask import Blueprint, request, session, jsonify
from models.models import db, Goods, GoodsType, Address, Admin, Court, Receipt, ReceiptItem, User, goodsCourt
from utils.utils import result, getNowDateTime, getOrderNum, cache_get, cache_set
from datetime import datetime
import os
import json
from sqlalchemy.exc import SQLAlchemyError

goods_bp = Blueprint('goods', __name__)

@goods_bp.route("/api/public/goods", methods=["POST"])
def public_goods():
    """获取上架商品列表（普通用户）"""
    cache_key = "public_goods"
    cached_data = cache_get(cache_key)
    if cached_data:
        return jsonify({"code": 200, "data": cached_data}), 200

    try:
        start = int(request.form.get("start", 0))
        nums = int(request.form.get("nums", 50))
        print(f"Public goods request: start={start}, nums={nums}")
        query = Goods.query.filter_by(is_active=True)
        goods = query.order_by(Goods.createTime.desc()).offset(start).limit(nums).all()
        data = []
        for good in goods:
            dic = good.__dict__
            del dic["_sa_instance_state"]
            for key, value in dic.items():
                if isinstance(value, datetime):
                    dic[key] = value.strftime("%Y-%m-%d %H:%M:%S")
            dic["goodsType_id"] = GoodsType.query.get(dic["goodsType_id"]).name if dic["goodsType_id"] else "未分类"
            dic["createAddress_id"] = f"{Address.query.get(dic['createAddress_id']).province}{Address.query.get(dic['createAddress_id']).town}{Address.query.get(dic['createAddress_id']).county}{Address.query.get(dic['createAddress_id']).detail}" if dic["createAddress_id"] else "未知地址"
            dic["sendAddress_id"] = f"{Address.query.get(dic['sendAddress_id']).province}{Address.query.get(dic['sendAddress_id']).town}{Address.query.get(dic['sendAddress_id']).county}{Address.query.get(dic['sendAddress_id']).detail}" if dic["sendAddress_id"] else "未知地址"
            images = json.loads(dic["images"]) if dic["images"] else []
            dic["image"] = images[0] if images else "https://via.placeholder.com/150"
            data.append(dic)
        print(f"Returning public goods: {len(data)} items")
        cache_set(cache_key, data, expire_time=60)  # 缓存60秒
        return jsonify({"code": 200, "data": data}), 200
    except Exception as e:
        print(f"Error in /api/public/goods: {str(e)}")
        return jsonify({"code": 500, "info": "服务器错误", "error": str(e)}), 500

# 管理员接口：商品管理
@goods_bp.route("/api/admin/goods/count", methods=["GET"])
def admin_goods_count():
    """获取商品总数（管理员）"""
    sId = session.get("_id")
    is_admin = sId and Admin.query.get(sId) is not None
    if not is_admin:
        return jsonify({"code": 403, "info": "仅管理员可访问"}), 403
    nums = Goods.query.count()
    print(f"Admin goods count: {nums}")
    return jsonify({"code": 200, "data": {"nums": nums}}), 200

@goods_bp.route("/api/admin/goods", methods=["POST"])
def admin_goods():
    """获取商品列表（管理员）"""
    sId = session.get("_id")
    is_admin = sId and Admin.query.get(sId) is not None
    if not is_admin:
        return jsonify({"code": 403, "info": "仅管理员可访问"}), 403
    try:
        start = int(request.form.get("start", 0))
        nums = int(request.form.get("nums", 15))
        status = request.form.get("status", "all")
        print(f"Admin goods request: start={start}, nums={nums}, status={status}")
        query = Goods.query
        if status == "active":
            query = query.filter_by(is_active=True)
            print("Admin requesting active goods")
        elif status == "inactive":
            query = query.filter_by(is_active=False)
            print("Admin requesting inactive goods")
        else:
            print("Admin requesting all goods")
        goods = query.order_by(Goods.createTime.desc()).offset(start).limit(nums).all()
        data = []
        for good in goods:
            dic = good.__dict__
            del dic["_sa_instance_state"]
            for key, value in dic.items():
                if isinstance(value, datetime):
                    dic[key] = value.strftime("%Y-%m-%d %H:%M:%S")
            dic["goodsType_id"] = GoodsType.query.get(dic["goodsType_id"]).name if dic["goodsType_id"] else "未分类"
            dic["createAddress_id"] = f"{Address.query.get(dic['createAddress_id']).province}{Address.query.get(dic['createAddress_id']).town}{Address.query.get(dic['createAddress_id']).county}{Address.query.get(dic['createAddress_id']).detail}" if dic["createAddress_id"] else "未知地址"
            dic["sendAddress_id"] = f"{Address.query.get(dic['sendAddress_id']).province}{Address.query.get(dic['sendAddress_id']).town}{Address.query.get(dic['sendAddress_id']).county}{Address.query.get(dic['sendAddress_id']).detail}" if dic["sendAddress_id"] else "未知地址"
            images = json.loads(dic["images"]) if dic["images"] else []
            dic["image"] = images[0] if images else "https://via.placeholder.com/150"
            data.append(dic)
        print(f"Returning admin goods: {len(data)} items")
        return jsonify({"code": 200, "data": data}), 200
    except Exception as e:
        print(f"Error in /api/admin/goods: {str(e)}")
        return jsonify({"code": 500, "info": "服务器错误", "error": str(e)}), 500

@goods_bp.route("/api/admin/goods/add", methods=["POST"])
def admin_goods_add():
    """添加新商品（管理员）"""
    sId = session.get("_id")
    is_admin = sId and Admin.query.get(sId) is not None
    if not is_admin:
        return jsonify({"code": 403, "info": "仅管理员可访问"}), 403
    try:
        form = request.form
        files = request.files.getlist("images")
        if not files:
            return jsonify({"code": 400, "info": "请至少上传一张图片"}), 400
        image_paths = []
        for file in files:
            if file and file.filename:
                filename = f"{getOrderNum()}{file.filename}"
                save_path = os.path.join("./static/goods", filename)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                file.save(save_path)
                image_paths.append(f"/static/goods/{filename}")
            else:
                return jsonify({"code": 400, "info": "无效的文件"}), 400
        data = {
            "name": form["name"],
            "goodsType_id": form["goodsType"],
            "originPrice": float(form["originPrice"]),
            "sellPrice": float(form["sellPrice"]),
            "contains": int(form["contains"]),
            "createTime": getNowDateTime(),
            "images": json.dumps(image_paths),
            "createAddress_id": form["createAddress"],
            "sendAddress_id": form["sendAddress"],
            "intro": form["intro"],
            "is_active": True
        }
        goods = Goods(**data)
        db.session.add(goods)
        db.session.commit()
        print(f"Added new good: {goods._id}")
        return jsonify({"code": 200, "info": "商品添加成功"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error in /api/admin/goods/add: {str(e)}")
        return jsonify({"code": 500, "info": "添加失败", "error": str(e)}), 500

@goods_bp.route("/api/admin/goods/toggle", methods=["DELETE"])
def admin_goods_toggle():
    """切换商品上下架状态（管理员）"""
    sId = session.get("_id")
    is_admin = sId and Admin.query.get(sId) is not None
    if not is_admin:
        return jsonify({"code": 403, "info": "仅管理员可访问"}), 403
    try:
        data = request.get_json()
        _id = data.get("id")
        if not _id:
            return jsonify({"code": 400, "message": "商品ID不能为空"}), 400
        goods = Goods.query.filter_by(_id=_id).first()
        if not goods:
            return jsonify({"code": 404, "message": "商品不存在"}), 404
        goods.is_active = not goods.is_active
        db.session.commit()
        action = "上架" if goods.is_active else "下架"
        print(f"Toggled good {goods._id} to {action}")
        return jsonify({"code": 200, "message": f"商品已{action}"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Error in /api/admin/goods/toggle: {str(e)}")
        return jsonify({"code": 500, "message": "操作失败", "error": str(e)}), 500

@goods_bp.route("/api/admin/goods/restock", methods=["POST"])
def admin_goods_restock():
    """商品补货（管理员）"""
    sId = session.get("_id")
    is_admin = sId and Admin.query.get(sId) is not None
    if not is_admin:
        return jsonify({"code": 403, "info": "仅管理员可访问"}), 403
    try:
        data = request.get_json()
        _id = data.get("id")
        quantity = data.get("quantity")
        if not _id or quantity is None:
            return jsonify({"code": 400, "message": "商品ID和补货数量不能为空"}), 400
        goods = Goods.query.filter_by(_id=_id).first()
        if not goods:
            return jsonify({"code": 404, "message": "商品不存在"}), 404
        goods.contains += int(quantity)
        if goods.contains < 0:
            return jsonify({"code": 400, "message": "库存不能为负数"}), 400
        db.session.commit()
        print(f"Restocked good {goods._id}, new contains: {goods.contains}")
        return jsonify({"code": 200, "message": "补货成功", "new_contains": goods.contains}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Error in /api/admin/goods/restock: {str(e)}")
        return jsonify({"code": 500, "message": "补货失败", "error": str(e)}), 500

# 商品类型接口（保持不变）
@goods_bp.route("/api/goods/type", methods=["GET"])
def goods_type():
    types = GoodsType.query.all()
    data = {"data": [dict(t.__dict__, _sa_instance_state=None) for t in types]}
    return result(200, data)

@goods_bp.route("/api/goods/type/add", methods=["POST"])
def goods_type_add():
    data = request.get_json() or request.form
    print(f"Received data: {data}")
    try:
        name = data.get("name")
        if not name:
            return jsonify({"code": 400, "info": "标签名称不能为空"}), 400
        db.session.add(GoodsType(name=name))
        db.session.commit()
        return result(200)
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "info": "服务器错误", "error": str(e)}), 500

@goods_bp.route("/api/goods/type/delete", methods=["DELETE"])
def goods_type_delete():
    _id = request.form["id"]
    GoodsType.query.filter_by(_id=_id).delete()
    db.session.commit()
    return result(200)

# 商品详情接口（仅返回上架商品）
@goods_bp.route("/api/goods/detail/<int:goodsId>", methods=["GET"])
def goods_detail(goodsId):
    goods = Goods.query.get(goodsId)
    if not goods or not goods.is_active:
        return result(404, {"info": "商品不存在或已下架"})
    goods.lookTimes = (goods.lookTimes or 0) + 1
    db.session.commit()
    data = {
        "_id": goods._id,
        "name": goods.name,
        "goodsType_id": GoodsType.query.get(goods.goodsType_id).name if goods.goodsType_id else "未分类",
        "originPrice": float(goods.originPrice) if goods.originPrice else 0.0,
        "sellPrice": float(goods.sellPrice) if goods.sellPrice else 0.0,
        "contains": goods.contains if goods.contains is not None else 0,
        "createTime": goods.createTime.strftime("%Y-%m-%d") if goods.createTime else "",
        "images": goods.images if goods.images else "[]",
        "createAddress_id": f"{Address.query.get(goods.createAddress_id).province}{Address.query.get(goods.createAddress_id).town}{Address.query.get(goods.createAddress_id).county}{Address.query.get(goods.createAddress_id).detail}" if goods.createAddress_id else "未知地址",
        "sendAddress_id": f"{Address.query.get(goods.sendAddress_id).province}{Address.query.get(goods.sendAddress_id).town}{Address.query.get(goods.sendAddress_id).county}{Address.query.get(goods.sendAddress_id).detail}" if goods.sendAddress_id else "未知地址",
        "intro": goods.intro if goods.intro else "",
        "lookTimes": goods.lookTimes if goods.lookTimes is not None else 0,
        "buyTimes": goods.buyTimes if goods.buyTimes is not None else 0,
        "likeTimes": goods.likeTimes if goods.likeTimes is not None else 0,
        "is_active": goods.is_active
    }
    try:
        image_list = json.loads(data["images"])
        data["image"] = image_list[0] if image_list else "https://via.placeholder.com/150"
    except json.JSONDecodeError:
        data["image"] = "https://via.placeholder.com/150"
    return result(200, data)

# 其他接口（购物车、搜索、推荐等）
@goods_bp.route("/api/add/goods/2/court", methods=["POST"])
def add_goods_2_court():
    try:
        sId = session.get("_id")
        if not sId:
            return jsonify({"code": 203, "info": "未登录"}), 203

        goodsId = request.json.get("goodsId")
        quantity = request.json.get("quantity", 1)

        if not goodsId:
            return jsonify({"code": 400, "info": "商品ID不能为空"}), 400

        goods = Goods.query.get(goodsId)
        if not goods or not goods.is_active:
            return jsonify({"code": 404, "info": "商品不存在或已下架"}), 404

        court = Court.query.filter_by(user_id=sId).first()
        if not court:
            return jsonify({"code": 404, "info": "购物车不存在"}), 404

        # 检查商品是否已在购物车中
        court_item = db.session.query(goodsCourt).filter_by(court_id=court._id, goods_id=goodsId).first()
        if court_item:
            # 如果商品已存在，更新数量
            new_quantity = court_item.quantity + quantity
            if new_quantity > goods.contains:
                return jsonify({"code": 400, "info": "商品库存不足"}), 400
            db.session.execute(
                goodsCourt.update()
                .where(goodsCourt.c.court_id == court._id)
                .where(goodsCourt.c.goods_id == goodsId)
                .values(quantity=new_quantity)
            )
        else:
            # 如果商品不存在，添加新记录
            if quantity > goods.contains:
                return jsonify({"code": 400, "info": "商品库存不足"}), 400
            court.goods.append(goods)
            db.session.execute(goodsCourt.insert().values(court_id=court._id, goods_id=goodsId, quantity=quantity))

        court.number = (court.number or 0) + quantity
        goods.likeTimes = (goods.likeTimes or 0) + 1
        
        db.session.commit()
        return jsonify({"code": 200, "info": "添加成功"})
    except Exception as e:
        db.session.rollback()
        print(f"添加购物车失败: {str(e)}")
        return jsonify({"code": 500, "info": "服务器错误"}), 500

@goods_bp.route("/api/remove/goods/from/court", methods=["POST"])
def remove_goods_from_court():
    sId = session.get("_id")
    if not sId:
        return jsonify({"code": 203, "info": "未登录"}), 203
    
    data = request.get_json() or request.form
    goodsId = data.get("goodsId")
    if not goodsId:
        return jsonify({"code": 400, "info": "商品ID不能为空"}), 400
        
    court = Court.query.filter_by(user_id=sId).first()
    if not court:
        return jsonify({"code": 404, "info": "购物车不存在"}), 404
        
    goods = Goods.query.get(goodsId)
    if not goods:
        return jsonify({"code": 404, "info": "商品不存在"}), 404
        
    try:
        # 先检查商品是否在购物车中
        court_item = db.session.query(goodsCourt).filter_by(court_id=court._id, goods_id=goodsId).first()
        if not court_item:
            return jsonify({"code": 404, "info": "商品不在购物车中"}), 404
            
        # 更新购物车商品数量
        court.number = max(0, (court.number or 0) - court_item.quantity)
        
        # 从购物车中删除商品
        db.session.execute(
            goodsCourt.delete().where(
                goodsCourt.c.court_id == court._id
            ).where(
                goodsCourt.c.goods_id == goodsId
            )
        )
        
        # 更新商品点赞数
        if goods.likeTimes and goods.likeTimes > 0:
            goods.likeTimes -= 1
            
        # 从购物车的商品列表中移除
        if goods in court.goods:
            court.goods.remove(goods)
            
        db.session.commit()
        return jsonify({"code": 200, "info": "移除成功"})
    except Exception as e:
        db.session.rollback()
        print(f"移除购物车失败: {str(e)}")
        return jsonify({"code": 500, "info": "服务器错误", "error": str(e)}), 500

@goods_bp.route("/api/goods/search", methods=["POST"])
def goods_search():
    keyWord = request.form["keyWord"]
    goods = Goods.query.filter(Goods.name.contains(keyWord), Goods.is_active == True).limit(50).all()
    data = {"data": [{
        "id": g._id,
        "name": g.name,
        "originPrice": g.originPrice,
        "sellPrice": g.sellPrice,
        "image": json.loads(g.images)[0] if g.images and json.loads(g.images) else "https://via.placeholder.com/150",
        "lookTimes": g.lookTimes,
        "likeTimes": g.likeTimes,
        "buyTimes": g.buyTimes,
    } for g in goods]}
    return result(200, data)

@goods_bp.route("/api/recommend/goods", methods=["POST"])
def recommend_goods():
    try:
        sId = session.get("_id")
        tagId = request.form.get("tagId")
        goodsId = request.form.get("goodsId")
        limit = int(request.form.get("limit", 5))
        user = User.query.get(sId) if sId else None
        is_new_user = not user or not Receipt.query.filter_by(user_id=sId).first()
        if is_new_user:
            query = Goods.query.filter(Goods.is_active == True)
            if goodsId:
                query = query.filter(Goods._id != goodsId)
            goods = query.order_by(Goods.buyTimes.desc()).limit(limit).all()
        else:
            receipts = Receipt.query.filter_by(user_id=sId).all()
            purchased_goods_ids = set()
            for receipt in receipts:
                item_ids = json.loads(receipt.itemId) if receipt.itemId and receipt.itemId != "[]" else []
                items = ReceiptItem.query.filter(ReceiptItem._id.in_(item_ids)).all()
                purchased_goods_ids.update(item.goodsId for item in items if item.goodsId)
            purchased_tags = set(Goods.query.get(gid).goodsType_id for gid in purchased_goods_ids if Goods.query.get(gid))
            tags_to_query = purchased_tags.union({tagId}) if tagId else purchased_tags
            query = Goods.query.filter(Goods.goodsType_id.in_(tags_to_query), Goods.is_active == True)
            if goodsId:
                query = query.filter(Goods._id != goodsId)
            goods = query.order_by(Goods.buyTimes.desc()).limit(limit).all()
            if len(goods) < limit:
                extra_query = Goods.query.filter(Goods.is_active == True, Goods._id != goodsId, ~Goods._id.in_([g._id for g in goods])).order_by(Goods.buyTimes.desc())
                extra_goods = extra_query.limit(limit - len(goods)).all()
                goods.extend(extra_goods[:limit - len(goods)])
        data = {"data": []}
        for good in goods:
            dic = good.__dict__
            del dic["_sa_instance_state"]
            for key, value in dic.items():
                if isinstance(value, datetime):
                    dic[key] = value.strftime("%Y-%m-%d %H:%M:%S")
            dic["image"] = json.loads(dic["images"])[0] if dic["images"] and json.loads(dic["images"]) else "https://via.placeholder.com/150"
            data["data"].append(dic)
        return result(200, data)
    except Exception as e:
        return result(500, {"info": "推荐商品加载失败", "error": str(e)})