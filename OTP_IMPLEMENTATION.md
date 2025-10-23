# MSG91 OTP Payment Verification Implementation

## Overview
This implementation adds OTP verification for payment status updates (Paid/Partially Paid) using MSG91 SMS service and Redis for OTP storage.

## Features
- Send OTP to customer's mobile number when marking payment as Paid/Partially Paid
- Verify OTP via MSG91 API
- Redis storage for OTP (5-minute TTL)
- Complete audit trail via communication tables
- Rate limiting and security measures

## Environment Variables Required

Add these to your `.env` file:

```env
# MSG91 Configuration
MSG91_AUTH_KEY=your_msg91_auth_key_here
MSG91_SENDER_ID=PROSPA
MSG91_OTP_LENGTH=4
MSG91_OTP_EXPIRE_MINUTES=5

# Redis Configuration (optional)
REDIS_URL=redis://localhost:6379/0
```

## Database Setup

1. Create the communication tables using the provided SQL:
   - `communication_template`
   - `communication`
   - `communication_log`

2. Insert OTP template:
```sql
INSERT INTO communication_template (template_id, template_name, channel_type, content, dlt_id, status, variables) 
VALUES ('OTP_SEND', 'OTP Send Template', 1, 'Your OTP for payment verification is {{otp_code}}. Valid for 5 minutes. - Prosparity', 'your_dlt_id', 'ACTIVE', '{"otp_code": "string"}');
```

## API Endpoints

### 1. Send OTP
**POST** `/api/v1/otp/send-otp-payment`

Request Body:
```json
{
  "loan_id": 123,
  "repayment_id": 456,
  "template_key": "1",
  "contact_type": "applicant"
}
```

**Contact Types Available:**
- `"applicant"` - Send to main applicant (default)
- `"co_applicant"` - Send to co-applicant

Response:
```json
{
  "success": true,
  "message": "OTP sent successfully",
  "mobile_number": "987****10",
  "communication_id": 789,
  "expires_in_minutes": 5
}
```

### 2. Verify OTP
**POST** `/api/v1/otp/verify-otp-payment`

Request Body:
```json
{
  "loan_id": 123,
  "repayment_id": 456,
  "otp_code": "123456",
  "contact_type": "applicant"
}
```

**Note:** Mobile number is automatically fetched based on `contact_type` and `loan_id`. No need to provide mobile number in request.

Response:
```json
{
  "success": true,
  "message": "OTP verified successfully",
  "mobile_number": "9876543210",
  "verified_at": "2024-01-01T12:00:00",
  "payment_status_updated": false
}
```

### 3. Verify OTP and Update Status (Combined)
**POST** `/api/v1/otp/verify-otp-and-update-status`

Request Body:
```json
{
  "loan_id": 123,
  "repayment_id": 456,
  "mobile": "9876543210",
  "otp_code": "123456",
  "status_update": {
    "loan_id": "123",
    "repayment_id": "456",
    "repayment_status": 3,
    "amount_collected": 5000.0,
    "payment_mode_id": 1
  }
}
```

## Usage Flow

1. **Frontend**: User marks payment as Paid/Partially Paid
2. **Backend**: Call `/send-otp-payment` API
3. **MSG91**: Sends OTP to customer's mobile
4. **Customer**: Receives OTP on mobile
5. **Frontend**: User enters OTP
6. **Backend**: Call `/verify-otp-payment` API
7. **Frontend**: If verified, call status update API

## Security Features

- OTP expires in 5 minutes
- One-time use (deleted after verification)
- Rate limiting (60s cooldown between sends)
- Mobile number validation
- Complete audit trail
- Redis fallback for reliability

## Dependencies Added

- `requests>=2.31.0` - For MSG91 API calls
- `redis>=4.5.0` - For OTP storage (optional)

## Files Created/Modified

**New Files:**
- `app/models/communication_template.py`
- `app/models/communication.py`
- `app/models/communication_log.py`
- `app/schemas/otp.py`
- `app/services/msg91_service.py`
- `app/api/v1/routes/otp.py`

**Modified Files:**
- `requirements.txt`
- `app/core/config.py`
- `app/models/__init__.py`
- `app/main.py`

## Testing

1. Start your FastAPI server
2. Access Swagger UI at `http://localhost:8000/docs`
3. Test the OTP endpoints
4. Check communication tables for audit logs

## Notes

- Redis is optional but recommended for better performance
- MSG91 template must be configured in your MSG91 dashboard
- Mobile numbers must be in 10-digit format
- All OTP operations are logged for audit purposes
