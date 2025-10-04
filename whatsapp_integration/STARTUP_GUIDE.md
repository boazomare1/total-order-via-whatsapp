# 🚀 WhatsApp Integration - Startup Guide

This guide helps you get your WhatsApp integration running quickly after powering on your laptop.

## 🎯 Quick Start (Recommended)

```bash
cd /home/boaz/test-bench/apps/whatsapp_integration/whatsapp_integration
./quick_start.sh
```

This script will:
- ✅ Clean up previous sessions
- ✅ Start the WhatsApp webhook
- ✅ Start ngrok tunnel
- ✅ Show you the new webhook URL
- ✅ Guide you to update Meta Developer Console

## 🔧 Complete Setup (If needed)

```bash
./startup_complete.sh
```

This comprehensive script includes:
- ✅ Prerequisites checking
- ✅ ERPNext startup
- ✅ Webhook startup
- ✅ ngrok tunnel setup
- ✅ Health checks
- ✅ Step-by-step Meta Console instructions

## 🔑 Access Token Management

### Update Token (when expired)
```bash
python update_token.py
```

### Manual Token Update
1. Get new token from: https://developers.facebook.com/apps/
2. Edit `standalone_webhook.py`
3. Update `WHATSAPP_TOKEN = "your_new_token"`

## 📋 Meta Developer Console Setup

Every time you restart, you need to:

1. **Get the ngrok URL** (shown by the script)
2. **Go to**: https://developers.facebook.com/apps/
3. **Select your WhatsApp Business app**
4. **Go to**: WhatsApp > Configuration
5. **Update Webhook URL**: `https://your-ngrok-url.ngrok.io/webhook`
6. **Click**: "Verify and Save"

## 🧪 Testing

### Test Webhook Health
```bash
curl http://localhost:5000/health
```

### Test ngrok Tunnel
```bash
curl https://your-ngrok-url.ngrok.io/health
```

### Test WhatsApp Flow
1. Send "menu" to your WhatsApp Business number
2. Follow the ordering process
3. Check ERPNext for the new order

## 🛑 Stopping Services

```bash
# Stop webhook
pkill -f standalone_webhook.py

# Stop ngrok
pkill -f ngrok

# Stop ERPNext
pkill -f bench
```

## 🔍 Troubleshooting

### Port Already in Use
```bash
# Kill processes on port 5000
lsof -ti :5000 | xargs kill -9
```

### ngrok Not Working
```bash
# Check ngrok status
curl http://localhost:4040/api/tunnels
```

### Webhook Not Responding
```bash
# Check webhook logs
# (logs will show in the terminal where you started it)
```

## 📊 Monitoring

### View ngrok Logs
```bash
tail -f /tmp/ngrok.log
```

### Check Running Processes
```bash
ps aux | grep -E "(standalone_webhook|ngrok|bench)"
```

## 🎯 Daily Workflow

1. **Power on laptop**
2. **Run**: `./quick_start.sh`
3. **Copy the ngrok URL**
4. **Update Meta Developer Console**
5. **Test with WhatsApp**
6. **Start taking orders!**

## 📱 What You Get

- ✅ **WhatsApp Order Processing**: Complete restaurant ordering
- ✅ **ERPNext Integration**: Orders saved to database
- ✅ **Real-time Messaging**: Customer communication
- ✅ **Order Tracking**: Status updates and confirmations

## 🆘 Need Help?

- Check the webhook logs for errors
- Verify ngrok is running: http://localhost:4040
- Test webhook health: http://localhost:5000/health
- Check ERPNext is running: http://localhost:8002

---

**Happy Ordering! 🍕📱**




