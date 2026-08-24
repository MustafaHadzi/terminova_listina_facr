import pandas as pd
import numpy as np
import requests

from bs4 import BeautifulSoup
from io import StringIO


# ============================================================
# Veřejná IP
# ============================================================

try:
    ip = requests.get("https://ifconfig.me", timeout=10).text.strip()
    print("Aktuální veřejná IP:", ip)
except Exception as e:
    print("Nepodařilo se zjistit veřejnou IP:", e)


# ============================================================
# 1. Soutěže
# ============================================================

souteze = pd.DataFrame([
    {
        "URL_REQ": "234e4354-c975-4caf-b3b2-27338679374b",
        "název": "7.liga - B.třída muži",
        "zkratka": "Muži",
        "kategorie": "Muzi",
        "pořadí": 1
    },
    {
        "URL_REQ": "589dae8f-1eb2-46d1-b6e4-e45a8f290dab",
        "název": "KP mladšího dorostu U 17",
        "zkratka": "Ml. dorost",
        "kategorie": "Ml_dorost",
        "pořadí": 3
    },
    {
        "URL_REQ": "8d3b98c2-fe4f-4f9e-a651-780d7fb297ad",
        "název": "OP mladších žáků",
        "zkratka": "Ml. žáci",
        "kategorie": "Ml_zaci",
        "pořadí": 6
    },
    {
        "URL_REQ": "12f22a94-83be-46ad-89dd-14c82f7c5cb2",
        "název": "OP starší přípravky",
        "zkratka": "St. přípravka",
        "kategorie": "St_pripravka",
        "pořadí": 7
    },
    {
        "URL_REQ": "0642cca4-a12a-4a06-866c-34eea323d418",
        "název": "OP mladší přípravky",
        "zkratka": "Ml. přípravka",
        "kategorie": "Ml_pripravka",
        "pořadí": 8
    },
    {
        "URL_REQ": "22abe66b-8006-434b-9fba-87e594cdd4b5",
        "název": "OP minipřípravky",
        "zkratka": "Mini přípravka",
        "kategorie": "Mini_pripravka",
        "pořadí": 9
    },

    # {
    #     "URL_REQ": "92a2e0ec-d85a-4b75-89fc-73fa15062eff",
    #     "název": "Pohár OFS muži",
    #     "zkratka": "Muži",
    #     "kategorie": "Muzi",
    #     "pořadí": 10
    # },
])


utkani_all = []

SPECIAL_TEAM = "TJ Dvůr Králové n. L. B (9)"


# ============================================================
# 2. Načtení jednotlivých soutěží
# ============================================================

