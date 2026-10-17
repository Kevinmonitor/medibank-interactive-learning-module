"""
"Ask in your language" box for the Hospital card and the Homesick card (OSHCwise) - Dimi's part

The student types what they need, in any of the 5 languages. Three things happen:

  1. LANGUAGE (ML, language_model.py)  - the card changes to the student's language
  2. SAFETY   (word list, intent_model.py) - emergency or self-harm words show help FIRST
  3. MEANING  (ML + NLP, intent_model.py) - the student walks to the right step
         "I want to do a blood test"  ->  the person in the picture walks to "Tests"
     or, if it belongs to another card ("I have a cold"), a button opens that card.

Use it on a guide page:
    import ask_box
    goto = ask_box.render("hospital")          # or "homesick"
    components.html(lb.inject(html, goto=goto), ...)

Nothing the student types is saved.
"""

import html

import streamlit as st

import intent_model as im
import language_box as lb
import language_model as lm

LANGS = lm.LANGS

# Other cards (button text in English is translated below; page files of the team's app)
OTHER_CARDS = {
    "sick": ("I get sick", "pages/Sick_Guide.py"),
    "medication": ("I need medication", "pages/Medication_Guide.py"),
    "claim": ("I need to make a claim", "pages/Claim_Guide.py"),
    "homesick": ("I feel homesickness", "pages/Homesick_Guide.py"),
    "hospital": ("I need to go to hospital", "pages/Hospital_Visit.py"),
}

# ---------- Words on the box, in the 5 languages ----------

