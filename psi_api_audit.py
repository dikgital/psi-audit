import requests
import csv
import time

API_KEY = "API_KEY"
INPUT_FILE = "urls_.txt"
OUTPUT_FILE = "core_web_vitals_report.csv"

def categorize_lcp(lcp):
    if lcp <= 2.5:
        return "Good"
    elif lcp <= 4.0:
        return "Needs Improvement"
    else:
        return "Poor"

def categorize_inp(inp_ms):
    if inp_ms is None:
        return "Not Available"
    if inp_ms <= 200:
        return "Good"
    elif inp_ms <= 500:
        return "Needs Improvement"
    else:
        return "Poor"

def categorize_cls(cls):
    if cls <= 0.1:
        return "Good"
    elif cls <= 0.25:
        return "Needs Improvement"
    else:
        return "Poor"

def check_core_web_vitals(api_key, url, strategy="mobile"):
    endpoint = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = {
        "url": url,
        "key": api_key,
        "strategy": strategy,
        "category": "performance"
    }

    resp = requests.get(endpoint, params=params)
    if resp.status_code != 200:
        return {"URL": url, "Error": f"{resp.status_code}: {resp.text}"}

    data = resp.json()

    metrics_field = data.get("loadingExperience", {}).get("metrics", {})
    lighthouse = data.get("lighthouseResult", {})

    # Default values
    lcp, inp, cls = None, None, None
    source = "Field (CrUX)"

    # --- 1. Try CrUX (field data)
    if "LARGEST_CONTENTFUL_PAINT_MS" in metrics_field:
        lcp = metrics_field["LARGEST_CONTENTFUL_PAINT_MS"]["percentile"] / 1000
    if "INTERACTION_TO_NEXT_PAINT" in metrics_field:
        inp = metrics_field["INTERACTION_TO_NEXT_PAINT"]["percentile"]
    elif "EXPERIMENTAL_INTERACTION_TO_NEXT_PAINT" in metrics_field:
        inp = metrics_field["EXPERIMENTAL_INTERACTION_TO_NEXT_PAINT"]["percentile"]
    if "CUMULATIVE_LAYOUT_SHIFT_SCORE" in metrics_field:
        cls = metrics_field["CUMULATIVE_LAYOUT_SHIFT_SCORE"]["percentile"] / 100

    # --- 2. Fallback ke Lighthouse (lab data)
    if not lcp or not inp or not cls:
        audits = lighthouse.get("audits", {})
        source = "Lab (Lighthouse)"
        try:
            if not lcp and "largest-contentful-paint" in audits:
                lcp = audits["largest-contentful-paint"]["numericValue"] / 1000
            if not inp and "interactive" in audits:  # INP belum fully ada di Lighthouse, pakai TTI fallback
                inp = audits["interactive"]["numericValue"]
            if not cls and "cumulative-layout-shift" in audits:
                cls = audits["cumulative-layout-shift"]["numericValue"]
        except:
            pass

    # Performance score (selalu dari lab)
    perf_score = None
    try:
        perf_score = lighthouse["categories"]["performance"]["score"] * 100
    except:
        pass

    return {
        "URL": url,
        "Data Source": source,
        "Performance Score": perf_score,
        "LCP (s)": round(lcp, 2) if lcp else None,
        "LCP Category": categorize_lcp(lcp) if lcp else "Not Available",
        "INP (ms)": round(inp) if inp else None,
        "INP Category": categorize_inp(inp),
        "CLS": round(cls, 3) if cls else None,
        "CLS Category": categorize_cls(cls) if cls else "Not Available",
    }

def main():
    with open(INPUT_FILE, "r") as f:
        urls = [u.strip() for u in f if u.strip()]

    results = []
    for url in urls:
        print(f"Checking {url} ...")
        res = check_core_web_vitals(API_KEY, url)
        results.append(res)
        time.sleep(1)  # biar aman dari rate limit

    # Save to CSV
    keys = results[0].keys()
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n✅ Done! Hasil tersimpan di {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
