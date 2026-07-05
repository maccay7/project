import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'

// Import jQuery and make it globally available
import jQuery from 'jquery'
if (typeof window !== 'undefined') {
  window.$ = jQuery
  window.jQuery = jQuery
}

createApp(App).use(router).mount('#app')