T = {
    "title": {"en": "Ask in your language", "si": "ඔබේ භාෂාවෙන් අහන්න", "fa": "به زبان خودتان بپرسید",
              "vi": "Hỏi bằng ngôn ngữ của bạn", "id": "Tanya dalam bahasa Anda"},
    "sub": {"en": "Type what you need. I find your language and walk you to the right step.",
            "si": "ඔබට අවශ්‍ය දේ ලියන්න. මම ඔබේ භාෂාව හඳුනාගෙන නිවැරදි පියවරට ඔබව රැගෙන යන්නම්.",
            "fa": "آنچه نیاز دارید را بنویسید. زبان شما را پیدا می‌کنم و شما را به مرحله درست می‌برم.",
            "vi": "Gõ điều bạn cần. Tôi sẽ nhận ra ngôn ngữ của bạn và đưa bạn đến đúng bước.",
            "id": "Ketik apa yang Anda butuhkan. Saya akan mengenali bahasa Anda dan membawa Anda ke langkah yang tepat."},
    "ph_hospital": {"en": "e.g. I need a blood test / mata blood test ekak one / tôi muốn về nhà",
                    "si": "උදා: මට blood test එකක් ඕනේ", "fa": "مثلاً: می‌خواهم آزمایش خون بدهم",
                    "vi": "ví dụ: tôi cần xét nghiệm máu", "id": "misalnya: saya perlu tes darah"},
    "ph_homesick": {"en": "e.g. I miss my family / mata gedara mathak wenawa / saya kangen rumah",
                    "si": "උදා: මට ගෙදර මතක් වෙනවා", "fa": "مثلاً: دلم برای خانواده‌ام تنگ شده",
                    "vi": "ví dụ: tôi nhớ gia đình", "id": "misalnya: saya kangen keluarga"},
    "ask": {"en": "Ask", "si": "අහන්න", "fa": "بپرس", "vi": "Hỏi", "id": "Tanya"},
    "lang": {"en": "Language", "si": "භාෂාව", "fa": "زبان", "vi": "Ngôn ngữ", "id": "Bahasa"},
    "try": {"en": "Try:", "si": "උත්සාහ කරන්න:", "fa": "امتحان کنید:", "vi": "Thử:", "id": "Coba:"},
    "found_lang": {"en": "Language", "si": "භාෂාව", "fa": "زبان", "vi": "Ngôn ngữ", "id": "Bahasa"},
    "understood": {"en": "I understood", "si": "මට තේරුණේ", "fa": "متوجه شدم", "vi": "Tôi hiểu là",
                   "id": "Saya memahami"},
    "walking": {"en": "Walking you to step {n}: {name}", "si": "ඔබව පියවර {n} වෙත රැගෙන යනවා: {name}",
                "fa": "شما را به مرحله {n} می‌بریم: {name}", "vi": "Đang đưa bạn đến bước {n}: {name}",
                "id": "Membawa Anda ke langkah {n}: {name}"},
    "turning": {"en": "Turning the wheel to suggestion {n}: {name}",
                "si": "රෝදය යෝජනාව {n} වෙත කරකවනවා: {name}",
                "fa": "چرخ را به پیشنهاد {n} می‌چرخانیم: {name}",
                "vi": "Đang xoay bánh xe đến gợi ý {n}: {name}",
                "id": "Memutar roda ke saran {n}: {name}"},
    "notsure": {"en": "I'm not completely sure. Did you mean:", "si": "මට හරියටම විශ්වාස නැහැ. ඔබ අදහස් කළේ:",
                "fa": "کاملاً مطمئن نیستم. منظورتان این بود:", "vi": "Tôi chưa chắc lắm. Ý bạn là:",
                "id": "Saya belum terlalu yakin. Maksud Anda:"},
    "short": {"en": "Please type a few more words.", "si": "කරුණාකර තව වචන කිහිපයක් ලියන්න.",
              "fa": "لطفاً چند کلمه بیشتر بنویسید.", "vi": "Vui lòng gõ thêm vài từ.",
              "id": "Silakan ketik beberapa kata lagi."},
    "other": {"en": "I couldn't find this on this card. Try a sentence like one of these:",
              "si": "මෙම කාඩ්පතේ මෙය සොයාගත නොහැකි විය. මෙවැනි වාක්‍යයක් උත්සාහ කරන්න:",
              "fa": "این را در این کارت پیدا نکردم. جمله‌ای مثل این‌ها را امتحان کنید:",
              "vi": "Tôi không tìm thấy điều này trong thẻ này. Hãy thử một câu như sau:",
              "id": "Saya tidak menemukannya di kartu ini. Coba kalimat seperti ini:"},
    "card_sick": {"en": "This sounds like a mild illness. It is usually not an emergency: a GP is the best first stop.",
                  "si": "මෙය සුළු අසනීපයක් ලෙස පෙනේ. සාමාන්‍යයෙන් මෙය හදිසි අවස්ථාවක් නොවේ: පළමුව GP (පවුලේ වෛද්‍යවරයා) හමුවන්න.",
                  "fa": "به نظر یک بیماری خفیف است. معمولاً اورژانسی نیست: بهترین قدم اول، پزشک عمومی (GP) است.",
                  "vi": "Có vẻ đây là bệnh nhẹ. Thường không phải cấp cứu: nên đến bác sĩ đa khoa (GP) trước.",
                  "id": "Sepertinya ini sakit ringan. Biasanya bukan keadaan darurat: dokter umum (GP) adalah tempat pertama."},
    "card_medication": {"en": "This is about medicine. The medication card shows you how to get it.",
                        "si": "මෙය ඖෂධ ගැනයි. ඖෂධ කාඩ්පත ඒවා ලබා ගන්නා ආකාරය පෙන්වයි.",
                        "fa": "این درباره دارو است. کارت دارو نشان می‌دهد چطور آن را بگیرید.",
                        "vi": "Đây là về thuốc. Thẻ thuốc sẽ chỉ bạn cách mua thuốc.",
                        "id": "Ini tentang obat. Kartu obat menunjukkan cara mendapatkannya."},
    "card_claim": {"en": "This is about getting your money back. The claim card shows you how.",
                   "si": "මෙය ඔබේ මුදල් ආපසු ලබා ගැනීම ගැනයි. ක්ලේම් කාඩ්පත ඒ ආකාරය පෙන්වයි.",
                   "fa": "این درباره پس گرفتن پول شماست. کارت claim نشان می‌دهد چطور.",
                   "vi": "Đây là về việc lấy lại tiền. Thẻ yêu cầu chi trả sẽ chỉ bạn cách làm.",
                   "id": "Ini tentang mendapatkan uang Anda kembali. Kartu klaim menunjukkan caranya."},
    "card_homesick": {"en": "This sounds like missing home or feeling down. The homesickness card can help.",
                      "si": "මෙය ගෙදර මතක් වීමක් හෝ දුකක් ලෙස පෙනේ. ගෙදර මතක් වීමේ කාඩ්පත උදව් කළ හැක.",
                      "fa": "به نظر دلتنگی یا ناراحتی است. کارت دلتنگی می‌تواند کمک کند.",
                      "vi": "Có vẻ bạn đang nhớ nhà hoặc buồn. Thẻ nhớ nhà có thể giúp bạn.",
                      "id": "Sepertinya Anda rindu rumah atau sedang sedih. Kartu rindu rumah bisa membantu."},
    "card_hospital": {"en": "This sounds like a hospital question. The hospital card walks you through it.",
                      "si": "මෙය රෝහල් ප්‍රශ්නයක් ලෙස පෙනේ. රෝහල් කාඩ්පත ඔබව පියවරෙන් පියවර රැගෙන යයි.",
                      "fa": "به نظر سؤالی درباره بیمارستان است. کارت بیمارستان قدم به قدم راهنمایی می‌کند.",
                      "vi": "Có vẻ đây là câu hỏi về bệnh viện. Thẻ bệnh viện sẽ hướng dẫn bạn từng bước.",
                      "id": "Sepertinya ini pertanyaan tentang rumah sakit. Kartu rumah sakit memandu Anda langkah demi langkah."},
    "open": {"en": "Open “{card}” →", "si": "“{card}” විවෘත කරන්න →", "fa": "باز کردن «{card}» ←",
             "vi": "Mở “{card}” →", "id": "Buka “{card}” →"},
    "emergency": {"en": "This could be an emergency. Call 000 now (free, 24/7). Do not wait for the app.",
                  "si": "මෙය හදිසි අවස්ථාවක් විය හැක. දැන්ම 000 අමතන්න (නොමිලේ, පැය 24ම). යෙදුම එනතුරු රැඳී නොසිටින්න.",
                  "fa": "ممکن است اورژانسی باشد. همین حالا با 000 تماس بگیرید (رایگان، شبانه‌روزی). منتظر برنامه نمانید.",
                  "vi": "Đây có thể là trường hợp cấp cứu. Hãy gọi 000 ngay (miễn phí, 24/7). Đừng chờ ứng dụng.",
                  "id": "Ini mungkin keadaan darurat. Segera telepon 000 (gratis, 24 jam). Jangan menunggu aplikasi."},
    "self_harm": {"en": "You are not alone, and help is available right now. If you are in danger call 000. "
                        "Lifeline: 13 11 14. Student Health and Support Line (24/7): 1800 887 283.",
                  "si": "ඔබ තනිවම නොවේ, දැන්ම උදව් ලබා ගත හැක. ඔබ අනතුරේ නම් 000 අමතන්න. "
                        "Lifeline: 13 11 14. ශිෂ්‍ය සෞඛ්‍ය සහ සහාය දුරකථන අංකය (පැය 24ම): 1800 887 283.",
                  "fa": "شما تنها نیستید و همین حالا کمک در دسترس است. اگر در خطر هستید با 000 تماس بگیرید. "
                        "Lifeline: 13 11 14. خط سلامت و حمایت دانشجویان (شبانه‌روزی): 1800 887 283.",
                  "vi": "Bạn không đơn độc, và luôn có người giúp bạn ngay lúc này. Nếu bạn gặp nguy hiểm, hãy gọi 000. "
                        "Lifeline: 13 11 14. Đường dây hỗ trợ sức khỏe sinh viên (24/7): 1800 887 283.",
                  "id": "Anda tidak sendirian, dan bantuan tersedia sekarang. Jika Anda dalam bahaya, telepon 000. "
                        "Lifeline: 13 11 14. Layanan Kesehatan dan Dukungan Mahasiswa (24 jam): 1800 887 283."},
    "how": {"en": "How the AI understood you", "si": "AI එක ඔබව තේරුම් ගත් ආකාරය", "fa": "هوش مصنوعی چطور متوجه شد",
            "vi": "AI đã hiểu bạn như thế nào", "id": "Bagaimana AI memahami Anda"},
    "cleaned": {"en": "1. NLP cleaning", "si": "1. NLP පිරිසිදු කිරීම", "fa": "۱. پاک‌سازی متن (NLP)",
                "vi": "1. Làm sạch văn bản (NLP)", "id": "1. Pembersihan teks (NLP)"},
    "m_lang": {"en": "2. Language model (ML)", "si": "2. භාෂා මාදිලිය (ML)", "fa": "۲. مدل تشخیص زبان (ML)",
               "vi": "2. Mô hình ngôn ngữ (ML)", "id": "2. Model bahasa (ML)"},
    "m_mean": {"en": "3. Meaning model (ML)", "si": "3. අර්ථ මාදිලිය (ML)", "fa": "۳. مدل تشخیص منظور (ML)",
               "vi": "3. Mô hình ý nghĩa (ML)", "id": "3. Model makna (ML)"},
    "other_label": {"en": "Something else", "si": "වෙනත් දෙයක්", "fa": "چیز دیگری", "vi": "Việc khác",
                    "id": "Hal lain"},
    "privacy": {"en": "Nothing you type is saved.", "si": "ඔබ ලියන කිසිවක් සුරැකෙන්නේ නැත.",
                "fa": "هیچ چیزی که می‌نویسید ذخیره نمی‌شود.", "vi": "Không có gì bạn gõ được lưu lại.",
                "id": "Apa pun yang Anda ketik tidak disimpan."},
}

