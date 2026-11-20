'use strict'
import Vue from 'vue'
import App from './App'
import router from './router'
import ElementUI from 'element-ui'
import Axios from 'axios'
import './default.css'
import 'element-ui/lib/theme-chalk/index.css'

Vue.config.productionTip = false
Vue.use(ElementUI)

Axios.defaults.baseURL = ""
Vue.prototype.$axios = Axios

Vue.filter('imageFilter', function(image) {
  if (!image) {
    console.warn("Image path is empty or undefined");
    return "https://via.placeholder.com/150"; // 默认图片
  }
  console.log("Original image path:", image);
  var list = image.split("/");
  var filename = list[list.length - 1];
  var filteredUrl = `http://127.0.0.1:5000/static/goods/${filename}`;
  console.log("Filtered image URL:", filteredUrl);
  return filteredUrl;
})

new Vue({
  el: '#app',
  router,
  components: { App },
  template: '<App/>'
})
