# DuraCapital Backend Setup Guide

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up MySQL Database

#### Using MySQL Workbench:
1. **Open MySQL Workbench**
2. **Create New Connection**:
   - Connection Name: `duracapital`
   - Hostname: `127.0.0.1` or `localhost`
   - Port: `3306`
   - Username: `root`
   - Password: [leave empty if no password]
   - Default Schema: `duracapital`

3. **Test Connection** and click **Test Connection**

4. **Execute Schema**:
   - Open the `database_schema.sql` file in this folder
   - Copy all SQL code
   - In MySQL Workbench, go to **File > Run SQL Script**
   - Paste the SQL code and execute

### 3. Configure Environment Variables
Create `.env` file in backend directory:
```env
FRED_API_KEY=b40141a5119f30bc2388d63f59d8847e
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=
DB_DATABASE=duracapital
```

### 4. Run the Backend
```bash
python app.py
```
The API will be available at: `http://localhost:5000`

## 📊 Database Tables Created

### Core Tables:
- **users** - User authentication and profiles
- **user_preferences** - User settings and preferences
- **calculations** - Financial calculation records
- **financial_instruments** - FRED instrument definitions
- **yield_curve_data** - Yield curve results
- **audit_log** - User activity tracking
- **sessions** - Authentication sessions
- **upload_history** - File upload tracking
- **reports** - Generated reports
- **system_config** - System configuration

## 🔌 API Endpoints

### Authentication:
- `GET /api/user/profile` - Get user profile
- `GET /api/user/preferences` - Get user preferences
- `GET /api/user/notifications/settings` - Get notification settings

### Financial Calculations:
- `GET /api/fred/yield-curve` - Get yield curve from FRED
- `POST /api/calculations/execute` - Execute calculation
- `GET /api/calculations/history` - Get calculation history

### Dashboard:
- `GET /api/dashboard/kpi` - Get dashboard metrics
- `GET /api/dashboard/recent-activity` - Get recent activity

### System:
- `GET /api/system/info` - Get system information

## 📈 FRED API Integration

### Active Series:
- **TB3MS** - 3-Month Treasury Bill Rate
- **DGS10** - 10-Year Treasury Constant Maturity Rate
- **DFF** - Federal Funds Effective Rate

### Yield Curve Calculation:
The backend fetches real-time data from FRED API and calculates:
- 3-Month Treasury yield
- 10-Year Treasury yield
- Federal Funds rate
- Complete yield curve

## 🔧 Testing with Postman

### Test Yield Curve:
```http
GET http://localhost:5000/api/fred/yield-curve
```

### Test Calculations:
```http
POST http://localhost:5000/api/calculations/execute
Content-Type: application/json

{
  "instrument_type": "yield_curve"
}
```

### Test Dashboard:
```http
GET http://localhost:5000/api/dashboard/kpi
GET http://localhost:5000/api/dashboard/recent-activity
```

## 🔗 Frontend Integration

The frontend is already configured to use these APIs. Once the backend is running:
1. All dashboard data will be real
2. Settings will load from database
3. Calculations will be stored and retrieved
4. All visualizations will show actual data

## 🛠️ Troubleshooting

### Database Issues:
- Ensure MySQL service is running
- Check connection parameters in `app.py`
- Verify schema was executed successfully

### API Issues:
- Check FRED API key is valid
- Verify internet connection for FRED calls
- Check Flask error logs

### Frontend Issues:
- Ensure CORS is properly configured
- Check API endpoints are accessible
- Verify data formats match frontend expectations

## 📝 Notes

- All calculations follow standard financial formulas
- FRED API calls are cached for performance
- Database connections are properly managed
- Error handling is comprehensive
- All endpoints return consistent JSON format

## 🔐 Security

- Passwords should be hashed (not plain text in production)
- JWT tokens recommended for authentication
- SQL injection protection implemented
- CORS configured for frontend access
- Input validation on all endpoints
