import { createRouter, createWebHistory } from 'vue-router'

const routes = [
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
    path: '/funds/:code',
    name: 'FundDetail',
    component: () => import('../views/FundDetail.vue')
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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
