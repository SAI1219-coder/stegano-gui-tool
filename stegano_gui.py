import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import unicodedata, re, os

END_MARK = "1111111111111110"  # 16bit 終端マーカー

# ---------- サニタイズ & 安全処理 ----------
def sanitize_message(user_text: str, ascii_only: bool = True, max_bytes: int = 10_000) -> bytes:
    """入力テキストを無害化し、UTF-8バイト列を返す"""
    norm = unicodedata.normalize("NFKC", user_text)

    cleaned = []
    for ch in norm:
        cat = unicodedata.category(ch)
        if ch in ("\n", "\t"):
            cleaned.append(ch)
        elif cat in ("Cc", "Cf"):
            continue
        else:
            cleaned.append(ch)
    norm = "".join(cleaned)

    if ascii_only:
        norm = re.sub(r"[^\x09\x0A\x20-\x7E]", "", norm)

    data = norm.encode("utf-8")
    if len(data) > max_bytes:
        raise ValueError(f"メッセージが長すぎます（{len(data)} bytes > {max_bytes} bytes）。")
    return data

def load_safe_png(path: str) -> Image.Image:
    """PNG画像を安全に読み込む"""
    if not path.lower().endswith(".png"):
        raise ValueError("PNG画像のみ対応です。")
    with Image.open(path) as im:
        im.verify()
    img = Image.open(path)
    return img.convert("RGB")

# ---------- 埋め込み処理 ----------
def encode_message(image_path: str, output_path: str, user_text: str):
    img = load_safe_png(image_path)
    pixels = img.load()

    msg_bytes = sanitize_message(user_text, ascii_only=True, max_bytes=10_000)

    needed_bits = len(msg_bytes) * 8 + len(END_MARK)
    capacity_bits = img.width * img.height
    if needed_bits > capacity_bits:
        raise ValueError(
            f"メッセージ容量オーバー：必要 {needed_bits} bit / 可能 {capacity_bits} bit。"
        )

    bin_msg = "".join(f"{b:08b}" for b in msg_bytes) + END_MARK

    i = 0
    for y in range(img.height):
        for x in range(img.width):
            if i >= len(bin_msg): break
            r, g, b = pixels[x, y]
            r = (r & ~1) | int(bin_msg[i])
            pixels[x, y] = (r, g, b)
            i += 1
        if i >= len(bin_msg): break

    root, _ = os.path.splitext(output_path)
    safe_out = root + ".png"
    img.save(safe_out, format="PNG")
    return safe_out

# ---------- 抽出処理 ----------
def decode_message(image_path: str) -> str:
    img = load_safe_png(image_path)
    pixels = img.load()

    bits = []
    for y in range(img.height):
        for x in range(img.width):
            r, g, b = pixels[x, y]
            bits.append("1" if (r & 1) else "0")

    bit_str = "".join(bits)
    end = bit_str.find(END_MARK)
    if end == -1:
        raise ValueError("終了マーカーが見つかりません（埋め込み無し/破損の可能性）。")
    bit_str = bit_str[:end]

    by = bytearray()
    for i in range(0, len(bit_str), 8):
        byte = bit_str[i:i+8]
        if len(byte) == 8:
            by.append(int(byte, 2))
    return by.decode("utf-8", errors="strict")

# ---------- GUI ----------
def select_image_for_encode():
    file_path = filedialog.askopenfilename(filetypes=[("PNG Images","*.png")])
    if not file_path: return
    msg = text_entry.get("1.0","end-1c")
    if not msg:
        messagebox.showerror("エラー", "メッセージを入力してください。")
        return
    output_path = filedialog.asksaveasfilename(defaultextension=".png")
    if not output_path: return
    try:
        out = encode_message(file_path, output_path, msg)
        messagebox.showinfo("完了", f"埋め込み完了！\n{out}")
    except Exception as e:
        messagebox.showerror("エラー", str(e))

def select_image_for_decode():
    file_path = filedialog.askopenfilename(filetypes=[("PNG Images","*.png")])
    if not file_path: return
    try:
        msg = decode_message(file_path)
        messagebox.showinfo("抽出結果", msg)
    except Exception as e:
        messagebox.showerror("エラー", str(e))

root = tk.Tk()
root.title("シンプル ステガノグラフィ ツール")

tk.Label(root, text="埋め込みたいメッセージ:").pack()
text_entry = tk.Text(root, height=5, width=50)
text_entry.pack()

tk.Button(root, text="画像を選んで埋め込む", command=select_image_for_encode).pack(pady=5)
tk.Button(root, text="画像から抽出する", command=select_image_for_decode).pack(pady=5)

root.mainloop()