# Example sentences under the box (English; translated with the same words in each language)
EXAMPLES = {
    "hospital": {
        "en": ["I want to do a blood test", "How long do I have to wait?", "When can I go home?"],
        "si": ["මට blood test එකක් කරන්න ඕනේ", "මට කොච්චර වෙලා ඉන්න වෙයිද?", "මට ගෙදර යන්න පුළුවන් කවදාද?"],
        "fa": ["می‌خواهم آزمایش خون بدهم", "چقدر باید صبر کنم؟", "کی می‌توانم به خانه بروم؟"],
        "vi": ["tôi muốn xét nghiệm máu", "tôi phải chờ bao lâu?", "khi nào tôi được về nhà?"],
        "id": ["saya mau tes darah", "berapa lama saya harus menunggu?", "kapan saya bisa pulang?"],
    },
    "homesick": {
        "en": ["I miss my family", "Can I see a counsellor?", "How can I make friends?"],
        "si": ["මට මගේ පවුල මතක් වෙනවා", "මට උපදේශකයෙක් හමුවෙන්න පුළුවන්ද?", "මට යාළුවෝ හොයාගන්නේ කොහොමද?"],
        "fa": ["دلم برای خانواده‌ام تنگ شده", "می‌توانم مشاور ببینم؟", "چطور دوست پیدا کنم؟"],
        "vi": ["tôi nhớ gia đình", "tôi có thể gặp chuyên viên tư vấn không?", "làm sao để kết bạn?"],
        "id": ["saya kangen keluarga", "bisakah saya bertemu konselor?", "bagaimana cara mencari teman?"],
    },
}

