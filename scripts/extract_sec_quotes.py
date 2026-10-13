"""Fetch the two SEC filings and save verbatim excerpts, asserting each one appears word for word.

    python scripts/extract_sec_quotes.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from collars.config import RESEARCH  # noqa: E402
from collars.data.sec import ARCHIVE, fetch_document  # noqa: E402

CIK = 1217286  # JPMorgan Trust I

FILINGS = {
    "S1": {
        "form": "497K", "acc": "0001193125-25-261069", "doc": "d92395d497k.htm", "filed": "2025-11-03",
        "desc": "Summary prospectus dated 2025-11-01, Hedged Equity Fund (Class R5/R6)",
        "quotes": [
            "The Fund will also systematically purchase and sell exchange traded put options and sell exchange traded call options, employing an option overlay known as a “Put/Spread Collar” strategy.",
            "The options may be based on the S&P 500 Index or on exchange-traded funds (ETFs) that replicate the S&P 500 Index (S&P 500 ETFs).",
            "The Fund typically holds options for three month periods (each, an “hedge period”) for the purpose of seeking to provide more predictable returns in any market cycle during the applicable hedge period.",
            "The quarterly hedge periods are based on returns from the first business day of January through the last business day of March; the first business day of April through the last business day of June; the first business day of July through the last business day of September; and the first business day of October through the last business day of December.",
            "The Fund constructs a Put/Spread Collar by buying a put option on the S&P 500 Index at a higher strike price and writing (or selling) a put option on the same index at a relatively lower strike price, resulting in what is known as a put option spread, while simultaneously selling a S&P 500 Index call option.",
            "The premiums received from writing index call options are intended to provide income which substantially offsets the cost of the put option spread,",
            "The Put/Spread Collar strategy is an actively managed process and is designed to provide a continuous market hedge for the portfolio.",
            "The put option spread is generally maintained at a level intended to protect the Fund from a decrease in the market of 5% to 20%, with potential upside generally capped at 3.5-5.5%.",
            "The upside cap could be more or less depending on market conditions.",
            # a page number ("2") falls inside this sentence in the filing text; quoted in two parts
            "The options are systematically reset on at",
            "least a quarterly basis to better capitalize on current market conditions and opportunities while seeking to provide predictable returns in all market cycles.",
            "Options positions are marked to market daily.",
            "the Fund may use future contracts, primarily futures on indexes, to more effectively gain targeted equity exposure from its cash positions and to hedge the Fund’s portfolio if it is unable to purchase or write the necessary options for its overlay strategy.",
        ],
    },
    "S2": {
        "form": "497K", "acc": "0001193125-26-079407", "doc": "d27473d497k.htm", "filed": "2026-02-27",
        "desc": "Supplement dated 2026-02-27 (effective 2026-03-01): replaces the derivatives paragraph",
        "quotes": [
            "In addition to the use of the Put/Spread Collar strategy described above, the Fund may use derivatives, primarily futures contracts, to gain exposure to indexes or certain securities within indexes, to more effectively gain targeted equity exposure from its cash positions, and to hedge the Fund’s portfolio if it is unable to purchase or write the necessary options for its overlay strategy.",
        ],
    },
    "S4": {
        "form": "497K", "acc": "0001193125-19-281595", "doc": "d804276d497k.htm", "filed": "2019-11-01",
        "desc": "Summary prospectus dated 2019-11-01 (Class R5/R6): no cap range and no calendar hedge-period wording",
        "quotes": [
            "The put option spread is generally maintained at a level whereby the Fund is protected from a decrease in the market of five to twenty percent.",
            "The options are systematically reset on at least a quarterly basis to better capitalize on current market conditions and opportunities while seeking to provide predictable returns in all market cycles.",
        ],
        "absent": ["capped at", "hedge period"],
    },
    "S5": {
        "form": "N-CSR", "acc": "0001193125-20-236339", "doc": "d899071dncsr.htm", "filed": "2020-08-31",
        "desc": "Annual report FY ended 2020-06-30, Hedged Equity Fund commentary and holdings",
        "quotes": [
            "The Fund captured 120% of the Benchmark’s total return with about 50% of the Benchmark’s volatility during the twelve month reporting period.",
            # A holdings line: the purchased put's actual strike, expiry and exercise style (a third source beyond N-PORT).
            "S&P 500 Index 9/30/2020 at USD 2,930.00, European Style",
            "The Fund used an enhanced index strategy that invests primarily in common stocks of large capitalization U.S. companies, while systematically purchasing and selling exchange-traded index put options and selling exchange-traded index call options.",
        ],
    },
}


def main() -> None:
    out = {"retrieved": date.today().isoformat(), "cik": CIK, "filings": {}}
    for key, f in FILINGS.items():
        text = fetch_document(CIK, f["acc"], f["doc"])
        missing = [q for q in f["quotes"] if q not in text]
        if missing:
            raise SystemExit(f"{key}: {len(missing)} quote(s) not found verbatim:\n" + "\n".join(missing))
        present = [a for a in f.get("absent", []) if a in text]
        if present:
            raise SystemExit(f"{key}: phrases expected to be absent were found: {present}")
        url = ARCHIVE.format(cik=CIK, acc_nodash=f["acc"].replace("-", "")) + f["doc"]
        out["filings"][key] = {k: v for k, v in f.items() if k != "doc"} | {"url": url}
        print(f"{key}: all {len(f['quotes'])} quotes verified verbatim")
    path = RESEARCH / "sources" / "sec_excerpts.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()
