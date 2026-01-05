from decimal import Decimal, ROUND_HALF_UP
from num2words import num2words

def arabic_money_in_words(amount):
    try:
        if amount in (None, ""):
            return ""

        amount = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        main_val = int(amount)
        fractional_val = int((amount - main_val) * 100)

        main_words = num2words(main_val, lang="ar")

        if fractional_val > 0:
            fraction_words = num2words(fractional_val, lang="ar")
            return f"{main_words} ريال سعودي و {fraction_words} هللة فقط"

        return f"{main_words} ريال سعودي فقط"

    except Exception:
        return ""
