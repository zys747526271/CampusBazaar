<template>
  <el-tabs
    @tab-click="tagClick"
    :tab-position="'left'"
    class="custom-tabs"
    v-model="activeTag"
  >
    <el-tab-pane
      v-for="(tag, index) of tags"
      :name="tag._id"
      :key="index"
      :label="tag.name"
    ></el-tab-pane>
  </el-tabs>
</template>

<script>
export default {
  name: 'Sidebar',
  props: {
    tags: {
      type: Array,
      required: true
    }
  },
  data() {
    return {
      activeTag: null
    };
  },
  watch: {
    tags(newTags) {
      if (newTags.length > 0 && !this.activeTag) {
        this.activeTag = newTags[0]._id;
        this.tagClick({ $options: { propsData: { name: newTags[0]._id } } });
      }
    }
  },
  methods: {
    tagClick(tag) {
      this.activeTag = tag.$options.propsData.name;
      this.$emit('tag-click', tag);
    }
  }
};
</script>

<style scoped>
.custom-tabs {
  width: 200px;
}

.el-tabs__nav {
  position: fixed;
  left: 20px;
  top: 100px;
  background: white;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  max-height: calc(100vh - 120px);
  overflow-y: auto;
}

.el-tabs__nav .el-tabs__item {
  padding: 10px 20px;
  transition: all 0.3s ease;
  border-radius: 4px;
  margin: 5px 0;
  background: #fff;
  color: #606266;
}

.el-tabs__nav .el-tabs__item:hover {
  background: linear-gradient(90deg, #f0f2f5, #e6e9f0);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  color: #409EFF;
  transform: translateX(5px);
}

.el-tabs__nav .el-tabs__item.is-active {
  background: #409EFF;
  color: white;
  box-shadow: 0 4px 12px rgba(64,158,255,0.3);
}

.el-tabs__nav .el-tabs__item.is-active:hover {
  background: #66b1ff;
}

@media (max-width: 768px) {
  .el-tabs__nav {
    left: 10px;
    padding: 10px;
  }
}
</style>
