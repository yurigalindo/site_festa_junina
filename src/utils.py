import base64
import io
import qrcode

# --- Pix Helper Functions ---
def generate_pix_payload(pix_key, merchant_name, merchant_city, amount_str, description, txid="***"):
    """
    Generates a static Pix BRCode payload.
    txid="***" for static QR codes that can be paid multiple times.
    For unique transactions, generate a unique txid.
    Amount is formatted as a string, e.g., "150.00"
    """
    payload_format_indicator = "000201"
    merchant_account_info = f"0014BR.GOV.BCB.PIX01{len(pix_key):02}{pix_key}"
    merchant_category_code = "52040000"
    transaction_currency = "5303986"
    transaction_amount = f"54{len(amount_str):02}{amount_str}"
    country_code = "5802BR"
    merchant_name_val = merchant_name[:25].upper()
    merchant_name_field = f"59{len(merchant_name_val):02}{merchant_name_val}"
    merchant_city_val = merchant_city[:15].upper()
    merchant_city_field = f"60{len(merchant_city_val):02}{merchant_city_val}"
    additional_data_field_txid = f"05{len(txid):02}{txid}"
    additional_data_field = f"62{len(additional_data_field_txid):02}{additional_data_field_txid}"

    payload_without_crc = (
        payload_format_indicator +
        "26" + str(len(merchant_account_info)).zfill(2) + merchant_account_info +
        merchant_category_code +
        transaction_currency +
        transaction_amount +
        country_code +
        merchant_name_field +
        merchant_city_field +
        additional_data_field
    )
    
    crc16 = calculate_crc16(payload_without_crc)
    return payload_without_crc + "6304" + crc16

def calculate_crc16(payload):
    """Calculates CRC16-CCITT for Pix payload."""
    crc = 0xFFFF
    polynomial = 0x1021
    for byte in payload.encode('utf-8'):
        crc ^= (byte << 8)
        for _ in range(8):
            if (crc & 0x8000):
                crc = (crc << 1) ^ polynomial
            else:
                crc = crc << 1
    return format(crc & 0xFFFF, '04X')

def generate_qr_code_base64(payload):
    """Generates a QR code from the payload and returns a base64 encoded image string."""
    img = qrcode.make(payload)
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str
# --- End Pix Helper Functions --- 