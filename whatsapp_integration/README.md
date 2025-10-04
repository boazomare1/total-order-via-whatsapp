# WhatsApp Integration for ERPNext

A complete WhatsApp Business API integration for ERPNext that allows customers to place orders via WhatsApp messages.

## Features

- 🍕 **Restaurant Menu System**: Interactive menu with categories (Pizzas, Burgers, Sides, Drinks)
- 📱 **WhatsApp Ordering**: Complete order flow through WhatsApp messages
- 🛒 **Order Management**: Create, track, and manage orders in ERPNext
- 🔄 **Real-time Updates**: Order status updates and confirmations
- 📊 **ERPNext Integration**: Full integration with ERPNext database

## Quick Start

### 1. Install the App
```bash
bench get-app whatsapp_integration
bench --site [your-site] install-app whatsapp_integration
```

### 2. Configure WhatsApp API
Add your WhatsApp API credentials to `site_config.json`:
```json
{
  "whatsapp_phone_id": "YOUR_PHONE_ID",
  "whatsapp_token": "YOUR_ACCESS_TOKEN",
  "whatsapp_verify_token": "YOUR_VERIFY_TOKEN"
}
```

### 3. Start the Webhook Server
```bash
cd apps/whatsapp_integration/whatsapp_integration
python standalone_webhook.py
```

### 4. Configure Meta Developer Console
- Set webhook URL: `https://your-domain.com/webhook`
- Set verify token: `YOUR_VERIFY_TOKEN`
- Subscribe to `messages` events

## How It Works

1. **Customer sends "menu"** to your WhatsApp Business number
2. **System shows menu** with categories and items
3. **Customer selects item** and variant (size, etc.)
4. **Customer enters quantity** and delivery address
5. **Order is created** in ERPNext with real order ID
6. **Confirmation sent** to customer with order details

## File Structure

```
whatsapp_integration/
├── standalone_webhook.py          # Main webhook server
├── api.py                         # ERPNext API integration
├── whatsapp_integration/
│   ├── doctype/
│   │   ├── whatsapp_order/        # Order doctype
│   │   ├── whatsapp_product_variant/  # Product variants
│   │   └── whatsapp_session/     # User sessions
│   └── hooks.py                   # Frappe hooks
└── www/
    └── webhook.py                 # Webhook endpoint
```

## API Endpoints

- `GET /webhook` - Webhook verification
- `POST /webhook` - Receive WhatsApp messages
- `GET /health` - Health check

## Order Flow

1. **Menu Display**: Customer types "menu"
2. **Item Selection**: Customer selects item (1-13)
3. **Variant Selection**: Customer selects size/variant
4. **Quantity Entry**: Customer enters quantity
5. **Address Entry**: Customer provides delivery address
6. **Order Creation**: Order saved to ERPNext
7. **Confirmation**: Customer receives order details

## Commands

- `menu` - Show restaurant menu
- `My Orders` - View order history
- `Status [Order ID]` - Check order status
- `Reorder [Order ID]` - Reorder previous order

## Requirements

- ERPNext/Frappe framework
- WhatsApp Business API access
- Python 3.8+
- Flask (for standalone webhook)

## Support

For issues and questions, please check the setup instructions in `setup_instructions.md`.

## License

MIT License - see LICENSE file for details.
