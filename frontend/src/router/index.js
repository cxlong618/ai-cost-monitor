import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'dashboard', component: () => import('../views/Dashboard.vue') },
  { path: '/accounts', name: 'accounts', component: () => import('../views/Accounts.vue') },
  { path: '/calculator', name: 'calculator', component: () => import('../views/Calculator.vue') },
]

export default createRouter({ history: createWebHistory(), routes })
