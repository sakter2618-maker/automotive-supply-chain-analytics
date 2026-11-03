# ইন্টারভিউ প্রস্তুতি গাইড — Automotive Supply Chain & Quality Analytics

এই প্রজেক্ট নিয়ে ইন্টারভিউতে (Ford, GM, Dana ইত্যাদি) যে প্রশ্ন আসতে পারে এবং কীভাবে উত্তর দেবেন।
উত্তরগুলো ইংরেজিতে দিলাম, কারণ ইন্টারভিউ ইংরেজিতে হবে; বাংলায় ব্যাখ্যা দেওয়া আছে।

---

## ১. ৩০ সেকেন্ডে প্রজেক্ট পরিচিতি (Elevator pitch)

> "I built an end-to-end supply chain and quality analytics project for an automotive manufacturer with
> 3 plants and 8 suppliers. I modeled the data in PostgreSQL, wrote 18 SQL queries, built a 7-page Streamlit
> dashboard in Python, and wrote a quality report. The key finding was that one overseas electronics supplier
> delivered only 58% on time and caused most of the stock-outs, and that delays only hurt production once they
> exceed the 3-day safety stock — weeks with a delay longer than 7 days lost about 364 units per plant.
> I also used an SPC p-chart to detect a brake-caliper quality problem that started in March 2026."

---

## ২. মূল সংজ্ঞাগুলো (মুখস্থ রাখুন)

| টার্ম | মানে | সূত্র |
|---|---|---|
| **OTD (On-Time Delivery)** | কত % ডেলিভারি সময়মতো এসেছে | on-time lots ÷ all lots |
| **PPM** | প্রতি ১০ লাখ পার্টসে কয়টা খারাপ | defects ÷ inspected × 1,000,000 |
| **First-pass yield** | কত % লট প্রথমবারেই পাস করেছে | pass lots ÷ all lots |
| **Schedule attainment** | পরিকল্পনার কত % ভালো ইউনিট বানানো গেছে | good units ÷ planned units |
| **Availability** | লাইন কত % সময় চালু ছিল | (scheduled − downtime) ÷ scheduled hours |
| **Safety stock** | দেরির জন্য রাখা বাড়তি স্টক (এখানে ৩ দিনের) | — |
| **Tier 1 / Tier 2** | Tier 1 সরাসরি OEM-কে দেয়; Tier 2 দেয় Tier 1-কে | — |
| **SCAR** | Supplier Corrective Action Request — সাপ্লায়ারকে সমস্যা ঠিক করার আনুষ্ঠানিক অনুরোধ | — |
| **8D** | ৮ ধাপের সমস্যা সমাধান পদ্ধতি (অটো ইন্ডাস্ট্রিতে খুব পরিচিত) | — |
| **p-chart (SPC)** | মাসিক defect %-কে ±3σ সীমার সাথে তুলনা; সীমার বাইরে গেলে "special cause" | p̄ ± 3·√(p̄(1−p̄)/n) |

---

## ৩. সম্ভাব্য প্রশ্ন ও উত্তর

**Q1. Where did the data come from? Is it real?**
> "The starting point was a public supply chain dataset with 100 SKUs and 5 suppliers. It had no dates or promised
> delivery dates, so it couldn't answer on-time or production-impact questions. I wrote a Python generator that builds a
> realistic automotive dataset calibrated to that file's ranges, with a fixed random seed so it's reproducible. I kept the
> original dataset and analyzed it on a separate dashboard page."

(বাংলায়: সৎভাবে বলবেন ডেটা synthetic — এটা দুর্বলতা না, বরং দেখায় আপনি ডেটার সীমাবদ্ধতা বুঝেছেন।)

**Q2. Which supplier is not delivering on time, and how do you know?**
> "Pacific Rim Electronics at 57.8% OTD vs a 95% target. Its late lots average 7.2 days late, and it has 100 lots more than
> 5 days late. The monthly heat map shows it was worst during the Jul–Oct 2025 raw-material shortage."

**Q3. How did you measure the impact of delays on production?**
> "I grouped each plant-week by its worst late critical part. Up to 3 days late, safety stock absorbs it — almost no
> lost units. 4–7 days late cost ~141 units per plant-week and over 7 days cost ~364, with attainment dropping from
> about 85% to 79%. In total, part shortages caused 30,600 lost units and 20% of all downtime."

(এখানে মূল আইডিয়া: সম্পর্কটা linear না — একটা threshold আছে, safety stock-এর সমান।)

**Q4. Which component has the highest defect rate? What would you do?**
> "Brake calipers from Ohio Valley Castings at 3.13%, or about 31,000 PPM. The p-chart shows four months above the upper
> control limit starting March 2026 — a special cause, likely tooling wear, with porosity as the top defect. I'd open an 8D
> with the supplier and put 100% inspection in place until the process is back in control."

**Q5. How did you build the supplier score? Why those weights?**
> "45% delivery, 40% quality, 15% fill rate, on absolute scales so it's easy to explain: the delivery score is OTD %, the
> quality score is 100 minus PPM divided by 300. Delivery and quality get the most weight because both stop the line.
> The weights sit in the Excel Assumptions sheet, so a manager can change them and see the ranking update."

**Q6. Rhein Precision Bearings is #2 by score but flagged "Corrective action". Isn't that a contradiction?**
> "No — the score is a blend, but the status rule needs minimum OTD. Rhein has excellent quality (2,337 PPM) but only
> 83.6% OTD, so it still needs a delivery action plan. That's why I show both."

**Q7. Show me a SQL query you're proud of.**
> Q8 (Pareto) বা Q17 (Scorecard) দেখান। বলুন: "I used window functions — `SUM() OVER (ORDER BY …)` for the cumulative
> Pareto percentage, and CTEs plus `RANK()` for the scorecard."

**Q8. Why Streamlit instead of Power BI/Tableau?**
> "Python gives me full control and the same logic is reused for the dashboard, the report and the Excel export — all
> metrics live in one file, `metrics.py`, which mirrors the SQL. It's also free to host publicly. I'm comfortable
> rebuilding the same model in Power BI if the team uses it."

**Q9. What would you do with more time?**
> "Connect to live ERP data, add demand forecasting to set safety stock per part by risk, add a supplier-risk alert when
> OTD drops below 85% for two weeks, and add OEE (availability × performance × quality)."

---

## ৪. ডেমো দেখানোর ক্রম (৩ মিনিট)

1. **Executive Overview** → KPI কার্ড আর ৪টা প্রশ্নের উত্তর।
2. সাইডবারে **Supplier region = Overseas** দিন → দেখান সংখ্যা কীভাবে বদলায়।
3. **Inventory & Production** → "Units lost vs delay" চার্ট — threshold-এর গল্প বলুন।
4. **Quality Control** → p-chart, Brake Caliper সিলেক্ট করা অবস্থায়।
5. **Supplier Scorecard** → bubble chart ও recommended actions।
