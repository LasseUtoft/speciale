import json
import logging
import streamlit as st

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_løsning_info(data):
    løsning_navn = data.get('Name', 'Navn ikke tilgængelig')
    beskrivelse = data.get('Description', 'Beskrivelse ikke tilgængelig')
    
    ##opstart
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

    return løsning_navn, beskrivelse, opstart_text, antal_blanketter, felter_anvendt, ekstra_info

def parse_felter_anvendt(data):
    """ Parse and return field types used in blanketter """
    typenames_translation = {
        "ElementGroup": "Gruppe",
        "ElementTextfield": "Tekstfelt",
        "ElementNumber": "Talfelt",
        "ElementMultiSelect": "Multivælger",
        "ElementPerson": "Personfelt",
        "ElementDate": "Datofelt",
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
    
    blanketter = data.get('ProcesData', {}).get('Blanketter', [])
    typenames = set()
    for blanket in blanketter:
        json_data = json.loads(blanket.get('Json', '{}'))
        items = json_data.get('Root', {}).get('Elements', [])
        for item in items:
            typename = item.get('Typename', 'Unknown')
            translated_typename = typenames_translation.get(typename, typename)
            typenames.add(translated_typename)
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

        if data_handler:
            type = "Dataaflevering"
        elif not data_handler and not blanket_view:
            type = "Tom aktivitet"
        elif activity_id in godkender_mapping:
            type = "Godkend"
        elif not data_handler:
            type = "Udfyld"
        else:
            type = "Uklassificeret"

        friendly_name = activity.get('FriendlyName', 'Unavngiven aktivitet')

        if type == "Tom aktivitet" and str(friendly_name).lower() == "none" and idx == total_activities - 1:
            friendly_name = "Slut"
        else:
            friendly_name = activity.get('FriendlyName', 'Unavngiven aktivitet')

        if type == "Udfyld" and benyt_signering:
            friendly_name += " (Inkl. signering)"

        if type == "Dataaflevering":
            dataaflevering_info = [f"\t- {handler.get('DatabehandlerNavn', '')}: {handler.get('Navn', '')}" for handler in data_handler]
            friendly_name += "\n" + "\n".join(dataaflevering_info)

        if type == "Godkend":
            referenced_activities = godkender_mapping.get(activity_id, [])
            referenced_names = [activity_by_id[ref].get('FriendlyName') for ref in referenced_activities if ref in activity_by_id]
            if referenced_names:
                friendly_name += f" (Afviser til {', '.join(referenced_names)})"

        classifications.append(f"{type}: {friendly_name}")

    return classifications

def extract_ekstra_info(data):
    """ Extract additional information from blanketter and mail templates """
    værdilister = []
    beskedskabeloner = []
    for blanket in data.get('ProcesData', {}).get('Blanketter', []):
        json_data = json.loads(blanket.get('Json', '{}'))
        værdilistenavn = json_data.get('ValgtVaerdilisteNavn', None)
        if værdilistenavn:
            værdilister.append(f"værdilisten '{værdilistenavn}'")
    
    for template in data.get('MailTemplate', []):
        navn = template.get('Navn', None)
        if navn:
            beskedskabeloner.append(f"beskedskabelonen '{navn}'")
    
    combined = værdilister + beskedskabeloner
    if combined:
        info = ", ".join(combined)
        return f"Løsningen anvender {info}"
    else:
        return "Ingen yderligere information tilgængelig"

def main():
    st.title('Speciale Demo: JSON-Til-Tekst')
    uploaded_file = st.file_uploader("Upload din JSON fil her", type=['json'])

    if uploaded_file is not None:
        data = json.load(uploaded_file)
        if data:
            løsning_navn, beskrivelse, opstart_text, antal_blanketter, felter_anvendt, ekstra_info = extract_løsning_info(data)
            classified_activities = classify_activities(data)
            
            # Display løsningens navn and description
            beskrivelse_text = st.text_area("Skriv en beskrivelse af din løsning", value=beskrivelse)

            output = (
            f"**Løsningens navn**: {løsning_navn}\n\n"
            f"**Beskrivelse:** {beskrivelse_text} {beskrivelse}\n\n"
            f"**Opstartes:** {opstart_text}\n\n"
            f"**Antal blanketter:** {antal_blanketter}\n\n"
            f"**Felter anvendt:** {felter_anvendt}\n\n"
            f"**Ekstra information:** {ekstra_info}\n\n"
            f"**Aktiviteter**\n\n"
            + "\n".join(f"- {activity.strip()}" if ":" not in activity else f"  - {activity.strip()}" for activity in classified_activities)
        )

    if st.button("Lav en beskrivelse af min JSON"):
        # Process data and display
        st.markdown(output)
    else:
        st.write("Når du trykker på knappen, vil der blive dannet en beskrivelse af din JSON.")

if __name__ == "__main__":
    main()

