import time
import os
import json
import re
from pathlib import Path
from datetime import datetime, timezone

# Playwright
from playwright.sync_api import sync_playwright

# AI & Data Processing
from groq import Groq
from google import genai
import pymupdf
import pandas as pd
from pymongo import MongoClient

# ==========================================
# 🔑 LOAD API KEYS FROM .ENV FILE
# ==========================================
import os
from dotenv import load_dotenv

load_dotenv() # Loads the keys from the .env file

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

groq_client = Groq(api_key=GROQ_API_KEY)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# Initialize MongoDB globally for connection pooling
try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client["hextgen_onboarding"]
    print("✅ Connected to MongoDB")
except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")

DOWNLOAD_DIR = Path(os.path.join(os.getcwd(), "downloads"))
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_DIR = Path(os.path.join(os.getcwd(), "Playwright_Profile"))

# ==========================================
# 🧹 SANITIZATION & VALIDATION LOGIC
# ==========================================
def empty_schema():
    return {
        "basic_details": {"hospital_name": None, "address": None, "reception_whatsapp": None},
        "admin_details": {"admin_name": None, "admin_mobile": None},
        "doctor_accounts": [],
        "lab_incharge": []
    }

def clean_phone_string(value):
    if not value: return None
    digits = re.sub(r"\D", "", str(value))
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits if len(digits) == 10 else value 

def sanitize_extracted_data(data):
    print("🧹 Sanitizing extracted data...")
    basic = data.get("basic_details", {})
    admin = data.get("admin_details", {})
    
    if basic.get("reception_whatsapp"):
        basic["reception_whatsapp"] = clean_phone_string(basic["reception_whatsapp"])
    if admin.get("admin_mobile"):
        admin["admin_mobile"] = clean_phone_string(admin["admin_mobile"])
        
    if basic.get("hospital_name"):
        basic["hospital_name"] = basic["hospital_name"].title()
        
    return data 

def valid_phone(value):
    if not value: return False
    digits = re.sub(r"\D", "", str(value))
    return len(digits) == 10 and digits[0] in "6789"

def validate_record(data):
    reasons = []
    basic = data.get("basic_details") or {}
    admin = data.get("admin_details") or {}
    
    if not basic.get("hospital_name"): 
        reasons.append("Missing Hospital Name")
    
    rec_whatsapp = basic.get("reception_whatsapp")
    admin_mobile = admin.get("admin_mobile")
    
    if not rec_whatsapp and not admin_mobile:
        reasons.append("Missing both Reception and Admin Mobile")
    else:
        if rec_whatsapp and not valid_phone(rec_whatsapp):
            reasons.append(f"Invalid Reception WhatsApp: {rec_whatsapp}")
        if admin_mobile and not valid_phone(admin_mobile):
            reasons.append(f"Invalid Admin Mobile: {admin_mobile}")
        
    status = "Needs Review" if reasons else "Validated"
    return {"status": status, "reasons": reasons}

