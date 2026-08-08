from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time
import random

app = FastAPI(title="Temp-SMS Sandbox API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ذاكرة مؤقتة لتخزين الأرقام والرسائل
database = {
    "numbers": {},  # phone_number -> expires_at
    "inboxes": {}   # phone_number -> [messages list]
}

class NumberCreateRequest(BaseModel):
    country_code: str = "+966"
    ttl_seconds: int = 600

class WebhookMessage(BaseModel):
    phone_number: str
    otp_code: str
    message_body: str
    sender: str = "SYSTEM"

class SimulateRequest(BaseModel):
    phone_number: str

@app.post("/api/v1/numbers/create")
def create_number(req: NumberCreateRequest):
    # توليد رقم عشوائي مكون من 9 أرقام بعد رمز الدولة (مثل السعودية)
    random_subscriber = "".join([str(random.randint(0, 9)) for _ in range(9)])
    phone = f"{req.country_code}{random_subscriber}"
    expires_at = time.time() + req.ttl_seconds
    
    database["numbers"][phone] = expires_at
    database["inboxes"][phone] = []
    
    return {
        "phone_number": phone,
        "expires_at": expires_at,
        "ttl_seconds": req.ttl_seconds
    }

@app.get("/api/v1/inbox/{phone_number}")
def get_inbox(phone_number: str):
    if phone_number not in database["inboxes"]:
        return {"phone_number": phone_number, "messages": []}
    return {
        "phone_number": phone_number,
        "messages": database["inboxes"][phone_number]
    }

@app.post("/api/v1/sms/webhook")
def receive_webhook(msg: WebhookMessage):
    if msg.phone_number not in database["inboxes"]:
        database["inboxes"][msg.phone_number] = []
    
    new_msg = {
        "otp_code": msg.otp_code,
        "body": msg.message_body,
        "sender": msg.sender,
        "received_at_iso": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    }
    database["inboxes"][msg.phone_number].insert(0, new_msg)
    return {"status": "success", "message": "SMS stored successfully"}

@app.post("/api/v1/sms/simulate")
def simulate_sms(req: SimulateRequest):
    otp = "".join([str(random.randint(0, 9)) for _ in range(6)])
    body = f"رمز التحقق الخاص بك هو {otp}. صالح لمدة 10 دقائق."
    
    if req.phone_number not in database["inboxes"]:
        database["inboxes"][req.phone_number] = []
        
    new_msg = {
        "otp_code": otp,
        "body": body,
        "sender": "SIMULATOR",
        "received_at_iso": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    }
    database["inboxes"][req.phone_number].insert(0, new_msg)
    return {"status": "success", "generated_otp": otp}
