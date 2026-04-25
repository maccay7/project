# Backend Data Points Documentation

This document outlines all hardcoded values across the frontend that should be replaced with dynamic data from the backend API.

## LoginView.vue

### User Authentication
- **Current**: Hardcoded email/password validation
- **Backend Needed**: 
  - `POST /api/auth/login` - Authenticate user
  - `POST /api/auth/logout` - Logout user
  - `GET /api/auth/me` - Get current user info
  - `POST /api/auth/forgot-password` - Send password reset
  - `POST /api/auth/reset-password` - Reset password

### Form Labels
- **Current**: "Email", "Password", "Remember Me", "Forgot Password?"
- **Backend Needed**: Localization API for form labels
- **API**: `GET /api/localization/auth-forms`

## DashboardView.vue

### KPI Data
- **Current**: Hardcoded kpiData array with financial metrics
- **Backend Needed**: 
  - `GET /api/dashboard/kpi` - Get dashboard KPIs
  - Data should include: total investments, active calculations, reports generated, system health

### Quick Actions
- **Current**: Hardcoded quickActions array
- **Backend Needed**: 
  - `GET /api/dashboard/quick-actions` - Get user's available quick actions
  - Should be filtered by user permissions

### Recent Activity
- **Current**: Hardcoded activities in recentActivities array:
  - "Treasury Bills dataset uploaded" (2 hours ago)
  - "Bond calculations completed" (4 hours ago) 
  - "Money market analysis generated" (6 hours ago)
  - "Monthly report exported to PDF" (1 day ago)
- **Backend Needed**: 
  - `GET /api/dashboard/recent-activity` - Get recent user activity
  - `GET /api/dashboard/system-activity` - Get system-wide activity
  - Data structure should include: id, text, time, color

## SettingsView.vue

### User Profile
- **Current**: 
  - Name: "Makanaka Kanyai"
  - Email: "makanakakanyai@gmail.com"
  - Role: "Administrator"
- **Backend Needed**: 
  - `GET /api/user/profile` - Get user profile
  - `PUT /api/user/profile` - Update user profile
  - `POST /api/user/avatar` - Upload avatar image

### Account Settings
- **Current**: Hardcoded user data (firstName, lastName, email, phone)
- **Backend Needed**: 
  - `GET /api/user/account` - Get account details
  - `PUT /api/user/account` - Update account details

### Preferences
- **Current**: Hardcoded language, timezone, date format, currency options
- **Backend Needed**: 
  - `GET /api/user/preferences` - Get user preferences
  - `PUT /api/user/preferences` - Update user preferences
  - `GET /api/system/languages` - Get available languages
  - `GET /api/system/timezones` - Get available timezones
  - `GET /api/system/date-formats` - Get available date formats
  - `GET /api/system/currencies` - Get available currencies

### Notifications
- **Current**: Hardcoded notification settings
- **Backend Needed**: 
  - `GET /api/user/notifications/settings` - Get notification preferences
  - `PUT /api/user/notifications/settings` - Update notification preferences

### Security
- **Current**: Static security buttons
- **Backend Needed**: 
  - `POST /api/auth/change-password` - Change password
  - `POST /api/auth/enable-2fa` - Enable 2FA
  - `GET /api/auth/2fa-status` - Get 2FA status
  - `GET /api/auth/login-history` - Get login history
  - `GET /api/auth/active-sessions` - Get active sessions
  - `DELETE /api/auth/session/:id` - Revoke specific session

### System Information
- **Current**: 
  - Version: "v1.0.0"
  - Environment: "Development"
  - Database: "MySQL"
  - API Status: "Online"
  - Storage Used: "2.3 GB / 10 GB"
- **Backend Needed**: 
  - `GET /api/system/info` - Get system information
  - `GET /api/system/health` - Get system health status
  - `GET /api/system/storage` - Get storage usage

### Quick Actions
- **Current**: Export Data, Import Data, Clear Cache buttons
- **Backend Needed**: 
  - `POST /api/data/export` - Export user data
  - `POST /api/data/import` - Import user data
  - `DELETE /api/system/cache` - Clear system cache

## Other Views (To be documented)

### UploadView.vue
- **Backend Needed**: 
  - `POST /api/upload` - Upload files
  - `GET /api/upload/history` - Get upload history
  - `DELETE /api/upload/:id` - Delete uploaded file

### CleaningView.vue
- **Backend Needed**: 
  - `GET /api/data/dirty` - Get data needing cleaning
  - `POST /api/data/clean` - Clean data
  - `GET /api/cleaning/rules` - Get cleaning rules

### CalculationsView.vue
- **Backend Needed**: 
  - `POST /api/calculations/execute` - Run calculations
  - `GET /api/calculations/history` - Get calculation history
  - `GET /api/calculations/templates` - Get calculation templates

### ReportsView.vue
- **Backend Needed**: 
  - `GET /api/reports` - Get available reports
  - `POST /api/reports/generate` - Generate report
  - `GET /api/reports/:id/download` - Download report

### VisualizationsView.vue
- **Backend Needed**: 
  - `GET /api/visualizations/charts` - Get chart data
  - `GET /api/visualizations/config` - Get visualization configs
  - `POST /api/visualizations/custom` - Create custom visualization

## General Backend Requirements

### Authentication & Authorization
- JWT token-based authentication
- Role-based access control (RBAC)
- Session management
- API rate limiting

### Error Handling
- Standardized error response format
- HTTP status codes
- Error localization

### Data Validation
- Input validation on all endpoints
- Data sanitization
- File upload validation

### Caching
- Redis for session storage
- Application-level caching
- Cache invalidation strategies

### Logging & Monitoring
- Request/response logging
- Error tracking
- Performance metrics
- User activity logging

## Database Schema Requirements

### Users Table
- id, email, password_hash, first_name, last_name, phone, role, created_at, updated_at

### User Preferences Table
- user_id, language, timezone, date_format, currency, notification_settings

### System Info Table
- version, environment, database_type, api_status, storage_used, last_updated

### Audit Log Table
- id, user_id, action, resource, ip_address, user_agent, timestamp

### Sessions Table
- id, user_id, token, expires_at, ip_address, user_agent, created_at
