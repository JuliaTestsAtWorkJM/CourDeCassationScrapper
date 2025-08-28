import requests
import pandas as pd
from datetime import date, timedelta
import os
import sys
import traceback

def main():
    try:
        # --- Step 1: Fetch data from Judilibre API ---
        url = "https://www.courdecassation.fr/recherche-judilibre-api"
        params = {
            "search_api_fulltext": "arbitrage",
            "date_du": "",
            "date_au": "",
            "judilibre_juridiction": "all",
            "op": "Rechercher sur judilibre"
        }

        print("Fetching data...")
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()

        # --- Step 2: Extract results ---
        results = []
        for item in data.get("results", []):
            case_id = item.get("id")
            case_url = f"https://www.courdecassation.fr/judilibre/{case_id}"
            results.append({
                "id": case_id,
                "title": item.get("title"),
                "url": case_url,
                "date": item.get("date"),
                "juridiction": item.get("juridiction"),
                "summary": (item.get("text") or "")[:200]  # preview
            })

        df_today = pd.DataFrame(results)

        # --- Step 3: Save today’s CSV ---
        today = date.today()
        filename_today = f"judilibre_{today}.csv"
        df_today.to_csv(filename_today, index=False, encoding="utf-8")
        print(f"Saved {filename_today}")

        # --- Step 4: Compare with yesterday ---
        yesterday = today - timedelta(days=1)
        filename_yesterday = f"judilibre_{yesterday}.csv"
        report_filename = f"changes_{today}.md"

        if os.path.exists(filename_yesterday):
            print("Comparing with yesterday’s file...")
            df_yesterday = pd.read_csv(filename_yesterday)

            # New & removed
            new_cases = set(df_today["id"]) - set(df_yesterday["id"])
            removed_cases = set(df_yesterday["id"]) - set(df_today["id"])

            # Modified cases
            common_ids = set(df_today["id"]) & set(df_yesterday["id"])
            changed_cases = []

            for case_id in common_ids:
                row_today = df_today[df_today["id"] == case_id].iloc[0]
                row_yesterday = df_yesterday[df_yesterday["id"] == case_id].iloc[0]

                diffs = {}
                for col in ["title", "date", "juridiction", "summary"]:
                    if str(row_today[col]) != str(row_yesterday[col]):
                        diffs[col] = {
                            "yesterday": row_yesterday[col],
                            "today": row_today[col]
                        }

                if diffs:
                    changed_cases.append((case_id, diffs))

            # --- Step 5: Write Markdown report with clickable links ---
            with open(report_filename, "w", encoding="utf-8") as f:
                f.write(f"# Changes for {today}\n\n")

                # New cases
                f.write("## 🟢 New cases since yesterday\n\n")
                if new_cases:
                    f.write("| Date | Juridiction | Title |\n")
                    f.write("|------|------------|-------|\n")
                    for case_id in new_cases:
                        row = df_today[df_today["id"] == case_id].iloc[0]
                        title_md = f"[{row['title']}]({row['url']})"
                        f.write(f"| {row['date']} | {row['juridiction']} | {title_md} |\n")
                else:
                    f.write("_No new cases_\n")

                f.write("\n")

                # Removed cases
                f.write("## 🔴 Removed cases since yesterday\n\n")
                if removed_cases:
                    f.write("| Date | Juridiction | Title |\n")
                    f.write("|------|------------|-------|\n")
                    for case_id in removed_cases:
                        row = df_yesterday[df_yesterday["id"] == case_id].iloc[0]
                        title_md = f"[{row['title']}]({row['url']})"
                        f.write(f"| {row['date']} | {row['juridiction']} | {title_md} |\n")
                else:
                    f.write("_No removed cases_\n")

                f.write("\n")

                # Modified cases
                f.write("## 🟡 Modified cases since yesterday\n\n")
                if changed_cases:
                    for case_id, diffs in changed_cases:
                        row = df_today[df_today["id"] == case_id].iloc[0]
                        f.write(f"### [{row['title']}]({row['url']}) (Case ID: {case_id})\n\n")
                        for field, change in diffs.items():
                            f.write(f"- **{field}** changed:\n")
                            f.write(f"    - Yesterday: {change['yesterday']}\n")
                            f.write(f"    - Today: {change['today']}\n\n")
                else:
                    f.write("_No modified cases_\n")

            print(f"Markdown report saved as {report_filename}")
        else:
            print("No yesterday file found — skipping comparison.")

    except Exception as e:
        print("ERROR: Something went wrong while running the scraper.")
        print(traceback.format_exc())
        sys.exit(1)  # Exit with non-zero code to trigger GitHub Actions failure

if __name__ == "__main__":
    main()
