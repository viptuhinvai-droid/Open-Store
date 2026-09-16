# OPEN STORE ব্যাকএন্ড — ধাপ ১: ফাউন্ডেশন

এটা OPEN STORE-এর মূল ব্যাকএন্ড API। ওয়েবসাইট আর মোবাইল অ্যাপ — দুটোই এই একই API ব্যবহার করবে।

## এখানে কী আছে

- `app/models.py` — ডেটাবেস টেবিল (অ্যাপ রেকর্ড, অডিট লগ, Stage/ContactStatus)
- `app/crud.py` — সব নিয়ম এখানে প্রয়োগ হয় (যেমন: VERIFIED না হলে AUTHORIZED করা যাবে না)
- `app/main.py` — API endpoints
- `render.yaml` — Render-এ এক ক্লিকে ডিপ্লয় করার জন্য

## GitHub-এ আপলোড করবেন কীভাবে

1. GitHub-এ একটা নতুন repository বানান, নাম দিন যেমন `open-store-backend`
2. এই পুরো ফোল্ডারের সব ফাইল সেই repository-তে আপলোড করুন
   (GitHub ওয়েবসাইট থেকেই ফোন দিয়ে "Add file → Upload files" করে করা যায়)

## Render-এ ডিপ্লয় করবেন কীভাবে

1. [render.com](https://render.com) -এ অ্যাকাউন্ট বানান (GitHub দিয়ে লগইন করলে সহজ হবে)
2. Dashboard-এ **New → Blueprint** এ ক্লিক করুন
3. আপনার `open-store-backend` repository সিলেক্ট করুন
4. Render নিজে থেকেই `render.yaml` ফাইলটা পড়ে নেবে এবং:
   - একটা free PostgreSQL ডেটাবেস বানাবে
   - একটা free web service বানাবে (আপনার API)
   - দুটোকে নিজে থেকেই কানেক্ট করে দেবে
5. **Apply** চাপুন — কয়েক মিনিটের মধ্যে API লাইভ হয়ে যাবে
6. লাইভ হলে আপনি একটা লিংক পাবেন, যেমন `https://open-store-api.onrender.com`
   সেই লিংকের শেষে `/docs` যোগ করে ব্রাউজারে খুললে (`https://open-store-api.onrender.com/docs`)
   একটা ইন্টারেক্টিভ টেস্ট পেজ দেখবেন — সেখান থেকে সব ফিচার ফোন থেকেই টেস্ট করা যাবে।

## এখনো যা বাকি (পরের ধাপে করব)

- ডেভেলপারকে রিয়েল ইমেইল পাঠানো (এখন এটা শুধু একটা placeholder — `main.py`-এর `attempt_contact` ফাংশনে TODO লেখা আছে)
- অ্যাডমিন লগইন/অথেনটিকেশন (এখন যে কেউ verify/authorize করতে পারবে — এটা নিরাপদ না, শুধু টেস্টের জন্য ঠিক আছে)
- ইউজার-facing ওয়েবসাইট (যেখানে মানুষ অ্যাপ ব্রাউজ করবে)
- মোবাইল অ্যাপ
