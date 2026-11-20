<template>
  <div id="goods-manage">
    <h2>商品管理</h2>
    <div class="filter-bar">
      <el-select v-model="statusFilter" placeholder="筛选状态" @change="fetchGoods(1)">
        <el-option label="全部商品" value="all"></el-option>
        <el-option label="上架商品" value="active"></el-option>
        <el-option label="下架商品" value="inactive"></el-option>
      </el-select>
    </div>
    <el-table :data="tableData" style="width: 100%">
      <el-table-column label="商品 ID" prop="_id" width="100"></el-table-column>
      <el-table-column label="商品名称" prop="name" width="150"></el-table-column>
      <el-table-column label="描述" prop="intro" width="200"></el-table-column>
      <el-table-column label="库存" prop="contains" width="100"></el-table-column>
      <el-table-column label="售价" prop="sellPrice" width="100"></el-table-column>
      <el-table-column label="状态" prop="is_active" width="100" :formatter="row => row.is_active ? '上架' : '下架'"></el-table-column>
      <el-table-column label="操作" width="200">
        <template slot-scope="scope">
          <el-button type="danger" size="mini" @click="toggleActive(scope.row)" v-if="scope.row.is_active">下架</el-button>
          <el-button type="success" size="mini" @click="toggleActive(scope.row)" v-else>上架</el-button>
          <el-button type="primary" size="mini" @click="restock(scope.row)">补货</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      layout="prev, pager, next"
      @current-change="fetchGoods"
      :page-size="pageSize"
      :total="total"
    />
    <div class="add-goods">
      <h3>添加商品</h3>
      <el-form :model="form" ref="form" label-width="80px">
        <el-form-item label="商品名称">
          <el-input v-model="form.name"></el-input>
        </el-form-item>
        <el-form-item label="商品图片">
          <el-upload
            :auto-upload="false"
            list-type="picture-card"
            :on-change="handleFileChange"
            :on-remove="handleRemove"
            :file-list="fileList"
            multiple
          >
            <i class="el-icon-plus"></i>
          </el-upload>
        </el-form-item>
        <el-form-item label="原价">
          <el-input v-model.number="form.originPrice" type="number"></el-input>
        </el-form-item>
        <el-form-item label="售价">
          <el-input v-model.number="form.sellPrice" type="number"></el-input>
        </el-form-item>
        <el-form-item label="库存" :rules="[{ required: true, message: '库存不能为空' }, { type: 'number', message: '库存必须为数字值' }]">
          <el-input v-model.number="form.contains" type="number"></el-input>
        </el-form-item>
        <el-form-item label="商品标签">
          <el-select v-model="form.goodsType" placeholder="请选择商品标签">
            <el-option v-for="tag in tags" :key="tag._id" :label="tag.name" :value="tag._id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="生产地址">
          <el-select v-model="form.createAddress" placeholder="请选择生产地址">
            <el-option v-for="address in addresses" :key="address._id" :label="address.province + address.town + address.county + address.detail" :value="address._id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="发货地址">
          <el-select v-model="form.sendAddress" placeholder="请选择发货地址">
            <el-option v-for="address in addresses" :key="address._id" :label="address.province + address.town + address.county + address.detail" :value="address._id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="商品简介">
          <el-input type="textarea" v-model="form.intro"></el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="addGoods">立即创建</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script>
