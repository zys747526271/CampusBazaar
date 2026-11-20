<template>
  <div id="court">
    <nav-bar
      :active-route.sync="activeRoute"
      :is-logged-in.sync="isLoggedIn"
      :username.sync="username"
      :show-search-bar="true"
      @open-loading="openLoading"
      @close-loading="closeLoading"
    />

    <div class="main-content">
      <div class="court-section">
        <h2>我的购物车</h2>
        <div class="goods-list">
          <el-card v-for="(good, index) in goods" :key="index" shadow="hover" class="goods-card">
            <img :src="good.image | imageFliter" :alt="good.name" class="goods-image" />
            <div class="goods-info">
              <p class="name">{{ good.name }}</p>
              <p class="price">原价: <del>{{ good.originPrice }}</del> 现价: ¥{{ good.sellPrice }}</p>
              <el-input-number v-model="good.quantity" :min="1" :max="good.contains" size="mini" @change="updateQuantity(good)" style="width: 100px; margin-top: 10px;"></el-input-number>
              <el-button type="danger" size="mini" @click="removeCourt(good)" style="float: right; margin-top: 10px;">移除</el-button>
            </div>
          </el-card>
          <el-empty v-if="goods.length === 0" description="购物车为空"></el-empty>
        </div>
        <div class="summary" v-if="goods.length > 0">
          <span>总价: ¥{{ totalPrice }}</span>
          <el-button type="primary" @click="buy">提交订单</el-button>
        </div>
      </div>
    </div>

    <el-dialog title="选择收货地址" :visible.sync="dialogFormVisible" width="50%">
      <el-table :data="address" style="width: 100%;" max-height="300" @row-click="selectAddress" highlight-current-row>
        <el-table-column prop="province" label="省份" width="100"></el-table-column>
        <el-table-column prop="town" label="城市" width="100"></el-table-column>
        <el-table-column prop="county" label="区县" width="100"></el-table-column>
        <el-table-column prop="detail" label="详细地址"></el-table-column>
      </el-table>
      <el-button type="info" @click="showAddAddress = !showAddAddress" style="margin-top: 10px;">{{ showAddAddress ? '取消添加' : '添加新地址' }}</el-button>
      <el-form v-if="showAddAddress" :model="addressFrom" class="address-form">
        <el-form-item label="省/市/区" :label-width="formLabelWidth">
          <el-select v-model="addressFrom.province" placeholder="请选择省份" @change="handleProvinceChange" class="address-select">
            <el-option v-for="province in provinces" :key="province" :label="province" :value="province"></el-option>
          </el-select>
          <el-select v-model="addressFrom.town" placeholder="请选择城市" @change="handleCityChange" class="address-select">
            <el-option v-for="city in citys" :key="city" :label="city" :value="city"></el-option>
          </el-select>
          <el-select v-model="addressFrom.county" placeholder="请选择区县" class="address-select">
            <el-option v-for="area in areas" :key="area" :label="area" :value="area"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="详细地址" :label-width="formLabelWidth">
          <el-input v-model="addressFrom.detail" placeholder="请输入详细地址"></el-input>
        </el-form-item>
        <el-button type="primary" @click="addAddress">添加地址</el-button>
      </el-form>
      <div slot="footer" class="dialog-footer">
        <el-button @click="dialogFormVisible = false">取消</el-button>
        <el-button type="primary" @click="realBuy" :disabled="sendAddress === null">确定</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import addressData from '@/assets/ChinaCitys.json';
import NavBar from './NavBar.vue';

