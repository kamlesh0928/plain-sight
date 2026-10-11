import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "samples"
W, H = 720, 1000

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "C:/Windows/Fonts/arial.ttf",
]
BOLD_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def load_font(paths, size):
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def wrap(draw, text, font, max_w):
    lines = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            trial = f"{line} {word}".strip()
            if draw.textlength(trial, font=font) <= max_w:
                line = trial
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def sms(name, sender, body, time="10:42"):
    img = Image.new("RGB", (W, H), "#EDEDED")
    d = ImageDraw.Draw(img)
    f, fb, fs = load_font(FONT_PATHS, 30), load_font(BOLD_PATHS, 32), load_font(FONT_PATHS, 22)
    d.rectangle([0, 0, W, 120], fill="#FFFFFF")
    d.text((36, 44), sender, font=fb, fill="#111111")
    lines = wrap(d, body, f, 560)
    h = len(lines) * 42 + 44
    d.rounded_rectangle([30, 170, 30 + 620, 170 + h], radius=26, fill="#FFFFFF")
    for i, line in enumerate(lines):
        d.text((56, 192 + i * 42), line, font=f, fill="#1A1A1A")
    d.text((56, 170 + h + 14), time, font=fs, fill="#777777")
    img.save(OUT / f"{name}.png")


def upi(name, who, amount, note, button):
    img = Image.new("RGB", (W, H), "#F6F8FB")
    d = ImageDraw.Draw(img)
    f, fb = load_font(FONT_PATHS, 30), load_font(BOLD_PATHS, 34)
    big = load_font(BOLD_PATHS, 78)
    d.rectangle([0, 0, W, 120], fill="#1D5D9B")
    d.text((36, 44), "Payment request", font=fb, fill="#FFFFFF")
    d.ellipse([W // 2 - 60, 190, W // 2 + 60, 310], fill="#C9D5DC")
    d.text((W // 2 - 20, 232), who[0], font=fb, fill="#15222E")
    d.text((W // 2 - d.textlength(who, font=fb) / 2, 340), who, font=fb, fill="#15222E")
    d.text((W // 2 - d.textlength(amount, font=big) / 2, 410), amount, font=big, fill="#15222E")
    y = 540
    for line in wrap(d, note, f, 560):
        d.text((W // 2 - d.textlength(line, font=f) / 2, y), line, font=f, fill="#444444")
        y += 42
    d.rounded_rectangle([60, 780, W - 60, 870], radius=16, fill="#1D5D9B")
    d.text((W // 2 - d.textlength(button, font=fb) / 2, 805), button, font=fb, fill="#FFFFFF")
    img.save(OUT / f"{name}.png")


def doc(name, title, rows, footer):
    img = Image.new("RGB", (W, H), "#DADDE0")
    d = ImageDraw.Draw(img)
    f, fb, fs = load_font(FONT_PATHS, 28), load_font(BOLD_PATHS, 38), load_font(FONT_PATHS, 24)
    d.rectangle([40, 40, W - 40, H - 40], fill="#FFFFFF")
    d.text((80, 90), title, font=fb, fill="#15222E")
    d.line([80, 150, W - 80, 150], fill="#15222E", width=3)
    y = 190
    for k, v in rows:
        d.text((80, y), k, font=f, fill="#666666")
        d.text((W - 80 - d.textlength(v, font=f), y), v, font=f, fill="#111111")
        y += 62
    y += 30
    for line in wrap(d, footer, fs, W - 160):
        d.text((80, y), line, font=fs, fill="#444444")
        y += 36
    img.save(OUT / f"{name}.png")


# accept = risk levels that count as a correct answer
SAMPLES = [
    # ---- scams ----
    ("kyc_sms_scam", ["likely_scam"], lambda n: sms(n, "BK-KYCINFO",
        "Dear customer, your account will be BLOCKED today. Complete KYC now: http://bit.ly/kyc-upd8 or call 98XXXXXX10 immediately.")),
    ("upi_collect_trap", ["likely_scam"], lambda n: upi(n, "Rohit S.", "\u20b94,999",
        "Enter your UPI PIN to RECEIVE money. Request expires in 2 minutes.", "Approve")),
    ("lottery_scam", ["likely_scam"], lambda n: sms(n, "+91 90XXXXXX55",
        "CONGRATULATIONS! You won \u20b925,00,000 in the Lucky Draw. Pay \u20b94,500 processing fee to claim. Reply with your Aadhaar and bank details.")),
    ("fake_loan_scam", ["likely_scam"], lambda n: sms(n, "LN-QUICKLOAN",
        "Instant loan of \u20b950,000 approved without documents! Pay \u20b92,000 insurance fee first. Download our app: loan-fast.apk")),
    ("fake_support_scam", ["likely_scam"], lambda n: sms(n, "+91 80XXXXXX42",
        "Your wallet is frozen. Call customer care 91XXXXXX08 or install the AnyDesk app so our agent can fix it now.")),
    ("power_cut_scam", ["likely_scam"], lambda n: sms(n, "+91 70XXXXXX19",
        "Dear consumer, your power will be disconnected tonight at 9:30 PM because last month's bill is unpaid. Call officer 98XXXXXX77 immediately.")),
    ("wrong_transfer_scam", ["careful", "likely_scam"], lambda n: sms(n, "+91 99XXXXXX03",
        "Sorry, I sent \u20b98,000 to your number by mistake. Please send it back to this UPI ID: ra****@upi. Very urgent, I need it for hospital.")),
    # ---- borderline ----
    ("insurance_link_unknown", ["careful", "likely_scam"], lambda n: sms(n, "VK-INSURE",
        "Your policy premium is due. Pay now to avoid lapse: https://pay-policy.in/x7 - Team Insure")),
    ("cashback_offer", ["careful", "likely_scam"], lambda n: sms(n, "AD-OFFERS",
        "Get \u20b9500 cashback on your next payment! Click to claim: tinyurl.com/cb500. Offer ends tonight.")),
    # ---- legitimate-looking ----
    ("bank_debit_alert", ["safe"], lambda n: sms(n, "VM-MYBANK",
        "Rs 450.00 debited from A/c XX1234 on 10-Oct via UPI to ABC STORE. Ref 6128XXXX. If not you, call the number on the back of your card. Never share OTP.")),
    ("recharge_ok", ["safe"], lambda n: sms(n, "JD-RECHRG",
        "Recharge of \u20b9299 successful for 98XXXXXX21. Validity 28 days. Thank you for choosing us.")),
    ("electricity_bill", ["safe", "careful"], lambda n: doc(n, "Electricity Bill", [
        ("Consumer No.", "XXXX 4471"), ("Billing period", "Sep 2026"), ("Units used", "212"),
        ("Amount due", "\u20b91,846"), ("Due date", "20-Oct-2026")],
        "Pay at the official app, the branch counter or an authorised centre. Do not share OTP with anyone.")),
    ("delivery_otp", ["safe", "careful"], lambda n: sms(n, "AM-DELIVR",
        "Your OTP for order delivery is 482913. Share it only with the delivery partner at your door. Do not share it on a call.")),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    expected = []
    for name, accept, draw in SAMPLES:
        draw(name)
        expected.append({"file": f"{name}.png", "accept": accept})
    with open(ROOT / "eval" / "expected.json", "w", encoding="utf-8") as fh:
        json.dump(expected, fh, indent=2)
        fh.write("\n")
    print(f"Wrote {len(expected)} samples to {OUT}")


if __name__ == "__main__":
    main()
