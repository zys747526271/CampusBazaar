<template>
  <div id="balance">
    <nav-bar
      :active-route.sync="activeRoute"
      :is-logged-in.sync="isLoggedIn"
      :username.sync="username"
      :show-search-bar="false"
      @open-loading="openLoading"
      @close-loading="closeLoading"
    />

    <div class="main-content">
      <div class="balance-section">
        <h2>余额充值</h2>
        <el-card class="balance-card" shadow="always">
          <div class="balance-info">
            <span class="balance-label">当前余额：</span>
            <span class="balance-value">￥{{ balance.toFixed(2) }}</span>
          </div>

          <el-form ref="rechargeForm" :model="rechargeForm" :rules="rules" class="recharge-form">
            <el-form-item label="充值金额" prop="money">
              <el-input
                v-model.number="rechargeForm.money"
                placeholder="请输入充值金额（最低1元）"
                clearable
                type="number"
                :min="1"
                step="1"
              >
                <template slot="prepend">￥</template>
              </el-input>
            </el-form-item>
            <div class="quick-options">
              <el-button
                v-for="option in quickOptions"
                :key="option"
                @click="setAmount(option)"
                plain
                size="small"
              >
                ￥{{ option }}
              </el-button>
            </div>
            <el-form-item>
              <el-button type="primary" @click="topUp" :loading="loading">立即充值</el-button>
            </el-form-item>
            <div class="tips">
              <p>温馨提示：充值金额将直接存入您的账户余额，可用于商城消费。</p>
            </div>
          </el-form>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script>
import NavBar from './NavBar.vue';
import axios from 'axios';

export default {
  components: {
    NavBar
  },
  name: 'Balance',
  created() {
    this.checkLoginStatus();
    this.getBalance();
  },
  data() {
    return {
      loading: false,
      balance: 0,
      rechargeForm: {
        money: ''
      },
      rules: {
        money: [
          { required: true, message: '请输入充值金额', trigger: 'blur' },
          { type: 'number', min: 1, message: '金额必须大于0', trigger: 'blur' }
        ]
      },
      quickOptions: [50, 100, 200, 500],
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
    openLoading(text = "充值中...") {
      this.loading = true;
      this.$message({
        message: text,
        type: 'info',
        duration: 0
      });
    },
    // 关闭加载提示
    closeLoading() {
      this.loading = false;
      this.$message.closeAll();
    },
    // 获取当前余额
    async getBalance() {
      this.openLoading("加载余额...");
      try {
        const res = await this.$axios.get("/api/self");
        this.closeLoading();
        if (res.data.code === 200) {
          this.balance = res.data.data.balance || 0;
        } else {
          this.$message.error(res.data.info || '获取余额失败');
        }
      } catch (err) {
        this.closeLoading();
        console.error('获取余额失败:', err);
        this.$message.error('网络错误，请稍后重试');
      }
    },
    // 设置快捷充值金额
    setAmount(amount) {
      this.rechargeForm.money = amount;
    },
    // 执行充值
    async topUp() {
      this.$refs.rechargeForm.validate(async (valid) => {
        if (valid) {
          this.openLoading();
          try {
            const formData = new FormData();
            formData.append('balance', this.rechargeForm.money);

            const res = await this.$axios.post("/api/balance", formData, {
              headers: {
                'Content-Type': 'multipart/form-data'
              }
            });

            this.closeLoading();
            if (res.data.code === 200) {
              this.$message.success('充值成功');
              this.balance += this.rechargeForm.money;
              this.rechargeForm.money = '';
              this.$refs.rechargeForm.resetFields();
            } else {
              this.$message.error(res.data.info || '充值失败');
            }
          } catch (err) {
            this.closeLoading();
            console.error('充值请求失败:', err);
            // 检查错误响应是否存在并提取信息
            let errorMessage = '充值失败，请检查网络';
            if (err.response && err.response.data && err.response.data.info) {
              errorMessage = err.response.data.info;
            }
            this.$message.error(errorMessage);
          }
        } else {
          this.$message.warning('请正确输入充值金额');
        }
      });
    },
    // 检查登录状态
    async checkLoginStatus() {
      const userId = sessionStorage.getItem('_id');
      if (!userId) {
        this.isLoggedIn = false;
        this.username = '';
        this.$router.push('/login');
        return;
      }
      try {
        const res = await this.$axios.get("/api/self");
        if (res.data.code === 200) {
          this.isLoggedIn = true;
          this.username = res.data.data.name || '用户';
          this.balance = res.data.data.balance || 0;
        } else {
          this.isLoggedIn = false;
          sessionStorage.removeItem('_id');
          this.$router.push('/login');
        }
      } catch (err) {
        console.error("检查登录状态失败:", err);
        this.isLoggedIn = false;
        sessionStorage.removeItem('_id');
        this.$router.push('/login');
      }
    }
  }
};
</script>

<style scoped>
#balance {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 20px;
}

.main-content {
  margin-top: 80px;
  padding: 0 20px;
}

.balance-section {
  max-width: 1200px;
  margin: 0 auto;
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
}

.balance-section h2 {
  font-size: 24px;
  color: #333;
  margin: 0 0 20px;
  text-align: center;
}

.balance-card {
  padding: 20px;
  text-align: center;
}

.balance-info {
  margin-bottom: 20px;
}

.balance-label {
  font-size: 16px;
  color: #666;
}

.balance-value {
  font-size: 24px;
  color: #409EFF;
  font-weight: bold;
  margin-left: 10px;
}

.recharge-form {
  max-width: 400px;
  margin: 0 auto;
}

.quick-options {
  margin: 10px 0;
  display: flex;
  justify-content: space-around;
}

.quick-options .el-button {
  border-radius: 20px;
}

.el-button[type="primary"] {
  background: #409EFF;
  border: none;
  color: white;
  border-radius: 4px;
  width: 100%;
  margin-top: 20px;
}

.el-button[type="primary"]:hover {
  background: #66b1ff;
}

@media (max-width: 768px) {
  .main-content {
    margin-top: 70px;
  }

  .balance-section {
    padding: 15px;
  }

  .recharge-form {
    max-width: 100%;
  }
}
</style>
