"""Frontend POC Streamlit : question + ville + top_k, réponse + Sources. Pas d'historique."""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from backend import ask, RagError

st.title("ocrproject9 — chatbot événements (POC)")

question = st.text_input(
    "Ta question",
    placeholder="Ex : Quels concerts de jazz à Paris ce week-end ?",
)
city = st.text_input("Ville (optionnel, vide = toutes)", value="")
top_k = st.slider("top_k", 1, 10, 5)

if st.button("Chercher"):
    if not question.strip():
        st.warning("Pose une question d'abord.")
    else:
        try:
            with st.spinner("Recherche..."):
                res = ask(question, city=city, top_k=top_k)
            st.subheader("Réponse")
            st.write(res["answer"])
            st.subheader("Sources")
            if not res["sources"]:
                st.info("Aucune source.")
            for d in res["sources"]:
                m = d.metadata
                st.markdown(f"**{m.get('city', '?')}** · score {m.get('score', 0):.2f} · {m.get('date', '')}")
                st.caption(d.page_content[:500])
        except ValueError:
            st.warning("Pose une question d'abord.")
        except RagError as e:
            if getattr(e, "status_code", None) == 401:
                st.error("Token RAG invalide (401). Vérifie RAGIFIX_API_TOKEN.")
            elif getattr(e, "status_code", None) and e.status_code >= 500:
                st.error(f"Le RAG a renvoyé une erreur {e.status_code}. Réessaie plus tard.")
            else:
                st.error(f"Erreur : {e}")
