
<template>
  <v-app>
    <router-view />
  </v-app>

<template>
  <div v-if="$route.path !== '/'" class="layout">
    <aside class="sidebar">
      <h2>FinSys</h2>
      <router-link to="/dashboard">Dashboard</router-link>
      <router-link to="/instruments">Instruments</router-link>
      <router-link to="/upload">Upload</router-link>
      <router-link to="/reports">Reports</router-link>
      <button class="logout" @click="$router.push('/')">Logout</button>
    </aside>

    <div class="main">
      <header class="header">Financial Instruments System</header>
      <router-view />
    </div>
  </div>

  <router-view v-else />
</template>