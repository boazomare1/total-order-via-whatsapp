# WhatsApp Integration Setup Instructions

## 1. Meta WhatsApp Business API Setup

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create a new app and add WhatsApp Business API
3. Get your:
   - Access Token (from WhatsApp > Getting Started)
   - Phone Number ID (from WhatsApp > Getting Started)
   - Verify Token (create your own, e.g., "frappe_verify_token")

## 2. Configure Your ERPNext Site

Add these to your `site_config.json`:

```json
{
  "whatsapp_token": "YOUR_ACCESS_TOKEN_HERE",
  "whatsapp_phone_id": "YOUR_PHONE_NUMBER_ID_HERE", 
  "whatsapp_verify_token": "frappe_verify_token"
}
```

## 3. Install and Migrate

```bash
cd /path/to/your/bench
bench --site yoursite install-app whatsapp_integration
bench --site yoursite migrate
```

## 4. Test Locally with ngrok

```bash
# Start your ERPNext site
bench start

# In another terminal, expose with ngrok
ngrok http 8000
```

Copy the ngrok URL (e.g., `https://abc123.ngrok.io`)

## 5. Configure Meta Webhook

1. Go to Meta Developer Dashboard > Your App > WhatsApp > Configuration
2. Set Webhook URL: `https://abc123.ngrok.io/api/method/whatsapp_integration.api.whatsapp_webhook`
3. Set Verify Token: `frappe_verify_token`
4. Subscribe to `messages` events

## 6. Add Your Phone as Tester

1. In Meta Dashboard > WhatsApp > Getting Started
2. Add your phone number as a tester
3. Accept the invitation on your WhatsApp

## 7. Test the Flow

Send a message to your test WhatsApp number:
- "order" - to start ordering
- Follow the prompts to select item, quantity, address
- Confirm with "yes"

## 8. Check Results

- Orders will be created in ERPNext as "WhatsApp Order" documents
- Sessions are tracked in "WhatsApp Session" documents
- Check ERPNext logs for any errors

## Example Conversation Flow

```
You: order
Bot: 🍕 Welcome! Here's our menu:
     1. Pizza - $10
     2. Burger - $8
     Reply with the number (1-10) or item name to select.

You: 1
Bot: Great! You selected: Pizza
     How many would you like? (Enter a number)

You: 2
Bot: Perfect! 2x Pizza
     Total: $20
     Please enter your delivery address:

You: 123 Main Street, Nairobi
Bot: 📋 Order Summary:
     Item: 2x Pizza
     Price per item: $10
     Total: $20
     Delivery to: 123 Main Street, Nairobi
     Confirm this order? Reply 'yes' to place order or 'no' to cancel.

You: yes
Bot: ✅ Order placed successfully!
     Order Number: WAP-00001
     Estimated delivery: 30 minutes
     Thank you for your order! 🎉
```