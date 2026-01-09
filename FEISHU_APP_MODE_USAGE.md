# Feishu Plugin - App Mode Usage Guide

## Overview

The Feishu plugin now supports two modes:

1. **Webhook Mode** (Original) - Send messages to Feishu groups via custom bot webhooks
2. **App Mode** (New) - Send messages to individual users via self-built application

## Webhook Mode (Original)

### URL Format
```
feishu://{webhook_token}/
```

### Example
```bash
curl -X POST http://localhost:8000/notify \
  -d "urls=feishu://1daf203e-e9d7-4430-97cf-9b7448618f00" \
  -d "body=CPU usage 80 percents"
```

### Setup
1. Visit https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot
2. Create a custom bot in your Feishu group
3. Copy the webhook token

---

## App Mode (New)

### URL Format
```
feishu://app/{AppID}/{AppSecret}/{email1}/{email2}/...
```

### Examples

#### Send to single user
```bash
curl -X POST http://localhost:8000/notify \
  -d "urls=feishu://app/cli_abc123xyz/secret456def/user@example.com" \
  -d "title=Alert" \
  -d "body=CPU usage 80 percents"
```

#### Send to multiple users
```bash
curl -X POST http://localhost:8000/notify \
  -d "urls=feishu://app/cli_abc123xyz/secret456def/user1@example.com/user2@example.com" \
  -d "body=Server restart scheduled"
```

#### Using query string parameters
```bash
curl -X POST http://localhost:8000/notify \
  -d "urls=feishu://app/?app_id=cli_abc123xyz&app_secret=secret456def&to=user1@example.com&to=user2@example.com" \
  -d "body=Multiple recipients via query string"
```

#### YAML Configuration
```yaml
urls:
  - feishu://app/cli_abc123xyz/secret456def/user1@example.com/user2@example.com/
```

### Setup

#### 1. Create Self-Built Application
1. Visit https://open.feishu.cn/open-apis/app-management
2. Click "Create App" -> "Create Self-Built App"
3. Enter app name and select workspace
4. Note your **App ID** and **App Secret** from the app credentials page

#### 2. Configure Required Permissions

Navigate to **Permissions & API Scopes** in your app settings, and enable:

- **获取与发送单聊、群组消息** (im:message)
- **以应用的身份发消息** (im:message:send_as_bot)
- **获取用户 user ID** (contact:user.base:readonly)

#### 3. Publish App

After configuring permissions, you need to publish the app:
1. Go to **Version Management & Release**
2. Create a new version
3. Click "Publish"

#### 4. Get User Email

Make sure you have the valid email addresses of users you want to message.

---

## How It Works

### Authentication Flow (App Mode)

1. Plugin obtains `tenant_access_token` using AppID and AppSecret
2. Token is cached for 2 hours (with 5-minute buffer)
3. For each target email, plugin sends message via Feishu API

### API Endpoints Used

- **Get Token**: `POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal`
- **Send Message**: `POST https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=email`

### Error Handling

- If one user's message fails, plugin continues to send to other users
- Notification is considered successful if at least one message is sent
- Detailed error logs are generated for troubleshooting

---

## Comparison

| Feature | Webhook Mode | App Mode |
|---------|--------------|----------|
| Target | Group chat only | Individual users |
| Setup | Simple (one-time token) | Requires app creation & permissions |
| Recipients | All group members | Specific users |
| Message Type | text | text |
| Authentication | Token | AppID + AppSecret + OAuth token |

---

## Troubleshooting

### Common Issues

#### 1. "At least one valid email target is required"
**Cause**: No valid email addresses provided
**Solution**: Ensure at least one valid email format (user@domain.com)

#### 2. "Failed to get tenant_access_token"
**Cause**: Invalid AppID/AppSecret or insufficient permissions
**Solution**:
- Verify AppID and AppSecret are correct
- Ensure app is published
- Check required permissions are granted

#### 3. "Failed to send Feishu notification to {email}"
**Cause**: User not found or app doesn't have permission
**Solution**:
- Verify email address is correct
- Ensure user is in the same workspace
- Check app has "获取用户 user ID" permission

---

## Best Practices

1. **Use environment variables** for credentials:
   ```bash
   export FEISHU_APP_ID="cli_abc123xyz"
   export FEISHU_APP_SECRET="secret456def"
   ```

2. **Validate emails** before adding to URL to avoid errors

3. **Monitor logs** for rate limiting or permission issues

4. **Test with single recipient** before scaling to multiple users

5. **Keep credentials secure** - don't commit URLs with secrets to version control
