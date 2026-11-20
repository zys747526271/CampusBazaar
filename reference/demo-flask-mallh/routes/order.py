from flask import Blueprint, request, session, jsonify
from models.models import db, User, Goods, Receipt, ReceiptItem, Court, Address, Admin, goodsCourt
from utils.utils import result, getNowDateTime, generate_order_num
import json
import traceback
from sqlalchemy.exc import SQLAlchemyError

order_bp = Blueprint('order', __name__)

@order_bp.route("/api/buy/goods", methods=["POST"])
def buy_goods():
    """购买商品"""
    sId = session.get("_id")
    if not sId:
        return jsonify({"code": 203, "info": "未登录"})
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "info": "请求数据不能为空"})
    
    try:
        user = User.query.get(sId)
        if not user:
            return jsonify({"code": 404, "info": "用户不存在"})
        
        payValue = float(data.get("payValue", 0))
        if not payValue:
            return jsonify({"code": 400, "info": "支付金额不能为空"})
        if user.balance < payValue:
            return jsonify({"code": 204, "info": "余额不足"})
        
        goodsList = json.loads(data.get("goodsList", "[]"))
        if not goodsList:
            return jsonify({"code": 400, "info": "商品列表不能为空"})
        
        court = Court.query.filter_by(user_id=sId).first()
        if not court:
            return jsonify({"code": 404, "info": "购物车不存在"})
        
        # 验证所有商品
        for goods in goodsList:
            goods_item = Goods.query.get(goods.get("id"))
            if not goods_item:
                return jsonify({"code": 404, "info": f"商品 {goods.get('id')} 不存在"})
            
            number = int(goods.get("number", 0))
            if number <= 0:
                return jsonify({"code": 400, "info": f"商品数量必须大于0"})
                
            if goods_item.contains < number:
                return jsonify({"code": 400, "info": f"商品 {goods_item.name} 库存不足"})
                
            # 验证商品是否在购物车中
            court_item = db.session.query(goodsCourt).filter_by(
                court_id=court._id,
                goods_id=goods["id"]
            ).first()
            if not court_item:
                return jsonify({"code": 404, "info": f"商品 {goods_item.name} 不在购物车中"})
        
        # 开始事务处理
        itemIdList = []
        
        # 扣除用户余额
        user.balance -= payValue
        
        # 处理商品和购物车
        for goods in goodsList:
            goods_item = Goods.query.get(goods["id"])
            number = int(goods["number"])
            
            # 创建订单项
            item = ReceiptItem(goodsId=goods["id"], number=number)
            db.session.add(item)
            db.session.flush()  # 获取自增ID
            itemIdList.append(item._id)
            
            # 更新商品信息
            goods_item.buyTimes += number
            goods_item.contains -= number
            
            # 从购物车中移除商品
            db.session.execute(
                goodsCourt.delete().where(
                    (goodsCourt.c.court_id == court._id) & 
                    (goodsCourt.c.goods_id == goods["id"])
                )
            )
            
            if goods_item in court.goods:
                court.goods.remove(goods_item)
            
            court.number = max(0, court.number - number)
        
        # 创建订单
        receipt = Receipt(
            orderNum=generate_order_num(),
            createTime=getNowDateTime(),
            payValue=payValue,
            cutoffValue=float(data.get("cutoffValue", payValue)),
            user_id=sId,
            itemId=str(itemIdList),
            address=data.get("address", "暂无地址")
        )
        db.session.add(receipt)
        
        # 提交事务
        try:
            db.session.commit()
            return jsonify({"code": 200, "info": "订单创建成功", "orderNum": receipt.orderNum})
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"Error creating order: {str(e)}")
            return jsonify({"code": 500, "info": "订单创建失败", "error": str(e)})
            
    except json.JSONDecodeError:
        return jsonify({"code": 400, "info": "商品列表格式错误"})
    except ValueError as e:
        return jsonify({"code": 400, "info": str(e)})
    except Exception as e:
        if 'db' in locals():
            db.session.rollback()
        traceback.print_exc()
        return jsonify({"code": 502, "info": "服务器错误", "error": str(e)})