for _, row in souteze.iterrows():

    url = (
        "https://is1.fotbal.cz/souteze/detail-souteze.aspx"
        f"?req={row['URL_REQ']}&sport=fotbal"
    )

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:

        resp = requests.get(
            url,
            headers=headers,
            timeout=20,
            verify=False
        )

        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        tabulky = soup.find_all(
            "table",
            class_="soutez-zapasy"
        )

        print(
            f"\n[{row['zkratka']}] "
            f"{len(tabulky)} zápasových tabulek na: {url}"
        )

        # ----------------------------------------------------
        # QLIK:
        #
        # for j=1 to 40
        #
        # ----------------------------------------------------

        for idx, table in enumerate(tabulky[:40], start=1):

            try:

                html_string = str(table)

                df = pd.read_html(
                    StringIO(html_string)
                )[0]

                # --------------------------------------------
                # Přeskočit neplatnou tabulku
                # --------------------------------------------

                if (
                    df.empty
                    or "datum a čas" not in df.columns
                    or "domácí" not in df.columns
                    or "hosté" not in df.columns
                ):
                    continue


                # ====================================================
                # PŮVODNÍ hodnoty týmů
                #
                # Musíme je zachovat, protože Qlik testuje například:
                #
                # TJ Dvůr Králové n. L. B (9)
                #
                # ještě před Subfield(..., ' (', 1)
                # ====================================================

                domaci_raw = (
                    df["domácí"]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                )

                hoste_raw = (
                    df["hosté"]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                )


                # ====================================================
                # QLIK:
                #
                # Where not wildmatch(domácí, 'VOLNO*')
                #   and not wildmatch(hosté, 'VOLNO*');
                # ====================================================

                mask_volno = (
                    domaci_raw.str.startswith(
                        "VOLNO",
                        na=False
                    )
                    |
                    hoste_raw.str.startswith(
                        "VOLNO",
                        na=False
                    )
                )

                df = df.loc[~mask_volno].copy()

                if df.empty:
                    continue

                domaci_raw = domaci_raw.loc[df.index]
                hoste_raw = hoste_raw.loc[df.index]


                # ====================================================
                # DATUM A ČAS
                # ====================================================

                df["datum a čas"] = (
                    df["datum a čas"]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                )

                dt = pd.to_datetime(
                    df["datum a čas"],
                    format="%d.%m.%Y %H:%M",
                    errors="coerce"
                )


                # ----------------------------------------------------
                # Qlik používá jako nulové datum 30.12.1899
                # ----------------------------------------------------

                qlik_epoch = pd.Timestamp("1899-12-30")


                # ----------------------------------------------------
                # QLIK:
                #
                # Num(Floor(Timestamp#(...))) as %Date
                # ----------------------------------------------------

                df["%Date"] = (
                    dt.dt.normalize() - qlik_epoch
                ).dt.days


                # ----------------------------------------------------
                # QLIK:
                #
                # Date(
                #   Num(Floor(Timestamp#(...)))
                # ) as "Datum utkání"
                # ----------------------------------------------------

                df["Datum utkání"] = dt.dt.date


                # ----------------------------------------------------
                # QLIK:
                #
                # Num(Timestamp#(...)) as Timestamp
                # ----------------------------------------------------

                df["Timestamp"] = (
                    (dt.dt.normalize() - qlik_epoch).dt.days
                    +
                    (
                        dt.dt.hour * 3600
                        + dt.dt.minute * 60
                        + dt.dt.second
                    ) / 86400
                )


                # ----------------------------------------------------
                # QLIK:
                #
                # Time(Frac(Timestamp#(...)))
                # ----------------------------------------------------

                df["Čas utkání"] = dt.dt.time


                # ====================================================
                # DOMÁCÍ / HOSTÉ
                # ====================================================

                # ----------------------------------------------------
                # QLIK:
                #
                # Subfield(domácí,' (', 1)
                # ----------------------------------------------------

                df["domácí"] = (
                    domaci_raw
                    .str.split(
                        " (",
                        n=1,
                        regex=False
                    )
                    .str[0]
                    .str.strip()
                )


                # ----------------------------------------------------
                # QLIK:
                #
                # Subfield(hosté,' (', 1)
                # ----------------------------------------------------

                df["hosté"] = (
                    hoste_raw
                    .str.split(
                        " (",
                        n=1,
                        regex=False
                    )
                    .str[0]
                    .str.strip()
                )


                # ====================================================
                # UTKÁNÍ
                # ====================================================

                # ----------------------------------------------------
                # QLIK:
                #
                # Replace(
                #   Subfield(domácí,' (',1)
                #   &' - '&
                #   Subfield(hosté,' (',1),
                #   ',',
                #   ''
                # ) as utkání
                # ----------------------------------------------------

                df["utkání"] = (
                    df["domácí"]
                    + " - "
                    + df["hosté"]
                ).str.replace(
                    ",",
                    "",
                    regex=False
                )


                # ====================================================
                # @Tremesna
                # ====================================================

                oba_tymy_raw = (
                    domaci_raw
                    + " - "
                    + hoste_raw
                )

                # ----------------------------------------------------
                # QLIK:
                #
                # if(
                #   SubStringCount(
                #       domácí &' - '& hosté,
                #       'Třem'
                #   )>0
                #   or
                #   SubStringCount(
                #       domácí &' - '& hosté,
                #       'TJ Dvůr Králové n. L. B (9)'
                #   )>0,
                #   1,
                #   0
                # ) as @Tremesna
                # ----------------------------------------------------

                mask_tremesna = (
                    oba_tymy_raw.str.contains(
                        "Třem",
                        regex=False,
                        na=False
                    )
                    |
                    oba_tymy_raw.str.contains(
                        SPECIAL_TEAM,
                        regex=False,
                        na=False
                    )
                )

                df["@Tremesna"] = (
                    mask_tremesna.astype(int)
                )


                # ====================================================
                # JE TŘEMEŠNÁ DOMÁCÍ?
                # ====================================================

                mask_domaci = (
                    domaci_raw.str.contains(
                        "Třem",
                        regex=False,
                        na=False
                    )
                    |
                    domaci_raw.str.contains(
                        SPECIAL_TEAM,
                        regex=False,
                        na=False
                    )
                )


                # ====================================================
                # SOUPEŘ
                # ====================================================

                # ----------------------------------------------------
                # QLIK:
                #
                # if(
                #   SubStringCount(domácí,'Třem')>0
                #   or
                #   SubStringCount(
                #       domácí,
                #       'TJ Dvůr Králové n. L. B (9)'
                #   )>0,
                #
                #   Subfield(hosté,' (',1),
                #   Subfield(domácí,' (',1)
                #
                # ) as Soupeř
                # ----------------------------------------------------

                df["Soupeř"] = np.where(
                    mask_domaci,
                    df["hosté"],
                    df["domácí"]
                )


                # ====================================================
                # DOMA / VENKU
                # ====================================================

                # ----------------------------------------------------
                # QLIK:
                #
                # if(..., 'D', 'V')
                # ----------------------------------------------------

                df["Doma/Venku"] = np.where(
                    mask_domaci,
                    "D",
                    "V"
                )


                # ====================================================
                # INFORMACE O SOUTĚŽI
                # ====================================================

                df["název soutěže"] = row["název"]
                df["zkratka soutěže"] = row["zkratka"]
                df["kategorie soutěže"] = row["kategorie"]
                df["pořadí"] = row["pořadí"]


                # ====================================================
                # HŘIŠTĚ
                # ====================================================

                # ----------------------------------------------------
                # QLIK:
                #
                # if(
                #   SubStringCount(
                #       domácí,
                #       'TJ Dvůr Králové n. L. B (9)'
                #   ),
                #   'B.Třemešná',
                #   hřiště
                # ) as hřiště
                # ----------------------------------------------------

                mask_special_domaci = (
                    domaci_raw.str.contains(
                        SPECIAL_TEAM,
                        regex=False,
                        na=False
                    )
                )

                if "hřiště" in df.columns:

                    df["hřiště"] = np.where(
                        mask_special_domaci,
                        "B.Třemešná",
                        df["hřiště"].fillna("")
                    )

                else:

                    df["hřiště"] = np.where(
                        mask_special_domaci,
                        "B.Třemešná",
                        ""
                    )


                # ====================================================
                # POZNÁMKA
                # ====================================================

                # ----------------------------------------------------
                # QLIK:
                #
                # Replace(
                #   Replace(pzn., '/', ''),
                #   ',',
                #   ''
                # ) as poznámka
                # ----------------------------------------------------

                if "pzn." in df.columns:

                    df["poznámka"] = (
                        df["pzn."]
                        .fillna("")
                        .astype(str)
                        .str.replace(
                            "/",
                            "",
                            regex=False
                        )
                        .str.replace(
                            ",",
                            "",
                            regex=False
                        )
                    )

                else:

                    df["poznámka"] = ""


                # ====================================================
                # Odpovídá:
                #
                # Concatenate(Utkani)
                # ====================================================

                utkani_all.append(df)

            except Exception as e:

                print(
                    f"   Tabulka {idx}: "
                    f"chyba při čtení: {e}"
                )

    except Exception as e:

        print(
            f"Chyba při načítání {url}: {e}"
        )


