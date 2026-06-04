import { nextTick } from 'vue'
import Chart from 'chart.js/auto'
import { chartJsOptions } from './fredChartHelper'

/** Draw Chart.js on canvas after tab is visible. */
export async function renderFredLineChart(canvasRef, chartData, chartInstanceRef) {
  for (let i = 0; i < 15; i++) {
    await nextTick()
    if (canvasRef.value) break
    await new Promise(r => setTimeout(r, 40))
  }
  if (!canvasRef.value || !chartData?.datasets?.length) return null

  await new Promise(r => requestAnimationFrame(r))

  if (chartInstanceRef.current) {
    chartInstanceRef.current.destroy()
    chartInstanceRef.current = null
  }

  const ctx = canvasRef.value.getContext('2d')
  chartInstanceRef.current = new Chart(ctx, {
    type: 'line',
    data: chartData,
    options: chartJsOptions()
  })
  setTimeout(() => chartInstanceRef.current?.resize(), 100)
  return chartInstanceRef.current
}
