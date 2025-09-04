import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from io import StringIO

# 1️⃣ Soutěže ručně zadané
souteze = pd.DataFrame([
    {"URL_REQ": "ca4833f5-5c2a-4737-85eb-eb884a7f1669", "název": "8.liga - OP II.třídy muži", "zkratka": "Muži", "kategorie": "Muzi", "pořadí": 1},
    {"URL_REQ": "25eb6e79-1ee7-4f37-b009-3e8ad82dd9a8", "název": "KP mladšího dorostu U 17", "zkratka": "Ml. dorost", "kategorie": "Ml_dorost", "pořadí": 3},
    {"URL_REQ": "7ed63c5b-135b-446e-a7fd-5970a7a42f79", "název": "OP mladších žáků", "zkratka": "Ml. žáci", "kategorie": "Ml_zaci", "pořadí": 6},
    {"URL_REQ": "601ae6ee-b2ad-481e-b65c-c3213628dc14", "název": "OP starší přípravky", "zkratka": "St. přípravka", "kategorie": "St_pripravka", "pořadí": 7},
    {"URL_REQ": "81c78fe9-035d-4e09-9a8f-5d4a6523e635", "název": "OP mladší přípravky", "zkratka": "Ml. přípravka", "kategorie": "Ml_pripravka", "pořadí": 8},
    {"URL_REQ": "43013500-b4b2-4fe4-a7af-a32b48e2dd4a", "název": "OP minipřípravky", "zkratka": "Mini přípravka", "kategorie": "Mini_pripravka", "pořadí": 9},    
    {"URL_REQ": "92a2e0ec-d85a-4b75-89fc-73fa15062eff", "název": "Pohár OFS muži", "zkratka": "Muži", "kategorie": "Muzi", "pořadí": 10},
])

utkani_all = []

# 2️⃣ Iterace přes soutěže
for _, row in souteze.iterrows():
    url = f"https://is1.fotbal.cz/souteze/detail-souteze.aspx?req={row['URL_REQ']}&sport=fotbal"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, "html.parser")
        tabulky = soup.find_all("table", class_="soutez-zapasy")

        print(f"\n[{row['zkratka']}] {len(tabulky)} zápasových tabulek na: {url}")

        for idx, table in enumerate(tabulky):
            try:
                html_string = str(table)
                df = pd.read_html(StringIO(html_string))[0]  # <-- Použít StringIO

                # Přeskoč prázdné nebo nekompletní tabulky
                if df.empty or "datum a čas" not in df.columns:
                    continue

                # Čištění a formátování
                df["datum a čas"] = df["datum a čas"].astype(str).str.strip()
                df["Datum utkání"] = pd.to_datetime(df["datum a čas"], format="%d.%m.%Y %H:%M", errors="coerce").dt.date
                df["Čas utkání"] = pd.to_datetime(df["datum a čas"], format="%d.%m.%Y %H:%M", errors="coerce").dt.time
                df["%Date"] = pd.to_datetime(df["datum a čas"], format="%d.%m.%Y %H:%M", errors="coerce").map(lambda x: x.toordinal() if pd.notnull(x) else None)
                df["Timestamp"] = pd.to_datetime(df["datum a čas"], format="%d.%m.%Y %H:%M", errors="coerce")

                df["domácí"] = df["domácí"].astype(str).str.extract(r"^(.*?)\s*\(")[0].fillna(df["domácí"])
                df["hosté"] = df["hosté"].astype(str).str.extract(r"^(.*?)\s*\(")[0].fillna(df["hosté"])
                df["utkání"] = (df["domácí"] + " - " + df["hosté"]).str.replace(",", "")

                df["@Tremesna"] = df["domácí"].str.contains("Třem", na=False) | df["hosté"].str.contains("Třem", na=False)
                df["Soupeř"] = df.apply(lambda x: x["hosté"] if "Třem" in x["domácí"] else x["domácí"], axis=1)
                df["Doma/Venku"] = df["domácí"].str.contains("Třem", na=False).map(lambda x: "D" if x else "V")

                df["název soutěže"] = row["název"]
                df["zkratka soutěže"] = row["zkratka"]
                df["kategorie soutěže"] = row["kategorie"]
                df["pořadí"] = row["pořadí"]

                # poznámka, pokud existuje
                if "pzn." in df.columns:
                    df["poznámka"] = (
                        df["pzn."]
                        .fillna("")  # ← Důležité: nahradí NaN za prázdný řetězec
                        .astype(str)
                        .str.replace("/", "")
                        .str.replace(",", "")
                    )
                else:
                    df["poznámka"] = ""

                df = df.sort_values("%Date", ascending=False)

                utkani_all.append(df)

            except Exception as e:
                print(f"   Tabulka {idx + 1}: chyba při čtení: {e}")

    except Exception as e:
        print(f" Chyba při načítání {url}: {e}")