@order_bp.route("/api/self/receipt", methods=["GET"])
def self_receipt():
    """获取用户订单列表，支持搜索订单号、商品名和下单时间"""
    sId = session.get("_id")
    if not sId:
        return jsonify({"code": 203, "info": "未登录"})
    
    is_admin = Admin.query.get(sId) is not None
    user_id = request.args.get("user_id", sId)
    status = request.args.get("status", "all")
    page = int(request.args.get("page", 1))
    size = int(request.args.get("size", 10))
    search_query = request.args.get("search", "").strip()

    try:
        # 基础查询
        query = Receipt.query.filter_by(user_id=user_id)
        
        # 状态筛选
        if status != "all":
            query = query.filter_by(status=status)
        
        # 搜索逻辑：订单号、商品名、下单时间
        if search_query:
            # 关联 ReceiptItem 和 Goods
            query = query.outerjoin(ReceiptItem, ReceiptItem.orderNum == Receipt.orderNum)\
                        .outerjoin(Goods, Goods._id == ReceiptItem.goodsId)\
                        .filter(
                            db.or_(
                                Receipt.orderNum.ilike(f"%{search_query}%"),
                                Goods.name.ilike(f"%{search_query}%"),
                                Receipt.createTime.ilike(f"%{search_query}%")
                            )
                        ).distinct()  # 避免重复订单
        
        # 分页
        total = query.count()
        receipts = query.order_by(Receipt.createTime.desc())\
                       .offset((page - 1) * size)\
                       .limit(size)\
                       .all()
        
        # 数据构造
        data = {"data": [], "total": total}
        for receipt in receipts:
            goodsIdList = receipt.get_goods_id_list()  # 使用现有方法
            goods_list = []
            for goodsId in goodsIdList:
                item = ReceiptItem.query.filter_by(_id=goodsId).first()
                if not item:
                    continue
                goods = Goods.query.get(item.goodsId)
                if goods:
                    send_address = Address.query.get(goods.sendAddress_id)
                    try:
                        images = json.loads(goods.images) if goods.images else []
                        image = images[0] if images else "https://via.placeholder.com/150"
                    except json.JSONDecodeError:
                        image = "https://via.placeholder.com/150"
                    goods_list.append({
                        "id": goods._id,
                        "name": goods.name,
                        "sellPrice": float(goods.sellPrice),
                        "image": image,
                        "quantity": item.number,
                        "sendAddress": f"{send_address.province}{send_address.town}{send_address.county}{send_address.detail}" if send_address else "暂无地址"
                    })
            data["data"].append({
                "orderNum": receipt.orderNum,
                "createTime": receipt.createTime.strftime("%Y-%m-%d %H:%M:%S"),
                "payValue": float(receipt.payValue),
                "cutoffValue": float(receipt.cutoffValue) if receipt.cutoffValue else 0.0,
                "address": receipt.address if receipt.address else "暂无地址",
                "status": receipt.status,
                "goodsList": goods_list
            })
        
        return jsonify({"code": 200, "data": data})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"code": 500, "info": "服务器错误", "error": str(e)})


@order_bp.route("/api/order/cancel", methods=["POST"])
def cancel_order():
    sId = session.get("_id")
    if not sId:
        return jsonify({"code": 203, "info": "未登录"})
    data = request.get_json()
    order_num = data.get("orderNum")
    receipt = Receipt.query.filter_by(orderNum=order_num, user_id=sId).first()
    if not receipt:
        return jsonify({"code": 404, "info": "订单不存在"})
    if receipt.status != "pending_payment":
        return jsonify({"code": 400, "info": "只有待支付订单可以取消"})
    receipt.status = "cancelled"
    user = User.query.get(sId)
    user.balance += receipt.payValue  # 退款
    db.session.commit()
    return jsonify({"code": 200, "info": "订单已取消"})

#收发货
@order_bp.route("/api/order/confirm", methods=["POST"])
def confirm_receipt():
    sId = session.get("_id")
    if not sId:
        return jsonify({"code": 203, "info": "未登录"})
    data = request.get_json()
    order_num = data.get("orderNum")
    receipt = Receipt.query.filter_by(orderNum=order_num, user_id=sId).first()
    if not receipt:
        return jsonify({"code": 404, "info": "订单不存在"})
    if receipt.status != "shipped":
        return jsonify({"code": 400, "info": "只有已发货订单可以确认收货"})
    receipt.status = "completed"
    db.session.commit()
    return jsonify({"code": 200, "info": "已确认收货"})

#支付接口
@order_bp.route("/api/order/pay", methods=["POST"])
def pay_order():
    sId = session.get("_id")
    if not sId:
        return jsonify({"code": 203, "info": "未登录"})
    data = request.get_json()
    order_num = data.get("orderNum")
    receipt = Receipt.query.filter_by(orderNum=order_num, user_id=sId).first()
    if not receipt:
        return jsonify({"code": 404, "info": "订单不存在"})
    if receipt.status != "pending_payment":
        return jsonify({"code": 400, "info": "订单状态不支持支付"})
    # 这里应集成支付网关逻辑，支付成功后更新状态
    receipt.status = "pending_shipping"
    db.session.commit()
    return jsonify({"code": 200, "info": "支付成功"})