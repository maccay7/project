import { createRouter, createWebHistory } from 'vue-router'
import Login from '../pages/Login.vue'
import Dashboard from '../pages/Dashboard.vue'
import Instruments from '../pages/Instruments.vue'
import Upload from '../pages/Upload.vue'
import Reports from '../pages/Reports.vue'

const routes = [
  { path: '/', component: Login },
  { path: '/dashboard', component: Dashboard },
  { path: '/instruments', component: Instruments },
  { path: '/upload', component: Upload },
  { path: '/reports', component: Reports }
]

export default createRouter({
  history: createWebHistory(),
  routes
})