export default {
  components: {
    NavBar
  },
  created() {
    this.initGoodsList();
    this.loadAddressData();
    this.checkLoginStatus();
  },
  data() {
    return {
      loading: null,
      goods: [], // 购物车商品列表
      address: [], // 地址列表
      dialogFormVisible: false,
      showAddAddress: false,
      addressFrom: {
        province: '',
        town: '',
        county: '',
        detail: ''
      },
      sendAddress: null,
      formLabelWidth: '120px',
      addressData: [],
      provinces: [],
      citys: [],
      areas: [],
      activeRoute: this.$route.path,
      isLoggedIn: false,
      username: ''
    };
  },
  computed: {
    // 计算购物车总价
    totalPrice() {
      return this.goods.reduce((sum, good) => sum + parseFloat(good.sellPrice) * (good.quantity || 1), 0).toFixed(2);
    }
  },
  watch: {
    '$route'(to) {
      this.activeRoute = to.path;
      this.checkLoginStatus();
    }
  },
  methods: {
    // 显示加载提示
    openLoading(text = "数据加载...") {
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
    // 初始化购物车商品列表
    initGoodsList() {
      this.openLoading();
      this.$axios.get("/api/self/court")
        .then(res => {
          this.closeLoading();
          if (res.data.code === 200) {
            this.goods = res.data.data.data || [];
          } else {
            this.$message.error(res.data.info || "加载购物车失败");
          }
        })
        .catch(err => {
          this.closeLoading();
          console.error("加载购物车失败:", err);
          this.$message.error("加载购物车失败，请检查网络");
        });
    },
    // 加载地址数据
    loadAddressData() {
      this.addressData = addressData;
      this.provinces = addressData.map(item => item.province);
    },
    // 处理省份选择变化
    handleProvinceChange(province) {
      const selectedProvince = this.addressData.find(item => item.province === province);
      this.citys = selectedProvince.citys.map(item => item.city);
      this.addressFrom.town = '';
      this.addressFrom.county = '';
      this.areas = [];
    },
    // 处理城市选择变化
    handleCityChange(city) {
      const selectedProvince = this.addressData.find(item => item.province === this.addressFrom.province);
      const selectedCity = selectedProvince.citys.find(item => item.city === city);
      this.areas = selectedCity.areas.map(item => item.area);
      this.addressFrom.county = '';
    },
    // 添加新地址
    addAddress() {
      if (!this.addressFrom.province || !this.addressFrom.town || !this.addressFrom.county || !this.addressFrom.detail) {
        this.$message.warning("请将地址信息补充完整");
        return;
      }
      this.openLoading("地址添加中...");
      this.$axios.post("/api/self/address/add", this.addressFrom)
        .then(res => {
          this.closeLoading();
          if (res.data.code === 200) {
            this.$message.success("地址添加成功");
            this.address.unshift({ ...this.addressFrom });
            this.addressFrom = { province: '', town: '', county: '', detail: '' };
            this.citys = [];
            this.areas = [];
          } else {
            this.$message.error(res.data.info || "添加失败");
          }
        })
        .catch(err => {
          this.closeLoading();
          console.error("添加地址失败:", err);
          this.$message.error("添加失败");
        });
    },
    // 从购物车移除商品
    removeCourt(good) {
      this.openLoading("移除中...");
      this.$axios.post("/api/remove/goods/from/court", { goodsId: good._id })
        .then(res => {
          this.closeLoading();
          if (res.data.code === 200) {
            this.$message.success("已移除购物车");
            this.goods.splice(this.goods.findIndex(g => g._id === good._id), 1);
          } else {
            this.$message.error(res.data.info || "移除失败");
          }
        })
        .catch(err => {
          this.closeLoading();
          console.error("移除失败:", err);
          this.$message.error("移除失败");
        });
    },
    // 更新商品数量
    updateQuantity(good) {
      this.openLoading("更新数量...");
      this.$axios.post("/api/update/court", {
        goodsId: good._id,
        quantity: good.quantity
      })
        .then(res => {
          this.closeLoading();
          if (res.data.code === 200) {
            this.$message.success("数量更新成功");
          } else {
            this.$message.error(res.data.info || "更新数量失败");
            good.quantity = res.data.oldQuantity || 1;
          }
        })
        .catch(err => {
          this.closeLoading();
          console.error("更新数量失败:", err);
          this.$message.error("更新数量失败");
          good.quantity = good.quantity || 1;
        });
    },
    // 提交订单
    buy() {
      if (this.goods.length === 0) {
        this.$message.warning("购物车为空");
        return;
      }
      this.openLoading("加载地址...");
      this.$axios.get("/api/self/address")
        .then(res => {
          this.closeLoading();
          if (res.data.code === 200) {
            this.address = res.data.data.address || [];
            this.dialogFormVisible = true;
            this.sendAddress = null;
          } else {
            this.$message.error(res.data.info || "加载地址失败");
          }
        })
        .catch(err => {
          this.closeLoading();
          console.error("加载地址失败:", err);
          this.$message.error("加载地址失败");
        });
    },
    // 选择地址
    selectAddress(row) {
      this.sendAddress = this.address.indexOf(row);
    },
    // 确认购买
    realBuy() {
      if (this.sendAddress === null) {
        this.$message.warning("请选择收货地址");
        return;
      }
      this.dialogFormVisible = false;
      this.openLoading("订单提交中...");
      const goodsList = this.goods.map(good => ({
        id: good._id,
        number: good.quantity || 1
      }));
      const payValue = this.totalPrice;
      const selectedAddress = this.address[this.sendAddress];
      const address = `${selectedAddress.province}${selectedAddress.town}${selectedAddress.county}${selectedAddress.detail}`;
      const payload = {
        payValue: payValue,
        goodsList: JSON.stringify(goodsList),
        cutoffValue: payValue,
        address: address
      };
      this.$axios.post("/api/buy/goods", payload, {
        headers: { 'Content-Type': 'application/json' }
      })
        .then(res => {
          this.closeLoading();
          if (res.data.code === 200) {
            this.$message.success("购买成功！");
            this.goods = [];
            this.checkLoginStatus();
          } else {
            this.$message.error(res.data.info || "提交订单失败");
          }
        })
        .catch(err => {
          this.closeLoading();
          console.error("提交订单失败:", err);
          this.$message.error("提交订单失败");
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
#court {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 20px;
}

.main-content {
  margin-top: 70px;
  padding: 0 20px;
}

.court-section {
  max-width: 1200px;
  margin: 0 auto;
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.05);
}

.court-section h2 {
  font-size: 20px;
  color: #333;
  margin: 0 0 20px;
}

.goods-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.goods-card {
  padding: 10px;
  text-align: center;
  transition: all 0.3s ease;
}

.goods-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 15px rgba(0,0,0,0.1);
}

.goods-image {
  width: 100%;
  height: 150px;
  object-fit: contain;
  border-radius: 4px;
}

.goods-info {
  padding: 15px;
}

.goods-info .name {
  font-size: 16px;
  color: #333;
  margin: 5px 0;
  font-weight: bold;
}

.goods-info .price {
  font-size: 14px;
  color: #666;
  margin: 5px 0;
}

.summary {
  text-align: right;
}

.summary span {
  font-size: 18px;
  color: #ff4444;
  margin-right: 20px;
}

.address-form {
  margin-top: 20px;
}

.address-select {
  width: 150px;
  margin-right: 10px;
}

.dialog-footer {
  text-align: right;
}

.el-table .current-row {
  background-color: #e6f7ff !important;
}

@media (max-width: 768px) {
  .main-content {
    margin-top: 70px;
  }

  .court-section {
    padding: 15px;
  }

  .goods-list {
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  }

  .goods-image {
    height: 120px;
  }

  .address-select {
    width: 100%;
    margin-right: 0;
    margin-bottom: 10px;
  }
}
</style>
