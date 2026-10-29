import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/Login.vue') },
  { path: '/', name: 'dashboard', component: () => import('../views/Dashboard.vue') },
  { path: '/accounts', name: 'accounts', component: () => import('../views/Accounts.vue') },
  { path: '/alerts', name: 'alerts', component: () => import('../views/Alerts.vue') },
  { path: '/calculator', name: 'calculator', component: () => import('../views/Calculator.vue') },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const token = localStorage.getItem('acm_token')
  if (to.name !== 'login' && !token) return { name: 'login' }
})

export default router
