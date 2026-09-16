import streamlit as st
import pandas as pd
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# 1. Load Keys & Connect to Database
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

@st.cache_resource
def init_connection():
    return MongoClient(MONGO_URI)

client = init_connection()
db = client["hextgen_onboarding"]

# 2. Page Config & Custom CSS for Healthcare Theme
st.set_page_config(page_title="HextGen Onboarding", layout="wide", page_icon="🏥")

st.markdown("""
    <style>
    /* Main background and text */
    .stApp {
        background-color: #f8fafd;
    }
    /* Headers */
    h1, h2, h3 {
        color: #1e3a8a;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    /* Custom Banner */
    .hospital-banner {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="hospital-banner"><h1>🏥 HextGen Omni-Modal Onboarding System</h1><p>Live AI Data Extraction & Management Portal</p></div>', unsafe_allow_html=True)

# 3. Create Tabs
tab1, tab2, tab3 = st.tabs(["📊 Hospital Data", "📜 Live Audit Logs", "⚙️ Bot Settings"])

# --- TAB 1: HOSPITAL DATA ---
with tab1:
    hospitals = list(db["hospitals"].find({}, {"_id": 0}))
    
    # Quick Metric Card
    st.metric(label="Total Hospitals Onboarded", value=len(hospitals))
    st.divider()
    
    if hospitals:
        flat_data = []
        for h in hospitals:
            data = h.get("data", {})
            basic = data.get("basic_details", {})
            admin = data.get("admin_details", {})
            
            flat_data.append({
                "Phone ID": h.get("hospital_phone"),
                "Hospital Name": basic.get("hospital_name"),
                "Admin Name": admin.get("admin_name"),
                "Status": h.get("validation", {}).get("status", "Unknown"),
                "Last Updated": h.get("last_updated")
            })
            
        df_hospitals = pd.DataFrame(flat_data)
        st.dataframe(df_hospitals, use_container_width=True)
    else:
        st.info("No hospital data found yet.")

# --- TAB 2: AUDIT LOGS ---
with tab2:
    st.subheader("Live System Audit Logs")
    logs = list(db["audit_logs"].find({}, {"_id": 0}).sort("timestamp", -1))
    
    if logs:
        df_logs = pd.DataFrame(logs)
        st.dataframe(df_logs, use_container_width=True)
    else:
        st.info("No audit logs found yet.")

# --- TAB 3: DYNAMIC SETTINGS (Add & Delete) ---
with tab3:
    st.subheader("Control WhatsApp Patrol Groups")
    st.write("Changes made here instantly update the AI Agent's patrol route.")
    
    config = db["settings"].find_one({"type": "bot_config"})
    current_groups = config.get("groups", []) if config else []
    
    col1, col2 = st.columns(2)
    
    # ADD GROUP SECTION
    with col1:
        st.markdown("### ➕ Add New Group")
        new_group = st.text_input("Enter exact WhatsApp Group Name:")
        if st.button("Add Group", type="primary"):
            if new_group and new_group not in current_groups:
                current_groups.append(new_group)
                db["settings"].update_one(
                    {"type": "bot_config"},
                    {"$set": {"groups": current_groups}},
                    upsert=True
                )
                st.success(f"Added '{new_group}'!")
                st.rerun()
            elif new_group in current_groups:
                st.warning("Group already exists!")
                
    # DELETE GROUP SECTION
    with col2:
        st.markdown("### 🗑️ Remove Group")
        if current_groups:
            group_to_delete = st.selectbox("Select group to stop monitoring:", current_groups)
            if st.button("Delete Group"):
                current_groups.remove(group_to_delete)
                db["settings"].update_one(
                    {"type": "bot_config"},
                    {"$set": {"groups": current_groups}},
                    upsert=True
                )
                st.error(f"Removed '{group_to_delete}'!")
                st.rerun()
        else:
            st.info("No groups to delete.")