CSS = """
<style>
[class*="st-key-askbox"] {
  border: 1.5px solid #d7dbe1; border-radius: 18px; padding: 1.1rem 1.3rem 0.9rem;
  background: linear-gradient(135deg, #ffffff 0%, #f6f8fb 60%, #fdf1f0 100%);
  box-shadow: 0 6px 20px rgba(20, 58, 90, .08); margin: .4rem 0 1rem;
}
.ask-head { display:flex; align-items:center; gap:.7rem; margin-bottom:.15rem; }
.ask-icon { width:40px; height:40px; border-radius:12px; display:grid; place-items:center; font-size:1.3rem;
  background: linear-gradient(135deg, #C8322E, #e0574f); color:#fff; box-shadow:0 4px 12px rgba(200,50,46,.3); }
.ask-title { font:700 1.15rem "Lucida Sans","Lucida Sans Unicode",Arial,sans-serif; color:#143a5a; }
.ask-sub { color:#5E6B7A; font-size:.9rem; margin:0 0 .3rem 0; }
[class*="st-key-askbox"] [data-testid="stTextInput"] input {
  border-radius: 12px; font-size: 1.02rem; padding: .7rem .9rem; }
[class*="st-key-ask_go"] button { background:#C8322E; color:#fff; border:0; border-radius:12px; min-height:2.75rem;
  font-weight:700; width:100%; }
[class*="st-key-ask_go"] button:hover { background:#a82823; color:#fff; }
[class*="st-key-ask_ex_"] button { border-radius:99px; border:1.5px solid #d7dbe1; background:#fff; color:#143a5a;
  font-size:.82rem; padding:.15rem .8rem; min-height:0; }
[class*="st-key-ask_ex_"] button:hover { border-color:#143a5a; color:#143a5a; }
[class*="st-key-ask_alt_"] button { border-radius:99px; border:1.5px solid #143a5a; color:#143a5a; background:#fff; }
.ask-result { border-radius:14px; padding:.8rem 1rem; margin:.5rem 0 .2rem; background:#fff; border:1.5px solid #e3e6ea; }
.ask-chips { display:flex; flex-wrap:wrap; gap:.4rem; margin-bottom:.45rem; }
.chip { display:inline-flex; align-items:center; gap:.35rem; border-radius:99px; padding:.18rem .7rem;
  font-size:.8rem; font-weight:700; }
.chip.lang { background:#E9F0FA; color:#2B5FA8; }
.chip.mean { background:#E8F5EE; color:#1E8E4E; }
.chip.warn { background:#FDF4E3; color:#B7791F; }
.ask-walk { font-weight:700; color:#143a5a; font-size:1rem; }
.ask-walk .arrow { display:inline-block; animation: askwalk 1.2s ease-in-out infinite; }
@keyframes askwalk { 0%,100% { transform: translateX(0); } 50% { transform: translateX(6px); } }
.ask-alert { border-radius:14px; padding:.85rem 1rem; margin:.5rem 0; font-weight:700; }
.ask-alert.red { background:#FCEDEC; color:#A82824; border:1.5px solid #C8322E; }
.ask-alert.blue { background:#E9F0FA; color:#143a5a; border:1.5px solid #2B5FA8; font-weight:600; }
.bars { margin:.2rem 0 .6rem; }
.bar { display:grid; grid-template-columns: 9.5rem 1fr 3rem; gap:.5rem; align-items:center; font-size:.82rem;
  margin:.18rem 0; color:#1D2A3A; }
.bar .track { height:.55rem; background:#EEF1F4; border-radius:99px; overflow:hidden; }
.bar .fill { height:100%; border-radius:99px; background:linear-gradient(90deg,#2B5FA8,#5b8fd6); }
.bar.best .fill { background:linear-gradient(90deg,#C8322E,#e0574f); }
.code { font-family: ui-monospace, Menlo, monospace; background:#F1F4F8; border-radius:8px; padding:.3rem .55rem;
  display:inline-block; font-size:.85rem; }
.ask-privacy { color:#8a96a3; font-size:.75rem; margin-top:.3rem; }
</style>
"""


