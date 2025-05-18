import gradio as gr
import requests
import os
from datetime import date
import pandas as pd

# ---------------------- API Config ----------------------

API_KEY = os.getenv("AIML_API_KEY") or "your_aimlapi_key_here"
API_URL = "https://api.aimlapi.com/v1/chat/completions"
SYSTEM_PROMPT = (
    "You are a highly knowledgeable and friendly veterinary assistant AI. "
    "Provide clear, thorough, and helpful responses to users about pets (dogs and cats). "
    "Responses should be detailed, covering causes, symptoms, treatments, nutrition, precautions, "
    "recovery time, and practical advice. Use friendly, empathetic language and encourage consulting a vet for serious concerns. "
    "Avoid using markdown or special characters like asterisks. Use plain text and label sections clearly with headings such as 'Causes:', 'Symptoms:', etc."
)

# ---------------------- AI State ----------------------

chat_history = []
followup_count = 0

# ---------------------- Dropdowns ----------------------

breed_options = {
    "Cat": ["Persian", "Siamese", "Maine Coon", "British Shorthair", "Other"],
    "Dog": ["German Shepherd", "Labrador", "Bulldog", "Pomeranian", "Other"]
}

symptom_list = [
    "Vomiting", "Diarrhea", "Loss of Appetite", "Coughing", "Scratching", "Hair Loss", "Lethargy", "Other"
]

breed_info_topics = [
    "Favourite Food", "Most Common Diseases", "Precautions", "Allergies", "Favourite Activities", "Other"
]

# ---------------------- Helper Functions ----------------------

def update_breed(pet_type):
    return gr.update(choices=breed_options.get(pet_type, []), value=None, visible=True), gr.update(visible=False, value="")

def handle_breed_other(breed_choice):
    return gr.update(visible=(breed_choice == "Other"), value="")

def handle_symptom_other(symptom):
    return gr.update(visible=(symptom == "Other"), value="")

def handle_info_other(info):
    return gr.update(visible=(info == "Other"), value="")

