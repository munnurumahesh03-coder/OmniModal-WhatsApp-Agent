import importlib.metadata

# 1. Define the core packages used in our Omni-Modal Agent
core_packages = [
    "playwright",
    "groq",
    "google-genai",
    "pymupdf",
    "pandas",
    "pymongo",
    "python-dotenv",
    "streamlit"  # <-- Added Streamlit here!
]

# 2. Dynamically fetch their exact installed versions
requirements_lines = []
for pkg in core_packages:
    try:
        version = importlib.metadata.version(pkg)
        requirements_lines.append(f"{pkg}=={version}")
    except importlib.metadata.PackageNotFoundError:
        print(f"⚠️ Warning: {pkg} is not installed!")

# 3. Write to requirements.txt
with open("requirements.txt", "w") as f:
    f.write("\n".join(requirements_lines))

print("✅ requirements.txt generated dynamically with exact versions:\n")
print("\n".join(requirements_lines))
