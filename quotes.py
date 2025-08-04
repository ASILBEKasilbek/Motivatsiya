import random

QUOTES = {
    1: [("Boshladingiz — eng muhimi shu! 🚀", "Katta yo‘l har doim birinchi qadamdan boshlanadi.")],
    3: [("3 kun — bu allaqachon harakat! 👣", "Harakatni davom ettirish — eng yaxshi strategiya.")],
    5: [("5 kun — siz chindan boshladingiz! 💪", "O‘zingizni rag‘batlantiring va davom eting.")],
    7: [("1 hafta — barqarorlik boshlanishi! 🔥", "Endi bu odatga aylanishi mumkin.")],
    10: [("10 kun! Siz sabrni o‘rganyapsiz! 🧠", "Endi o‘zingizga ishonch kuchaymoqda.")],
    15: [("15 kun! 🏃 Siz barqaror yo‘ldasiz!", "Kichik qadamlar — katta yutuqlarning kaliti.")],
    20: [("20 kun! O‘zgaryapsiz! 🌱", "Yangi siz shakllanmoqda — davom eting!")],
    25: [("25 kun — jiddiy bosqich! 🛠", "Endi to‘xtamaslik muhim.")],
    30: [("1 oy — zo‘r natija! 🏆", "O‘tgan oyni tahlil qiling va rejalashtiring.")],
    40: [("40 kun! Kuchli odat! 💥", "Endi bu sizning bir qismingizga aylanishi kerak.")],
    50: [("50 kun — yarmidan ko‘pi! 🚧", "Harakatni sekinlashtirmang — tezlikni oshiring.")],
    60: [("60 kun — bu kuch! ⚡️", "Oldinga qarab harakatda davom eting.")],
    70: [("70 kun! Siz bardavomsiz! 🧭", "Endi orqaga yo‘l yo‘q.")],
    80: [("80 kun — ajoyib natija! 🌄", "Bu bosqichda ruhiy kuchingiz o‘sdi.")],
    90: [("90 kun! Ko‘pchilik bu yerga yetmaydi! 🔥", "Siz o‘z ustingizda ishlayapsiz.")],
    100: [("100 kun — siz kuchli odamlardansiz! 🥇", "Endi katta maqsadlar haqida o‘ylang.")],
    120: [("120 kun! 🌟 Siz har kuni o‘sayapsiz!", "Doimiylik sizni kuchli qiladi.")],
    150: [("150 kun — bu sadoqat! 🔒", "O‘zingizga va maqsadingizga sodiqlik misoli.")],
    180: [("180 kun — yarim yil! ⏳", "Shunchalik bardavomlik — noyob fazilat.")],
    200: [("200 kun! 🔥 Siz ilhom manbaasiz!", "Katta orzularni yana bir bor aniqlang.")],
    250: [("250 kun! 📈 Sizda aniq o‘sish bor!", "Endi boshqalarga ham yordam bering.")],
    300: [("300 kun! 💎 Sizda kuchli irodaviy yadro bor!", "Ushbu bosqichda yangi yuksakliklarga erishing.")],
    330: [("330 kun — hayotingiz o‘zgardi! 🚀", "O‘zgarishlar kuchini endi siz boshqarayapsiz.")],
    365: [("1 YIL! 🎉 Siz chinakam G‘OLIBsiz!", "Bu endi sizning yangi hayotingiz!")],
}

def get_motivational_message(day_count):
    for key in sorted(QUOTES.keys(), reverse=True):
        if day_count >= key:
            quote, advice = random.choice(QUOTES[key])
            return f"{quote}\n💡 Maslahat: {advice}"
    return f"Har bir kun yangi imkoniyat! Davom eting! 💪\n💡 Maslahat: Har kuni bir narsani yaxshilashga harakat qiling."
