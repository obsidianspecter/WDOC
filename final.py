import streamlit as st
import pandas as pd
import datetime
import sqlite3
import folium
from streamlit_folium import st_folium
import ollama

# Set up page configuration
st.set_page_config(
    page_title="Women's Health Assistant",
    page_icon="🌸",
    layout="wide",
)

# Initialize SQLite connection
conn = sqlite3.connect("health_assistant.db")
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS symptoms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    symptom TEXT,
    severity TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS medical_stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    latitude REAL,
    longitude REAL
)
""")
conn.commit()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

if "period_tracker" not in st.session_state:
    st.session_state.period_tracker = {"last_period": None, "cycle_length": 28}

if "symptoms" not in st.session_state:
    st.session_state.symptoms = []

if "dashboard_graphs" not in st.session_state:
    st.session_state.dashboard_graphs = []

# Helper Functions
def generate_response():
    response = ollama.chat(model="WDOC", stream=True, messages=st.session_state.messages)
    for partial_resp in response:
        token = partial_resp["message"]["content"]
        st.session_state["full_message"] += token
        yield token

def save_symptom_to_db(date, symptom, severity):
    cursor.execute(
        "INSERT INTO symptoms (date, symptom, severity) VALUES (?, ?, ?)",
        (date, symptom, severity)
    )
    conn.commit()

def delete_symptom_from_db(symptom):
    cursor.execute("DELETE FROM symptoms WHERE symptom = ?", (symptom,))
    conn.commit()

def get_all_symptoms():
    cursor.execute("SELECT id, date, symptom, severity FROM symptoms")
    return cursor.fetchall()

def save_medical_store(name, latitude, longitude):
    cursor.execute(
        "INSERT INTO medical_stores (name, latitude, longitude) VALUES (?, ?, ?)",
        (name, latitude, longitude)
    )
    conn.commit()

def get_all_medical_stores():
    cursor.execute("SELECT name, latitude, longitude FROM medical_stores")
    return cursor.fetchall()

def generate_period_calendar(last_period, cycle_length):
    """Generates a calendar-like table showing predicted period dates."""
    dates = []
    current_date = last_period
    for _ in range(12):  # Show predictions for 12 cycles
        next_period = current_date + datetime.timedelta(days=cycle_length)
        dates.append({"Cycle Start": current_date.strftime("%Y-%m-%d"), "Next Period": next_period.strftime("%Y-%m-%d")})
        current_date = next_period
    return pd.DataFrame(dates)

# Main App Title
st.title("🌸 Women's Health Assistant")
st.write("An AI-powered assistant for personalized women's health guidance and insights.")

# Tabs for Features
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "💬 Chat", "📅 Period Tracker", "📋 Symptom Tracker", "📊 Dashboard", "🗺️ Medical Stores"
])

# Chat Tab
with tab1:
    st.subheader("💬 Chat with the Assistant")
    
    for msg in st.session_state["messages"]:
        if msg["role"] == "user":
            st.chat_message(msg["role"], avatar="🧑‍💻").write(msg["content"])
        else:
            st.chat_message(msg["role"], avatar="🤖").write(msg["content"])

    if prompt := st.chat_input():
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user", avatar="🧑‍💻").write(prompt)
        st.session_state["full_message"] = ""
        st.chat_message("assistant", avatar="🤖").write_stream(generate_response)
        st.session_state.messages.append({"role": "assistant", "content": st.session_state["full_message"]})

# Period Tracker Tab
with tab2:
    st.subheader("📅 Period Tracker")
    last_period = st.date_input("Last Period Date", key="last_period", value=st.session_state.period_tracker["last_period"])
    cycle_length = st.number_input("Cycle Length (days)", 20, 40, value=st.session_state.period_tracker["cycle_length"], step=1, key="cycle_length")

    if st.button("Save Period Data"):
        st.session_state.period_tracker["last_period"] = last_period
        st.session_state.period_tracker["cycle_length"] = cycle_length
        st.success("Period data saved!")

    # Generate and display calendar
    if st.session_state.period_tracker["last_period"]:
        period_calendar = generate_period_calendar(last_period, cycle_length)
        st.markdown("### Predicted Period Calendar")
        st.table(period_calendar)  # Display the calendar as a table

# Symptom Tracker Tab
with tab3:
    st.subheader("📋 Symptom Tracker")
    symptom = st.text_input("Log Today's Symptom (e.g., cramps, mood swings):")
    severity = st.selectbox("Severity", ["Mild", "Moderate", "Severe"])
    if st.button("Log Symptom"):
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        save_symptom_to_db(today, symptom, severity)
        st.success("Symptom logged and saved to database!")

    # Display symptoms with options to filter and delete
    symptoms_data = get_all_symptoms()
    if symptoms_data:
        symptoms_df = pd.DataFrame(symptoms_data, columns=["ID", "Date", "Symptom", "Severity"])
        st.markdown("### View and Manage Symptoms")
        st.dataframe(symptoms_df.drop(columns=["ID"]))

        # Delete symptom
        selected_symptom = st.selectbox("Select a Symptom to Delete", symptoms_df["Symptom"].unique())
        if st.button("Delete Selected Symptom"):
            delete_symptom_from_db(selected_symptom)
            st.success(f"Symptom '{selected_symptom}' deleted.")

# Dashboard Tab
with tab4:
    st.subheader("📊 Dashboard")
    symptoms_data = get_all_symptoms()
    if symptoms_data:
        symptoms_df = pd.DataFrame(symptoms_data, columns=["ID", "Date", "Symptom", "Severity"])
        st.write("**Symptom Insights:**")
        bar_chart = st.bar_chart(symptoms_df.groupby("Symptom").size())
        st.session_state.dashboard_graphs.append(bar_chart)

    # Option to clear graphs
    if st.button("Clear Dashboard Graphs"):
        st.session_state.dashboard_graphs = []
        st.success("Dashboard graphs cleared.")

# Medical Stores Tab
with tab5:
    st.subheader("🗺️ Nearby Medical Stores")
    stores = get_all_medical_stores()

    # Add new medical store
    with st.expander("Add a New Medical Store"):
        store_name = st.text_input("Store Name")
        latitude = st.number_input("Latitude", format="%.6f", min_value=11.050, max_value=11.150)  # Confined to Sri Ramakrishna Engineering College area
        longitude = st.number_input("Longitude", format="%.6f", min_value=76.910, max_value=76.960)  # Confined to Sri Ramakrishna Engineering College area
        if st.button("Save Store"):
            save_medical_store(store_name, latitude, longitude)
            st.success("Medical store saved!")

    # Display map
    m = folium.Map(location=[11.1019, 76.9415], zoom_start=15)  # Centered on Sri Ramakrishna Engineering College
    for store in stores:
        folium.Marker([store[1], store[2]], popup=store[0]).add_to(m)
    st_folium(m, width=700, height=500)