def _t(key: str, lang: str, **values) -> str:
    text = T[key].get(lang) or T[key]["en"]
    return text.format(**values) if values else text


def _dir(lang: str) -> str:
    """Farsi reads right to left."""
    return ' dir="rtl"' if lang in lm.RTL else ""


def _esc(text: str) -> str:
    return html.escape(str(text))


def _bars(rows: list) -> str:
    """Little probability bars: [(label, p), ...]."""
    out = []
    for i, (label, p) in enumerate(rows):
        out.append(f'<div class="bar{" best" if i == 0 else ""}"><span>{_esc(label)}</span>'
                   f'<span class="track"><span class="fill" style="width:{p * 100:.0f}%;display:block"></span></span>'
                   f'<span>{p:.0%}</span></div>')
    return '<div class="bars">' + "".join(out) + "</div>"


def _answer_label(answer: str, card: str) -> str:
    """'step:5' -> 'Tests' (in the student's language), 'card:sick' -> 'I get sick'."""
    kind, _, value = answer.partition(":")
    if kind == "step":
        return lb.tr(im.STEP_NAMES[card][int(value)])
    if kind == "card":
        return lb.tr(OTHER_CARDS[value][0]) if value in OTHER_CARDS else value
    return _t("other_label", lb.current_language())


def _set_text(text: str) -> None:
    st.session_state["ask_text"] = text


