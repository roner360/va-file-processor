import streamlit as st
import fitz  # PyMuPDF
import re
import pandas as pd
import os
from io import BytesIO

# ----------------------------
# CONFIGURAZIONE BASE
# ----------------------------

# Regex per i vari campi
PREZZO_RE = re.compile(r"€\s*([\d.,]+)")
EAN_RE    = re.compile(r"Codici a barre\s*:\s*([0-9A-Z]+)")
QTA_RE    = re.compile(r"Quantità per cartone:\s*([\d]+)")
SKU_RE    = re.compile(r"\b\d{5,6}\b")  # SKU tipo 490550, 180006 ecc.

# Token da ignorare nelle descrizioni
DEFAULT_SKIP_TOKENS = [
    "Catalogo",
    "Ricerca per descrizione",
    "Offerte Web",
    "numero di cartoni",
    "NUOVI ARRIVI",
]

def parse_catalog_from_bytes(
    pdf_bytes: bytes,
    pdf_name: str,
    category_tokens=None,
    extra_skip_tokens=None,
    try_sku_from_text: bool = True,
) -> pd.DataFrame:
    """
    Versione per Streamlit:
    prende i bytes del PDF (da file uploader) e il nome file,
    ed estrae: prezzo; ean; nome; quantita_cartone; sku; nome_file_pdf
    """

    if category_tokens is None:
        category_tokens = []  # Es. ["AMMORBIDENTI"], ["LIQUIDO PIATTI"], ...
    if extra_skip_tokens is None:
        extra_skip_tokens = []

    # Apri il PDF da bytes
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    base_name = os.path.basename(pdf_name)

    skip_tokens = DEFAULT_SKIP_TOKENS + category_tokens + extra_skip_tokens

    records = []

    for page in doc:
        lines = page.get_text().splitlines()
        i = 0

        while i < len(lines):
            line = lines[i]
            m_q = QTA_RE.search(line)
            if not m_q:
                i += 1
                continue

            quantita = int(m_q.group(1))
            nome_parts = []
            prezzo = None
            ean = None

            j = i + 1
            while j < len(lines):
                l = lines[j].strip()

                # nuova scheda prodotto
                if "Quantità per cartone:" in l and j != i + 1:
                    break

                pm = PREZZO_RE.search(l)
                if pm:
                    prezzo = pm.group(1)

                em = EAN_RE.search(l)
                if em:
                    ean = em.group(1)

                if l and not any(tok in l for tok in skip_tokens):
                    if not l.startswith("Cartoni per"):
                        nome_parts.append(l)

                j += 1

            if nome_parts and prezzo:
                nome = " ".join(nome_parts)

                # pulizia pezzi logistici se rimasti dentro
                for tok in ["Cartoni per strato", "Cartoni per pallet", "numero di cartoni"]:
                    if tok in nome:
                        nome = nome.split(tok)[0].strip()

                # normalizza spazi
                nome = " ".join(nome.split())

                records.append({
                    "prezzo": prezzo,
                    "ean": ean,
                    "nome": nome,
                    "quantita_cartone": quantita,
                    "sku": None,  # la compiliamo dopo se riusciamo
                    "nome_file_pdf": base_name,
                })

            i = j

    # opzionale: prova ad agganciare gli SKU in ordine
    if try_sku_from_text and records:
        all_text = "".join(page.get_text() for page in doc)
        skus = SKU_RE.findall(all_text)
        if len(skus) == len(records):
            for rec, sku in zip(records, skus):
                rec["sku"] = sku

    df = pd.DataFrame(
        records,
        columns=["prezzo", "ean", "nome", "quantita_cartone", "sku", "nome_file_pdf"]
    )
    return df


def clean_name(n: str) -> str:
    if not isinstance(n, str):
        return n
    if "€" in n:
        n = n.split("€")[0].strip()
    if "Codici a barre" in n:
        n = n.split("Codici a barre")[0].strip()
    return " ".join(n.split())


# Mappatura categorie come nel tuo script originale
CATEGORY_MAP = {
    "ammorbidenti.pdf": ["AMMORBIDENTI"],
    "bibite.pdf": ["BIBITE GASSATE", "BIBITE"],
    "liquido piatti.pdf": ["LIQUIDO PIATTI"],
    "liquido pavimenti.pdf": ["LIQUIDO PAVIMENTI"],
    "candeggine.pdf": ["CANDEGGINE & AMMONIACHE"],
    "perborato.pdf": ["PERBORATO & SBIANCANTI"],
    # ... aggiungi qui altri file/categorie se ti servono
}


# ============================
#       APP STREAMLIT
# ============================

st.set_page_config(page_title="VA - Parser Cataloghi PDF")

st.title("VA – Parser Cataloghi PDF")
st.write("Carica un PDF del catalogo, lo trasformo in CSV pronto da scaricare.")

uploaded_file = st.file_uploader("Carica il PDF", type=["pdf"])

if uploaded_file is not None:
    st.info(f"Hai caricato: {uploaded_file.name}")

    pdf_bytes = uploaded_file.read()

    # Prendo le category_tokens in base al nome file (come nel tuo script)
    category_tokens = CATEGORY_MAP.get(uploaded_file.name, [])

    with st.spinner("Elaboro il PDF..."):
        df = parse_catalog_from_bytes(
            pdf_bytes,
            pdf_name=uploaded_file.name,
            category_tokens=category_tokens
        )
        df["nome"] = df["nome"].apply(clean_name)

    if df.empty:
        st.warning("Nessun prodotto trovato nel PDF. Controlla che il formato sia come quello previsto.")
    else:
        st.success(f"Elaborazione completata! Prodotti trovati: {len(df)}")

        st.subheader("Anteprima dati")
        st.dataframe(df.head(50))

        # Esporta in CSV (come nel tuo script originale, separatore ';')
        csv_buffer = BytesIO()
        df.to_csv(csv_buffer, sep=";", index=False)
        csv_buffer.seek(0)

        output_name = f"{uploaded_file.name}.csv"

        st.download_button(
            label="📥 Scarica CSV",
            data=csv_buffer,
            file_name=output_name,
            mime="text/csv"
        )

else:
    st.info("Carica un file PDF per iniziare.")

