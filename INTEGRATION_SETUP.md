# 🔗 Integration Setup Guide

This guide covers connecting the Railway backend with the Vercel dashboard and Electron app for a complete subscription system.

## 📋 Integration Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Electron App  │    │  Vercel Dashboard│    │ Railway Backend │
│   (Client)      │◄──►│   (Admin Web)    │◄──►│   (API Server)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                       │
         └────────────────────────┼───────────────────────┘
                                  │
                      API Calls & Authentication
```

## 🚀 Deployment URLs

After deploying your services, you'll have:

- **Railway Backend**: `https://your-railway-app.up.railway.app`
- **Vercel Dashboard**: `https://your-dashboard.vercel.app`
- **Electron App**: Desktop application connecting to Railway

## 🔧 Backend Configuration (Railway)

### 1. Environment Variables for CORS

In your Railway service, configure these environment variables:

```bash
# CORS Configuration - Critical for integration
ALLOWED_ORIGINS=["https://your-dashboard.vercel.app","http://localhost:3000","http://localhost:8080"]

# Alternative: If you have a custom domain
ALLOWED_ORIGINS=["https://dashboard.flowlytix.com","https://app.flowlytix.com","http://localhost:3000"]

# For development, you can temporarily allow all origins (NOT for production)
# ALLOWED_ORIGINS=["*"]  # ⚠️ Development only!
```

### 2. Complete Railway Environment Variables

```bash
# Application
APP_NAME=Flowlytix Subscription Server
ENVIRONMENT=production
DEBUG=false
VERSION=1.0.0

# Server
HOST=0.0.0.0
PORT=8000

# Database (Railway Auto-provided)
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

# Security
SECRET_KEY=your-super-secure-64-character-secret-key-change-this-immediately
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS - UPDATE WITH YOUR ACTUAL URLS
ALLOWED_ORIGINS=["https://your-dashboard.vercel.app","http://localhost:3000","http://localhost:8080"]

# Features
ENABLE_ANALYTICS=true
ENABLE_NOTIFICATIONS=true
ENABLE_DEVICE_TRACKING=true
```

### 3. Test Backend CORS

After deployment, test CORS configuration:

```bash
# Test from your dashboard domain
curl -H "Origin: https://your-dashboard.vercel.app" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS \
     https://your-railway-app.up.railway.app/api/v1/subscriptions

# Should return 200 with CORS headers
```

## 🎨 Dashboard Configuration (Vercel)

### 1. Vercel Environment Variables

In Vercel Dashboard → Project Settings → Environment Variables:

```bash
# API Configuration - Point to Railway backend
NEXT_PUBLIC_API_URL=https://your-railway-app.up.railway.app

# Application
NEXT_PUBLIC_APP_NAME=Flowlytix Dashboard
NEXT_PUBLIC_APP_URL=https://your-dashboard.vercel.app

# Features
NEXT_PUBLIC_ENABLE_ANALYTICS=true
NEXT_PUBLIC_ENABLE_REALTIME=true
NEXT_PUBLIC_ENABLE_NOTIFICATIONS=true

# Build optimization
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1
```

### 2. Update API Service Configuration

Your dashboard's API service should already be configured correctly, but verify:

```typescript
// src/services/api.ts
const API_CONFIG = {
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  // This will resolve to: https://your-railway-app.up.railway.app
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
};
```

### 3. Test Dashboard API Connection

After deployment, verify the connection:

```bash
# Check if dashboard can reach backend
curl https://your-dashboard.vercel.app/api/health

# Check backend health from dashboard
curl https://your-railway-app.up.railway.app/health
```

## 💻 Electron App Configuration

### 1. Update Subscription API Client

In your main Electron project, update the subscription service:

```typescript
// src/main/services/SubscriptionApiClient.ts
const SUBSCRIPTION_API_BASE_URL =
  process.env.SUBSCRIPTION_API_URL || "https://your-railway-app.up.railway.app";

export class SubscriptionApiClient {
  private baseUrl: string;

  constructor() {
    // Production URL points to Railway
    this.baseUrl = SUBSCRIPTION_API_BASE_URL;
  }

  // Rest of your implementation remains the same
}
```

### 2. Environment Configuration for Electron

Create/update `.env` file in your main Electron project:

```bash
# Production Subscription API
SUBSCRIPTION_API_URL=https://your-railway-app.up.railway.app

# Development (for local testing)
# SUBSCRIPTION_API_URL=http://localhost:8000
```

### 3. Update Build Configuration

Update your Electron build process to include the production API URL:

```typescript
// vite.config.ts or webpack config
export default defineConfig({
  // ... other config
  define: {
    "process.env.SUBSCRIPTION_API_URL": JSON.stringify(
      process.env.SUBSCRIPTION_API_URL ||
        "https://your-railway-app.up.railway.app"
    ),
  },
});
```