def _process(text: str, card: str) -> None:
    """Run the three models on the student's sentence and keep the result for this card."""
    found, lang_p, lang_ranked = lm.detect_language(text)
    meaning = im.understand(text, card)
    result = {"text": text, "lang": found, "lang_p": lang_p,
              "lang_ranked": list(lang_ranked.items())[:3], **meaning}
    goto = None
    if meaning["safety"] == "emergency" and card == "hospital":
        goto = 0                                               # the Emergency entrance
    elif meaning["safety"] == "self_harm" and card == "homesick":
        goto = 1                                               # "Talk to someone, any time"
    elif meaning["answer"] and meaning["answer"].startswith("step:"):
        goto = int(meaning["answer"].split(":")[1])
    result["goto"] = goto
    st.session_state[f"ask_result_{card}"] = result
    if goto is not None:
        st.session_state[f"goto_{card}"] = goto
    # Change the card language when the model is sure
    if found and lang_p >= lm.LANG_MIN_CONFIDENCE and found != lb.current_language():
        st.session_state["lang"] = found
        st.rerun()


def _show_result(card: str, lang: str) -> None:
    r = st.session_state.get(f"ask_result_{card}")
    if not r:
        return
    # 1. Safety first
    if r["safety"] == "emergency":
        st.markdown(f'<div class="ask-alert red"{_dir(lang)}>🚨 {_esc(_t("emergency", lang))}</div>',
                    unsafe_allow_html=True)
    elif r["safety"] == "self_harm":
        st.markdown(f'<div class="ask-alert red"{_dir(lang)}>💛 {_esc(_t("self_harm", lang))}</div>', unsafe_allow_html=True)

    if not r["ranked"]:
        st.caption(_t("short", lang))
        return

    chips = []
    if r["lang"]:
        chips.append(f'<span class="chip lang">🌐 {_t("found_lang", lang)}: {_esc(lm.LANG_NAMES[r["lang"]])} · '
                     f'{r["lang_p"]:.0%}</span>')
    answer = r["answer"]
    if answer:
        chips.append(f'<span class="chip mean">🎯 {_t("understood", lang)}: {_esc(_answer_label(answer, card))} · '
                     f'{r["confidence"]:.0%}</span>')
    else:
        chips.append(f'<span class="chip warn">🤔 {_esc(_answer_label(r["ranked"][0][0], card))} · '
                     f'{r["ranked"][0][1]:.0%}</span>')
    body = '<div class="ask-chips">' + "".join(chips) + "</div>"

    if r.get("goto") is not None:
        n, name = r["goto"] + 1, lb.tr(im.STEP_NAMES[card][r["goto"]])
        key = "walking" if card == "hospital" else "turning"
        body += f'<div class="ask-walk"><span class="arrow">🚶</span> {_esc(_t(key, lang, n=n, name=name))}</div>'
    st.markdown(f'<div class="ask-result"{_dir(lang)}>{body}</div>', unsafe_allow_html=True)

    # Another card, not sure, or not about this card
    if answer and answer.startswith("card:"):
        other = answer.split(":")[1]
        st.markdown(f'<div class="ask-alert blue"{_dir(lang)}>{_esc(_t("card_" + other, lang))}</div>', unsafe_allow_html=True)
        title, page = OTHER_CARDS[other]
        if st.button(_t("open", lang, card=lb.tr(title)), key=f"ask_open_{other}", type="primary"):
            st.switch_page(page)
    elif not answer:
        st.caption(_t("notsure", lang))
        options = [a for a, _ in r["ranked"] if a.startswith("step:")][:2]
        cols = st.columns(max(1, len(options)) + 2)
        for col, a in zip(cols, options):
            with col:
                if st.button(_answer_label(a, card), key=f"ask_alt_{a}"):
                    st.session_state[f"goto_{card}"] = int(a.split(":")[1])
                    r["goto"], r["answer"] = int(a.split(":")[1]), a
                    st.rerun()
    elif answer == "other":
        st.caption(_t("other", lang))

    # How the AI understood the sentence (for the curious, and for the project report)
    with st.expander("🧠 " + _t("how", lang)):
        st.markdown(f'**{_t("cleaned", lang)}**<br><span class="code">{_esc(r["cleaned"])}</span>',
                    unsafe_allow_html=True)
        st.markdown(f'**{_t("m_lang", lang)}**' +
                    _bars([(lm.LANG_NAMES[c], p) for c, p in r["lang_ranked"]]), unsafe_allow_html=True)
        st.markdown(f'**{_t("m_mean", lang)}**' +
                    _bars([(_answer_label(a, card), p) for a, p in r["ranked"]]), unsafe_allow_html=True)
        st.caption("TF-IDF (letter groups + words) → Logistic Regression · scikit-learn")


