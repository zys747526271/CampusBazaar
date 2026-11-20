<template>
  <div id="personal">
    <!-- 顶部固定菜单栏 -->
    <nav-bar
          :active-route.sync="activeRoute"
          :is-logged-in.sync="isLoggedIn"
          :username.sync="username"
          :show-search-bar="false"
          @open-loading="openLoading"
          @close-loading="closeLoading"
        />

    <!-- 用户信息内容区域 -->
    <div class="main-content">
      <div class="personal-section">
        <h2>用户信息</h2>
        <el-card shadow="hover" class="personal-card">
          <div class="action-buttons">
            <el-button v-if="!isEditing" type="primary" @click="startEditing">修改信息</el-button>
            <template v-if="isEditing">
              <el-button type="success" @click="saveChanges">确认修改</el-button>
              <el-button type="warning" @click="cancelEditing">退出修改</el-button>
            </template>
          </div>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="用户名">
              <el-input v-if="isEditing" v-model="editPerson.name" placeholder="请输入用户名" class="input-field"></el-input>
              <span v-else>{{ person.name || '未设置' }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="账号">
              <el-input v-if="isEditing" v-model="editPerson.account" disabled class="input-field"></el-input>
              <span v-else>{{ person.account }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="账户余额">
              <el-input v-if="isEditing" v-model="editPerson.balance" disabled class="input-field"></el-input>
              <span v-else>{{ person.balance || 0 }} 元</span>
            </el-descriptions-item>
            <el-descriptions-item label="VIP">
              <el-input v-if="isEditing" v-model="editPerson.vip" disabled class="input-field"></el-input>
              <el-tag v-else size="small" :type="person.vip === '暂无VIP' ? 'info' : 'success'">{{ person.vip }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="出生年月">
              <el-input v-if="isEditing" v-model="editPerson.age" disabled class="input-field"></el-input>
              <span v-else>{{ person.age ? `${new Date().getFullYear() - person.age}年` : '未设置' }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="身份证号">
              <el-input v-if="isEditing" v-model="editPerson.idCard" disabled class="input-field"></el-input>
              <span v-else>
                {{ showFullIdCard ? person.idCard : maskIdCard(person.idCard) }}
                <el-button v-if="person.idCard" type="text" @click="toggleIdCard">{{ showFullIdCard ? '隐藏' : '显示' }}</el-button>
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="性别">
              <el-select v-if="isEditing" v-model="editPerson.gender" placeholder="请选择性别" class="input-field">
                <el-option label="男" value="男"></el-option>
                <el-option label="女" value="女"></el-option>
                <el-option label="其他" value="其他"></el-option>
              </el-select>
              <span v-else>{{ person.gender || '未设置' }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="最近登录">
              <el-input v-if="isEditing" v-model="editPerson.loginTime" disabled class="input-field"></el-input>
              <span v-else>{{ person.loginTime || '未知' }}</span>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 收货地址单独区域 -->
        <el-card shadow="hover" class="address-card" style="margin-top: 20px;">
          <h3>收货地址</h3>
          <div v-if="isEditing" class="address-edit">
            <div v-for="(addr, index) in editPerson.address" :key="index" class="address-item">
              <el-select v-model="addr.province" placeholder="请选择省份" @change="handleProvinceChange(index)" class="address-select">
                <el-option v-for="province in provinces" :key="province" :label="province" :value="province"></el-option>
              </el-select>
              <el-select v-model="addr.town" placeholder="请选择城市" @change="handleCityChange(index)" class="address-select">
                <el-option v-for="city in cities[index]" :key="city" :label="city" :value="city"></el-option>
              </el-select>
              <el-select v-model="addr.county" placeholder="请选择区县" class="address-select">
                <el-option v-for="area in areas[index]" :key="area" :label="area" :value="area"></el-option>
              </el-select>
              <el-input v-model="addr.detail" placeholder="请输入详细地址" class="address-detail"></el-input>
              <el-button type="danger" @click="removeAddress(index)">删除</el-button>
            </div>
            <el-button type="info" @click="addAddress">添加地址</el-button>
          </div>
          <el-table v-else :data="person.address" style="width: 100%;" max-height="300">
            <el-table-column prop="province" label="省份" width="150"></el-table-column>
            <el-table-column prop="town" label="城市" width="150"></el-table-column>
            <el-table-column prop="county" label="区县" width="150"></el-table-column>
            <el-table-column prop="detail" label="详细地址"></el-table-column>
          </el-table>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script>
import SearchBar from './SearchBar.vue';
import addressData from '@/assets/ChinaCitys.json';
import NavBar from './NavBar.vue';

export default {
  components: {
    NavBar
  },
  created() {
    this.getPersonal();
    this.checkLoginStatus();
    this.loadAddressData();
  },
  data() {
    return {
      loading: null,
      person: {},
      editPerson: {},
      isEditing: false,
      activeRoute: this.$route.path,
      isLoggedIn: false,
      username: '',
      showFullIdCard: false,
      addressData: [],
      provinces: [],
      cities: [],
      areas: []
    };
  },
  watch: {
    '$route'(to) {
      this.activeRoute = to.path;
      this.checkLoginStatus();
    }
  },
  methods: {
    openLoading(text = "数据加载...") {
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
    getPersonal() {
      this.openLoading();
      this.$axios.get("/api/self")
        .then(res => {
          this.closeLoading();
          if (res.data.code === 200) {
            this.person = res.data.data || {};
            this.editPerson = JSON.parse(JSON.stringify(this.person));
            console.log("用户信息:", this.person);
            this.updateAddressOptions();
          } else {
            this.$message.error(res.data.info || "加载用户信息失败");
          }
        })
        .catch(err => {
          this.closeLoading();
          console.error("加载用户信息失败:", err);
          this.$message.error("加载用户信息失败");
        });
    },
    startEditing() {
      this.isEditing = true;
    },
    cancelEditing() {
      this.isEditing = false;
      this.editPerson = JSON.parse(JSON.stringify(this.person));
      this.updateAddressOptions();
    },
    saveChanges() {
      this.openLoading("保存中...");
      this.$axios.post("/api/update/self", {
        name: this.editPerson.name,
        gender: this.editPerson.gender,
        address: JSON.stringify(this.editPerson.address)
      })
        .then(res => {
          this.closeLoading();
          if (res.data.code === 200) {
            this.$message.success("信息修改成功");
            this.isEditing = false;
            this.person = JSON.parse(JSON.stringify(this.editPerson));
            this.checkLoginStatus(); // 刷新顶部用户名
            this.getPersonal(); // 刷新用户信息
          } else {
            this.$message.error(res.data.info || "修改失败");
          }
        })
        .catch(err => {
          this.closeLoading();
          console.error("修改用户信息失败:", err);
          this.$message.error("修改失败");
        });
    },
    addAddress() {
      this.editPerson.address.push({ province: '', town: '', county: '', detail: '' });
      this.cities.push([]);
      this.areas.push([]);
    },
    removeAddress(index) {
      this.editPerson.address.splice(index, 1);
      this.cities.splice(index, 1);
      this.areas.splice(index, 1);
    },
    loadAddressData() {
      this.addressData = addressData;
      this.provinces = addressData.map(item => item.province);
    },
    handleProvinceChange(index) {
      const selectedProvince = this.addressData.find(item => item.province === this.editPerson.address[index].province);
      this.$set(this.cities, index, selectedProvince.citys.map(item => item.city));
      this.editPerson.address[index].town = '';
      this.editPerson.address[index].county = '';
      this.$set(this.areas, index, []);
    },
    handleCityChange(index) {
      const selectedProvince = this.addressData.find(item => item.province === this.editPerson.address[index].province);
      const selectedCity = selectedProvince.citys.find(item => item.city === this.editPerson.address[index].town);
      this.$set(this.areas, index, selectedCity.areas.map(item => item.area));
      this.editPerson.address[index].county = '';
    },
    updateAddressOptions() {
      this.cities = [];
      this.areas = [];
      this.editPerson.address.forEach((addr, index) => {
        const selectedProvince = this.addressData.find(item => item.province === addr.province);
        if (selectedProvince) {
          this.cities.push(selectedProvince.citys.map(item => item.city));
          const selectedCity = selectedProvince.citys.find(item => item.city === addr.town);
          this.areas.push(selectedCity ? selectedCity.areas.map(item => item.area) : []);
        } else {
          this.cities.push([]);
          this.areas.push([]);
        }
      });
    },
    maskIdCard(idCard) {
      if (!idCard) return '未设置';
      return idCard.slice(0, 6) + '********' + idCard.slice(-4);
    },
    toggleIdCard() {
      this.showFullIdCard = !this.showFullIdCard;
    },
    searchGoods(keyword) {
      this.$router.push({
        path: '/search',
        query: { keyword }
      });
    },
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
            console.log("登录用户:", this.username);
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
    logout() {
      this.openLoading("退出中...");
      this.$axios.post("/api/quit", { type: 'user' })
        .then(res => {
          this.closeLoading();
          if (res.data.code === 200) {
            sessionStorage.removeItem('_id');
            this.isLoggedIn = false;
            this.username = '';
            this.$router.push('/login');
            this.$message.success("已退出登录");
          }
        })
        .catch(err => {
          this.closeLoading();
          console.error("退出失败:", err);
          this.$message.error("退出失败");
        });
    },
    handleMenuCommand(command) {
      if (command === 'logout') {
        this.logout();
      } else {
        this.$router.push(command);
      }
    }
  }
};
</script>

<style scoped>
#personal {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 20px;
}

.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: #fff;
  padding: 10px 20px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
  height: 60px;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
}

.top-nav {
  display: flex;
  align-items: center;
  width: 100%;
}

.nav-menu {
  border-bottom: none;
  flex-grow: 1;
}

.user-menu {
  min-width: 100px;
}

.search-bar-wrapper {
  margin-left: 20px;
  width: 300px;
  transition: width 0.3s ease;
}

.desktop-menu {
  display: flex;
}

.mobile-menu {
  display: none;
}

.el-dropdown-link {
  cursor: pointer;
  color: #409EFF;
  font-size: 16px;
  display: flex;
  align-items: center;
}

.el-icon-menu {
  margin-right: 5px;
}

.main-content {
  margin-top: 70px;
  padding: 0 20px;
}

.personal-section {
  max-width: 1200px;
  margin: 0 auto;
}

.personal-section h2 {
  font-size: 20px;
  color: #333;
  margin: 0 0 20px;
}

.personal-card,
.address-card {
  background: #fff;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.05);
}

.action-buttons {
  margin-bottom: 20px;
  text-align: right;
}

.input-field {
  width: 200px;
}

.address-card h3 {
  font-size: 18px;
  color: #333;
  margin: 0 0 15px;
}

.address-edit {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.address-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.address-select {
  width: 150px;
}

.address-detail {
  width: 300px;
}

.el-descriptions :deep(.el-descriptions-item__label) {
  width: 120px;
}

.el-descriptions :deep(.el-descriptions-item__content) {
  width: auto;
}

@media (max-width: 768px) {
  .header {
    height: auto;
    padding: 5px 10px;
  }

  .header-content {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }

  .top-nav {
    width: 100%;
    justify-content: space-between;
  }

  .desktop-menu {
    display: none;
  }

  .mobile-menu {
    display: block;
  }

  .search-bar-wrapper {
    margin-left: 10px;
    width: 200px;
  }

  .main-content {
    margin-top: 70px;
  }

  .personal-card,
  .address-card {
    padding: 10px;
  }

  .el-descriptions {
    display: block;
  }

  .el-descriptions :deep(.el-descriptions-item) {
    display: block;
    margin-bottom: 10px;
  }

  .el-descriptions :deep(.el-descriptions-item__label) {
    width: 100%;
    display: block;
  }

  .el-descriptions :deep(.el-descriptions-item__content) {
    width: 100%;
    display: block;
  }

  .input-field,
  .address-select,
  .address-detail {
    width: 100%;
    margin-right: 0;
    margin-bottom: 10px;
  }

  .address-item {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 480px) {
  .search-bar-wrapper {
    width: 150px;
  }
}
</style>
