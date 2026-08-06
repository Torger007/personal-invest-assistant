import { createRouter, createWebHistory } from 'vue-router'
import { authApi } from '../api'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { public: true }
  },
  {
    path: '/',
    name: 'MarketOverview',
    component: () => import('../views/MarketOverview.vue')
  },
  {
    path: '/funds',
    name: 'Funds',
    component: () => import('../views/FundList.vue')
  },
  {
    path: '/funds/:positionId',
    redirect: '/funds'
  },
  {
    path: '/sectors',
    name: 'Sectors',
    component: () => import('../views/SectorAnalysis.vue')
  },
  {
    path: '/advice',
    name: 'Advice',
    component: () => import('../views/AdviceReport.vue')
  },
  {
    path: '/agent',
    name: 'Agent',
    component: () => import('../views/AgentSettings.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async to => {
  if (to.meta.public) return true
  try {
    await authApi.me()
    return true
  } catch {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
})

export default router