export default {
  name: 'GoodsManage',
  data() {
    return {
      loading: null,
      statusFilter: 'all',
      tableData: [],
      pageSize: 15,
      total: 0,
      tags: [],
      addresses: [],
      fileList: [],
      form: {
        name: '',
        intro: '',
        originPrice: null,
        sellPrice: null,
        contains: null,
        goodsType: null,
        createAddress: null,
        sendAddress: null
      }
    };
  },
  created() {
    this.checkAdmin();
    this.fetchTags();
    this.fetchAddresses();
    this.fetchTotal();
    this.fetchGoods(1);
  },
  methods: {
    openLoading(text = "加载...") {
      this.loading = this.$loading({
        lock: true,
        text: text,
        spinner: 'el-icon-loading',
        background: 'rgba(0, 0, 0, 0.7)'
      });
    },
    closeLoading() {
      if (this.loading) this.loading.close();
    },
    checkAdmin() {
      this.openLoading("权限检查中...");
      this.$axios.post("/api/islogin")
        .then(res => {
          this.closeLoading();
          if (res.data.code !== 200 || res.data.data.type !== 'admin') {
            this.$message.error('仅管理员可访问');
            this.$router.push('/center');
          }
        })
        .catch(err => {
          this.closeLoading();
          console.error("权限检查失败:", err);
          this.$message.error('请先登录');
          this.$router.push('/login');
        });
    },
    fetchTags() {
      this.$axios.get("/api/goods/type")
        .then(res => {
          if (res.data.code === 200) this.tags = res.data.data.data;
        })
        .catch(err => console.error("获取标签失败:", err));
    },
    fetchAddresses() {
      this.$axios.get("/api/address")
        .then(res => {
          if (res.data.code === 200) this.addresses = res.data.data.data;
        })
        .catch(err => console.error("获取地址失败:", err));
    },
    fetchTotal() {
      this.$axios.get("/api/admin/goods/count")
        .then(res => {
          if (res.data.code === 200) this.total = res.data.data.nums;
        })
        .catch(err => console.error("获取总数失败:", err));
    },
    fetchGoods(page) {
      this.openLoading("加载商品...");
      this.$axios.post("/api/admin/goods", {
        start: (page - 1) * this.pageSize,
        nums: this.pageSize,
        status: this.statusFilter
      })
        .then(res => {
          this.closeLoading();
          console.log("Admin goods response:", res.data);
          if (res.data.code === 200) this.tableData = res.data.data;
        })
        .catch(err => {
          this.closeLoading();
          console.error("加载商品失败:", err);
        });
    },
    toggleActive(row) {
      const action = row.is_active ? '下架' : '上架';
      this.$confirm(`此操作将${action}该商品, 是否继续?`, '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
        .then(() => {
          this.openLoading(`${action}中...`);
          this.$axios.delete("/api/admin/goods/toggle", { data: { id: row._id } })
            .then(res => {
              this.closeLoading();
              if (res.data.code === 200) {
                this.$message.success(`${action}成功!`);
                row.is_active = !row.is_active;
              } else {
                this.$message.error(res.data.message || `${action}失败!`);
              }
            })
            .catch(err => {
              this.closeLoading();
              console.error(`${action}失败:`, err);
              this.$message.error(`${action}失败!`);
            });
        })
        .catch(() => this.$message.info(`已取消${action}`));
    },
    restock(row) {
      this.$prompt('请输入补货数量', '补货', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputPattern: /^[0-9]+$/,
        inputErrorMessage: '请输入正整数'
      }).then(({ value }) => {
        this.openLoading("补货中...");
        this.$axios.post("/api/admin/goods/restock", { id: row._id, quantity: value })
          .then(res => {
            this.closeLoading();
            if (res.data.code === 200) {
              this.$message.success(`补货成功，新库存: ${res.data.new_contains}`);
              row.contains = res.data.new_contains;
            } else {
              this.$message.error(res.data.message || '补货失败!');
            }
          })
          .catch(err => {
            this.closeLoading();
            console.error("补货失败:", err);
            this.$message.error('补货失败!');
          });
      }).catch(() => this.$message.info('已取消补货'));
    },
    handleFileChange(file, fileList) {
      this.fileList = fileList.map(f => ({ name: f.name, raw: f.raw }));
    },
    handleRemove(file, fileList) {
      this.fileList = fileList.map(f => ({ name: f.name, raw: f.raw }));
    },
    addGoods() {
      this.$refs.form.validate(valid => {
        if (!valid) return;
        const formData = new FormData();
        for (const key in this.form) {
          formData.append(key, this.form[key] || '');
        }
        this.fileList.forEach(file => formData.append("images", file.raw));
        this.openLoading("商品添加中...");
        this.$axios.post("/api/admin/goods/add", formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
          .then(res => {
            this.closeLoading();
            if (res.data.code === 200) {
              this.$message.success("商品添加成功");
              this.form = { name: '', intro: '', originPrice: null, sellPrice: null, contains: null, goodsType: null, createAddress: null, sendAddress: null };
              this.fileList = [];
              this.fetchGoods(1);
            } else {
              this.$message.error(res.data.info || "添加失败");
            }
          })
          .catch(err => {
            this.closeLoading();
            console.error("添加失败:", err);
            this.$message.error("添加失败");
          });
      });
    }
  }
};
</script>

<style scoped>
#goods-manage {
  padding: 20px;
  background: #f5f7fa;
}

h2 {
  margin-bottom: 20px;
}

.filter-bar {
  margin-bottom: 20px;
}

.add-goods {
  margin-top: 20px;
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.el-table {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.el-pagination {
  margin-top: 20px;
}
</style>
