import json
import logging
import streamlit as st
import pyperclip

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_løsning_info(data):
    løsning_navn = data.get('Name', 'Navn ikke tilgængelig')
    beskrivelse = data.get('Description', 'Ingen beskrivelse angivet')
    
    opstartes = []

    arbejdsgang_settings = data.get('ArbejdsgangSkabelonSettings', {})

    if arbejdsgang_settings.get('InternStart', False):
        opstartes.append("internt")
    if arbejdsgang_settings.get('EksternStart', False):
        opstartes.append("eksternt")
    if arbejdsgang_settings.get('AnonymStart', False):
        opstartes.append("anonymt")

    if len(opstartes) == 0:
        opstart_text = "Ingen opstartsmetode angivet"
    elif len(opstartes) == 1:
        opstart_text = opstartes[0].capitalize()
    elif len(opstartes) == 2:
        opstart_text = " eller ".join([opstartes[0].capitalize(), opstartes[1]])
    else:
        opstart_text = ", ".join([word for word in opstartes[:-1]])
        opstart_text = opstart_text.capitalize() + " eller " + opstartes[-1]

    antal_blanketter = len(data.get('ProcesData', {}).get('Blanketter', []))
    felter_anvendt = parse_felter_anvendt(data)

    ekstra_info = extract_ekstra_info(data)

    if beskrivelse is None:
        beskrivelse = 'Ingen beskrivelse angivet'

    return løsning_navn, beskrivelse, opstart_text, antal_blanketter, felter_anvendt, ekstra_info

def recursive_parse_elements(items, typenames_translation, typenames, exclude_types):
    for item in items:
        typename = item.get('Typename', 'Unknown')
        if typename not in exclude_types:  # Only add if not in the exclude list
            translated_typename = typenames_translation.get(typename, typename)
            typenames.add(translated_typename)
        if 'Elements' in item:
            recursive_parse_elements(item['Elements'], typenames_translation, typenames, exclude_types)

def parse_felter_anvendt(data):
    typenames_translation = {
        "ElementGroup": "Gruppe",
        "ElementTextfield": "Tekstfelt",
        "ElementTextFieldFormatted": "Tekstfelt med formatering",
        "ElementNumber": "Talfelt",
        "ElementMultiSelect": "Multivælger",
        "ElementPerson": "Personfelt",
        "ElementDate": "Datofelt",
        "ElementEmail": "E-mailadresse",
        "ElementInfoText": "Informationtekst",
        "ElementYesNo": "JaNejFelt",
        "ElementCheckBox": "Afkrydsningsfelt",
        "ElementList": "Liste",
        "ElementVaerdiliste": "Værdiliste",
        "ElementAutonummerering": "Autonummeringsfelt",
        "ElementFacit": "Facitfelt",
        "ElementAvanceretSammenligning": "Sammenligningsfelt",
        "ElementBruger": "Brugervælger",
        "ElementCPROpslag": "CPR-Opslag",
        "ElementCVROpslag": "CVR-Opslag",
        "ElementSamtykke": "Samtykkefelt",
        "ElementPhone": "Telefonfelt",
        "ElementUnderskrift": "Underskriftfelt",
        "ElementAdresse": "Adressefelt",
        "ElementAfstand": "Afstandsfelt",
        "ElementGisKort": "GIS-Kort",
        "ElementMatrikel": "Matrikelvælger",
        "ElementBooking": "Bookingelement",
        "ElementDagTimeAntal": "Dag- og timeantal",
        "ElementDagAntal": "Dagantal",
        "ElementTime": "Klokkeslæt",
        "ElementPosteringSumAar": "Brugerpostering liste",
        "ElementTimeAntal": "Timeantal",
        "ElementTimedagpenge": "Timedagpenge",
        "ElementTable": "Tabel",
        "ElementHeadline": "Overskrift",
        "ElementStandardTekst": "Standardtekst",
        "ElementUniktId": "Unik ID-felt",
        "ElementImageCrop": "Billedefelt",
        "ElementUpload": "Filupload-felt",
        "ElementHelpDocument": "Hjælpedokument",
        "ElementLink": "Link-felt",
        "ElementQRCode": "QR Kode",
        "ElementVideo": "Video-felt",
        "ElementFirma": "Virksomhedsoplysninger",
        "ElementAPI": "API-felt"
    }
    
    exclude_types = {"ElementEkstraLinjer", "ElementContainer", "ElementRoot"}

    blanketter = data.get('ProcesData', {}).get('Blanketter', [])
    typenames = set()
    
    for blanket in blanketter:
        try:
            json_data = json.loads(blanket.get('Json', '{}'))
            items = json_data.get('Root', {}).get('Elements', [])
            recursive_parse_elements(items, typenames_translation, typenames, exclude_types)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

    return ", ".join(sorted(typenames))