# 3️⃣ Spojit a uložit výsledky
if utkani_all:
    df_final = pd.concat(utkani_all, ignore_index=True)
    df_final.to_csv("utkani.csv", index=False, encoding="utf-8-sig")
    print(f"\n OK Uloženo {len(df_final)} zápasů do 'utkani.csv'")
 # 4️⃣ Výstup do HTML souborů podle kategorií
    html_header = """<!--HTMLOutput-->
<html>
<head>
<style>
table {
border-collapse: collapse;
width: 100%;
color: #333;
font-family: Helvetica;
font-size: 12px;
text-align: left;
border-radius: 10px;
overflow: hidden;
box-shadow: 0 0 20px;
margin: auto;
margin-top: 50px;
margin-bottom: 50px;
}
th {
background-color: #666666;
color: #ffffff;
font-weight: bold;
padding: 5px;
text-transform: uppercase;
letter-spacing: 1px;
border-top: 1px solid #fff;
border-bottom: 1px solid #ccc;
text-align: left;
}
tr:nth-child(even) td {
background-color:#e0e0e0;
}
tr:hover td {
background-color: #999;
}
td {
background-color: #fff;
padding: 5px;
border: 1px solid #ccc;
font-weight: bold;
}
</style>
</head>
<body>
"""
    html_footer = "</table></body></html>"

    columns_html = {
        "Datum utkání": "Datum",
        "utkání": "Utkání",
        "skóre": "Skóre",
        "hřiště": "Hřiště",
        "poznámka": "Poznámka",
        "název soutěže": "Soutěž"
    }

    for zkratka, df_group in df_final.groupby("kategorie soutěže"):
        df_export = df_group.copy()
        # df_export = df_export[list(columns_html.keys())].rename(columns=columns_html)

        df_export = df_export.sort_values("%Date")

        # Použij přímo sloupec 'datum a čas' s požadovaným formátem
        df_export = df_export[df_export["utkání"].str.contains("Bílá Třemešná", na=False)]
        df_export["Datum"] = df_export["datum a čas"].astype(str).str.strip()

        # Vyber a přejmenuj sloupce
        df_export = df_export[[
            "Datum", "utkání", "skóre", "hřiště", "poznámka", "název soutěže"
        ]].rename(columns={
            "utkání": "Utkání",
            "skóre": "Skóre",
            "hřiště": "Hřiště",
            "poznámka": "Poznámka",
            "název soutěže": "Soutěž"
        })

        #df_export = df_export.sort_values("Datum", ascending=False)

        html_table = df_export.to_html(index=False, border=0, escape=False)
        full_html = html_header + html_table + html_footer

        filename = f"Utkani_{zkratka}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(full_html)

        print(f"[OK] Vytvořen HTML soubor: {filename}")

else:
    print("⚠️ Žádná utkání nebyla nalezena.")

# 5️⃣ Výstup do jednoho HTML souboru - pouze domácí zápasy (hřiště obsahuje "Třemešná")
df_domaci_all = df_final[
    df_final["hřiště"].str.contains("Třemešná", case=False, na=False)
].copy()

# ⚠️ Odebrat zápasy mladších žáků proti Spartě Úpice
mask_mlzaci_upice = (
    (df_domaci_all["kategorie soutěže"] == "Ml_zaci") &
    (df_domaci_all["utkání"].str.contains("Sparta Úpice", case=False, na=False))
)
df_domaci_all = df_domaci_all[~mask_mlzaci_upice]

if not df_domaci_all.empty:
    df_domaci_all["Datum"] = df_domaci_all["datum a čas"].astype(str).str.strip()
    
    df_domaci_all = df_domaci_all.sort_values("%Date")
    
    df_domaci_all = df_domaci_all[[
        "Datum", "utkání", "skóre", "hřiště", "poznámka", "název soutěže"
    ]].rename(columns={
        "utkání": "Utkání",
        "skóre": "Skóre",
        "hřiště": "Hřiště",
        "poznámka": "Poznámka",
        "název soutěže": "Soutěž"
    })



    html_table_domaci = df_domaci_all.to_html(index=False, border=0, escape=False)
    full_html_domaci = html_header + html_table_domaci + html_footer

    filename_domaci = "Utkani_DOMA.html"
    with open(filename_domaci, "w", encoding="utf-8") as f:
        f.write(full_html_domaci)

    print(f"[OK] Vytvořen společný HTML soubor s domácími zápasy (hřiště Třemešná): {filename_domaci}")
