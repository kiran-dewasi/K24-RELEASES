from PIL import Image, ImageDraw, ImageFont
import os

def create_invoice_image(filename="test_invoice.jpg", num_items=10):
    # Create white background - adjust height based on items
    height = 400 + (num_items * 30) + 100
    img = Image.new('RGB', (800, height), color='white')
    d = ImageDraw.Draw(img)
    
    # Try to load a font, fallback to default
    try:
        font_header = ImageFont.truetype("arial.ttf", 24)
        font_bold = ImageFont.truetype("arial.ttf", 16)
        font_text = ImageFont.truetype("arial.ttf", 14)
    except IOError:
        font_header = ImageFont.load_default()
        font_bold = ImageFont.load_default()
        font_text = ImageFont.load_default()

    # Header
    d.text((50, 50), "INVOICE", fill="black", font=font_header)
    d.text((50, 90), "Invoice #: INV-2024-001", fill="black", font=font_text)
    d.text((50, 110), "Date: 2024-01-27", fill="black", font=font_text)
    d.text((50, 130), "Bill To: John Doe Enterprises", fill="black", font=font_text)

    # Table Header
    y = 180
    d.text((50, y), "Item Description", fill="black", font=font_bold)
    d.text((350, y), "Qty", fill="black", font=font_bold)
    d.text((450, y), "Rate", fill="black", font=font_bold)
    d.text((550, y), "Amount", fill="black", font=font_bold)
    
    y += 30
    d.line((50, y, 750, y), fill="black", width=2)
    y += 20

    # Items
    base_items = [
        ("Wireless Mouse Gen2", 500), ("Mechanical Keyboard", 3500), ("USB-C Cable 2m", 200),
        ("Monitor Stand Adjustable", 1200), ("Webcam HD 1080p", 2500), ("Laptop Sleeve 15 inch", 400),
        ("HDMI Cable 3m", 150), ("Bluetooth Headset", 1800), ("Screen Cleaning Kit", 50),
        ("Ergonomic Mouse Pad", 100), ("External SSD 1TB", 8000), ("USB Hub 4-Port", 600),
        ("Laptop Cooling Pad", 1500), ("Wireless Charger", 900), ("Cable Organizer Clips", 200)
    ]
    
    total = 0
    for i in range(num_items):
        idx = i % len(base_items)
        name, base_rate = base_items[idx]
        # Vary qty slightly
        qty = (i % 5) + 1
        rate = base_rate
        amt = qty * rate
        
        # Add index to name to make unique if repeating
        if i >= len(base_items):
            name = f"{name} (v{i})"
            
        d.text((50, y), name, fill="black", font=font_text)
        d.text((350, y), str(qty), fill="black", font=font_text)
        d.text((450, y), f"{rate:.2f}", fill="black", font=font_text)
        d.text((550, y), f"{amt:.2f}", fill="black", font=font_text)
        total += amt
        y += 30

    d.line((50, y, 750, y), fill="black", width=2)
    y += 20
    
    # Total
    d.text((450, y), "Total:", fill="black", font=font_bold)
    d.text((550, y), f"{total:.2f}", fill="black", font=font_bold)

    img.save(filename)
    print(f"Created {filename} with {num_items} items")

if __name__ == "__main__":
    create_invoice_image("test_invoice_8items.jpg", 8)
    create_invoice_image("test_invoice_12items.jpg", 12)
    create_invoice_image("test_invoice_15items.jpg", 15)
