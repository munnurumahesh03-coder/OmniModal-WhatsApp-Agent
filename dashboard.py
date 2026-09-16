import streamlit as st
import pandas as pd
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# Page Config
st.set_page_config(page_title="HextGen AI Agent", page_icon="🏥", layout="wide")

# Title
st.title("🏥 HextGen Omni-Modal Onboarding System")
st.subheader("Live AI Data Extraction & Management Portal")

# Initialize MongoDB Connection
@st.cache_resource
def init_connection():
    return MongoClient(MONGO_URI)

try:
    client = init_connection()
    db = client["hextgen_onboarding"]
except Exception as e:
    st.error(f"❌ Database connection failed: {e}")
    st.stop()

# Create Tabs
tab1, tab2, tab3 = st.tabs(["📊 Hospital Data", "📜 Live Audit Logs", "⚙️ Bot Settings"])

# ==========================================
# TAB 1: HOSPITAL DATA
# ==========================================
with tab1:
    st.header("Onboarded Hospitals")
    
    hospitals = list(db["hospitals"].find({}, {"_id": 0}))
    
    if hospitals:
        st.metric("Total Hospitals Onboarded", len(hospitals))
        
        # Flatten the nested JSON for the dataframe
        flat_data = []
        for h in hospitals:
            data = h.get("data", {})
            basic = data.get("basic_details", {})
            admin = data.get("admin_details", {})
            
            flat_data.append({
                "Hospital Phone (ID)": h.get("hospital_phone"),
                "Hospital Name": basic.get("hospital_name"),
                "Address": basic.get("address"),
                "Reception WhatsApp": basic.get("reception_whatsapp"),
                "Admin Name": admin.get("admin_name"),
                "Admin Mobile": admin.get("admin_mobile"),
                "Status": h.get("validation", {}).get("status", "Unknown"),
                "Last Updated": h.get("last_updated")
            })
            
        df = pd.DataFrame(flat_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hospital data found yet. Waiting for the AI agent to extract data...")

# ==========================================
# TAB 2: LIVE AUDIT LOGS
# ==========================================
with tab2:
    st.header("System Audit Logs")
    
    logs = list(db["audit_logs"].find({}, {"_id": 0}).sort("timestamp", -1).limit(100))
    
    if logs:
        log_df = pd.DataFrame(logs)
        st.dataframe(log_df, use_container_width=True)
    else:
        st.info("No audit logs found. Logs will appear here when the agent processes messages.")

# ==========================================
# TAB 3: BOT SETTINGS (DYNAMIC GROUPS)
# ==========================================
with tab3:
    st.header("🤖 Dynamic Bot Patrol Route")
    st.write("Manage the WhatsApp groups the AI agent monitors. Changes apply instantly on the next patrol cycle.")
    
    # Fetch current config
    config = db["settings"].find_one({"type": "bot_config"})
    if not config:
        # Initialize if empty
        db["settings"].insert_one({"type": "bot_config", "groups": ["HextGen Onboarding - Test"]})
        config = db["settings"].find_one({"type": "bot_config"})
        
    current_groups = config.get("groups", [])
    
    # Display current groups
    st.subheader("Currently Monitored Groups")
    for i, group in enumerate(current_groups):
        st.markdown(f"✅ **{group}**")
        
    st.divider()
    
    col1, col2 = st.columns(2)
    
    # Add Group
    with col1:
        st.subheader("➕ Add New Group")
        new_group = st.text_input("Exact WhatsApp Group Name:")
        if st.button("Add Group", type="primary"):
            if new_group and new_group not in current_groups:
                current_groups.append(new_group)
                db["settings"].update_one(
                    {"type": "bot_config"},
                    {"$set": {"groups": current_groups}}
                )
                st.success(f"Added '{new_group}'! The bot will scan it on the next cycle.")
                st.rerun()
            elif new_group in current_groups:
                st.warning("Group is already being monitored.")
                
    # Delete Group
    with col2:
        st.subheader("🗑️ Remove Group")
        if current_groups:
            group_to_remove = st.selectbox("Select group to stop monitoring:", current_groups)
            if st.button("Remove Group"):
                current_groups.remove(group_to_remove)
                db["settings"].update_one(
                    {"type": "bot_config"},
                    {"$set": {"groups": current_groups}}
                )
                st.success(f"Removed '{group_to_remove}'! The bot will ignore it now.")
                st.rerun()
        else:
            st.info("No groups to remove.")
