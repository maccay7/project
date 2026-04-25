<template>
  <div class="dashboard">
    <div class="card kpi">Total Bonds: 120</div>
    <div class="card kpi">T-Bills: 80</div>
    <div class="card kpi">Money Market: 50</div>

    <div class="card chart">
      <h3>Yield Curve</h3>
      <div class="chart-box">[Graph Placeholder]</div>
    </div>
  </div>
</template>

<style>
.dashboard {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 15px;
}
.kpi { text-align: center; font-size: 18px; }
.chart {
  grid-column: span 3;
}
.chart-box {
  height: 200px;
  background: var(--accent);
}
</style>