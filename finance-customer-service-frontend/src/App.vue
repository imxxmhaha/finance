<script setup>
// 根组件，只负责路由渲染
</script>

<template>
  <router-view />
</template>

<style>
/* 全局样式重置 */
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: "Outfit", "Zen Maru Gothic", "PingFang SC", "Microsoft YaHei", sans-serif;
  background: #070a14;
  color: #e6e3dc;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

button, input {
  font: inherit;
}

#app {
  min-height: 100vh;
}
</style>
