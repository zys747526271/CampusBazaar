<template>
  <div id="vip">
    <nav-bar
      :active-route.sync="activeRoute"
      :is-logged-in.sync="isLoggedIn"
      :username.sync="username"
      :show-search-bar="false"
      @open-loading="openLoading"
      @close-loading="closeLoading"
    />

    <div class="main-content">
      <div class="vip-section">
        <h2>VIP 会员套餐</h2>
        <div class="vip-list">
          <div
            class="vip-card"
            v-for="(vip, index) in vips"
            :key="index"
            :class="`vip-card-${vip.level}`"
          >
            <div class="vip-title">
              {{ getVipTitle(vip.level) }}
            </div>
            <div class="vip-benefits">
              <p>享受以下权益：</p>
              <ul>
                <li v-for="(benefit, i) in getVipBenefits(vip.level)" :key="i">{{ benefit }}</li>
              </ul>
            </div>
            <el-button type="primary" class="buy-btn" @click="buyVip(vip._id)">立即购买</el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import NavBar from './NavBar.vue';

export default {
  name: 'vip',
  components: {
    NavBar
  },
  created() {
    this.getAllVipItems();
    this.checkLoginStatus();
  },
  data() {
    return {
      loading: null,
      vips: [],
      activeRoute: this.$route.path,
      isLoggedIn: false,
      username: ''
    };
  },
  watch: {
    '$route'(to) {
      this.activeRoute = to.path;
      this.checkLoginStatus();
    }
  },
  methods: {
    // 显示加载提示
    openLoading(text = "加载...") {
      this.loading = this.$loading({
        lock: true,
        text: text,
        spinner: 'el-icon-loading',
        background: 'rgba(0, 0, 0, 0.7)'
      });
    },
    // 关闭加载提示
    closeLoading() {
      if (this.loading) {
        this.loading.close();
      }
    },
    // 获取所有 VIP 套餐
    getAllVipItems() {
      this.openLoading("VIP数据加载中...");
      this.$axios.get("/api/vip")
        .then(res => {
          this.closeLoading();
          if (res.data.code === 200) {
            this.vips = res.data.data;
            if (this.vips.length === 0) {
              this.$message.warning("暂无VIP套餐");
            }
          } else {
            this.$message.error(res.data.info || "加载VIP数据失败");
          }
        })
        .catch(err => {
          this.closeLoading();
          console.error("加载VIP数据失败:", err);
          this.$message.error("加载VIP数据失败，请检查网络");
        });
    },
    // 获取 VIP 标题
    getVipTitle(level) {
      switch (level) {
        case 1: return "普通会员";
        case 2: return "豪华会员";
        case 3: return "超级会员";
        default: return "VIP 会员";
      }
    },
    // 获取 VIP 权益
    getVipBenefits(level) {
      switch (level) {
        case 1: return ["享受 9 折优惠"];
        case 2: return ["享受 8 折优惠"];
        case 3: return ["享受 7 折优惠"];
        default: return ["享受专属折扣"];
      }
    },
    // 购买 VIP
    buyVip(vipId) {
      this.openLoading("交易中...");
      this.$axios.post("/api/buy/vip", { vipId })
        .then(res => {
          this.closeLoading();
          if (res.data.code === 200) {
            this.$message.success("购买成功");
            this.checkLoginStatus();
          } else {
            this.$message.warning(res.data.info || "购买失败");
          }
        })
        .catch(err => {
          this.closeLoading();
          console.error("购买失败:", err);
          this.$message.error("购买失败");
        });
    },
    // 检查登录状态
    checkLoginStatus() {
      const userId = sessionStorage.getItem('_id');
      if (!userId || userId === '') {
        this.isLoggedIn = false;
        this.username = '';
        this.$router.push('/login');
        return;
      }
      this.isLoggedIn = true;
      this.$axios.get("/api/self")
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
    }
  }
};
</script>

<style scoped>
#vip {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 20px;
}

.main-content {
  margin-top: 70px;
  padding: 0 20px;
}

.vip-section {
  max-width: 1200px;
  margin: 0 auto;
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
}

.vip-section h2 {
  font-size: 24px;
  color: #333;
  margin: 0 0 20px;
  font-weight: 600;
}

.vip-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.vip-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s ease;
}

.vip-card:hover {
  transform: translateY(-5px);
}

.vip-title {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 20px;
  color: #333;
}

.vip-benefits {
  text-align: left;
  margin-bottom: 20px;
}

.vip-benefits p {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 10px;
  color: #666;
}

.vip-benefits ul {
  list-style: none;
  padding: 0;
}

.vip-benefits li {
  font-size: 14px;
  margin-bottom: 8px;
  color: #888;
}

.buy-btn {
  width: 100%;
  background: #409EFF;
  border: none;
  border-radius: 4px;
  color: #fff;
}

.buy-btn:hover {
  background: #66b1ff;
}

.vip-card-1 { border: 2px solid #409EFF; }
.vip-card-2 { border: 2px solid #ff9a9e; }
.vip-card-3 { border: 2px solid #fbc2eb; }

@media (max-width: 768px) {
  .vip-list {
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  }
}
</style>
