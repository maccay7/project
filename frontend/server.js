const express = require('express');
const axios = require('axios');
const cors = require('cors');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 5000;
const FRED_API_KEY = process.env.FRED_API_KEY; // get from https://fred.stlouisfed.org/docs/api/api_key.html

app.use(cors());
app.use(express.json());

app.get('/api/fred/series/:seriesId', async (req, res) => {
  const { seriesId } = req.params;
  const { limit = 100, sort_order = 'desc' } = req.query;
  try {
    const response = await axios.get(`https://api.stlouisfed.org/fred/series/observations`, {
      params: {
        series_id: seriesId,
        api_key: FRED_API_KEY,
        file_type: 'json',
        limit,
        sort_order,
      }
    });
    res.json({ success: true, data: response.data.observations });
  } catch (error) {
    console.error(error.message);
    res.status(500).json({ success: false, error: error.message });
  }
});

app.listen(PORT, () => console.log(`FRED proxy running on port ${PORT}`));