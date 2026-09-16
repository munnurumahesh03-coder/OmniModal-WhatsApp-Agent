from pymongo import MongoClient

MONGO_URI = "mongodb+srv://munnurumahesh03_db_user:Mahesh1234@cluster0.nnmimjx.mongodb.net/?appName=Cluster0"
db = MongoClient(MONGO_URI)["hextgen_onboarding"]

# Save the list of groups to the database
db["settings"].update_one(
    {"type": "bot_config"},
    {"$set": {
        "groups": [
            "HextGen Onboarding - North",
            "HextGen Onboarding - South", 
            "HextGen Onboarding - Apollo",
            "HextGen Onboarding - City Care",
            "HextGen Onboarding - Test"
        ]
    }},
    upsert=True
)
print("✅ Groups successfully saved to MongoDB!")
