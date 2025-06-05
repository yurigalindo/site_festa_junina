import base64
import io
import qrcode
from pybrcode.pix import generate_simple_pix
import os
from dotenv import load_dotenv

load_dotenv()

# --- Pix Helper Functions ---
def generate_pix_payload(amount, names):
    pix_id = names.replace(" ", "").replace(",", "")
    if len(pix_id) > 25:
        pix_id = pix_id[:25]
    else:
        pix_id = pix_id
    pix_obj = generate_simple_pix(
        key=os.getenv('PIX_KEY'),
        fullname=os.getenv('MERCHANT_NAME'),
        city=os.getenv('MERCHANT_CITY'),
        value=15*amount,
        description=names,
        pix_id=pix_id
    )
    payload_string = str(pix_obj) # This is the "Copia e Cola" text
    payload_image_b64 = pix_obj.toBase64() # This is the QR code image in base64
    return payload_string, payload_image_b64
