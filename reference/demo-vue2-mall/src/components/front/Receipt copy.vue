<template>
  <div id="receipt">
    <nav-bar
      :active-route.sync="activeRoute"
      :is-logged-in.sync="isLoggedIn"
      :username.sync="username"
      :show-search-bar="true"
      @open-loading="openLoading"
      @close-loading="closeLoading"
    />

    <div class="main-content">
      <div class="receipt-section">
        <h2>我的订单</h2>
        <div class="search-bar">
          <el-input
            v-model="searchQuery"
            placeholder="输入订单号或商品名称搜索"
            clearable
            @keyup.enter.native="searchReceipts"
            style="width: 300px;"
          >
            <el-button slot="append" icon="el-icon-search" style="font-size: 14px; padding: 8px 12px;" @click="searchReceipts"></el-button>
          </el-input>
        </div>
        <el-table
          ref="receiptTable"
          :data="receipts"
          style="width: 100%; margin-top: 20px;"
          stripe
          v-if="receipts.length > 0"
          @row-click="handleRowClick"
          highlight-current-row
          class="receipt-table"
          :max-height="tableHeight"
        >
          <el-table-column type="expand">
            <template slot-scope="scope">
              <div class="expand-details">
                <div class="details-left">
                  <div class="detail-item">
                    <span class="detail-label">订单号：</span>
                    <span class="detail-value">{{ scope.row.orderNum }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">购买时间：</span>
                    <span class="detail-value">{{ scope.row.createTime }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">实际支付：</span>
                    <span class="detail-value">￥{{ scope.row.payValue }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">优惠金额：</span>
                    <span class="detail-value">￥{{ scope.row.cutoffValue.toFixed(2) }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">收货地址：</span>
                    <span class="detail-value">{{ scope.row.address }}</span>
                  </div>
                  <div class="detail-item" v-if="scope.row.goodsList.length > 0">
                    <span class="detail-label">发货地址：</span>
                    <span class="detail-value">{{ scope.row.goodsList[0].sendAddress }}</span>
                  </div>
                </div>
                <div class="details-right">
                  <div class="detail-item">
                    <span class="detail-label">商品详情：</span>
                    <ul class="goods-list">
                      <li v-for="(good, index) in scope.row.goodsList" :key="index">
                        <span class="goods-name" v-html="highlight(good.name, searchQuery)"></span>
                        <span class="goods-quantity">x{{ good.quantity }}</span>
                        <span class="goods-price">￥{{ good.sellPrice }} <del v-if="good.originPrice > good.sellPrice">￥{{ good.originPrice }}</del></span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="订单号" prop="orderNum" align="center" width="180">
            <template slot-scope="scope">
              <span v-html="highlight(scope.row.orderNum, searchQuery)"></span>
            </template>
          </el-table-column>
          <el-table-column label="状态" align="center" width="100">
            <template slot-scope="scope">
              <el-tag v-if="scope.$index === 0 && currentPage === 1" type="success">最新</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="购买时间" prop="createTime" align="center" width="150"></el-table-column>
          <el-table-column label="实际支付" prop="payValue" align="center" width="120">
            <template slot-scope="scope">
              <span class="price">￥{{ scope.row.payValue }}</span>
            </template>
          </el-table-column>
          <el-table-column label="商品信息" align="center">
            <template slot-scope="scope">
              <ul class="goods-list" v-if="scope.row.goodsList.length > 0">
                <li v-for="(good, index) in scope.row.goodsList" :key="index">
                  <span class="goods-name" v-html="highlight(good.name, searchQuery)"></span>
                  <span class="goods-quantity">x{{ good.quantity }}</span>
                  <span class="goods-price">￥{{ good.sellPrice }}</span>
                </li>
              </ul>
              <span v-else>无商品信息</span>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="receipts.length === 0" description="暂无订单" class="empty-tip">
          <el-button type="primary" @click="$router.push('/')">去逛逛</el-button>
        </el-empty>
        <el-pagination
          v-if="receipts.length > 0"
          @current-change="handlePageChange"
          :current-page="currentPage"
          :page-size="pageSize"
          layout="total, prev, pager, next"
          :total="total"
          class="pagination"
        ></el-pagination>
      </div>
    </div>
  </div>
</template>

<script>
import NavBar from './NavBar.vue';

export default {
  name: 'Receipt',
  components: {
    NavBar,
  },
  created() {
    this.checkLoginStatus();
  },
  data() {
    return {
      loading: null,
      receipts: [],
      currentPage: 1,
      pageSize: 10,
      total: 0,
      activeRoute: this.$route.path,
      isLoggedIn: false,
      username: '',
      userId: null, // 存储用户ID
      searchQuery: '', // 搜索关键字
      tableHeight: 500, // 动态表格高度
    };
  },
  mounted() {
    this.updateTableHeight();
    window.addEventListener('resize', this.updateTableHeight);
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.updateTableHeight);
  },
  watch: {
    '$route'(to) {
      this.activeRoute = to.path;
      this.checkLoginStatus();
    },
  },
  methods: {
    openLoading(text = '数据加载...') {
      this.loading = this.$loading({
        lock: true,
        text: text,
        spinner: 'el-icon-loading',
        background: 'rgba(0, 0, 0, 0.7)',
      });
    },
    closeLoading() {
      if (this.loading) {
        this.loading.close();
      }
    },
    updateTableHeight() {
      this.tableHeight = window.innerHeight - 200; // 动态调整表格高度
    },
    highlight(text, query) {
    if (!query || !text) return text;
    const strText = String(text); // 确保是字符串
    const regex = new RegExp(`(${query})`, 'gi');
    const result = strText.replace(regex, '<span class="highlight">$1</span>');
    console.log(`Text: ${strText}, Query: ${query}, Result: ${result}`);
    return result;
  },
  getAllReceipt(page = 1) {
    if (!this.userId) {
      this.$message.error('用户ID未获取，请重新登录');
      this.$router.push('/login');
      return;
    }
    this.openLoading();
    this.$axios
      .get(`/api/self/receipt`, {
        params: {
          page: page,
          size: this.pageSize,
          user_id: this.userId,
          search: this.searchQuery
        }
      })
      .then((res) => {
        this.closeLoading();
        if (res.data.code === 200) {
          this.receipts = [...(res.data.data.data || [])]; // 强制更新
          this.total = res.data.data.total || this.receipts.length;
          this.currentPage = page;
          this.$nextTick(() => {
            this.$refs.receiptTable.doLayout(); // 强制重新渲染
          });
        } else {
          this.$message.error(res.data.info || '获取订单失败');
        }
      })
      .catch((err) => {
        this.closeLoading();
        this.$message.error('获取订单失败，请检查网络或登录状态');
      });
  },
    handleRowClick(row) {
      this.$refs.receiptTable.toggleRowExpansion(row);
    },
    handlePageChange(page) {
      this.getAllReceipt(page);
    },
    searchReceipts() {
    console.log('Search Query:', this.searchQuery); // 调试
    this.currentPage = 1;
    this.getAllReceipt();
  },
    checkLoginStatus() {
      const userId = sessionStorage.getItem('_id');
      if (!userId) {
        this.isLoggedIn = false;
        this.username = '';
        this.userId = null;
        this.$router.push('/login');
        return;
      }
      this.isLoggedIn = true;
      this.userId = userId;
      this.openLoading('验证登录状态...');
      this.$axios
        .get('/api/self')
        .then((res) => {
          this.closeLoading();
          if (res.data.code === 200) {
            this.username = res.data.data.name || '用户';
            this.getAllReceipt(); // 登录成功后加载订单
          } else {
            this.isLoggedIn = false;
            this.userId = null;
            sessionStorage.removeItem('_id');
            this.$message.error('登录状态无效，请重新登录');
            this.$router.push('/login');
          }
        })
        .catch((err) => {
          this.closeLoading();
          console.error('获取用户信息失败:', err);
          this.isLoggedIn = false;
          this.userId = null;
          sessionStorage.removeItem('_id');
          this.$message.error('获取用户信息失败，请重新登录');
          this.$router.push('/login');
        });
    },
  },
};
</script>

<style scoped>
#receipt {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 20px;
}

.main-content {
  margin-top: 80px;
  padding: 0 20px;
}

.receipt-section {
  max-width: 1200px;
  margin: 0 auto;
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
}

.receipt-section h2 {
  font-size: 24px;
  color: #333;
  margin: 0 0 20px;
  text-align: center;
}

.search-bar {
  margin-bottom: 20px;
  display: flex;
  justify-content: center;
}

.receipt-table {
  border-radius: 8px;
  overflow: hidden;
}

.expand-details {
  padding: 20px;
  background: #f9f9f9;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  gap: 20px;
}

.details-left,
.details-right {
  flex: 1;
}

.detail-item {
  margin-bottom: 15px;
  display: flex;
  align-items: flex-start;
}

.detail-label {
  font-weight: bold;
  color: #333;
  min-width: 100px;
}

.detail-value {
  color: #666;
  flex: 1;
  word-break: break-word;
}

.goods-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.goods-list li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #eee;
}

.goods-list li:last-child {
  border-bottom: none;
}

.goods-name {
  font-size: 14px;
  color: #333;
  flex: 1;
}

.goods-quantity {
  font-size: 14px;
  color: #666;
  margin: 0 10px;
}

.goods-price {
  font-size: 14px;
  color: #409eff;
  font-weight: bold;
}

.goods-price del {
  color: #999;
  font-size: 12px;
  margin-left: 5px;
}

.price {
  font-size: 16px;
  color: #409eff;
  font-weight: bold;
}

.empty-tip {
  margin-top: 50px;
}

.pagination {
  margin-top: 20px;
  text-align: center;
}

.el-button {
  margin-top: 20px;
  background: #409eff;
  border: none;
  color: white;
  border-radius: 4px;
}

.el-button:hover {
  background: #66b1ff;
}

.highlight {
  background-color: #ffff99;
  font-weight: bold;
}

@media (max-width: 768px) {
  .main-content {
    margin-top: 70px;
  }

  .receipt-section {
    padding: 15px;
  }

  .receipt-section h2 {
    font-size: 20px;
  }

  .expand-details {
    flex-direction: column;
  }

  .detail-label {
    min-width: 80px;
  }

  .search-bar {
    flex-direction: column;
  }

  .el-input {
    width: 100% !important;
    margin-bottom: 10px;
  }
}
</style>
