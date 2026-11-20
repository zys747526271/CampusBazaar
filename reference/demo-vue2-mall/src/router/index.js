import Vue from 'vue';
import Router from 'vue-router';
import Login from '@/components/Login';
import Regist from '@/components/Regist';
import AdminIndex from '@/components/admin/AdminIndex';
import GoodsManage from '@/components/admin/GoodsManage';
import UserManage from '@/components/admin/UserManage';
import TagManage from '@/components/admin/TagManage';
import VipManage from '@/components/admin/VipManage';
import AddressManage from '@/components/admin/AddressManage';
import MainIndex from '@/components/front/MainIndex';
import Center from '@/components/front/Center';
import Court from '@/components/front/Court';
import Personal from '@/components/front/Personal';
import Balance from '@/components/front/Balance';
import VIP from '@/components/front/VIP';
import Receipt from '@/components/front/Receipt';
import GoodsDetail from '@/components/front/GoodsDetail';
import SearchResult from '@/components/front/SearchResult';
import MoreGoods from '@/components/front/MoreGoods';

Vue.use(Router);

export default new Router({
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: Login
    },
    {
      path: "/regist",
      name: "Regist",
      component: Regist
    },
    {
      path: "/admin/index",
      name: "AdminIndex",
      component: AdminIndex,
      children: [
        { path: 'goods', component: GoodsManage },
        { path: 'user', component: UserManage },
        { path: 'tag', component: TagManage },
        { path: 'address', component: AddressManage },
        { path: 'vip', component: VipManage }
      ]
    },
    {
      path: "/",
      name: "MainIndex",
      component: MainIndex,
      children: [
        {
          path: '', // 默认路由显示新主页
          component: Center
        },
        {
          path: 'center',
          component: Center
        },
        {
          path: 'receipt',
          component: Receipt
        },
        {
          path: 'vip',
          component: VIP
        },
        {
          path: 'goods/:_id', // 修改为动态路由
          name: "GoodsDetail",
          component: GoodsDetail,
          props: true // 启用 props 传递参数
        },
        {
          path: 'court',
          component: Court
        },
        {
          path: 'personal',
          component: Personal
        },
        {
          path: 'balance',
          component: Balance
        },
        {
          path: 'search',
          name: 'SearchResult',
          component: SearchResult
        },
        {
          path: 'more',
          name: 'MoreGoods',
          component: MoreGoods
        }
      ]
    }
  ]
});
