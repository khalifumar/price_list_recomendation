import csv
import glob
import os
import re
import pandas as pd
from rapidfuzz import fuzz, process

class PricingEngine:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.custom_items = []
        self.rtu_items = []
        self.all_items = []
        self._load_all_data()

    @staticmethod
    def _parse_number(val) -> float:
        """Helper untuk membersihkan format angka, rupiah, koma, dan spasi ke float."""
        if pd.isna(val):
            return 0.0
        s = str(val).strip().replace('Rp', '').replace(' ', '').replace(',', '')
        try:
            return float(s)
        except Exception:
            return 0.0

    @staticmethod
    def _find_header_line(file_path: str) -> int:
        """Mendeteksi baris header secara dinamis dengan mencari baris berkolom utama."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            for row_idx, row in enumerate(reader):
                low_cells = [c.strip().lower() for c in row if c.strip()]
                # Abaikan baris penanda panduan format seperti [R-TP]-[Product]...
                if any(c.startswith('[') for c in low_cells):
                    continue
                has_product = any(c == 'product' or 'product' in c for c in low_cells)
                has_specs = any(any(k in c for k in ['material', 'size', 'cogs', 'brand']) for c in low_cells)
                if has_product and has_specs:
                    return row_idx
                if row_idx > 200:
                    break
        return 0

    @staticmethod
    def _get_val(row: dict, candidates: list, default: str = "-"):
        for c in candidates:
            if c in row and pd.notna(row[c]) and str(row[c]).strip() != '':
                return str(row[c]).strip()
        return default

    def _load_all_data(self):
        """Membaca semua file katalog CSV di data/custom dan data/rtu."""
        self.custom_items.clear()
        self.rtu_items.clear()

        # 1. Baca semua file Custom
        custom_files = glob.glob(os.path.join(self.data_dir, "custom", "*.csv"))
        for f in custom_files:
            file_subcat = (
                os.path.basename(f)
                .replace('price_list_custom_', '')
                .replace('_2026.csv', '')
                .replace('_', ' ')
                .title()
            )
            h_idx = self._find_header_line(f)
            try:
                df = pd.read_csv(f, header=h_idx)
                df.columns = [str(c).strip() for c in df.columns]
                pcols = [c for c in df.columns if 'product' in c.lower()]
                if not pcols:
                    continue
                pcol = pcols[0]

                df_valid = df[
                    df[pcol].notna() & 
                    (df[pcol].astype(str).str.strip() != '') & 
                    (~df[pcol].astype(str).str.startswith('#'))
                ].copy()

                for _, r in df_valid.iterrows():
                    r_dict = r.to_dict()
                    prod_name = str(r_dict.get(pcol, "-")).strip()
                    brand = self._get_val(r_dict, ['Brand', 'Code'])
                    material = self._get_val(r_dict, ['Material (gsm)', 'Material'])
                    size = self._get_val(r_dict, ['Size Close', 'Size (P x L x T)', 'Size'])
                    size_open = self._get_val(r_dict, ['Size Open'])
                    color = self._get_val(r_dict, ['Color'])
                    detail_color = self._get_val(r_dict, ['Detail Color'])
                    finishing = self._get_val(r_dict, ['Finishing'])
                    qty = self._get_val(r_dict, ['Qty', 'Qty/Ctn', 'MOQ'])
                    pola = self._get_val(r_dict, ['Pola'])

                    # Cari COGS vendor terendah
                    cogs = 0.0
                    for c_cand in ['COGS', 'Price', 'COGS (Excl).2', 'COGS (Excl).1', 'COGS (Excl)']:
                        if c_cand in r_dict and self._parse_number(r_dict[c_cand]) > 0:
                            cogs = self._parse_number(r_dict[c_cand])
                            break

                    price_list = 0.0
                    for p_cand in ['Price List', 'Price List.1', 'Price List.2']:
                        if p_cand in r_dict and self._parse_number(r_dict[p_cand]) > 0:
                            price_list = self._parse_number(r_dict[p_cand])
                            break

                    specs = {
                        "Kategori Katalog": "Custom",
                        "Sub-Kategori": file_subcat,
                        "Brand": brand,
                        "Produk": prod_name,
                        "Bahan (Material)": material,
                        "Ukuran Jadi (Close)": size,
                        "Ukuran Terbuka (Open)": size_open,
                        "Warna / Cetak": color,
                        "Detail Warna": detail_color,
                        "Finishing": finishing,
                        "Pola": pola,
                        "Qty Produksi / MOQ": qty
                    }

                    item = {
                        "type": "Custom",
                        "subcat": file_subcat,
                        "product": prod_name,
                        "brand": brand,
                        "material": material,
                        "size": size,
                        "base_cogs": cogs,
                        "price_list": price_list,
                        "specs": specs,
                        "search_str": f"{file_subcat} {brand} {prod_name} {material} {size} {finishing}".lower(),
                        "raw": r_dict
                    }
                    self.custom_items.append(item)
            except Exception as e:
                print(f"Error loading custom file {f}: {e}")

        # 2. Baca semua file RTU
        rtu_files = glob.glob(os.path.join(self.data_dir, "rtu", "*.csv"))
        for f in rtu_files:
            file_subcat = (
                os.path.basename(f)
                .replace('price_list_rtu_', '')
                .replace('_2026.csv', '')
                .replace('_', ' ')
                .title()
            )
            h_idx = self._find_header_line(f)
            try:
                df = pd.read_csv(f, header=h_idx)
                df.columns = [str(c).strip() for c in df.columns]
                pcols = [c for c in df.columns if 'product' in c.lower()]
                if not pcols:
                    continue
                pcol = pcols[0]

                df_valid = df[
                    df[pcol].notna() & 
                    (df[pcol].astype(str).str.strip() != '') & 
                    (~df[pcol].astype(str).str.startswith('[')) & 
                    (~df[pcol].astype(str).str.startswith('#'))
                ].copy()

                for _, r in df_valid.iterrows():
                    r_dict = r.to_dict()
                    prod_name = str(r_dict.get(pcol, "-")).strip()
                    if prod_name.lower() in ('product', 'polos', 'cogs'):
                        continue

                    code = self._get_val(r_dict, ['Code'])
                    material = self._get_val(r_dict, ['Material (gsm)', 'Material'])
                    size = self._get_val(r_dict, ['Size (P x L x T)', 'Size'])
                    color = self._get_val(r_dict, ['Color'])
                    category = self._get_val(r_dict, ['Category'], default="RTU")
                    moq = self._get_val(r_dict, ['MOQ'])
                    qty_ctn = self._get_val(r_dict, ['Qty/Ctn'])
                    remarks = self._get_val(r_dict, ['Remarks'])

                    cogs = 0.0
                    for c_cand in ['COGS (Excl)', 'COGS', 'Price Real', 'Price']:
                        if c_cand in r_dict and self._parse_number(r_dict[c_cand]) > 0:
                            cogs = self._parse_number(r_dict[c_cand])
                            break

                    price_list = 0.0
                    for p_cand in ['Price List', 'Price List.1', 'Price List.2']:
                        if p_cand in r_dict and self._parse_number(r_dict[p_cand]) > 0:
                            price_list = self._parse_number(r_dict[p_cand])
                            break

                    cogs_sablon = (
                        self._parse_number(r_dict.get('COGS Sablon 1W1S', 0)) or 
                        self._parse_number(r_dict.get('COGS 1S 1W', 0))
                    )

                    specs = {
                        "Kategori Katalog": "RTU",
                        "Sub-Kategori": file_subcat,
                        "Kode": code,
                        "Produk": prod_name,
                        "Bahan (Material)": material,
                        "Ukuran (Dimensi)": size,
                        "Warna": color,
                        "MOQ": moq,
                        "Qty per Karton": qty_ctn,
                        "Catatan (Remarks)": remarks,
                        "COGS Sablon 1W1S": f"Rp {cogs_sablon:,.0f}" if cogs_sablon > 0 else "-"
                    }

                    item = {
                        "type": "RTU",
                        "subcat": file_subcat,
                        "product": prod_name,
                        "brand": code,
                        "material": material,
                        "size": size,
                        "base_cogs": cogs,
                        "price_list": price_list,
                        "specs": specs,
                        "search_str": f"{file_subcat} {code} {prod_name} {material} {size}".lower(),
                        "raw": r_dict
                    }
                    self.rtu_items.append(item)
            except Exception as e:
                print(f"Error loading rtu file {f}: {e}")

        self.all_items = self.custom_items + self.rtu_items

    def search(self, query: str, category: str = "Semua", subcat: str = "Semua", limit: int = 5):
        """
        Pencarian cerdas terpadu di seluruh katalog Custom dan RTU.
        category: 'Semua', 'Custom', 'RTU'
        subcat: 'Semua' atau nama subkategori spesifik (misal: 'Box', 'Paper Bag', 'Food Wrap')
        """
        stopwords = {
            'spesifikasi', 'spek', 'detail', 'produk', 'product', 'bahan', 'ukuran', 
            'dari', 'apa', 'tolong', 'cari', 'tentang', 'info', 'ada', 'harga', 
            'berapa', 'untuk', 'tipe', 'bagaimana', 'katalog', 'bisa', 'minta', 'buat', 'rekomendasi'
        }
        words = [w for w in query.lower().split() if w not in stopwords]
        clean_query = ' '.join(words) if words else query.lower()

        # Filter target items berdasarkan category dan subcat
        target_list = []
        if category in ("Semua", "Custom"):
            target_list.extend(self.custom_items)
        if category in ("Semua", "RTU"):
            target_list.extend(self.rtu_items)

        if subcat != "Semua":
            target_list = [item for item in target_list if item['subcat'].lower() == subcat.lower()]

        q_clean = clean_query.lower()
        q_norm = q_clean.replace(' ', '').replace('x', ' ')

        candidates = []
        for item in target_list:
            prod = str(item['product']).lower()
            brand = str(item['brand']).lower()
            mat = str(item['material']).lower()
            sz = str(item['size']).lower()
            subc = str(item['subcat']).lower()

            s_prod = max(
                fuzz.token_set_ratio(q_clean, prod),
                fuzz.token_set_ratio(q_clean, f"{brand} {prod}"),
                fuzz.token_set_ratio(q_clean, f"{subc} {prod}")
            )
            s_mat = fuzz.token_set_ratio(q_clean, mat) if mat != '-' else 0

            sz_norm = sz.replace(' ', '').replace('x', ' ')
            s_sz = fuzz.partial_ratio(sz_norm, q_norm) if sz != '-' else 0

            s_full_part = fuzz.partial_ratio(q_clean, item['search_str'])
            s_full_tok = fuzz.token_set_ratio(q_clean, item['search_str'])

            score = (s_prod * 0.4) + (s_mat * 0.2) + (s_sz * 0.2) + (max(s_full_part, s_full_tok) * 0.2)

            if score >= 45:
                candidates.append((score, {**item, "score": score}))

        candidates.sort(key=lambda x: x[0], reverse=True)
        return [c[1] for c in candidates[:limit]]

    def get_subcategories(self):
        """Mengembalikan daftar sub-kategori unik dari katalog."""
        subcats = set()
        for item in self.all_items:
            subcats.add(item['subcat'])
        return sorted(list(subcats))

    def calculate_price(self, cogs: float, target_margin_percent: float):
        """Menghitung harga jual dan profit berdasarkan target gross margin."""
        if cogs <= 0:
            return 0, 0
        if target_margin_percent >= 100:
            target_margin_percent = 99.0
        selling_price = cogs / (1 - (target_margin_percent / 100.0))
        profit = selling_price - cogs
        return round(selling_price), round(profit)