def classify_activities(data):

    if not data:
        logging.warning("Ingen data til dokumentation.")
        return []

    activities = data.get('ProcesData', {}).get('Aktiviteter', [])
    total_activities = len(activities)

    activity_by_id = {activity.get('Id'): activity for activity in activities}

    godkender_mapping = {}
    for activity in activities:
        activity_id = activity.get('Id')
        for condition in activity.get('Betingelser', []):
            if 'GodkenderAktivitetId' in condition and not condition.get('Godkendt', False):
                godkender_id = condition['GodkenderAktivitetId']
                if godkender_id not in godkender_mapping:
                    godkender_mapping[godkender_id] = []
                if activity_id not in godkender_mapping[godkender_id]:
                    godkender_mapping[godkender_id].append(activity_id)

    classifications = []

    for idx, activity in enumerate(activities):
        activity_id = activity.get('Id')
        data_handler = activity.get('AktivitetDatabehandler', [])
        blanket_view = activity.get('AktivitetBlanketVisning', [])
        skabelon_settings = activity.get('AktivitetSkabelonSettings', {})
        benyt_signering = skabelon_settings.get('BenytSignering', False)
        dataaflevering_info = []

        if data_handler:
            type = "Dataaflevering"
        elif not data_handler and not blanket_view:
            type = "Tom aktivitet"
        elif activity_id in godkender_mapping:
            type = "Godkend"
        else:
            type = "Udfyld"

        friendly_name = activity.get('FriendlyName')
        if not friendly_name:
            friendly_name = 'Unavngiven aktivitet'

        if type == "Tom aktivitet":
            if friendly_name.lower() == "none" and idx == total_activities - 1:
                friendly_name = "Slut"
            elif friendly_name == "Unavngiven aktivitet" and idx == total_activities - 1:
                friendly_name = "Unavngiven aktivitet (Slut)"

        if type == "Udfyld" and benyt_signering:
            friendly_name += " (Inkl. signering)"

        if type == "Dataaflevering":
            dataaflevering_info = [f"\t- {handler.get('DatabehandlerNavn', '')}: {handler.get('Navn', '')}" for handler in data_handler]
            if dataaflevering_info:
                friendly_name += "\n" + "\n".join(dataaflevering_info)
            else:
                friendly_name += "\nIngen dataafleveringsinformation tilgængelig"

        if type == "Godkend":
            referenced_activities = godkender_mapping.get(activity_id, [])
            referenced_names = [activity_by_id[ref].get('FriendlyName') for ref in referenced_activities if ref in activity_by_id]
            if referenced_names:
                friendly_name += f" (Afviser til {', '.join(referenced_names)})"

        classifications.append(f"{type}: {friendly_name}")

    return classifications

def extract_ekstra_info(data):

    værdilister = []
    beskedskabeloner = []
    for blanket in data.get('ProcesData', {}).get('Blanketter', []):
        json_data = json.loads(blanket.get('Json', '{}'))
        værdilistenavn = json_data.get('ValgtVaerdilisteNavn', None)
        if værdilistenavn:
            værdilister.append(f"værdilisten '{værdilistenavn}'")
    
    beskedskabeloner = []
    for template in data.get('MailTemplate', []):
        navn = template.get('Navn', None)
        formatted_navn = f"beskedskabelonen '{navn}'"
        if navn and formatted_navn not in beskedskabeloner:
            beskedskabeloner.append(formatted_navn)
    
    combined = værdilister + beskedskabeloner
    if combined:
        info = ", ".join(combined)
        return f"Løsningen anvender {info}"
    else:
        return "Ingen værdilister eller beskedskabeloner."

def main():
    st.title('Speciale Demo: JSON-Til-Tekst')
    st.markdown("###")
    st.subheader('Upload din JSON fil')
    uploaded_file = st.file_uploader("Træk din JSON fil ned i feltet eller vælg 'Browse files' for at uploade din arbejdsgang-JSON", type=['json'])

    if uploaded_file is not None:
        data = json.load(uploaded_file)
        if data:
            løsning_navn, beskrivelse, opstart_text, antal_blanketter, felter_anvendt, ekstra_info = extract_løsning_info(data)
            classified_activities = classify_activities(data)
        st.markdown("###")    
        st.subheader("Beskriv din løsning")
        beskrivelse_text = st.text_area("Her kan du tilføje en beskrivels af din løsning, eller uddybe den der allerede er angivet i XFlow", value=beskrivelse)

        head = (
            f"{løsning_navn}\n\n"
        )
        body = (
            "\n\n"
            f"**Beskrivelse:** {beskrivelse_text}\n\n"
            f"**Opstartes:** {opstart_text}\n\n"
            f"**Antal blanketter:** {antal_blanketter}\n\n"
            f"**Felter anvendt:** {felter_anvendt}\n\n"
            f"**Ekstra information:** {ekstra_info}\n\n"
            f"**Aktiviteter**\n"
            + "\n".join(f"- {activity.strip()}" if ":" not in activity else f"  - {activity.strip()}" for activity in classified_activities)
        )

        st.markdown("###")

        if st.button("Lav en beskrivelse af min JSON"):

            styled_output = f"""<div style="background-color: #f8f9fa; border-left: 5px solid #007BFF; padding: 10px; margin: 10px 0; border-radius: 5px;"><h3>{head}</h3>{body}</div>"""
            st.markdown(styled_output, unsafe_allow_html=True)

            if st.button("Tryk her for at kopiere beskrivelsen til din udklipsholder"):
                pyperclip.copy(styled_output)
                
            st.button("Tryk her for at poste din løsning i Community")
            
        else:
            st.markdown("*Når du trykker på knappen, vil der blive dannet en beskrivelse af din JSON.*")

if __name__ == "__main__":
    main()