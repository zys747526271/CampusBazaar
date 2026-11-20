<template>
  <div id="regist">
    <div class="regist-container">
      <h1>欢迎注册</h1>
      <el-form :model="form" :rules="rules" ref="registForm" class="regist-form">
        <el-form-item prop="account">
          <el-input
            placeholder="请输入手机号（必填）"
            v-model="form.account"
            class="input-field"
            prefix-icon="el-icon-phone"
            @input="validatePhone"
          ></el-input>
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            placeholder="请输入密码（必填）"
            v-model="form.password"
            show-password
            class="input-field"
            prefix-icon="el-icon-lock"
          ></el-input>
        </el-form-item>
        <el-form-item prop="username">
          <el-input
            placeholder="请输入用户名（选填）"
            v-model="form.username"
            class="input-field"
            prefix-icon="el-icon-user"
          ></el-input>
        </el-form-item>
        <div v-if="registType === 'user'" class="form-section">
          <el-form-item prop="birthDate">
            <el-date-picker
              v-model="form.birthDate"
              type="date"
              placeholder="请选择出生日期（选填）"
              class="input-field"
              format="yyyy-MM-dd"
              value-format="yyyy-MM-dd"
            ></el-date-picker>
          </el-form-item>
          <el-form-item prop="idCard">
            <el-input
              placeholder="请输入身份证号（必填）"
              v-model="form.idCard"
              class="input-field"
              prefix-icon="el-icon-tickets"
              @input="validateIdCard"
            ></el-input>
          </el-form-item>
          <el-form-item prop="gender">
            <el-select v-model="form.gender" placeholder="请选择性别（选填）" class="input-field">
              <el-option label="男" value="男"></el-option>
              <el-option label="女" value="女"></el-option>
              <el-option label="其他" value="其他"></el-option>
            </el-select>
          </el-form-item>
        </div>
        <div v-if="registType === 'admin'" class="form-section">
          <el-form-item prop="level">
            <el-select v-model="form.level" placeholder="请选择管理员等级（选填）" class="input-field">
              <el-option label="普通管理员 (1)" :value="1"></el-option>
              <el-option label="高级管理员 (2)" :value="2"></el-option>
            </el-select>
          </el-form-item>
        </div>
        <el-form-item>
          <el-radio-group v-model="registType" class="radio-group">
            <el-radio label="user" class="radio-btn">用户注册</el-radio>
            <el-radio label="admin" class="radio-btn">管理员注册</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <div class="btn-group">
        <el-button class="action-btn regist-btn" type="primary" @click="regist">注册</el-button>
        <div class="back-buttons">
          <el-button class="back-btn" @click="$router.push('/login')">返回登录</el-button>
          <el-button class="back-btn" @click="$router.push('/')">返回主页</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Regist',
  data() {
    const validatePhone = (rule, value, callback) => {
      const phoneReg = /^1[3-9]\d{9}$/;
      if (!value) {
        callback(new Error('请输入手机号'));
      } else if (!phoneReg.test(value)) {
        callback(new Error('请输入有效的11位手机号'));
      } else {
        callback();
      }
    };
    const validateIdCard = (rule, value, callback) => {
      const idCardReg = /^[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}(\d|X)$/i;
      if (!value) {
        callback(new Error('请输入身份证号'));
      } else if (!idCardReg.test(value)) {
        callback(new Error('请输入有效的身份证号'));
      } else {
        callback();
      }
    };
    return {
      form: {
        account: '',
        password: '',
        username: '',
        birthDate: '',
        idCard: '',
        gender: '',
        level: undefined
      },
      registType: 'user',
      rules: {
        account: [{ validator: validatePhone, trigger: 'blur' }],
        password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
        idCard: [{ validator: validateIdCard, trigger: 'blur' }]
      },
      loading: null
    };
  },
  mounted() {
    this.$nextTick(() => {
      const container = document.querySelector('.regist-container');
      if (container) {
        container.classList.add('fade-in');
      }
    });
  },
  methods: {
    validatePhone() {
      this.$refs.registForm.validateField('account');
    },
    validateIdCard() {
      this.$refs.registForm.validateField('idCard');
    },
    regist() {
      this.$refs.registForm.validate((valid) => {
        if (!valid) {
          return;
        }

        this.openLoading("注册中...");

        const payload = {
          account: this.form.account,
          password: this.form.password,
          name: this.form.username || undefined
        };

        if (this.registType === 'user') {
          Object.assign(payload, {
            birthDate: this.form.birthDate || undefined,
            idCard: this.form.idCard,
            gender: this.form.gender || undefined
          });
          this.$axios.post("/api/regist", payload)
            .then(res => {
              this.closeLoading();
              if (res.data.code === 200) {
                this.$message.success("注册成功，已为您自动登录");
                this.loginAfterRegist();
              } else {
                this.$message.error(res.data.info || "注册失败");
              }
            })
            .catch(err => {
              this.closeLoading();
              console.error("注册失败:", err);
              this.$message.error("注册失败");
            });
        } else if (this.registType === 'admin') {
          Object.assign(payload, {
            level: this.form.level || 1
          });
          this.$axios.post("/api/admin/add", payload)
            .then(res => {
              this.closeLoading();
              if (res.data.code === 200) {
                this.$message.success("管理员注册成功，请登录");
                this.$router.push('/login');
              } else {
                this.$message.error(res.data.info || "注册失败");
              }
            })
            .catch(err => {
              this.closeLoading();
              console.error("注册失败:", err);
              this.$message.error("注册失败");
            });
        }
      });
    },
    loginAfterRegist() {
      this.$axios.post("/api/login", {
        account: this.form.account,
        password: this.form.password,
        type: this.registType
      })
      .then(res => {
        if (res.data.code === 200) {
          // 存储 _id 到 sessionStorage
          sessionStorage.setItem('_id', res.data._id);
          this.$router.push("/");
        } else {
          this.$message.error(res.data.info || "自动登录失败，请手动登录");
          this.$router.push("/login");
        }
      })
      .catch(err => {
        console.error("自动登录失败:", err);
        this.$message.error("自动登录失败，请手动登录");
        this.$router.push("/login");
      });
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
    }
  }
};
</script>

