<template>
  <div id="login">
    <div class="login-container">
      <h1>欢迎登录</h1>
      <div class="info">
        <el-input
          placeholder="请输入账号"
          v-model="account"
          class="input-field"
          prefix-icon="el-icon-user"
        ></el-input>
        <el-input
          placeholder="请输入密码"
          v-model="password"
          show-password
          class="input-field"
          prefix-icon="el-icon-lock"
        ></el-input>
      </div>
      <div class="tool">
        <div class="type">
          <el-radio v-model="type" label="admin" class="radio-btn">管理员</el-radio>
          <el-radio v-model="type" label="user" class="radio-btn">普通用户</el-radio>
        </div>
        <div class="password">
          <el-link @click="gotoRegist" type="primary" class="link-btn">注册账号</el-link>
          <el-link type="danger" class="link-btn">忘记密码</el-link>
        </div>
        <div class="btn">
          <el-button
            class="login-btn"
            @click="login"
            type="primary"
          >登录</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Login',
  created() {
    this.isLogin();
  },
  data() {
    return {
      account: '',
      password: '',
      type: "user",
      loading: null,
    };
  },
  mounted() {
    this.$nextTick(() => {
      const container = document.querySelector('.login-container');
      if (container) {
        container.classList.add('fade-in');
      }
    });
  },
  methods: {
    isLogin() {
      this.openLoading();
      this.$axios.post("/api/islogin")
        .then(res => {
          console.log("isLogin response:", res);
          if (res.data.code == 200) {
            if (res.data.data.type == "admin") {
              this.$router.push("/admin/index");
            } else {
              this.$router.push("/");
            }
          }
          this.closeLoading();
        })
        .catch(err => {
          console.log("isLogin error:", err);
          this.closeLoading();
        });
    },
    gotoRegist() {
      this.$router.push("/regist");
    },
    openLoading(text = "加载...") {
      this.loading = this.$loading({
        lock: true,
        text: text,
        spinner: 'el-icon-loading',
        background: 'rgba(0, 0, 0, 0.7)'
      });
    },
    closeLoading() {
      if (this.loading) {
        this.loading.close();
      }
    },
    login() {
      if (!this.account || this.account.trim() === '') {
        this.$message({ message: '请输入您的账号', type: 'warning' });
        return;
      } else if (!this.password || this.password.trim() === '') {
        this.$message({ message: '请输入您的密码', type: 'warning' });
        return;
      }
      console.log("Sending login request:", { account: this.account, password: this.password, type: this.type });
      this.openLoading("登录中...");
      this.$axios.post("/api/login", { account: this.account, password: this.password, type: this.type }, {
        withCredentials: true,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        timeout: 10000
      })
        .then(res => {
          this.closeLoading();
          console.log("Login response:", res.data);
          if (res.data.code == 200) {
            sessionStorage.setItem('_id', res.data._id || 'default_id');
            console.log("Stored _id:", sessionStorage.getItem('_id'));
            // 验证登录状态
            const maxRetries = 3;
            const retryDelay = 1000; // 1秒
            let retryCount = 0;

            const checkLoginStatus = () => {
              this.$axios.post("/api/islogin", {}, {
                withCredentials: true,
                headers: {
                  'Accept': 'application/json'
                },
                timeout: 5000
              })
              .then(checkRes => {
                if (checkRes.data.code === 200) {
                  if (this.type == "admin") {
                    this.$router.push("/admin/index");
                  } else {
                    this.$router.push("/");
                  }
                } else {
                  if (retryCount < maxRetries) {
                    retryCount++;
                    console.log(`登录状态验证重试 ${retryCount}/${maxRetries}`);
                    setTimeout(checkLoginStatus, retryDelay);
                  } else {
                    this.$message.error("登录状态验证失败，请重新登录");
                    sessionStorage.removeItem('_id');
                  }
                }
              })
              .catch(err => {
                console.error("验证登录状态失败:", err);
                if (retryCount < maxRetries) {
                  retryCount++;
                  console.log(`登录状态验证重试 ${retryCount}/${maxRetries}`);
                  setTimeout(checkLoginStatus, retryDelay);
                } else {
                  this.$message.error("登录状态验证失败，请检查网络后重试");
                  sessionStorage.removeItem('_id');
                }
              });
            };

            checkLoginStatus();
          } else {
            this.$message.error(res.data.info || "登录失败");
          }
        })
        .catch(err => {
          this.closeLoading();
          console.error("Login error:", err);
          this.$message.error("登录失败");
        });
    }
  }
};
</script>

<style scoped>
/* 样式保持不变 */
#login {
  min-height: 100vh;
  background: linear-gradient(135deg, #2c3e50, #34495e);
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

.login-container {
  width: 100%;
  max-width: 500px;
  background: white;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  opacity: 0;
  transform: translateY(20px);
  transition: all 0.5s ease;
}

.login-container.fade-in {
  opacity: 1;
  transform: translateY(0);
}

h1 {
  text-align: center;
  font-size: 28px;
  font-weight: 600;
  color: #333;
  margin-bottom: 30px;
}

.info {
  margin-bottom: 20px;
}

.input-field {
  margin-bottom: 20px;
  transition: all 0.3s ease;
}

.input-field:hover {
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.tool {
  text-align: center;
}

.type {
  display: flex;
  justify-content: space-between;
  margin-bottom: 15px;
}

.radio-btn {
  color: #666;
  transition: all 0.3s ease;
}

.radio-btn:hover {
  color: #409EFF;
  transform: scale(1.05);
}

.password {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}

.link-btn {
  font-size: 14px;
  transition: all 0.3s ease;
}

.link-btn:hover {
  text-decoration: underline;
  transform: translateY(-2px);
}

.btn {
  display: flex;
  justify-content: center;
}

.login-btn {
  width: 100%;
  height: 45px;
  font-size: 16px;
  font-weight: 500;
  background: linear-gradient(90deg, #409EFF, #66b1ff);
  border: none;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.login-btn:hover {
  background: linear-gradient(90deg, #66b1ff, #409EFF);
  box-shadow: 0 5px 15px rgba(64, 158, 255, 0.4);
  transform: translateY(-2px);
}

@media (max-width: 768px) {
  .login-container {
    padding: 20px;
    max-width: 90%;
  }

  h1 {
    font-size: 24px;
  }

  .type {
    flex-direction: column;
    gap: 10px;
  }

  .password {
    flex-direction: column;
    gap: 10px;
  }

  .login-btn {
    height: 40px;
  }
}
</style>