def ask_ai(pet, breed, other_breed, age, gender, weight, topic, symptom, other_symptom, condition, info_topic, other_info, user_detail):
    global chat_history, followup_count
    followup_count = 0

    pet = pet.strip()
    final_breed = other_breed.strip() if breed == "Other" else breed
    final_symptom = other_symptom.strip() if symptom == "Other" else symptom
    final_info = other_info.strip() if info_topic == "Other" else info_topic
    age = age.strip()
    gender = gender.strip()
    weight = weight.strip()
    condition = condition.strip()
    user_detail = user_detail.strip()[:100]

    prompt_parts = [
        f"Pet: {pet}",
        f"Breed: {final_breed}",
        f"Age: {age}",
        f"Gender: {gender}",
        f"Weight: {weight}"
    ]

    if topic == "Symptom Checker":
        prompt_parts.append(f"Symptom: {final_symptom}")
        prompt_parts.append(
            "Please provide a detailed explanation including: typical causes, when and how this symptom usually appears, "
            "recommended treatments and home care, expected recovery timeline, preventive measures, and when to seek a vet."
        )
    elif topic == "Nutrition":
        prompt_parts.append(f"Condition: {condition if condition else 'None'}")
        prompt_parts.append(
            "Provide a comprehensive nutrition guide for this breed/condition: best foods available locally (Pakistan), benefits of each food, "
            "recommended feeding quantity and frequency, and tips for maintaining optimal health."
        )
    elif topic == "Breed Info":
        prompt_parts.append(f"Information Requested: {final_info}")
        prompt_parts.append(
            "Give detailed and interesting information on the selected topic related to the breed, covering key facts, practical tips, "
            "common concerns, and any special advice."
        )

    if user_detail:
        prompt_parts.append(f"User Detail: {user_detail}")

    user_prompt = "\n".join(prompt_parts)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    payload = {
        "model": "gpt-4o-mini-2024-07-18",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1200  # Increased token limit
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        answer = result['choices'][0]['message']['content'].strip()
        chat_history.clear()
        chat_history.extend(messages + [{"role": "assistant", "content": answer}])
        return answer
    except Exception as e:
        return f"❌ Error: {str(e)}"

def handle_followup(user_input):
    global chat_history, followup_count
    if followup_count >= 5:
        return "⚠️ Max of 5 follow-up questions reached."

    chat_history.append({"role": "user", "content": user_input})

    payload = {
        "model": "gpt-4o-mini-2024-07-18",
        "messages": chat_history,
        "temperature": 0.6,
        "max_tokens": 600
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        reply = result['choices'][0]['message']['content'].strip()
        chat_history.append({"role": "assistant", "content": reply})
        followup_count += 1
        return reply
    except Exception as e:
        return f"❌ Error: {str(e)}"

# ---------------------- Vaccination Tracker ----------------------

vaccination_records = []

def save_vaccination_record(pet_type, breed, pet_name, age, last_date, total_doses, upcoming_date, vaccine_type, notes):
    record = {
        "Pet Type": pet_type,
        "Breed": breed,
        "Pet Name": pet_name,
        "Age": age,
        "Last Vaccination Date": last_date,
        "Total Doses": total_doses,
        "Upcoming Dose Date": upcoming_date,
        "Vaccine Type": vaccine_type,
        "Notes": notes
    }
    vaccination_records.append(record)
    return f"✅ Record saved for {pet_name} ({breed})"

def view_all_vaccination_records():
    if not vaccination_records:
        return "📭 No records saved yet."
    df = pd.DataFrame(vaccination_records)
    return df

# ---------------------- UI ----------------------

with gr.Blocks() as demo:
    gr.Markdown("# 🐾 Smart Paws: AI Assistant + Vaccination Tracker")

    with gr.Tabs():
        # --- Tab 1: AI Assistant ---
        with gr.TabItem("🧠 Smart Paws AI Assistant"):
            with gr.Row():
                pet = gr.Dropdown(["Cat", "Dog"], label="🐕 Pet Type")
                breed = gr.Dropdown(label="🐾 Select Breed", visible=False)
                other_breed = gr.Textbox(label="✍️ Enter Breed", visible=False)
            pet.change(update_breed, pet, [breed, other_breed])
            breed.change(handle_breed_other, breed, other_breed)

            with gr.Row():
                age = gr.Textbox(label="🎂 Age (e.g. 2 years or 8 months)")
                gender = gr.Dropdown(["Male", "Female", "Unknown"], label="🚻 Gender")
                weight = gr.Textbox(label="⚖️ Weight (e.g. 10 kg)")

            topic = gr.Dropdown(["Symptom Checker", "Nutrition", "Breed Info"], label="📚 Select Topic")

            with gr.Column(visible=False) as symptom_section:
                symptom = gr.Dropdown(symptom_list, label="🤒 Select Symptom")
                other_symptom = gr.Textbox(label="✍️ Enter Symptom", visible=False)
                symptom.change(handle_symptom_other, symptom, other_symptom)

            with gr.Column(visible=False) as nutrition_section:
                condition = gr.Textbox(label="🩺 Condition (Optional, e.g. slim, weak)")

            with gr.Column(visible=False) as breed_info_section:
                info_topic = gr.Dropdown(breed_info_topics, label="ℹ️ Select Info Type")
                other_info = gr.Textbox(label="✍️ Enter Info Topic", visible=False)
                info_topic.change(handle_info_other, info_topic, other_info)

            user_detail = gr.Textbox(label="📝 Extra Detail (optional, max 100 chars)", max_lines=2)

            def show_topic_fields(selected_topic):
                return [
                    gr.update(visible=(selected_topic == "Symptom Checker")),
                    gr.update(visible=(selected_topic == "Nutrition")),
                    gr.update(visible=(selected_topic == "Breed Info"))
                ]

            topic.change(show_topic_fields, topic, [symptom_section, nutrition_section, breed_info_section])

            submit_btn = gr.Button("Get Advice")
            output = gr.Textbox(label="💬 AI Response", lines=20)

            gr.Markdown("## 🔄 Ask Follow-up")
            followup_input = gr.Textbox(label="🗣️ Follow-up Question")
            followup_btn = gr.Button("Ask Follow-up")
            followup_output = gr.Textbox(label="💡 Follow-up Response", lines=8)

            submit_btn.click(
                ask_ai,
                inputs=[pet, breed, other_breed, age, gender, weight, topic, symptom, other_symptom, condition, info_topic, other_info, user_detail],
                outputs=output
            )

            followup_btn.click(handle_followup, inputs=followup_input, outputs=followup_output)

        # --- Tab 2: Vaccination Records ---
        with gr.TabItem("💉 Pet Vaccination Records"):
            gr.Markdown("### 💉 Enter Vaccination Details")

            with gr.Row():
                v_pet_type = gr.Dropdown(["Dog", "Cat"], label="Pet Type")
                v_breed = gr.Textbox(label="Breed")
                v_pet_name = gr.Textbox(label="Pet Name")
                v_age = gr.Textbox(label="Age")

            with gr.Row():
                v_last_vaccination = gr.Textbox(label="Last Vaccination Date (YYYY-MM-DD)")
                v_total_doses = gr.Number(label="Total Doses Taken")
                v_upcoming_dose = gr.Textbox(label="Upcoming Dose Date (YYYY-MM-DD)")

            v_vaccine_type = gr.Dropdown(["Rabies", "DHPP", "FVRCP", "Bordetella", "Leptospirosis", "Other"], label="Vaccine Type")
            v_notes = gr.Textbox(label="Additional Notes", lines=3)

            save_btn = gr.Button("Save Record")
            save_output = gr.Textbox(label="📋 Status")

            view_btn = gr.Button("📑 View All Records")
            table_output = gr.Dataframe(label="📊 Saved Records", visible=True)

            save_btn.click(
                save_vaccination_record,
                inputs=[v_pet_type, v_breed, v_pet_name, v_age, v_last_vaccination, v_total_doses, v_upcoming_dose, v_vaccine_type, v_notes],
                outputs=save_output
            )

            view_btn.click(view_all_vaccination_records, inputs=[], outputs=table_output)

# ---------------------- Run App ----------------------

if __name__ == "__main__":
    demo.launch()
