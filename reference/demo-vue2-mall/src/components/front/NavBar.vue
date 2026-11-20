<template>
  <div class="header">
    <div class="header-content">
      <div class="top-nav">
        <!-- 桌面端导航 -->
        <el-menu mode="horizontal" :default-active="activeRoute" class="nav-menu desktop-menu">
          <el-menu-item index="/" @click="$router.push('/')">商城中心</el-menu-item>
          <el-menu-item index="/vip" @click="$router.push('/vip')">VIP</el-menu-item>
          <el-menu-item index="/court" @click="$router.push('/court')">购物车</el-menu-item>
          <el-menu-item index="/receipt" @click="$router.push('/receipt')">订单</el-menu-item>
          <el-menu-item index="/balance" @click="$router.push('/balance')">余额</el-menu-item>
          <el-menu-item index="/personal" @click="$router.push('/personal')">我的信息</el-menu-item>
          <template v-if="!isLoggedIn">
            <el-menu-item index="/login" @click="$router.push('/login')">登录</el-menu-item>
            <el-menu-item index="/regist" @click="$router.push('/regist')">注册</el-menu-item>
          </template>
          <el-submenu v-else index="user" class="user-menu">
            <template slot="title">{{ username }}</template>
            <el-menu-item @click="logout">退出登录</el-menu-item>
          </el-submenu>
        </el-menu>
        <!-- 移动端折叠菜单 -->
        <el-dropdown class="mobile-menu" trigger="click" @command="handleMenuCommand">
          <span class="el-dropdown-link">
            <i class="el-icon-menu"></i> 菜单
          </span>
          <el-dropdown-menu slot="dropdown">
            <el-dropdown-item command="/">商城中心</el-dropdown-item>
            <el-dropdown-item command="/vip">VIP</el-dropdown-item>
            <el-dropdown-item command="/court">购物车</el-dropdown-item>
            <el-dropdown-item command="/receipt">订单</el-dropdown-item>
            <el-dropdown-item command="/balance">余额</el-dropdown-item>
            <el-dropdown-item command="/personal">我的信息</el-dropdown-item>
            <el-dropdown-item v-if="!isLoggedIn" command="/login">登录</el-dropdown-item>
            <el-dropdown-item v-if="!isLoggedIn" command="/regist">注册</el-dropdown-item>
            <el-dropdown-item v-if="isLoggedIn" command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </el-dropdown>
        <!-- 搜索栏插槽 -->
        <div class="search-bar-wrapper" v-if="showSearchBar">
          <search-bar @search="handleSearch"></search-bar>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import SearchBar from './SearchBar.vue'; // 引入搜索栏组件

export default {
  name: 'NavBar',
  components: {
    SearchBar
  },
  props: {
    activeRoute: {
      type: String,
      default: '/'
    },
    isLoggedIn: {
      type: Boolean,
      default: false
    },
    username: {
      type: String,
      default: ''
    },
    showSearchBar: {
      type: Boolean,
      default: true
    }
  },
  watch: {
    '$route'(to) {
      this.$emit('update:activeRoute', to.path);
    }
  },
  methods: {
    logout() {
      this.openLoading("退出中...");
      this.$axios.post("/api/quit", { type: 'user' })
        .then(res => {
          this.closeLoading();
          if (res.data.code === 200) {
            sessionStorage.removeItem('_id');
            this.$emit('update:isLoggedIn', false);
            this.$emit('update:username', '');
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
    },
    handleSearch(keyword) {
      // 处理搜索逻辑
      this.$emit('search', keyword);
    },
    openLoading(text = "退出中...") {
      this.$emit('open-loading', text);
    },
    closeLoading() {
      this.$emit('close-loading');
    }
  }
};
</script>

<style scoped>
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
}

@media (max-width: 480px) {
  .search-bar-wrapper {
    width: 150px;
  }
}
</style>
