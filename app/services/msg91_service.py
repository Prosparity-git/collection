import requests
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from app.core.config import settings
from sqlalchemy.orm import Session

class MSG91Service:
    def __init__(self):
        self.auth_key = settings.MSG91_AUTH_KEY
        
        self.otp_length = settings.MSG91_OTP_LENGTH
        self.otp_expiry = settings.MSG91_OTP_EXPIRE_MINUTES
        self.base_url = "https://control.msg91.com/api/v5/otp"
    
    def generate_otp(self) -> str:
        """Generate random OTP"""
        return ''.join(random.choices(string.digits, k=self.otp_length))
    
    def send_otp(self, mobile_number: str, otp: str, template_id: str, variables: Optional[Dict[str, Any]] = None) -> Tuple[bool, Dict[str, Any]]:
        """Send OTP via MSG91 with optional template variables in JSON body.
        variables example for template params order: {"Param1": otp, "Param2": agent_name, "Param3": amount}
        """
        try:
            # Format mobile number with country code (91 for India)
            formatted_mobile = f"91{mobile_number}"
            
            # MSG91 SendOTP API call
            url = self.base_url
            params = {
                "mobile": formatted_mobile,
                "authkey": self.auth_key,
                "template_id": template_id,
                "otp": otp,
                "otp_expiry": self.otp_expiry,
                "realTimeResponse": "1"
            }
            
            headers = {
                "content-type": "application/json"
            }
            
            # Make POST request with query parameters and JSON body for variables
            json_body: Dict[str, Any] = variables or {}
            response = requests.post(url, params=params, json=json_body, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return True, {
                    "success": True,
                    "message": "OTP sent successfully",
                    "request_id": result.get("request_id"),
                    "response": result
                }
            else:
                return False, {
                    "success": False,
                    "message": f"Failed to send OTP: {response.text}",
                    "response": response.text
                }
                
        except requests.exceptions.RequestException as e:
            return False, {
                "success": False,
                "message": f"Network error: {str(e)}",
                "response": None
            }
        except Exception as e:
            return False, {
                "success": False,
                "message": f"Error sending OTP: {str(e)}",
                "response": None
            }
    
    def verify_otp(self, mobile_number: str, otp: str) -> Tuple[bool, Dict[str, Any]]:
        """Verify OTP via MSG91"""
        try:
            # Format mobile number with country code
            formatted_mobile = f"91{mobile_number}"
            
            # MSG91 Verify OTP API call
            verify_url = "https://control.msg91.com/api/v5/otp/verify"
            params = {
                "mobile": formatted_mobile,
                "otp": otp
            }
            
            headers = {
                "authkey": self.auth_key
            }
            
            # Make GET request
            response = requests.get(verify_url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                # Check if verification was successful
                message = result.get("message", "").lower()
                if "successfully" in message or "verified" in message:
                    return True, {
                        "success": True,
                        "message": "OTP verified successfully",
                        "response": result
                    }
                else:
                    return False, {
                        "success": False,
                        "message": result.get("message", "OTP verification failed"),
                        "response": result
                    }
            else:
                return False, {
                    "success": False,
                    "message": f"OTP verification failed: {response.text}",
                    "response": response.text
                }
                
        except requests.exceptions.RequestException as e:
            return False, {
                "success": False,
                "message": f"Network error: {str(e)}",
                "response": None
            }
        except Exception as e:
            return False, {
                "success": False,
                "message": f"Error verifying OTP: {str(e)}",
                "response": None
            }

    def resend_otp(self, mobile_number: str, retry_type: str = "text") -> Tuple[bool, Dict[str, Any]]:
        """
        Resend OTP via MSG91 retry API.
        retry_type: "text" for SMS (default) or "voice" for voice call.
        """
        try:
            formatted_mobile = f"91{mobile_number}"
            url = f"{self.base_url}/retry"
            params = {
                "authkey": self.auth_key,
                "retrytype": retry_type,
                "mobile": formatted_mobile
            }
            # GET request as per MSG91 docs
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                result = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"raw": response.text}
                return True, {
                    "success": True,
                    "message": "OTP resent successfully",
                    "response": result
                }
            return False, {
                "success": False,
                "message": f"Failed to resend OTP: {response.text}",
                "response": response.text
            }
        except requests.exceptions.RequestException as e:
            return False, {
                "success": False,
                "message": f"Network error: {str(e)}",
                "response": None
            }
        except Exception as e:
            return False, {
                "success": False,
                "message": f"Error resending OTP: {str(e)}",
                "response": None
            }

# Create service instance
msg91_service = MSG91Service()