<style scoped>
#regist {
  min-height: 100vh;
  background: linear-gradient(135deg, #2c3e50, #34495e);
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

.regist-container {
  width: 100%;
  max-width: 600px;
  background: white;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  opacity: 0;
  transform: translateY(20px);
  transition: all 0.5s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.regist-container.fade-in {
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

.regist-form {
  width: 100%;
  max-width: 450px;
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  align-items: center; /* 保持居中 */
}

.el-form-item {
  width: 100%;
  display: flex;
  justify-content: center; /* 使表单项居中 */
}

.input-field {
  width: 300px; /* 保持固定宽度 */
  height: 45px;
  margin-bottom: 20px;
  transition: all 0.3s ease;
}

.input-field /deep/ .el-input__inner,
.input-field /deep/ .el-select .el-input__inner,
.input-field /deep/ .el-date-editor.el-input__inner {
  height: 45px;
  line-height: 45px;
  padding: 0 15px 0 40px; /* 原为 0 15px，调整左侧padding留出图标空间 */
  text-align: left; /* 确保文字从左侧开始，但因padding会看起来靠右一点 */
}

.input-field:hover {
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.form-section {
  width: 100%;
  max-width: 450px;
}

.radio-group {
  width: 100%;
  max-width: 450px;
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}

.radio-btn {
  color: #666;
  transition: all 0.3s ease;
}

.radio-btn:hover {
  color: #409EFF;
  transform: scale(1.05);
}

.btn-group {
  width: 100%;
  max-width: 450px;
  display: flex;
  flex-direction: column;
  gap: 15px;
  align-items: center;
}

.action-btn {
  width: 100%;
  height: 50px;
  font-size: 16px;
  font-weight: 500;
  border-radius: 25px;
  transition: all 0.3s ease;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.regist-btn {
  background: linear-gradient(90deg, #409EFF, #66b1ff);
  border: none;
  color: white;
}

.regist-btn:hover {
  background: linear-gradient(90deg, #66b1ff, #409EFF);
  box-shadow: 0 5px 15px rgba(64, 158, 255, 0.4);
  transform: translateY(-2px);
}

.back-buttons {
  width: 100%;
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.back-btn {
  width: 48%;
  height: 40px;
  font-size: 14px;
  background: #ffffff;
  color: #409EFF;
  border: 1px solid #409EFF;
  border-radius: 20px;
  transition: all 0.3s ease;
}

.back-btn:hover {
  background: #e6f7ff;
  box-shadow: 0 5px 15px rgba(64, 158, 255, 0.2);
  transform: translateY(-2px);
}

@media (max-width: 768px) {
  .regist-container {
    padding: 20px;
    max-width: 90%;
  }

  h1 {
    font-size: 24px;
  }

  .radio-group {
    flex-direction: column;
    gap: 10px;
  }

  .input-field {
    width: 100%;
  }

  .back-buttons {
    flex-direction: column;
    gap: 10px;
  }

  .back-btn {
    width: 100%;
  }
}
</style>
