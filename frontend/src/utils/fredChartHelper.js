import api from '@/services/api'

/** Load FRED time-series for chart (same data as visualizations + reports). */
export async function loadFredSeriesChart(seriesId, limit = 365) {
  const res = await api.fredAPI.getSeries(seriesId, limit, 'desc')
  if (!res?.success || !res.data?.length) return null
  const reversed = [...res.data].reverse()
  return {
    labels: reversed.map(o => o.date),
    datasets: [{
      label: res.series_id || seriesId,
      data: reversed.map(o => o.value),
      borderColor: '#0B2044',
      backgroundColor: 'rgba(11, 32, 68, 0.1)',
      tension: 0.35,
      fill: true
    }],
    latest: res.data[0]?.value
  }
}

export async function loadFredSeriesForReport(seriesId) {
  return loadFredSeriesChart(seriesId, 120)
}

export function chartJsOptions() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    plugins: { legend: { position: 'top' } },
    scales: {
      y: { title: { display: true, text: 'Yield (%)' } },
      x: { 
        title: { display: true, text: 'Date' }, 
        ticks: { 
          maxRotation: 45, 
          autoSkip: true,
          maxTicksLimit: 12
        },
        time: {
          unit: 'day',
          displayFormats: {
            day: 'MMM d',
            week: 'MMM d',
            month: 'MMM yyyy'
          }
        }
      }
    }
  }
}

export function determineTimeUnit(dataPoints) {
  if (!dataPoints || dataPoints.length < 2) return 'day'
  
  const firstDate = new Date(dataPoints[0])
  const lastDate = new Date(dataPoints[dataPoints.length - 1])
  const daysDiff = (lastDate - firstDate) / (1000 * 60 * 60 * 24)
  
  if (daysDiff > 365) return 'month'
  if (daysDiff > 30) return 'week'
  return 'day'
}
