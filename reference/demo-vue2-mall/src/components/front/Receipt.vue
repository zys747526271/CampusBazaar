<template>
  <div class="order-page">
    <nav-bar
      :active-route.sync="activeRoute"
      :is-logged-in.sync="isLoggedIn"
      :username.sync="username"
      :show-search-bar="false"
      @open-loading="openLoading"
      @close-loading="closeLoading"
    />

    <div class="main-content">
      <!-- 搜索栏 -->
      <div class="search-section">
        <el-input
          v-model="searchQuery"
          placeholder="搜索订单号、商品名称或下单时间（如 2025-03）"
          clearable
          class="search-input"
          @keyup.enter.native="fetchOrders"
        >
          <el-button slot="append" icon="el-icon-search" @click="fetchOrders"></el-button>
        </el-input>
      </div>

      <!-- 订单状态筛选 -->
      <el-tabs v-model="activeStatus" @tab-click="handleTabClick" class="order-tabs">
        <el-tab-pane label="全部订单" name="all"></el-tab-pane>
        <el-tab-pane label="待支付" name="pending_payment"></el-tab-pane>
        <el-tab-pane label="待发货" name="pending_shipping"></el-tab-pane>
        <el-tab-pane label="已发货" name="shipped"></el-tab-pane>
        <el-tab-pane label="已完成" name="completed"></el-tab-pane>
      </el-tabs>

      <!-- 订单列表 -->
      <el-table
        :data="orderList"
        style="width: 100%"
        v-loading="loading"
        :empty-text="emptyText"
        row-class-name="order-row"
      >
        <el-table-column prop="orderNum" label="订单编号" width="180">
          <template slot-scope="scope">
            <span v-html="highlightText(scope.row.orderNum, searchQuery)"></span>
          </template>
        </el-table-column>
        <el-table-column label="商品信息" width="300">
          <template slot-scope="scope">
            <div class="goods-info">
              <div v-for="item in scope.row.goodsList" :key="item.id" class="goods-item">
                <img :src="item.image" alt="商品图片" class="goods-image" />
                <span v-html="highlightText(`${item.name} x ${item.quantity}`, searchQuery)"></span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="payValue" label="订单金额" width="120">
          <template slot-scope="scope">
            <span class="price">¥{{ scope.row.payValue.toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="下单时间" width="160">
          <template slot-scope="scope">
            <span v-html="highlightText(scope.row.createTime, searchQuery)"></span>
          </template>
        </el-table-column>
        <el-table-column prop="statusText" label="订单状态" width="120">
          <template slot-scope="scope">
            <span :class="`status-${scope.row.status}`">{{ scope.row.statusText }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center">
          <template slot-scope="scope">
            <div class="action-buttons">
              <el-button
                v-if="scope.row.status === 'pending_payment'"
                type="primary"
                size="small"
                @click="handlePayOrder(scope.row)"
              >去支付</el-button>
              <el-button
                v-if="scope.row.status === 'pending_payment'"
                type="danger"
                size="small"
                @click="handleCancelOrder(scope.row)"
              >取消订单</el-button>
              <el-button
                v-if="scope.row.status === 'shipped'"
                type="success"
                size="small"
                @click="handleConfirmReceipt(scope.row)"
              >确认收货</el-button>
              <el-button type="text" @click="handleViewDetail(scope.row)">查看详情</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-if="total > 0"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
        :current-page="page"
        :page-sizes="[10, 20, 50]"
        :page-size="size"
        layout="total, sizes, prev, pager, next, jumper"
        :total="total"
        class="pagination"
      ></el-pagination>

      <!-- 订单详情对话框 -->
      <el-dialog
        title="订单详情"
        :visible.sync="detailVisible"
        width="50%"
        :before-close="handleCloseDetail"
        class="order-dialog"
      >
        <div v-if="currentOrder" class="detail-content">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="订单编号">{{ currentOrder.orderNum }}</el-descriptions-item>
            <el-descriptions-item label="下单时间">{{ currentOrder.createTime }}</el-descriptions-item>
            <el-descriptions-item label="订单状态">
              <span :class="`status-${currentOrder.status}`">{{ currentOrder.statusText }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="收货地址">{{ currentOrder.address }}</el-descriptions-item>
            <el-descriptions-item label="订单金额">
              <span class="price">¥{{ currentOrder.payValue.toFixed(2) }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="优惠金额">
              <span class="discount">¥{{ (currentOrder.payValue - currentOrder.cutoffValue).toFixed(2) }}</span>
            </el-descriptions-item>
          </el-descriptions>
          <el-table :data="currentOrder.goodsList" style="margin-top: 20px" class="detail-table">
            <el-table-column label="商品图片" width="100">
              <template slot-scope="scope">
                <img :src="scope.row.image" alt="商品图片" class="detail-goods-image" />
              </template>
            </el-table-column>
            <el-table-column prop="name" label="商品名称"></el-table-column>
            <el-table-column prop="sellPrice" label="单价" width="100">
              <template slot-scope="scope">
                ¥{{ scope.row.sellPrice.toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column prop="quantity" label="数量" width="80"></el-table-column>
            <el-table-column label="小计" width="120">
              <template slot-scope="scope">
                ¥{{ (scope.row.sellPrice * scope.row.quantity).toFixed(2) }}
              </template>
            </el-table-column>
          </el-table>
        </div>
        <span slot="footer" class="dialog-footer">
          <el-button @click="detailVisible = false">关闭</el-button>
        </span>
      </el-dialog>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import NavBar from './NavBar.vue';

export default {
  name: 'OrderPage',
  components: {
    NavBar
  },
  data() {
    return {
      activeRoute: this.$route.path,
      isLoggedIn: false,
      username: '',
      activeStatus: 'all',
      orderList: [],
      loading: false,
      page: 1,
      size: 10,
      total: 0,
      detailVisible: false,
      currentOrder: null,
      emptyText: '暂无订单',
      searchQuery: '',
      statusMap: {
        'pending_payment': '待支付',
        'pending_shipping': '待发货',
        'shipped': '已发货',
        'completed': '已完成',
        'cancelled': '已取消'
      }
    };
  },
  created() {
    this.checkLoginStatus();
    this.fetchOrders();
  },
  watch: {
    '$route'(to) {
      this.activeRoute = to.path;
      this.checkLoginStatus();
    }
  },
  methods: {
    openLoading(text = "加载中...") {
      this.loading = true;
      this.$message({
        message: text,
        type: 'info',
        duration: 0
      });
    },
    closeLoading() {
      this.loading = false;
      this.$message.closeAll();
    },
    async fetchOrders() {
      this.loading = true;
      try {
        const response = await axios.get('/api/self/receipt', {
          params: {
            status: this.activeStatus,
            page: this.page,
            size: this.size,
            search: this.searchQuery.trim()
          }
        });
        if (response.data.code === 200) {
          const { data, total } = response.data.data;
          this.orderList = data.map(order => ({
            ...order,
            statusText: this.statusMap[order.status] || '未知状态',
            goodsList: order.goodsList.map(item => ({
              ...item,
              image: item.image || 'https://via.placeholder.com/150'
            }))
          }));
          this.total = total;
          this.emptyText = total === 0 ? (this.searchQuery ? '未找到匹配的订单' : '暂无订单') : '';
        } else {
          this.$message.error(response.data.info || '获取订单失败');
          this.orderList = [];
          this.total = 0;
          this.emptyText = '获取订单失败';
        }
      } catch (error) {
        console.error('获取订单失败:', error);
        this.$message.error('网络错误，请稍后重试');
        this.orderList = [];
        this.total = 0;
        this.emptyText = '网络错误';
      } finally {
        this.loading = false;
      }
    },
    handleTabClick() {
      this.page = 1;
      this.fetchOrders();
    },
    handleSizeChange(val) {
      this.size = val;
      this.page = 1;
      this.fetchOrders();
    },
    handleCurrentChange(val) {
      this.page = val;
      this.fetchOrders();
    },
    handleViewDetail(row) {
      this.currentOrder = { ...row };
      this.detailVisible = true;
    },
    handleCloseDetail() {
      this.detailVisible = false;
      this.currentOrder = null;
    },
    async handlePayOrder(row) {
      this.$confirm('确认支付此订单？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          const response = await axios.post('/api/order/pay', { orderNum: row.orderNum });
          if (response.data.code === 200) {
            this.$message.success('支付成功');
            row.status = 'pending_shipping';
            row.statusText = this.statusMap['pending_shipping'];
            this.checkLoginStatus();
          } else {
            this.$message.error(response.data.info || '支付失败');
          }
        } catch (error) {
          console.error('支付失败:', error);
          this.$message.error('支付失败，请重试');
        }
      }).catch(() => {
        this.$message.info('已取消支付');
      });
    },
    async handleCancelOrder(row) {
      this.$confirm('确定取消此订单吗？取消后金额将退回余额', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          const response = await axios.post('/api/order/cancel', { orderNum: row.orderNum });
          if (response.data.code === 200) {
            this.$message.success('订单已取消');
            row.status = 'cancelled';
            row.statusText = this.statusMap['cancelled'];
            this.checkLoginStatus();
          } else {
            this.$message.error(response.data.info || '取消失败');
          }
        } catch (error) {
          console.error('取消订单失败:', error);
          this.$message.error('取消失败，请重试');
        }
      }).catch(() => {
        this.$message.info('已取消操作');
      });
    },
    async handleConfirmReceipt(row) {
      this.$confirm('确认收到商品吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          const response = await axios.post('/api/order/confirm', { orderNum: row.orderNum });
          if (response.data.code === 200) {
            this.$message.success('已确认收货');
            row.status = 'completed';
            row.statusText = this.statusMap['completed'];
          } else {
            this.$message.error(response.data.info || '确认失败');
          }
        } catch (error) {
          console.error('确认收货失败:', error);
          this.$message.error('确认失败，请重试');
        }
      }).catch(() => {
        this.$message.info('已取消操作');
      });
    },
    checkLoginStatus() {
      const userId = sessionStorage.getItem('_id');
      if (!userId) {
        this.isLoggedIn = false;
        this.username = '';
        this.$router.push('/login');
        return;
      }
      this.isLoggedIn = true;
      axios.get("/api/self")
        .then(res => {
          if (res.data.code === 200) {
            this.username = res.data.data.name || '用户';
          } else {
            this.isLoggedIn = false;
            sessionStorage.removeItem('_id');
            this.$router.push('/login');
          }
        })
        .catch(err => {
          console.error("获取用户信息失败:", err);
          this.isLoggedIn = false;
          sessionStorage.removeItem('_id');
          this.$router.push('/login');
        });
    },
    highlightText(text, query) {
      if (!query || !text) return text;
      const regex = new RegExp(`(${query})`, 'gi');
      return text.replace(regex, '<span class="highlight">$1</span>');
    }
  }
};
</script>

<style scoped>
.order-page {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 20px;
}

.main-content {
  max-width: 1200px;
  margin: 80px auto 0;
  padding: 0 20px;
}

/* 搜索栏 */
.search-section {
  margin-bottom: 20px;
}

.search-input {
  max-width: 500px;
}

.search-input .el-input__inner {
  border-radius: 20px 0 0 20px;
}

.search-input .el-input-group__append {
  border-radius: 0 20px 20px 0;
  background: #409eff;
  color: #fff;
}

/* 订单状态标签 */
.order-tabs {
  background: #fff;
  padding: 10px 20px;
  border-radius: 8px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
  margin-bottom: 20px;
}

.el-tabs__item {
  font-size: 16px;
  font-weight: 500;
  color: #666;
}

.el-tabs__item.is-active {
  color: #409eff;
}

/* 订单表格 */
.el-table {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
}

.order-row:hover {
  background: #f9f9f9;
}

.goods-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.goods-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.goods-image {
  width: 50px;
  height: 50px;
  object-fit: cover;
  border-radius: 4px;
}

.el-table .cell {
  font-size: 14px;
  color: #606266;
}

.price {
  color: #ff4444;
  font-weight: bold;
}

.status-pending_payment { color: #e6a23c; }
.status-pending_shipping { color: #409eff; }
.status-shipped { color: #67c23a; }
.status-completed { color: #909399; }
.status-cancelled { color: #f56c6c; }

/* 高亮样式 */
.highlight {
  background: #fff3cd;
  color: #e6a23c;
  padding: 2px 4px;
  border-radius: 2px;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
}

.el-button {
  margin-right: 10px;
  min-width: 70px;
  padding: 8px 12px;
}

.el-button--text {
  color: #409eff;
  min-width: auto;
  vertical-align: middle;
}

/* 分页 */
.pagination {
  margin-top: 20px;
  text-align: right;
  background: #fff;
  padding: 10px;
  border-radius: 8px;
}

/* 订单详情对话框 */
.order-dialog .el-dialog {
  border-radius: 8px;
}

.detail-content {
  padding: 20px;
}

.el-descriptions {
  margin-bottom: 20px;
}

.el-descriptions-item__label {
  width: 120px;
  background: #fafafa;
  font-weight: bold;
}

.el-descriptions-item__content {
  color: #606266;
}

.detail-goods-image {
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: 4px;
}

.discount {
  color: #67c23a;
}

.detail-table {
  border: 1px solid #ebeef5;
}

.dialog-footer {
  text-align: right;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .main-content {
    margin-top: 70px;
    padding: 0 15px;
  }

  .search-input {
    max-width: 100%;
  }

  .order-tabs {
    padding: 10px;
  }

  .el-table {
    font-size: 12px;
  }

  .goods-image {
    width: 40px;
    height: 40px;
  }

  .el-button {
    min-width: 60px;
    padding: 6px 10px;
    font-size: 12px;
  }

  .pagination {
    text-align: center;
  }

  .order-dialog .el-dialog {
    width: 90%;
  }

  .detail-goods-image {
    width: 50px;
    height: 50px;
  }
}

@media (max-width: 480px) {
  .goods-item {
    flex-direction: column;
    align-items: flex-start;
    text-align: left;
  }

  .el-table .cell {
    padding: 5px;
  }

  .el-button {
    min-width: 50px;
    padding: 5px 8px;
  }

  .action-buttons {
    flex-direction: column;
    align-items: center;
  }

  .pagination {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 10px;
  }

  .el-descriptions-item__label {
    width: 100px;
  }
}
</style>