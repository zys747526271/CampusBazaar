<template>
  <div class="search-bar">
    <el-input
      v-model="keyword"
      placeholder="请输入商品名称"
      @keyup.enter.native="handleSearch"
      class="search-input"
    >
      <el-button slot="append" icon="el-icon-search" @click="handleSearch"></el-button>
    </el-input>
  </div>
</template>

<script>
export default {
  name: 'SearchBar',
  data() {
    return {
      keyword: ''
    };
  },
  methods: {
    handleSearch() {
      if (this.keyword.trim()) {
        this.$emit('search', this.keyword);
        this.keyword = '';
      } else {
        this.$message.warning("请输入搜索内容");
      }
    }
  }
};
</script>

<style scoped>
.search-bar {
  width: 100%;
  max-width: 500px;
  transition: all 0.3s ease;
}

.search-input {
  width: 100%;
}
</style>
