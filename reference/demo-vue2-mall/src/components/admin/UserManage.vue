<template>
  <div id="user-manage">
    <div class="main-container">
      <!-- 左侧用户列表 -->
      <div class="left-panel">
        <div class="search-bar">
          <el-select v-model="userSearchType" placeholder="搜索类型" style="width: 150px; margin-right: 10px;">
            <el-option label="用户名/账号" value="user"></el-option>
            <el-option label="订单号" value="order"></el-option>
            <el-option label="购买商品" value="goods"></el-option>
          </el-select>
          <el-input
            v-model="userSearchQuery"
            placeholder="输入搜索内容"
            clearable
            @keyup.enter.native="searchUsers"
            style="width: 300px;"
          >
            <el-button slot="append" icon="el-icon-search" @click="searchUsers"></el-button>
          </el-input>
        </div>
        <el-table
          :data="userTableData"
          border
          style="width: 100%; margin-top: 20px;"
          :max-height="tableHeight"
          :row-class-name="rowClassName"
          @row-click="selectUser"
          highlight-current-row
        >
          <el-table-column prop="createTime" label="注册时间" width="150"></el-table-column>
          <el-table-column prop="account" label="账号" width="120">
            <template slot-scope="scope">
              <span v-html="highlight(scope.row.account, userSearchQuery, userSearchType === 'user')"></span>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="姓名" width="120">
            <template slot-scope="scope">
              <span v-html="highlight(scope.row.name, userSearchQuery, userSearchType === 'user')"></span>
            </template>
          </el-table-column>
          <el-table-column prop="balance" label="余额" width="120"></el-table-column>
          <el-table-column label="登录时间" width="150">
            <template slot-scope="scope">
              <div class="time-split">
                <div>{{ formatDate(scope.row.loginTime) }}</div>
                <div>{{ formatTime(scope.row.loginTime) }}</div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="退出时间" width="150">
            <template slot-scope="scope">
              <div class="time-split">
                <div>{{ formatDate(scope.row.logoutTime) }}</div>
                <div>{{ formatTime(scope.row.logoutTime) }}</div>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="banned" label="状态" width="100">
            <template slot-scope="scope">
              <el-tag :type="scope.row.banned ? 'danger' : 'success'">
                {{ scope.row.banned ? '已封禁' : '正常' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200">
            <template slot-scope="scope">
              <el-button
                :type="scope.row.banned ? 'success' : 'danger'"
                size="small"
                @click.stop="toggleBanUser(scope.row)"
              >
                {{ scope.row.banned ? '解封' : '封禁' }}
              </el-button>
              <el-button type="danger" size="small" @click.stop="deleteUser(scope.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          layout="total, prev, pager, next"
          @current-change="userPageChange"
          :current-page="userCurrentPage"
          :page-size="userPageSize"
          :total="userTotal"
          style="margin-top: 10px; text-align: center;"
        ></el-pagination>
      </div>

      <!-- 右侧订单和详情 -->
      <div class="right-panel">
        <div class="search-bar" v-if="selectedUser">
          <el-select v-model="orderSearchType" placeholder="搜索类型" style="width: 150px; margin-right: 10px;">
            <el-option label="订单号" value="order"></el-option>
            <el-option label="购买商品" value="goods"></el-option>
          </el-select>
          <el-input
            v-model="orderSearchQuery"
            placeholder="输入搜索内容"
            clearable
            @keyup.enter.native="searchOrders"
            style="width: 300px;"
          >
            <el-button slot="append" icon="el-icon-search" @click="searchOrders"></el-button>
          </el-input>
        </div>
        <el-table
          v-if="selectedUser"
          :data="orderTableData"
          border
          style="width: 100%; margin-top: 20px;"
          :max-height="tableHeight"
          @row-click="selectOrder"
          highlight-current-row
        >
          <el-table-column prop="orderNum" label="订单号" width="180">
            <template slot-scope="scope">
              <span v-html="highlight(scope.row.orderNum, orderSearchQuery, orderSearchType === 'order')"></span>
            </template>
          </el-table-column>
          <el-table-column prop="createTime" label="购买时间" width="150"></el-table-column>
          <el-table-column prop="payValue" label="支付金额" width="120"></el-table-column>
          <el-table-column prop="address" label="收货地址" min-width="200"></el-table-column>
        </el-table>
        <el-pagination
          v-if="selectedUser && orderTableData.length > 0"
          @current-change="orderPageChange"
          :current-page="orderCurrentPage"
          :page-size="orderPageSize"
          :total="orderTotal"
          layout="total, prev, pager, next"
          style="margin-top: 10px; text-align: center;"
        ></el-pagination>
        <div v-if="selectedOrder" class="order-details">
          <h3>订单详情 - {{ selectedOrder.orderNum }}</h3>
          <el-descriptions border :column="2">
            <el-descriptions-item label="订单号">{{ selectedOrder.orderNum }}</el-descriptions-item>
            <el-descriptions-item label="购买时间">{{ selectedOrder.createTime }}</el-descriptions-item>
            <el-descriptions-item label="支付金额">￥{{ selectedOrder.payValue }}</el-descriptions-item>
            <el-descriptions-item label="优惠金额">￥{{ selectedOrder.cutoffValue.toFixed(2) }}</el-descriptions-item>
            <el-descriptions-item label="收货地址" :span="2">{{ selectedOrder.address }}</el-descriptions-item>
            <el-descriptions-item label="商品详情" :span="2">
              <ul class="goods-list">
                <li v-for="(good, index) in selectedOrder.goodsList" :key="index">
                  <span v-html="highlight(good.name, orderSearchQuery, orderSearchType === 'goods')"></span>
                  x {{ good.quantity }} - ￥{{ good.sellPrice }}
                </li>
              </ul>
            </el-descriptions-item>
          </el-descriptions>
        </div>
        <el-empty v-if="!selectedUser" description="请选择用户以查看订单"></el-empty>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'UserManage',
  created() {
    this.getUserTotal(); // 初始化用户总数
    this.getUserPageData(1); // 加载第一页用户数据
    this.updateTableHeight(); // 初始化表格高度
  },
  mounted() {
    window.addEventListener('resize', this.updateTableHeight); // 监听窗口大小变化
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.updateTableHeight); // 移除监听
  },
  data() {
    return {
      userTotal: 0, // 用户总数
      userPageSize: 10, // 每页用户数
      userCurrentPage: 1, // 当前用户页码
      userTableData: [], // 用户表格数据
      userSearchQuery: '', // 用户搜索关键字
      userSearchType: 'user', // 用户搜索类型
      selectedUser: null, // 选中的用户
      orderTotal: 0, // 订单总数
      orderPageSize: 5, // 每页订单数
      orderCurrentPage: 1, // 当前订单页码
      orderTableData: [], // 订单表格数据
      orderSearchQuery: '', // 订单搜索关键字
      orderSearchType: 'order', // 订单搜索类型
      selectedOrder: null, // 选中的订单
      loading: null, // 加载状态
      tableHeight: 500, // 表格最大高度，动态计算
    };
  },
  methods: {
    // 显示加载提示
    openLoading(text = '加载...') {
      this.loading = this.$loading({
        lock: true,
        text: text,
        spinner: 'el-icon-loading',
        background: 'rgba(0, 0, 0, 0.7)',
      });
    },
    // 关闭加载提示
    closeLoading() {
      if (this.loading) {
        this.loading.close();
      }
    },
    // 更新表格高度
    updateTableHeight() {
      const windowHeight = window.innerHeight;
      this.tableHeight = windowHeight - 200; // 减去顶部导航、搜索栏等高度
    },
    // 高亮搜索关键字
    highlight(text, query, match) {
      if (!match || !query || !text) return text;
      const regex = new RegExp(`(${query})`, 'gi');
      return text.replace(regex, '<span class="highlight">$1</span>');
    },
    // 格式化日期
    formatDate(time) {
      if (!time) return '未知';
      return time.split(' ')[0]; // 只取日期部分
    },
    // 格式化时间
    formatTime(time) {
      if (!time) return '';
      return time.split(' ')[1]; // 只取时间部分
    },
    // 获取用户总数
    getUserTotal() {
      this.openLoading('加载用户总数...');
      this.$axios
        .get('/api/users')
        .then((res) => {
          this.closeLoading();
          if (res.data.code === 200) {
            this.userTotal = res.data.data.nums;
          } else {
            this.$message.error(res.data.info || '获取用户总数失败');
          }
        })
        .catch((err) => {
          this.closeLoading();
          console.error('获取用户总数失败:', err);
          this.$message.error('网络错误，请稍后重试');
        });
    },
    // 获取分页用户数据
    getUserPageData(page) {
      this.openLoading('加载用户数据...');
      this.$axios
        .post('/api/users', {
          start: (page - 1) * this.userPageSize,
          nums: this.userPageSize,
          search: this.userSearchQuery,
          search_type: this.userSearchType,
        })
        .then((res) => {
          this.closeLoading();
          if (res.data.code === 200) {
            this.userTableData = res.data.data.data;
            this.userCurrentPage = page;
            if (this.userSearchQuery) {
              this.userTotal = this.userTableData.length; // 搜索时更新总数
            }
            if (this.selectedUser) {
              this.selectedUser = this.userTableData.find((u) => u._id === this.selectedUser._id) || null;
              if (this.selectedUser) this.getOrderPageData(1);
            }
          } else {
            this.$message.error(res.data.info || '加载用户数据失败');
          }
        })
        .catch((err) => {
          this.closeLoading();
          console.error('加载用户数据失败:', err);
          this.$message.error('网络错误，请稍后重试');
        });
    },
    // 用户分页变化
    userPageChange(page) {
      this.getUserPageData(page);
    },
    // 用户搜索
    searchUsers() {
      this.userCurrentPage = 1;
      this.getUserPageData(1);
    },
    // 选择用户
    selectUser(row) {
      this.selectedUser = row;
      this.orderSearchQuery = '';
      this.orderCurrentPage = 1;
      this.getOrderPageData(1);
    },
    // 获取分页订单数据
    getOrderPageData(page) {
      if (!this.selectedUser) return;
      this.openLoading('加载订单数据...');
      this.$axios
        .get(`/api/self/receipt?page=${page}&size=${this.orderPageSize}&user_id=${this.selectedUser._id}`, {
          params: {
            search: this.orderSearchQuery,
            search_type: this.orderSearchType,
          },
        })
        .then((res) => {
          this.closeLoading();
          if (res.data.code === 200) {
            this.orderTableData = res.data.data.data;
            this.orderTotal = res.data.data.total;
            this.orderCurrentPage = page;
            this.selectedOrder = null; // 重置订单详情
          } else {
            this.$message.error(res.data.info || '加载订单失败');
          }
        })
        .catch((err) => {
          this.closeLoading();
          console.error('加载订单失败:', err);
          this.$message.error('加载订单失败，请稍后重试');
        });
    },
    // 订单分页变化
    orderPageChange(page) {
      this.getOrderPageData(page);
    },
    // 订单搜索
    searchOrders() {
      this.orderCurrentPage = 1;
      this.getOrderPageData(1);
    },
    // 选择订单
    selectOrder(row) {
      this.selectedOrder = row;
    },
    // 删除用户
    deleteUser(row) {
      this.$confirm(`确认删除用户 ${row.name || row.account} 吗？`, '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      })
        .then(() => {
          this.openLoading('删除中...');
          this.$axios
            .delete('/api/user/delete', { data: { id: row._id } })
            .then((res) => {
              this.closeLoading();
              if (res.data.code === 200) {
                this.$message.success('删除成功');
                this.selectedUser = this.selectedUser && this.selectedUser._id === row._id ? null : this.selectedUser;
                this.getUserPageData(this.userCurrentPage);
              } else {
                this.$message.error(res.data.info || '删除失败');
              }
            })
            .catch((err) => {
              this.closeLoading();
              console.error('删除用户失败:', err);
              this.$message.error('删除失败，请稍后重试');
            });
        })
        .catch(() => {
          this.$message.info('已取消删除');
        });
    },
    // 封禁/解封用户
    toggleBanUser(row) {
      const action = row.banned ? '解封' : '封禁';
      this.$confirm(`确认${action}用户 ${row.name || row.account} 吗？`, '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      })
        .then(() => {
          this.openLoading(`${action}中...`);
          this.$axios
            .post('/api/user/ban', {
              user_id: row._id,
              is_banned: !row.banned,
            })
            .then((res) => {
              this.closeLoading();
              if (res.data.code === 200) {
                this.$message.success(`${action}成功`);
                row.banned = !row.banned;
              } else {
                this.$message.error(res.data.info || `${action}失败`);
              }
            })
            .catch((err) => {
              this.closeLoading();
              console.error(`${action}用户失败:`, err);
              this.$message.error(`${action}失败，请稍后重试`);
            });
        })
        .catch(() => {
          this.$message.info(`已取消${action}`);
        });
    },
    // 设置封禁用户的行样式
    rowClassName({ row }) {
      return row.banned ? 'banned-row' : '';
    },
  },
};
</script>

<style scoped>
#user-manage {
  padding: 20px;
  background: #f5f7fa;
  min-height: 100vh;
}

.main-container {
  display: flex;
  gap: 20px;
  height: calc(100vh - 40px); /* 减去padding */
}

.left-panel,
.right-panel {
  flex: 1;
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
  overflow-y: auto; /* 仅垂直滚动 */
  overflow-x: hidden; /* 无水平滚动 */
}

.search-bar {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}

.el-table {
  border-radius: 8px;
}

.el-table .banned-row {
  background-color: #ffebeb;
}

.time-split {
  display: flex;
  flex-direction: column;
  font-size: 12px;
}

.time-split div:first-child {
  font-weight: bold;
}

.order-details {
  margin-top: 20px;
  padding: 15px;
  background: #fafafa;
  border-radius: 8px;
}

.order-details h3 {
  margin: 0 0 10px;
  font-size: 18px;
  color: #333;
}

.goods-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.goods-list li {
  padding: 5px 0;
  border-bottom: 1px solid #eee;
}

.highlight {
  background-color: #ffff99;
  font-weight: bold;
}

@media (max-width: 768px) {
  .main-container {
    flex-direction: column;
    height: auto;
  }

  .search-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .el-select,
  .el-input {
    width: 100% !important;
    margin-bottom: 10px;
  }
}
</style>
