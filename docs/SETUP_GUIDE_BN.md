# সেটআপ গাইড (ধাপে ধাপে)

এই গাইডে তিনটা কাজ আছে: (১) GitHub-এ রিপো বানিয়ে ফাইল আপলোড, (২) Streamlit Cloud-এ ড্যাশবোর্ড লাইভ করা, (৩) PostgreSQL-এ SQL চালানো।

---

## ধাপ ১ — GitHub রিপো বানানো ও ফাইল আপলোড

1. github.com-এ লগইন করুন (অ্যাকাউন্ট: `sakter2618-maker`)।
2. উপরে ডানদিকে **+** → **New repository**।
3. **Repository name:** `automotive-supply-chain-analytics`
4. **Description:** `Automotive supply chain & quality analytics — Python/Streamlit dashboard, PostgreSQL, Excel`
5. **Public** সিলেক্ট করুন। "Add a README" টিক **দেবেন না** (আমাদের README আছে)।
6. **Create repository** চাপুন।

### ফাইল আপলোড (সবচেয়ে সহজ উপায় — ব্রাউজার দিয়ে)
1. জিপ ফাইলটা আপনার কম্পিউটারে **Extract** করুন।
2. নতুন রিপো পেজে **"uploading an existing file"** লিংকে ক্লিক করুন।
3. Extract করা ফোল্ডারের **ভেতরের সব ফাইল ও ফোল্ডার** (streamlit_app.py, README.md, app, src, sql, data, reports, excel, docs, .streamlit …) একসাথে টেনে এনে ছেড়ে দিন।
   - ⚠️ `.streamlit` ফোল্ডারটা লুকানো থাকতে পারে। Windows-এ File Explorer → **View → Show → Hidden items** চালু করুন।
4. নিচে **Commit message:** `Initial commit: automotive supply chain analytics` → **Commit changes**।
5. রিপো পেজে README সুন্দর করে চার্টসহ দেখাবে কিনা চেক করুন।

> Git কমান্ড দিয়ে করতে চাইলে (ফোল্ডারের ভেতরে টার্মিনাল খুলে):
> ```bash
> git init
> git add .
> git commit -m "Initial commit: automotive supply chain analytics"
> git branch -M main
> git remote add origin https://github.com/sakter2618-maker/automotive-supply-chain-analytics.git
> git push -u origin main
> ```

---

## ধাপ ২ — Streamlit Cloud-এ ড্যাশবোর্ড লাইভ করা

1. share.streamlit.io-তে GitHub দিয়ে লগইন করুন।
2. **Create app** → **Deploy a public app from GitHub**।
3. **Repository:** `sakter2618-maker/automotive-supply-chain-analytics`
4. **Branch:** `main` · **Main file path:** `streamlit_app.py`
5. **App URL:** চাইলে নাম দিন, যেমন `automotive-supply-chain-salma`
6. **Deploy** চাপুন। ২–৪ মিনিট লাগবে (requirements.txt থেকে প্যাকেজ ইনস্টল হবে)।
7. লাইভ লিংকটা কপি করে README-এর উপরে **"Live dashboard: _add your Streamlit Cloud link here_"** লাইনটা এডিট করে বসিয়ে দিন (GitHub-এ README খুলে ✏️ পেন্সিল আইকন)।
8. ড্যাশবোর্ডের স্ক্রিনশট (`reports/figures/dashboard_*.png`) আগে থেকেই README-তে দেওয়া আছে, নতুন করে কিছু করতে হবে না।

**কোনো এরর এলে:** Streamlit পেজে নিচে ডানদিকে **Manage app** → লগ দেখুন, এরর লেখাটা কপি করে আমাকে পাঠান।

### নিজের কম্পিউটারে চালাতে চাইলে
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```
ব্রাউজারে `http://localhost:8501` খুলবে।

---

## ধাপ ৩ — PostgreSQL-এ SQL চালানো (pgAdmin দিয়ে)

1. pgAdmin খুলুন → **Databases** এ রাইট-ক্লিক → **Create → Database** → নাম `supply_chain`।
2. `supply_chain` সিলেক্ট করে **Query Tool** খুলুন।
3. `sql/01_schema.sql` ফাইল খুলে পুরোটা চালান (▶ বা F5) — ৭টা টেবিল তৈরি হবে।
4. ডেটা ইমপোর্ট: প্রতিটা টেবিলে রাইট-ক্লিক → **Import/Export Data** → **Import** →
   ফাইল `data/processed/<টেবিলের নাম>.csv` → **Format: csv** → **Options → Header: ON** → OK।
   এই ক্রমে করুন: `suppliers` → `plants` → `components` → `purchase_orders` → `quality_inspections` → `inventory_daily` → `production_daily`
5. `sql/03_business_queries.sql` খুলে একটা একটা কুয়েরি সিলেক্ট করে চালান। প্রতিটার উপরে কমেন্টে লেখা আছে কোন প্রশ্নের উত্তর দেয়।
6. ভালো ফলাফলগুলোর স্ক্রিনশট রাখতে পারেন — ইন্টারভিউতে দেখাতে কাজে লাগবে।