def render(card: str):
    """Draw the box. Returns the step the student should walk to (or None)."""
    lang = lb.current_language()
    st.markdown(CSS, unsafe_allow_html=True)
    with st.container(key="askbox"):
        st.markdown(
            f'<div class="ask-head"{_dir(lang)}><div class="ask-icon">💬</div>'
            f'<div class="ask-title">{_esc(_t("title", lang))}</div></div>'
            f'<p class="ask-sub"{_dir(lang)}>{_esc(_t("sub", lang))}</p>',
            unsafe_allow_html=True,
        )
        text_col, go_col, pick_col = st.columns([5, 1, 1.6])
        with text_col:
            text = st.text_input(_t("title", lang), key="ask_text", label_visibility="collapsed",
                                 placeholder=_t("ph_" + card, lang))
        with go_col:
            st.button(_t("ask", lang), key="ask_go")
        with pick_col:
            codes = list(LANGS)
            picked = st.selectbox(_t("lang", lang), codes, index=codes.index(lang),
                                  format_func=lambda c: lm.LANG_NAMES[c], key=f"ask_pick_{lang}",
                                  label_visibility="collapsed")

        # Example sentences (click to try)
        examples = EXAMPLES[card].get(lang, EXAMPLES[card]["en"])
        cols = st.columns([0.6] + [2] * len(examples) + [1])
        cols[0].markdown(f'<div style="padding-top:.35rem;color:#5E6B7A;font-size:.85rem">{_t("try", lang)}</div>',
                         unsafe_allow_html=True)
        for i, (col, example) in enumerate(zip(cols[1:], examples)):
            with col:
                st.button(example, key=f"ask_ex_{i}", on_click=_set_text, args=(example,))

        # New sentence -> run the models (Enter, the Ask button or an example)
        text = (text or "").strip()
        if text and text != st.session_state.get(f"ask_done_{card}"):
            st.session_state[f"ask_done_{card}"] = text
            _process(text, card)
        elif picked != lang:
            st.session_state["lang"] = picked
            st.rerun()

        _show_result(card, lang)
        st.markdown(f'<div class="ask-privacy"{_dir(lang)}>🔒 {_t("privacy", lang)}</div>', unsafe_allow_html=True)
    return st.session_state.get(f"goto_{card}")
