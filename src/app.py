import os
import sys
import datetime
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from backend import ask, RagError

st.title("ocrproject9 : chatbot événements")

question = st.text_input(
    "Ta question",
    placeholder="Ex : Quels concerts de jazz à Paris ce week-end ?",
)

col_topk, col_city, col_dmin, col_dmax = st.columns([1, 3, 1.3, 1.3])
with col_topk:
    top_k = st.number_input("top_k", min_value=1, max_value=10, value=5, step=1)
with col_city:
    city = st.text_input("Ville", value="", placeholder="Vide = toutes")
with col_dmin:
    date_min = st.date_input("Date min", value=datetime.date.today())
with col_dmax:
    date_max = st.date_input("Date max", value=None)

if st.button("Chercher"):
    if not question.strip():
        st.warning("Pose une question d'abord.")
    else:
        try:
            with st.spinner("Recherche..."):
                res = ask(question, city=city, top_k=int(top_k),
                          date_min=date_min.isoformat() if date_min else "",
                          date_max=date_max.isoformat() if date_max else "")
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