## 🔐 Security & Authentication Flow

### 1. Authentication Sequence

```
1. Electron App → Railway: License activation request
2. Railway → Electron: JWT token + subscription details
3. Dashboard → Railway: Admin authentication (separate flow)
4. Dashboard → Railway: CRUD operations with admin token
```

### 2. JWT Token Sharing

The Electron app and Dashboard use separate authentication:

- **Electron App**: License-based authentication for subscription validation
- **Dashboard**: Admin authentication for management operations

### 3. CORS Security

Ensure production CORS is restrictive:

```python
# Backend CORS should only allow necessary origins
ALLOWED_ORIGINS = [
    "https://your-dashboard.vercel.app",    # Dashboard domain
    "https://dashboard.flowlytix.com",     # Custom domain if any
    # DO NOT include wildcard (*) in production
]
```

## 🧪 Integration Testing

### 1. End-to-End Test Checklist

- [ ] **Backend Health**: Railway backend responds to health checks
- [ ] **Dashboard API**: Dashboard can fetch data from Railway backend
- [ ] **CORS Working**: No CORS errors in browser console
- [ ] **Electron Connection**: Electron app can activate/validate licenses
- [ ] **Authentication**: Both apps can authenticate properly
- [ ] **Real-time Updates**: Dashboard shows live subscription changes
- [ ] **Error Handling**: Proper error responses and handling

### 2. Test Commands

```bash
# Test backend directly
curl https://your-railway-app.up.railway.app/health

# Test dashboard API connection
curl https://your-dashboard.vercel.app/api/test-connection

# Test CORS from browser
fetch('https://your-railway-app.up.railway.app/api/v1/subscriptions', {
  method: 'GET',
  headers: { 'Content-Type': 'application/json' }
})
```

### 3. Common Integration Issues

**CORS Errors**

- Verify ALLOWED_ORIGINS includes your Vercel URL
- Check Railway environment variables are saved
- Restart Railway service after CORS changes

**API Connection Failures**

- Verify NEXT_PUBLIC_API_URL is correct in Vercel
- Check Railway service is running and healthy
- Verify network connectivity between services

**Authentication Issues**

- Check JWT secret keys are consistent
- Verify token expiration settings
- Test authentication endpoints individually

## 📊 Monitoring Integration

### 1. Set up Health Checks

Monitor all services:

```bash
# Backend health
https://your-railway-app.up.railway.app/health

# Dashboard health
https://your-dashboard.vercel.app/api/health

# Integration endpoint
https://your-dashboard.vercel.app/api/test-backend-connection
```

### 2. Error Tracking

Configure error monitoring for all components:

- **Railway Backend**: Sentry integration in environment variables
- **Vercel Dashboard**: Vercel analytics + custom error reporting
- **Electron App**: Log subscription API errors for debugging

## 🚀 Production Deployment Checklist

Before going live with integrated system:

### Backend (Railway)

- [ ] All environment variables configured
- [ ] CORS origins updated with production URLs
- [ ] Database migrations applied
- [ ] Health checks passing
- [ ] Security headers configured

### Dashboard (Vercel)

- [ ] API URL points to Railway production
- [ ] Environment variables set
- [ ] Build succeeds without errors
- [ ] CORS errors resolved
- [ ] Authentication flow works

### Electron App

- [ ] API URL updated to Railway production
- [ ] Build includes production configuration
- [ ] License activation/validation tested
- [ ] Error handling for network issues

### Integration Testing

- [ ] Full end-to-end workflow tested
- [ ] Dashboard can manage Electron app subscriptions
- [ ] Real-time synchronization working
- [ ] Performance acceptable under load
- [ ] Security audit passed

## 📞 Troubleshooting

### Debug CORS Issues

```bash
# Check current CORS settings
curl -I https://your-railway-app.up.railway.app/api/v1/subscriptions

# Test from specific origin
curl -H "Origin: https://your-dashboard.vercel.app" \
     -I https://your-railway-app.up.railway.app/api/v1/subscriptions
```

### Debug API Connectivity

```bash
# Check if services can reach each other
# From Vercel function:
export async function testConnection() {
  const response = await fetch(process.env.NEXT_PUBLIC_API_URL + '/health');
  return response.json();
}
```

### Debug Environment Variables

```bash
# Railway CLI
railway variables

# Vercel CLI
vercel env ls
```

---

## 🎯 Next Steps

After integration is complete:

1. **Performance Monitoring**: Set up comprehensive monitoring
2. **Scale Testing**: Test with multiple concurrent users
3. **Security Audit**: Full security review of integrated system
4. **User Documentation**: Update user guides with new URLs
5. **Backup Strategy**: Ensure data backup across all services
6. **Disaster Recovery**: Test failover and recovery procedures