# ==========================================
# 🧠 AI & DATABASE LOGIC
# ==========================================
def extract_data_with_llm(raw_text):
    schema = json.dumps(empty_schema())
    prompt = f"Extract hospital onboarding data into this exact JSON schema. Return ONLY valid JSON.\n\nSCHEMA:\n{schema}\n\nDATA:\n{raw_text}"
    try:
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r"^```json\s*", "", content)
        content = re.sub(r"^```\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        return json.loads(content)
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return empty_schema()

def save_record(hospital_phone, new_data):
    print("🛡️ Running Validation Guardrails...")
    validation = validate_record(new_data)
    
    if validation["status"] == "Needs Review":
        print(f"⚠️ Record flagged for review: {validation['reasons']}")
    
    print(f"💾 Performing Smart Merge (upsert=True) into MongoDB for ID: {hospital_phone}...")
    try:
        collection = db["hospitals"]
        
        existing_record = collection.find_one({"hospital_phone": hospital_phone}) or {}
        merged_data = existing_record.get("data", {})
        
        for section, fields in new_data.items():
            if isinstance(fields, dict):
                if section not in merged_data:
                    merged_data[section] = {}
                for k, v in fields.items():
                    if v: merged_data[section][k] = v
            elif isinstance(fields, list):
                if section not in merged_data:
                    merged_data[section] = []
                for item in fields:
                    if item not in merged_data[section]:
                        merged_data[section].append(item)

        now = datetime.now(timezone.utc).isoformat()
        
        record = {
            "hospital_phone": hospital_phone,
            "data": merged_data,
            "validation": validation,
            "last_updated": now
        }
        
        collection.update_one(
            {"hospital_phone": hospital_phone},
            {"$set": record, "$setOnInsert": {"created_at": now}},
            upsert=True
        )
        
        db["audit_logs"].insert_one({
            "hospital_phone": hospital_phone,
            "timestamp": now,
            "status": validation["status"],
            "reasons": validation["reasons"],
            "action": "whatsapp_playwright_extraction"
        })
        print("✅ Data successfully saved to MongoDB and Audit Log created!")
    except Exception as e:
        print(f"❌ Database Error: {e}")

# ==========================================
# 🤖 PLAYWRIGHT RPA AGENT (5-GROUP PATROL MODE)
# ==========================================
def run_playwright_agent():
    print("🚀 Booting up the Hextgen Multi-Group Agent...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            accept_downloads=True,
            args=["--start-maximized"],
            no_viewport=True 
        )
        
        page = browser.pages[0]
        
        try:
            print("🌐 Opening WhatsApp Web...")
            page.goto("https://web.whatsapp.com", timeout=60000 )
            
            print("⏳ Waiting for WhatsApp to load...")
            page.wait_for_selector("#pane-side", timeout=120000)
            print("✅ Logged in successfully!")
            time.sleep(3)
            
            # 📋 FETCH GROUPS DYNAMICALLY FROM MONGODB
            print("🔄 Fetching target groups from MongoDB...")
            config = db["settings"].find_one({"type": "bot_config"})
            
            if config and "groups" in config:
                TARGET_GROUPS = config["groups"]
            else:
                print("⚠️ No groups found in DB! Falling back to Test group.")
                TARGET_GROUPS = ["HextGen Onboarding - Test"]
                
            print(f"✅ Loaded {len(TARGET_GROUPS)} groups from database!")

            
            # --- 🧠 THE BOT'S MULTI-GROUP MEMORY & WARM-UP ---
            last_processed_messages = {group: None for group in TARGET_GROUPS}
            first_run = {group: True for group in TARGET_GROUPS} 
            
            print("✅ Starting 5-Group Patrol...")
            
            # --- CONTINUOUS PATROL LOOP ---
            while True:
                for group_name in TARGET_GROUPS:
                    try:
                        print(f"\n🔍 Checking group: {group_name}...")
                        
                        # 1. Search for the group (Your original working code)
                        search_box = page.get_by_role("textbox").first
                        search_box.wait_for(state="visible", timeout=15000)
                        search_box.click()
                        
                        page.keyboard.press("Control+A")
                        page.keyboard.press("Backspace")
                        time.sleep(1)
                        
                        page.keyboard.type(group_name, delay=200)
                        time.sleep(4) 
                        
                        group = page.get_by_text(group_name, exact=True).first
                        if not group.is_visible():
                            print(f"⚠️ Could not find {group_name}. Skipping...")
                            continue
                        group.click()
                        time.sleep(2)
                        
                        # 2. Read the latest message
                        try:
                            page.wait_for_selector('div[role="row"]', timeout=5000)
                        except:
                            pass
                            
                        messages = page.locator('div[role="row"]')
                        count = messages.count()
                        
                        if count == 0:
                            first_run[group_name] = False
                            continue
                            
                        last_message = messages.nth(count - 1)
                        raw_msg_text = last_message.inner_text()
                        
                        # 3. The Ultimate Memory & Leak Fix
                        msg_signature = last_message.inner_html()
                        
                        if first_run[group_name]:
                            print("💤 No new messages here.")
                            last_processed_messages[group_name] = msg_signature
                            first_run[group_name] = False
                            continue
                            
                        if msg_signature == last_processed_messages[group_name]:
                            print("💤 No new messages here.")
                            continue
                            
                        print(f"🚨 NEW MESSAGE IN {group_name}! Processing...")
                        last_processed_messages[group_name] = msg_signature
                        
                        # 🛑 PREVENTS THE PANDAS BUG (Clears old files)
                        filepath = None
                        file_ext = ""
                        extracted_text = ""
                        
                        # 4. Extraction Logic
                        image_locator = last_message.locator('img[src^="blob:"]')
                        is_file = ".pdf" in raw_msg_text.lower() or ".csv" in raw_msg_text.lower() or ".xlsx" in raw_msg_text.lower() or ".jpg" in raw_msg_text.lower() or ".png" in raw_msg_text.lower() or last_message.locator('span[data-icon="download"]').count() > 0
                        
                        if is_file or image_locator.count() > 0:
                            print("📄 File or Image detected! Attempting to download...")
                            try:
                                with page.expect_download(timeout=15000) as download_info:
                                    if image_locator.count() > 0:
                                        image_locator.first.click()
                                    else:
                                        last_message.click()
                                    
                                    time.sleep(1.5) # Wait for animation
                                    
                                    try:
                                        overlay_btn = page.locator("button[aria-label*='Download' i], div[role='button'][aria-label*='Download' i]").first
                                        overlay_btn.wait_for(state="visible", timeout=5000)
                                        overlay_btn.click()
                                    except Exception:
                                        pass
                                
                                download = download_info.value
                                filepath = DOWNLOAD_DIR / download.suggested_filename
                                download.save_as(filepath)
                                print(f"✅ File downloaded: {filepath}")
                                
                            except Exception as download_error:
                                print(f"⚠️ Download failed: {download_error}")
                                page.keyboard.press("Escape")
                                time.sleep(2)
                                continue 
                                
                            page.keyboard.press("Escape")
                            time.sleep(1)
                            
                            if filepath:
                                file_ext = filepath.suffix.lower()
                                if file_ext == ".pdf":
                                    print("📄 PyMuPDF: Extracting text from PDF...")
                                    doc = pymupdf.open(filepath)
                                    extracted_text = "\n".join([p.get_text() for p in doc])
                                    doc.close()
                                elif file_ext in [".csv", ".xlsx"]:
                                    print("📊 Pandas: Extracting text from Spreadsheet...")
                                    df = pd.read_excel(filepath) if file_ext == ".xlsx" else pd.read_csv(filepath)
                                    extracted_text = df.head(100).to_csv(index=False)
                                elif file_ext in [".png", ".jpg", ".jpeg"]:
                                    print("🖼️ Gemini Vision: Uploading image to Google...")
                                    uploaded_image = gemini_client.files.upload(file=str(filepath))
                                    print("🖼️ Gemini Vision: Extracting text from Image...")
                                    response = gemini_client.models.generate_content(
                                        model='gemini-3.6-flash',
                                        contents=["Extract all readable text from this image. Return only the text.", uploaded_image]
                                    )
                                    extracted_text = response.text
                        else:
                            print("📝 Extracting standard text message...")
                            extracted_text = raw_msg_text

                        if not extracted_text.strip():
                            continue
                            
                        # 5. AI & Database
                        print("🧠 Structuring data with AI...")
                        json_data = extract_data_with_llm(extracted_text)
                        if isinstance(json_data, list):
                            json_data = json_data[0] if len(json_data) > 0 else empty_schema()
                        
                        json_data = sanitize_extracted_data(json_data)
                        
                        basic_details = json_data.get("basic_details") or {}
                        hospital_name = basic_details.get("hospital_name") or f"Unknown_Hospital_{int(time.time())}"
                        
                        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', hospital_name)
                        local_json_path = DOWNLOAD_DIR / f"{safe_name}_extracted.json"
                        with open(local_json_path, "w") as f:
                            json.dump(json_data, f, indent=4)
                        print(f"💾 Saved local copy to {local_json_path}")
                        
                        admin = json_data.get("admin_details") or {}
                        hospital_phone = basic_details.get("reception_whatsapp") or admin.get("admin_mobile") or "UNKNOWN_ID"
                        save_record(hospital_phone, json_data)
                        
                    except Exception as group_error:
                        print(f"⚠️ Error processing {group_name}: {group_error}")
                        page.keyboard.press("Escape")
                        time.sleep(2)
                
                print("\n🔄 Patrol cycle complete. Waiting 5 seconds before next cycle...")
                time.sleep(5)
                    
        except Exception as e:
            print(f"❌ CRITICAL ERROR: {e}")
            page.screenshot(path="error_screenshot.png")
            print("📸 Saved error_screenshot.png to see what went wrong.")
        finally:
            print("🛑 Browser closed.")
            browser.close()

if __name__ == "__main__":
    run_playwright_agent()
