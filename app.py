import streamlit as st

st.set_page_config(page_title="VA - Elaboratore di file")

st.title("VA – Elaboratore di file")
st.write("Carica un file, lo elaboro con Python e scarica il risultato.")

uploaded_file = st.file_uploader("Carica il file", type=None)

if uploaded_file is not None:
    st.info(f"Hai caricato: {uploaded_file.name}")

    # Contenuto del file in bytes
    file_bytes = uploaded_file.read()

    # -----------------------------
    # QUI METTI LA LOGICA DEL TUO VA
    # Per ora rimandiamo indietro lo stesso file
    result_bytes = file_bytes
    output_name = f"output_{uploaded_file.name}"
    # -----------------------------

    st.success("Elaborazione completata!")

    st.download_button(
        label="Scarica il file elaborato",
        data=result_bytes,
        file_name=output_name,
        mime="application/octet-stream",
    )