# ============================================================
# 3. Spojit výsledky
# ============================================================

if not utkani_all:

    print("⚠️ Žádná utkání nebyla nalezena.")

else:

    df_final = pd.concat(
        utkani_all,
        ignore_index=True
    )


    # --------------------------------------------------------
    # Seřazení
    # --------------------------------------------------------

    df_final = df_final.sort_values(
        ["%Date", "Timestamp"],
        ascending=True
    )


    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    df_final.to_csv(
        "utkani.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print(
        f"\nOK Uloženo {len(df_final)} zápasů "
        "do 'utkani.csv'"
    )


    # ========================================================
    # 4. HTML CSS
    # ========================================================

    html_header = """<!--HTMLOutput-->
<html>
<head>
<meta charset="utf-8">
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
    background-color: #e0e0e0;
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

    html_footer = """
</body>
</html>
"""


    # ========================================================
    # 5. HTML podle kategorií
    # ========================================================

    for kategorie, df_group in df_final.groupby(
        "kategorie soutěže"
    ):

        df_export = df_group.copy()


        # ----------------------------------------------------
        # Původně jsi měl:
        #
        # str.contains("Bílá Třemešná")
        #
        # Teď používáme stejnou logiku jako Qlik:
        #
        # @Tremesna = 1
        #
        # takže se zahrne i speciální tým:
        #
        # TJ Dvůr Králové n. L. B (9)
        # ----------------------------------------------------

        df_export = df_export[
            df_export["@Tremesna"] == 1
        ].copy()


        df_export = df_export.sort_values(
            ["%Date", "Timestamp"]
        )


        df_export["Datum"] = (
            df_export["datum a čas"]
            .astype(str)
            .str.strip()
        )


        df_export = df_export[[
            "Datum",
            "utkání",
            "skóre",
            "hřiště",
            "poznámka",
            "název soutěže"
        ]].rename(columns={
            "utkání": "Utkání",
            "skóre": "Skóre",
            "hřiště": "Hřiště",
            "poznámka": "Poznámka",
            "název soutěže": "Soutěž"
        })


        html_table = df_export.to_html(
            index=False,
            border=0,
            escape=False
        )


        full_html = (
            html_header
            + html_table
            + html_footer
        )


        filename = f"Utkani_{kategorie}.html"

        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(full_html)


        print(
            f"[OK] Vytvořen HTML soubor: "
            f"{filename}"
        )


    # ========================================================
    # 6. Všechny domácí zápasy
    # ========================================================

    # Používáme Doma/Venku = D.
    #
    # Je to přesnější než hledání textu
    # "Třemešná" ve sloupci hřiště.

    df_domaci_all = df_final[
        (df_final["@Tremesna"] == 1)
        &
        (df_final["Doma/Venku"] == "D")
    ].copy()


    # --------------------------------------------------------
    # Odebrat zápasy mladších žáků proti Spartě Úpice
    # --------------------------------------------------------

    mask_mlzaci_upice = (
        (
            df_domaci_all["kategorie soutěže"]
            == "Ml_zaci"
        )
        &
        (
            df_domaci_all["utkání"]
            .str.contains(
                "Sparta Úpice",
                case=False,
                na=False
            )
        )
    )


    df_domaci_all = df_domaci_all[
        ~mask_mlzaci_upice
    ].copy()


    # ========================================================
    # HTML DOMA
    # ========================================================

    if not df_domaci_all.empty:

        df_domaci_all = df_domaci_all.sort_values(
            ["%Date", "Timestamp"]
        )


        df_domaci_all["Datum"] = (
            df_domaci_all["datum a čas"]
            .astype(str)
            .str.strip()
        )


        df_domaci_all = df_domaci_all[[
            "Datum",
            "utkání",
            "skóre",
            "hřiště",
            "poznámka",
            "název soutěže"
        ]].rename(columns={
            "utkání": "Utkání",
            "skóre": "Skóre",
            "hřiště": "Hřiště",
            "poznámka": "Poznámka",
            "název soutěže": "Soutěž"
        })


        html_table_domaci = (
            df_domaci_all.to_html(
                index=False,
                border=0,
                escape=False
            )
        )


        full_html_domaci = (
            html_header
            + html_table_domaci
            + html_footer
        )


        filename_domaci = "Utkani_DOMA.html"


        with open(
            filename_domaci,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(full_html_domaci)


        print(
            "[OK] Vytvořen společný HTML soubor "
            f"s domácími zápasy: {filename_domaci}"
        )

    else:

        print(
            "Nebyla nalezena žádná domácí utkání."
        )